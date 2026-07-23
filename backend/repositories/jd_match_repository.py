"""Data access for persisted resume-vs-JD analyses."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import JdMatchAnalysis


class JdMatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, *, analysis: dict, storage: dict) -> JdMatchAnalysis:
        item = JdMatchAnalysis(
            resume_file_name=storage["resumeFileName"],
            jd_file_name=storage["jdFileName"],
            resume_storage_path=storage["resumeStoragePath"],
            jd_storage_path=storage["jdStoragePath"],
            resume_raw_extracted_text=storage.get("resumeRawExtractedText", ""),
            jd_raw_extracted_text=storage.get("jdRawExtractedText", ""),
            overall_match_score=analysis["overallMatchScore"],
            resume_ats_score=analysis["resumeAtsScore"],
            keyword_match_score=analysis["categoryScores"]["keywordMatch"],
            skills_match_score=analysis["categoryScores"]["skillsMatch"],
            education_match_score=analysis["categoryScores"]["educationMatch"],
            experience_match_score=analysis["categoryScores"]["experienceMatch"],
            certification_match_score=analysis["categoryScores"]["certificationMatch"],
            responsibilities_match_score=analysis["categoryScores"]["responsibilitiesMatch"],
            projects_match_score=analysis["categoryScores"].get("projectsMatch"),
            analysis_json=analysis,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_detail(self, analysis_id: uuid.UUID) -> Optional[JdMatchAnalysis]:
        return await self.session.get(JdMatchAnalysis, analysis_id)

    async def list_summaries(self) -> list[JdMatchAnalysis]:
        stmt = select(JdMatchAnalysis).order_by(JdMatchAnalysis.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())