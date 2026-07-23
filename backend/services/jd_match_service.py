"""Persistence workflow for resume-vs-JD analyses."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from pdf_extract import ExtractedResume
from repositories.jd_match_repository import JdMatchRepository


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


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
        return {
            "id": str(analysis.id),
            "createdAt": _iso_z(analysis.created_at),
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