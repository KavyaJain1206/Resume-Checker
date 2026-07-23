"""
server.py  -  FastAPI backend for the Resume Playbook Diagnostic Engine.

Endpoints
  GET  /api/roles                       -> target roles + experience levels
  POST /api/audit                       -> multipart (resume PDF + profile) -> audit + saves to Arsenal
  POST /api/audit/text                  -> JSON (pasted text + profile) -> audit only
  POST /api/jd-match                    -> multipart (resume PDF + JD PDF) -> match report, stateless
  POST /api/admin/login                 -> placement-team login -> bearer token
  GET  /api/admin/candidates            -> Student Arsenal directory (auth)
  GET  /api/admin/candidates/{id}       -> single candidate record (auth)
  GET  /api/admin/resume/{id}           -> original resume PDF (auth)
  GET  /api/health                      -> liveness + DB connectivity

Persistence is PostgreSQL only (see database/, models/, repositories/,
services/) — routes here are thin: parse the request, delegate to
CandidateService, return its result. No SQL and no file I/O happens
directly in this module.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

import playbook as PB
from config import settings
from database import check_connection, get_session
from jd_match_engine import analyze as run_jd_match
from pdf_extract import extract_from_text, extract_resume
from rule_engine import audit as run_rule_engine
from services import CandidateService
from services.jd_match_service import JdMatchService

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("resume_playbook.server")

SECRET = settings.secret_key.encode()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if await check_connection():
        logger.info("Database connection OK (%s)", settings.environment)
    else:
        logger.error(
            "Database is unreachable at startup. Check DATABASE_URL and that "
            "migrations have been applied (`alembic upgrade head`)."
        )
    yield


app = FastAPI(title="Resume Playbook Diagnostic API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=512)


# --- token helpers (stateless HMAC, no external dep) ----------------------
def make_token(email: str) -> str:
    exp = int(time.time()) + settings.token_ttl_seconds
    payload = f"{email}|{exp}".encode()
    sig = hmac.new(SECRET, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"." + sig).decode()


def verify_token(token: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        payload, sig = raw.rsplit(b".", 1)
        expected = hmac.new(SECRET, payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return False
        _, exp = payload.decode().split("|")
        return int(exp) > time.time()
    except Exception:
        return False


async def require_admin(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    if not verify_token(authorization.split(" ", 1)[1]):
        raise HTTPException(401, "Invalid or expired session")
    return True


def get_candidate_service(session: AsyncSession = Depends(get_session)) -> CandidateService:
    return CandidateService(session, settings.upload_dir_abs)


def get_jd_match_service(session: AsyncSession = Depends(get_session)) -> JdMatchService:
    return JdMatchService(session, settings.upload_dir_abs)


# --- models ---------------------------------------------------------------
class LoginBody(BaseModel):
    email: str
    password: str


class TextAuditBody(BaseModel):
    resumeText: str
    targetRole: str
    experienceLevel: str
    fullName: Optional[str] = None
    email: Optional[str] = None


# --- routes ---------------------------------------------------------------
@app.get("/api/health")
async def health():
    db_ok = await check_connection()
    return {"ok": db_ok, "store": "postgresql", "roles": len(PB.ROLE_KEYWORDS)}


@app.get("/api/roles")
async def roles():
    return {
        "roles": list(PB.ROLE_KEYWORDS.keys()),
        "experienceLevels": PB.EXPERIENCE_LEVELS,
    }


@app.post("/api/audit")
async def run_audit(
    resumeFile: UploadFile = File(...),
    targetRole: str = Form(...),
    experienceLevel: str = Form(...),
    fullName: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    location: str = Form(""),
    college: str = Form(""),
    degree: str = Form(""),
    branch: str = Form(""),
    gradYear: str = Form(""),
    cgpa: str = Form(""),
    skills: str = Form(""),
    linkedin: str = Form(""),
    github: str = Form(""),
    service: CandidateService = Depends(get_candidate_service),
):
    data = await resumeFile.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "File exceeds 5MB limit")
    if not resumeFile.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF resumes are accepted")

    try:
        extracted, result = service.extract_and_audit(
            file_bytes=data,
            file_name=resumeFile.filename,
            target_role=targetRole,
            experience_level=experienceLevel,
        )
    except Exception as e:
        logger.warning("Could not parse PDF %s: %s", resumeFile.filename, e)
        raise HTTPException(422, f"Could not parse PDF: {e}")

    candidate_id = await service.save_audit(
        file_bytes=data,
        file_name=resumeFile.filename,
        extracted=extracted,
        audit_result=result,
        profile={
            "fullName": fullName, "email": email, "phone": phone,
            "location": location, "college": college, "degree": degree,
            "branch": branch, "gradYear": gradYear, "cgpa": cgpa,
            "targetRole": targetRole, "experienceLevel": experienceLevel,
            "skills": skills, "linkedin": linkedin, "github": github,
        },
    )
    return {"id": str(candidate_id), "auditResult": result}


@app.post("/api/audit/text")
async def run_audit_text(body: TextAuditBody):
    extracted = extract_from_text(body.resumeText)
    result = run_rule_engine(extracted, body.targetRole, body.experienceLevel, "pasted.txt")
    return {"auditResult": result}


@app.post("/api/jd-match")
async def jd_match(
    resumeFile: UploadFile = File(...),
    jdFile: UploadFile = File(...),
    service: JdMatchService = Depends(get_jd_match_service),
):
    resume_bytes = await resumeFile.read()
    jd_bytes = await jdFile.read()
    for label, data, upload in (("resume", resume_bytes, resumeFile), ("JD", jd_bytes, jdFile)):
        if len(data) > settings.max_upload_bytes:
            raise HTTPException(413, f"{label} file exceeds 5MB limit")
        if not upload.filename.lower().endswith(".pdf"):
            raise HTTPException(400, f"Only PDF files are accepted ({label})")

    try:
        resume_extracted = extract_resume(resume_bytes)
        jd_extracted = extract_resume(jd_bytes)
    except Exception as e:
        logger.warning("Could not parse PDF(s) for JD match: %s", e)
        raise HTTPException(422, f"Could not parse PDF: {e}")

    result = run_jd_match(resume_extracted, jd_extracted, resumeFile.filename, jdFile.filename)
    await service.save_analysis(
        resume_bytes=resume_bytes,
        resume_file_name=resumeFile.filename,
        resume_extracted=resume_extracted,
        jd_bytes=jd_bytes,
        jd_file_name=jdFile.filename,
        jd_extracted=jd_extracted,
        analysis={
            **result,
            "overallMatchScore": result.get("jdMatchScore", 0),
        },
    )
    return {"jdMatchResult": result}


@app.get("/api/admin/jd-match-analyses")
async def list_jd_match_analyses(
    _: bool = Depends(require_admin),
    service: JdMatchService = Depends(get_jd_match_service),
):
    analyses = await service.list_summaries()
    return {"count": len(analyses), "analyses": analyses}


@app.get("/api/admin/jd-match-analyses/{analysis_id}")
async def get_jd_match_analysis(
    analysis_id: uuid.UUID,
    _: bool = Depends(require_admin),
    service: JdMatchService = Depends(get_jd_match_service),
):
    rec = await service.get_detail(analysis_id)
    if not rec:
        raise HTTPException(404, "Not found")
    return rec


@app.get("/api/admin/jd-match-resume/{analysis_id}")
async def get_jd_match_resume_file(
    analysis_id: uuid.UUID,
    _: bool = Depends(require_admin),
    service: JdMatchService = Depends(get_jd_match_service),
):
    rec = await service.get_detail(analysis_id)
    if not rec:
        raise HTTPException(404, "Not found")
    artifact = rec["resumeArtifact"]
    return FileResponse(artifact["storagePath"], media_type="application/pdf", filename=artifact["fileName"])


@app.get("/api/admin/jd-match-jd/{analysis_id}")
async def get_jd_match_jd_file(
    analysis_id: uuid.UUID,
    _: bool = Depends(require_admin),
    service: JdMatchService = Depends(get_jd_match_service),
):
    rec = await service.get_detail(analysis_id)
    if not rec:
        raise HTTPException(404, "Not found")
    artifact = rec["jdArtifact"]
    return FileResponse(artifact["storagePath"], media_type="application/pdf", filename=artifact["fileName"])


@app.post("/api/admin/login")
async def admin_login(body: LoginBody):
    if body.email.strip().lower() == settings.admin_email.lower() and body.password == settings.admin_password:
        return {"token": make_token(body.email), "expiresIn": settings.token_ttl_seconds}
    raise HTTPException(401, "Invalid credentials")


@app.get("/api/admin/candidates")
async def list_candidates(
    _: bool = Depends(require_admin),
    service: CandidateService = Depends(get_candidate_service),
):
    summary = await service.list_summaries()
    return {"count": len(summary), "candidates": summary}


@app.get("/api/admin/candidates/{candidate_id}")
async def get_candidate(
    candidate_id: uuid.UUID,
    _: bool = Depends(require_admin),
    service: CandidateService = Depends(get_candidate_service),
):
    rec = await service.get_detail(candidate_id)
    if not rec:
        raise HTTPException(404, "Not found")
    return rec


@app.get("/api/admin/resume/{candidate_id}")
async def get_resume_file(
    candidate_id: uuid.UUID,
    _: bool = Depends(require_admin),
    service: CandidateService = Depends(get_candidate_service),
):
    found = await service.get_resume_path(candidate_id)
    if not found:
        raise HTTPException(404, "Not found")
    storage_path, file_name = found
    return FileResponse(storage_path, media_type="application/pdf", filename=file_name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=settings.port, reload=settings.environment == "development")
