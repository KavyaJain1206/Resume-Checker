"""
repositories/candidate_repository.py
Data access for the candidate aggregate (candidate + skills + resume upload
+ audit results + their category scores/findings). No business logic here
— that lives in services/candidate_service.py. This is intentionally
create/read only: nothing in the app updates or deletes a candidate record
today, so this repository doesn't manufacture unused update/delete methods.
"""
from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import AuditCategoryScore, AuditFinding, AuditResult, Candidate, CandidateSkill, ResumeUpload


class CandidateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, *, candidate_id: uuid.UUID, profile: dict, skills: Sequence[str], resume: dict, audit: dict
    ) -> Candidate:
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
            target_role=profile["targetRole"],
            experience_level=profile["experienceLevel"],
            linkedin_url=profile.get("linkedin", ""),
            github_url=profile.get("github", ""),
        )
        candidate.skills = [CandidateSkill(skill=s) for s in skills if s]
        candidate.resume_upload = ResumeUpload(
            file_name=resume["fileName"],
            storage_path=resume["storagePath"],
            raw_extracted_text=resume.get("rawExtractedText", ""),
        )

        audit_result = AuditResult(
            overall_score=audit["overallScore"],
            recruiter_7sec_scan=audit["recruiter7SecScan"],
            ats_risk_level=audit["atsRiskLevel"],
            keyword_gaps=audit["keywordGaps"],
            passed_checks=audit["passedChecks"],
            bullet_count=audit["meta"]["bulletCount"],
            page_count=audit["meta"]["pageCount"],
            file_name=audit["meta"]["fileName"],
        )
        audit_result.category_scores = [
            AuditCategoryScore(category=cat, score=score)
            for cat, score in audit["categoryScores"].items()
        ]

        findings: list[AuditFinding] = []
        for i, f in enumerate(audit["criticalFixes"]):
            findings.append(AuditFinding(
                severity="critical", category=f["category"], title=f["title"],
                description=f.get("description", ""), why_it_matters=f.get("whyItMatters", ""),
                location=f.get("location", ""),
                original_text=f.get("originalText"), suggested_fix=f.get("suggestedFix"),
                sort_order=i,
            ))
        for i, f in enumerate(audit["importantTweaks"]):
            findings.append(AuditFinding(
                severity="important", category=f["category"], title=f["title"],
                description=f.get("description", ""), why_it_matters=f.get("whyItMatters", ""),
                action=f.get("action", ""),
                original_text=f.get("originalText"), suggested_fix=f.get("suggestedFix"),
                sort_order=i,
            ))
        audit_result.findings = findings
        candidate.audit_results = [audit_result]

        self.session.add(candidate)
        await self.session.flush()
        return candidate

    async def list_summaries(self) -> list[Candidate]:
        """Candidates ordered newest-first, with just enough eager-loaded to
        build the directory table (avoids N+1 on audit_results)."""
        stmt = (
            select(Candidate)
            .options(selectinload(Candidate.audit_results))
            .order_by(Candidate.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_detail(self, candidate_id: uuid.UUID) -> Optional[Candidate]:
        stmt = (
            select(Candidate)
            .where(Candidate.id == candidate_id)
            .options(
                selectinload(Candidate.skills),
                selectinload(Candidate.resume_upload),
                selectinload(Candidate.audit_results).selectinload(AuditResult.category_scores),
                selectinload(Candidate.audit_results).selectinload(AuditResult.findings),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_resume_upload(self, candidate_id: uuid.UUID) -> Optional[ResumeUpload]:
        stmt = select(ResumeUpload).where(ResumeUpload.candidate_id == candidate_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
