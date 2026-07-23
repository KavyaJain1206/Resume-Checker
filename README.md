# Resume Playbook 2026 — Diagnostic Engine

A replica of the *Playbook Diagnostic* platform: a frictionless student data-intake
portal that captures candidate profiles + resume PDFs into a backend **Student Arsenal**,
and returns an uncompromising, rule-based resume audit scored strictly against
**The Resume Playbook 2026**.

Two surfaces:
1. **Intake Portal** (`/`) — split-screen editorial landing + resume dropzone.
2. **Diagnostic Scorecard** — 9-dimension breakdown, keyword gaps, and a Priority
   Action Center with line-by-line fixes.
3. **Placement Admin → Student Arsenal** (`/arsenal`) — gated candidate directory.

Stack: **React + TypeScript + Tailwind + Framer Motion + Lucide** (frontend) ·
**FastAPI + pdfplumber + PostgreSQL** via SQLAlchemy 2.x async / asyncpg / Alembic (backend).
Deterministic rule engine — no LLM, same resume always yields the same score.

---

## Quick start

### 1. Database
Create a dedicated role + database (see `backend/.env.example` for the expected shape):
```sql
CREATE ROLE resume_app WITH LOGIN PASSWORD 'choose-a-password';
CREATE DATABASE resume_playbook OWNER resume_app;
```

### 2. Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # optional
pip install -r requirements.txt
cp .env.example .env                                    # then set DATABASE_URL
alembic upgrade head                                    # creates the schema — never done at app startup
python server.py                                        # -> http://localhost:8000
```
`GET /api/health` reports live DB connectivity. See `backend/deploy/` for the
production (systemd + gunicorn) setup.

### 3. Frontend
```bash
cd frontend
npm install
npm run dev                                             # -> http://localhost:5173
```
Vite proxies `/api/*` to the backend on port 8000.

### Placement Admin demo login
`admin@placement.team` / `playbook2026` (override in `backend/.env`).

---

## The 9 scoring dimensions (weights)

| # | Dimension | Weight | Playbook source |
|---|-----------|--------|-----------------|
| 1 | ATS Safety & Formatting | 15% | Ch.11–12 |
| 2 | Contact & Professionalism | 10% | Ch.4, 10 |
| 3 | Section Order & Hierarchy | 10% | Ch.3, 15 |
| 4 | Impact & Metrics Quantification | 20% | Ch.9 |
| 5 | Action Verbs & Buzzword Flagger | 10% | Ch.7, 9 |
| 6 | Project Quality | 15% | Ch.8 |
| 7 | Role & Keyword Tailoring | 10% | Ch.14, App.D |
| 8 | Recruiter 7-Second Scan | 5% | Ch.12 |
| 9 | Summary / Objective Quality | 5% | Ch.5 |

The engine parses raw PDF text **and** layout signals (images, multi-column
detection via word coordinates) so ATS checks reflect the real file, not just text.

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/roles` | roles + experience levels |
| POST | `/api/audit` | multipart: resume PDF + profile → audit; saved to Arsenal |
| POST | `/api/audit/text` | JSON: pasted text + profile → audit only |
| POST | `/api/admin/login` | placement-team login → bearer token |
| GET | `/api/admin/candidates` | directory (auth) |
| GET | `/api/admin/candidates/{id}` | full record (auth) |
| GET | `/api/admin/resume/{id}` | original resume PDF (auth) |
| GET | `/api/health` | liveness + DB connectivity |

## Notes
- Output matches the dashboard JSON contract (`overallScore`, `categoryScores`,
  `criticalFixes`, `importantTweaks`, `keywordGaps`, `passedChecks`, `recruiter7SecScan`, `atsRiskLevel`).
- Colors `#f97316 / #171717 / #fafafa`, Montserrat throughout.
