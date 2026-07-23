"""
services/candidate_service.py
Orchestrates the request-level workflow: extract PDF -> run the (unchanged)
rule engine -> persist via the repository -> reassemble the exact JSON
contract the frontend already expects. Routes in server.py should only ever
call into this service, never touch the repository or session directly.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional
import re

from sqlalchemy.ext.asyncio import AsyncSession

from models import AuditFinding, Candidate
from pdf_extract import ExtractedResume, extract_from_text, extract_resume
from repositories import CandidateRepository
from jd_match_engine import DEGREE_RE, EMAIL_RE, GITHUB_RE, LINKEDIN_RE, PHONE_RE, _extract_name as infer_resume_name
from rule_engine import audit as run_rule_engine


def parse_skills(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _display_name(full_name: str, raw_extracted_text: str = "") -> str:
    name = full_name.strip()
    if name:
        return name
    inferred = infer_resume_name(raw_extracted_text.splitlines()) if raw_extracted_text else None
    return inferred or "(unnamed)"


def _infer_optional_profile(raw_extracted_text: str) -> dict:
    text = raw_extracted_text or ""
    email_m = EMAIL_RE.search(text)
    phone_m = PHONE_RE.search(text)
    linkedin_m = LINKEDIN_RE.search(text)
    github_m = GITHUB_RE.search(text)
    degree_m = DEGREE_RE.search(text)
    skills_zone = ""
    lower = text.lower()
    if "skills" in lower:
        after_skills = lower.split("skills", 1)[1]
        skills_zone = after_skills.split("education", 1)[0].split("experience", 1)[0].split("projects", 1)[0]
    skills = [s.strip(" •-*\t\r\n") for s in re.split(r"[,/|;\n]", skills_zone) if s.strip(" •-*\t\r\n")]
    skills = [s for s in skills if 1 < len(s) <= 40]
    return {
        "email": email_m.group(0) if email_m else "",
        "phone": phone_m.group(0).strip() if phone_m else "",
        "linkedin": linkedin_m.group(0) if linkedin_m else "",
        "github": github_m.group(0) if github_m else "",
        "degree": degree_m.group(0).strip() if degree_m else "",
        "skills": skills[:12],
    }


def _finding_to_dict(f: AuditFinding) -> dict:
    item = {
        "id": str(f.id),
        "category": f.category,
        "title": f.title,
        "description": f.description,
        "whyItMatters": f.why_it_matters,
    }
    if f.severity == "critical":
        item["location"] = f.location
    else:
        item["action"] = f.action
    if f.original_text:
        item["originalText"] = f.original_text
    if f.suggested_fix:
        item["suggestedFix"] = f.suggested_fix
    return item


class CandidateService:
    def __init__(self, session: AsyncSession, upload_dir: str):
        self.session = session
        self.upload_dir = upload_dir
        self.repo = CandidateRepository(session)

    def extract_and_audit(
        self, *, file_bytes: bytes, file_name: str, target_role: str, experience_level: str,
    ) -> tuple[ExtractedResume, dict]:
        """PDF parsing + the pure rule engine. Raises on unparseable PDFs —
        callers should catch this separately from save_audit() so a parse
        failure (422) is never confused with a persistence failure (500)."""
        extracted = extract_resume(file_bytes)
        audit_result = run_rule_engine(extracted, target_role, experience_level, file_name)
        return extracted, audit_result

    async def save_audit(
        self, *, file_bytes: bytes, file_name: str, extracted: ExtractedResume, audit_result: dict, profile: dict,
    ) -> uuid.UUID:
        candidate_id = uuid.uuid4()
        os.makedirs(self.upload_dir, exist_ok=True)
        storage_path = os.path.join(self.upload_dir, f"{candidate_id}.pdf")
        with open(storage_path, "wb") as f:
            f.write(file_bytes)

        skills = parse_skills(profile.get("skills", ""))
        await self.repo.create(
            candidate_id=candidate_id,
            profile=profile,
            skills=skills,
            resume={"fileName": file_name, "storagePath": storage_path, "rawExtractedText": extracted.raw_text},
            audit=audit_result,
        )
        return candidate_id

    @staticmethod
    def run_text_audit(resume_text: str, target_role: str, experience_level: str) -> dict:
        extracted = extract_from_text(resume_text)
        return run_rule_engine(extracted, target_role, experience_level, "pasted.txt")

    async def list_summaries(self) -> list[dict]:
        candidates = await self.repo.list_summaries()
        summaries = []
        for c in candidates:
            latest = c.audit_results[0] if c.audit_results else None
            raw_text = c.resume_upload.raw_extracted_text if c.resume_upload else ""
            summaries.append({
                "id": str(c.id),
                "createdAt": _iso_z(c.created_at),
                "fullName": _display_name(c.full_name, raw_text),
                "email": c.email,
                "college": c.college,
                "targetRole": c.target_role,
                "experienceLevel": c.experience_level,
                "overallScore": latest.overall_score if latest else 0,
                "atsRiskLevel": latest.ats_risk_level if latest else "HIGH",
                "recruiter7SecScan": latest.recruiter_7sec_scan if latest else "FAIL",
            })
        return summaries

    async def get_detail(self, candidate_id: uuid.UUID) -> Optional[dict]:
        c: Optional[Candidate] = await self.repo.get_detail(candidate_id)
        if c is None:
            return None
        latest = c.audit_results[0] if c.audit_results else None
        findings = latest.findings if latest else []
        critical = [_finding_to_dict(f) for f in findings if f.severity == "critical"]
        important = [_finding_to_dict(f) for f in findings if f.severity == "important"]
        raw_text = c.resume_upload.raw_extracted_text if c.resume_upload else ""
        inferred = _infer_optional_profile(raw_text)
        return {
            "id": str(c.id),
            "createdAt": _iso_z(c.created_at),
            "profile": {
                "fullName": _display_name(c.full_name, raw_text),
                "email": c.email or inferred["email"],
                "phone": c.phone or inferred["phone"],
                "location": c.location,
                "college": c.college,
                "degree": c.degree or inferred["degree"],
                "branch": c.branch, "gradYear": c.grad_year, "cgpa": c.cgpa,
                "targetRole": c.target_role, "experienceLevel": c.experience_level,
                "skills": [s.skill for s in c.skills] or inferred["skills"],
                "socials": {
                    "linkedin": c.linkedin_url or inferred["linkedin"],
                    "github": c.github_url or inferred["github"],
                },
            },
            "resumeArtifact": {
                "fileName": c.resume_upload.file_name if c.resume_upload else "",
                "fileUrl": f"/api/admin/resume/{c.id}",
                "rawExtractedText": c.resume_upload.raw_extracted_text if c.resume_upload else "",
            },
            "auditResult": {
                "overallScore": latest.overall_score if latest else 0,
                "recruiter7SecScan": latest.recruiter_7sec_scan if latest else "FAIL",
                "atsRiskLevel": latest.ats_risk_level if latest else "HIGH",
                "categoryScores": {s.category: s.score for s in (latest.category_scores if latest else [])},
                "criticalFixes": critical,
                "importantTweaks": important,
                "keywordGaps": latest.keyword_gaps if latest else {"found": [], "missingHighPriority": []},
                "passedChecks": latest.passed_checks if latest else [],
                "meta": {
                    "targetRole": c.target_role, "experienceLevel": c.experience_level,
                    "bulletCount": latest.bullet_count if latest else 0,
                    "pageCount": latest.page_count if latest else 0,
                    "fileName": latest.file_name if latest else "",
                },
            },
        }

    async def get_resume_path(self, candidate_id: uuid.UUID) -> Optional[tuple[str, str]]:
        upload = await self.repo.get_resume_upload(candidate_id)
        if upload is None:
            return None
        return upload.storage_path, upload.file_name
