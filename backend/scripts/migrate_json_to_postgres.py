"""
scripts/migrate_json_to_postgres.py
One-off import of the legacy JSON file store (backend/data/arsenal.json)
into PostgreSQL. Safe to re-run: candidates already present (by id) are
skipped. Run once, after `alembic upgrade head`, when cutting a JSON-store
deployment over to Postgres:

    cd backend
    python -m scripts.migrate_json_to_postgres
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from config import settings
from database import session_scope
from models import AuditCategoryScore, AuditFinding, AuditResult, Candidate, CandidateSkill, ResumeUpload

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger("migrate_json_to_postgres")

ARSENAL_JSON = Path(__file__).resolve().parent.parent / "data" / "arsenal.json"


def _findings_from_record(rec_audit: dict) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for i, f in enumerate(rec_audit.get("criticalFixes", [])):
        findings.append(AuditFinding(
            severity="critical", category=f.get("category", ""), title=f.get("title", ""),
            description=f.get("description", ""), why_it_matters=f.get("whyItMatters", ""),
            location=f.get("location", ""),
            original_text=f.get("originalText"), suggested_fix=f.get("suggestedFix"),
            sort_order=i,
        ))
    for i, f in enumerate(rec_audit.get("importantTweaks", [])):
        findings.append(AuditFinding(
            severity="important", category=f.get("category", ""), title=f.get("title", ""),
            description=f.get("description", ""), why_it_matters=f.get("whyItMatters", ""),
            action=f.get("action", ""),
            original_text=f.get("originalText"), suggested_fix=f.get("suggestedFix"),
            sort_order=i,
        ))
    return findings


async def import_record(session, rec: dict) -> bool:
    candidate_id = uuid.UUID(rec["id"])
    existing = await session.execute(select(Candidate.id).where(Candidate.id == candidate_id))
    if existing.scalar_one_or_none() is not None:
        logger.info("Skipping %s (already imported)", candidate_id)
        return False

    profile = rec.get("profile", {})
    audit = rec.get("auditResult", {})
    artifact = rec.get("resumeArtifact", {})
    created_at = datetime.fromisoformat(rec["createdAt"].replace("Z", "+00:00"))

    candidate = Candidate(
        id=candidate_id,
        full_name=profile.get("fullName", ""),
        email=profile.get("email", ""),
        phone=profile.get("phone", ""),
        location=profile.get("location", ""),
        college=profile.get("college", ""),
        degree=profile.get("degree", ""),
        branch=profile.get("branch", ""),
        grad_year=profile.get("gradYear", ""),
        cgpa=profile.get("cgpa", ""),
        target_role=profile.get("targetRole", ""),
        experience_level=profile.get("experienceLevel", ""),
        linkedin_url=(profile.get("socials") or {}).get("linkedin", ""),
        github_url=(profile.get("socials") or {}).get("github", ""),
        created_at=created_at,
        updated_at=created_at,
    )
    candidate.skills = [CandidateSkill(skill=s) for s in profile.get("skills", []) if s]

    storage_path = settings.upload_dir_abs + f"/{candidate_id}.pdf"
    if Path(storage_path).is_file():
        candidate.resume_upload = ResumeUpload(
            file_name=artifact.get("fileName", "resume.pdf"),
            storage_path=storage_path,
            raw_extracted_text=artifact.get("rawExtractedText", ""),
            uploaded_at=created_at,
        )
    else:
        logger.warning(
            "No resume file on disk for %s at %s — importing candidate without a resume_upload row",
            candidate_id, storage_path,
        )

    audit_result = AuditResult(
        candidate_id=candidate_id,
        overall_score=audit.get("overallScore", 0),
        recruiter_7sec_scan=audit.get("recruiter7SecScan", "FAIL"),
        ats_risk_level=audit.get("atsRiskLevel", "HIGH"),
        keyword_gaps=audit.get("keywordGaps", {"found": [], "missingHighPriority": []}),
        passed_checks=audit.get("passedChecks", []),
        bullet_count=audit.get("meta", {}).get("bulletCount", 0),
        page_count=audit.get("meta", {}).get("pageCount", 0),
        file_name=audit.get("meta", {}).get("fileName", ""),
        created_at=created_at,
    )
    audit_result.category_scores = [
        AuditCategoryScore(category=cat, score=score)
        for cat, score in audit.get("categoryScores", {}).items()
    ]
    audit_result.findings = _findings_from_record(audit)
    candidate.audit_results = [audit_result]

    session.add(candidate)
    logger.info("Imported %s (%s)", candidate_id, profile.get("fullName") or "(unnamed)")
    return True


async def main() -> None:
    if not ARSENAL_JSON.is_file():
        logger.info("No legacy JSON store found at %s — nothing to import.", ARSENAL_JSON)
        return

    records = json.loads(ARSENAL_JSON.read_text(encoding="utf-8"))
    logger.info("Found %d record(s) in %s", len(records), ARSENAL_JSON)

    imported = 0
    async with session_scope() as session:
        for rec in records:
            if await import_record(session, rec):
                imported += 1

    logger.info("Done. Imported %d new record(s), %d already present.", imported, len(records) - imported)


if __name__ == "__main__":
    asyncio.run(main())
