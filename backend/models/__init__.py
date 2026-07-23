"""
models/__init__.py
Importing this module registers every ORM model on database.base.Base's
metadata — Alembic's env.py imports this module (not the individual model
files) so `--autogenerate` sees the full schema.
"""
from models.audit_category_score import AuditCategoryScore
from models.audit_finding import AuditFinding
from models.audit_result import AuditResult
from models.candidate import Candidate
from models.candidate_skill import CandidateSkill
from models.jd_match_analysis import JdMatchAnalysis
from models.resume_upload import ResumeUpload

__all__ = [
    "Candidate",
    "CandidateSkill",
    "ResumeUpload",
    "JdMatchAnalysis",
    "AuditResult",
    "AuditCategoryScore",
    "AuditFinding",
]
