"""
server.py  -  FastAPI backend for the Resume Playbook Diagnostic Engine.

Endpoints
  GET  /api/roles                       -> target roles + experience levels
  POST /api/audit                       -> multipart (resume PDF + profile) -> audit + saves to Arsenal
  POST /api/audit/text                  -> JSON (pasted text + profile) -> audit only
  POST /api/admin/login                 -> placement-team login -> bearer token
  GET  /api/admin/candidates            -> Student Arsenal directory (auth)
  GET  /api/admin/candidates/{id}       -> single candidate record (auth)
  GET  /api/health
"""
from __future__ import annotations
import os
import uuid
import hmac
import time
import base64
import hashlib
import datetime as dt
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import playbook as PB
from pdf_extract import extract_resume, extract_from_text
from rule_engine import audit
from store import get_store

# --- config ---------------------------------------------------------------
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@placement.team")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "playbook2026")
SECRET = os.getenv("SECRET_KEY", "change-me-in-prod").encode()
TOKEN_TTL = 24 * 3600  # 24h
MAX_BYTES = 5 * 1024 * 1024
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "resumes")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Resume Playbook Diagnostic API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

STORE, STORE_KIND = get_store()


# --- token helpers (stateless HMAC, no external dep) ----------------------
def make_token(email: str) -> str:
    exp = int(time.time()) + TOKEN_TTL
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
    return {"ok": True, "store": STORE_KIND, "roles": len(PB.ROLE_KEYWORDS)}


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
):
    data = await resumeFile.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File exceeds 5MB limit")
    if not resumeFile.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF resumes are accepted")
    try:
        extracted = extract_resume(data)
    except Exception as e:
        raise HTTPException(422, f"Could not parse PDF: {e}")

    result = audit(extracted, targetRole, experienceLevel, resumeFile.filename)

    rec_id = str(uuid.uuid4())
    # persist the raw file
    safe_name = f"{rec_id}.pdf"
    with open(os.path.join(UPLOAD_DIR, safe_name), "wb") as f:
        f.write(data)

    record = {
        "id": rec_id,
        "createdAt": dt.datetime.utcnow().isoformat() + "Z",
        "profile": {
            "fullName": fullName, "email": email, "phone": phone,
            "location": location, "college": college, "degree": degree,
            "branch": branch, "gradYear": gradYear, "cgpa": cgpa,
            "targetRole": targetRole, "experienceLevel": experienceLevel,
            "skills": [s.strip() for s in skills.split(",") if s.strip()],
            "socials": {"linkedin": linkedin, "github": github},
        },
        "resumeArtifact": {
            "fileName": resumeFile.filename,
            "fileUrl": f"/api/admin/resume/{rec_id}",
            "rawExtractedText": extracted.raw_text,
        },
        "auditResult": result,
    }
    await STORE.insert(record)
    return {"id": rec_id, "auditResult": result}


@app.post("/api/audit/text")
async def run_audit_text(body: TextAuditBody):
    extracted = extract_from_text(body.resumeText)
    result = audit(extracted, body.targetRole, body.experienceLevel, "pasted.txt")
    return {"auditResult": result}


@app.post("/api/admin/login")
async def admin_login(body: LoginBody):
    if body.email.strip().lower() == ADMIN_EMAIL.lower() and body.password == ADMIN_PASSWORD:
        return {"token": make_token(body.email), "expiresIn": TOKEN_TTL}
    raise HTTPException(401, "Invalid credentials")


@app.get("/api/admin/candidates")
async def list_candidates(_: bool = Depends(require_admin)):
    rows = await STORE.list_all()
    # summarize for the directory table
    summary = [{
        "id": r["id"],
        "createdAt": r["createdAt"],
        "fullName": r["profile"]["fullName"] or "(unnamed)",
        "email": r["profile"]["email"],
        "college": r["profile"]["college"],
        "targetRole": r["profile"]["targetRole"],
        "experienceLevel": r["profile"]["experienceLevel"],
        "overallScore": r["auditResult"]["overallScore"],
        "atsRiskLevel": r["auditResult"]["atsRiskLevel"],
        "recruiter7SecScan": r["auditResult"]["recruiter7SecScan"],
    } for r in rows]
    return {"count": len(summary), "candidates": summary}


@app.get("/api/admin/candidates/{rec_id}")
async def get_candidate(rec_id: str, _: bool = Depends(require_admin)):
    rec = await STORE.get(rec_id)
    if not rec:
        raise HTTPException(404, "Not found")
    return rec


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
