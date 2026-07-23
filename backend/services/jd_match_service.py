"""Persistence workflow for resume-vs-JD analyses."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional
import re

from sqlalchemy.ext.asyncio import AsyncSession

from pdf_extract import ExtractedResume
from repositories.jd_match_repository import JdMatchRepository
from jd_match_engine import DEGREE_RE, EMAIL_RE, GITHUB_RE, LINKEDIN_RE, PHONE_RE


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _infer_optional_profile(raw_extracted_text: str) -> dict:
    text = raw_extracted_text or ""
    email_m = EMAIL_RE.search(text)
    phone_m = PHONE_RE.search(text)
    linkedin_m = LINKEDIN_RE.search(text)
    github_m = GITHUB_RE.search(text)
    degree_m = DEGREE_RE.search(text)
    lower = text.lower()
    skills_zone = ""
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


class JdMatchService:
    def __init__(self, session: AsyncSession, storage_dir: str):
        self.session = session
        self.storage_dir = storage_dir
        self.repo = JdMatchRepository(session)

    def _write_pdf(self, analysis_id: uuid.UUID, suffix: str, file_bytes: bytes) -> str:
        os.makedirs(self.storage_dir, exist_ok=True)
        storage_path = os.path.join(self.storage_dir, f"{analysis_id}_{suffix}.pdf")
        with open(storage_path, "wb") as handle:
            handle.write(file_bytes)
        return storage_path

    async def save_analysis(
        self,
        *,
        resume_bytes: bytes,
        resume_file_name: str,
        resume_extracted: ExtractedResume,
        jd_bytes: bytes,
        jd_file_name: str,
        jd_extracted: ExtractedResume,
        analysis: dict,
    ) -> uuid.UUID:
        analysis_id = uuid.uuid4()
        resume_storage_path = self._write_pdf(analysis_id, "resume", resume_bytes)
        jd_storage_path = self._write_pdf(analysis_id, "jd", jd_bytes)

        await self.repo.create(
            analysis=analysis,
            storage={
                "resumeFileName": resume_file_name,
                "jdFileName": jd_file_name,
                "resumeStoragePath": resume_storage_path,
                "jdStoragePath": jd_storage_path,
                "resumeRawExtractedText": resume_extracted.raw_text,
                "jdRawExtractedText": jd_extracted.raw_text,
            },
        )
        return analysis_id

    async def list_summaries(self) -> list[dict]:
        analyses = await self.repo.list_summaries()
        summaries = []
        for analysis in analyses:
            payload = analysis.analysis_json or {}
            summaries.append({
                "id": str(analysis.id),
                "createdAt": _iso_z(analysis.created_at),
                "resumeFileName": analysis.resume_file_name,
                "jdFileName": analysis.jd_file_name,
                "overallMatchScore": analysis.overall_match_score,
                "resumeAtsScore": analysis.resume_ats_score,
                "finalRecommendation": payload.get("finalRecommendation", "Weak Match"),
            })
        return summaries

    async def get_detail(self, analysis_id: uuid.UUID) -> Optional[dict]:
        analysis = await self.repo.get_detail(analysis_id)
        if analysis is None:
            return None
        payload = analysis.analysis_json or {}
        optional_profile = payload.get("optionalProfile") or {}
        inferred = _infer_optional_profile(analysis.resume_raw_extracted_text)
        profile_name = payload.get("candidateName") or "(unnamed)"
        skills = optional_profile.get("skills") or inferred["skills"]
        return {
            "id": str(analysis.id),
            "createdAt": _iso_z(analysis.created_at),
            "profile": {
                "fullName": profile_name,
                "email": optional_profile.get("email") or inferred["email"] or None,
                "phone": optional_profile.get("phone") or inferred["phone"] or None,
                "location": None,
                "college": None,
                "degree": optional_profile.get("degree") or inferred["degree"] or None,
                "branch": None,
                "gradYear": None,
                "cgpa": None,
                "skills": skills,
                "socials": {
                    "linkedin": optional_profile.get("linkedin") or inferred["linkedin"] or None,
                    "github": optional_profile.get("github") or inferred["github"] or None,
                },
            },
            "resumeArtifact": {
                "fileName": analysis.resume_file_name,
                "fileUrl": f"/api/admin/jd-match-resume/{analysis.id}",
                "storagePath": analysis.resume_storage_path,
                "rawExtractedText": analysis.resume_raw_extracted_text,
            },
            "jdArtifact": {
                "fileName": analysis.jd_file_name,
                "fileUrl": f"/api/admin/jd-match-jd/{analysis.id}",
                "storagePath": analysis.jd_storage_path,
                "rawExtractedText": analysis.jd_raw_extracted_text,
            },
            "analysis": payload,
            "scores": {
                "overallMatchScore": analysis.overall_match_score,
                "resumeAtsScore": analysis.resume_ats_score,
                "keywordMatchScore": analysis.keyword_match_score,
                "skillsMatchScore": analysis.skills_match_score,
                "educationMatchScore": analysis.education_match_score,
                "experienceMatchScore": analysis.experience_match_score,
                "certificationMatchScore": analysis.certification_match_score,
                "responsibilitiesMatchScore": analysis.responsibilities_match_score,
                "projectsMatchScore": analysis.projects_match_score,
            },
        }