import type { AuditResult, CandidateSummary, JdMatchDetail, JdMatchResult, JdMatchSummary } from "./types";

const BASE = import.meta.env.VITE_API_BASE || "";

export async function getRoles(): Promise<{ roles: string[]; experienceLevels: string[] }> {
  const r = await fetch(`${BASE}/api/roles`);
  if (!r.ok) throw new Error("Could not load roles");
  return r.json();
}

export async function runAudit(form: FormData): Promise<{ id: string; auditResult: AuditResult }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45_000);
  let r: Response;
  try {
    r = await fetch(`${BASE}/api/audit`, { method: "POST", body: form, signal: controller.signal });
  } catch (err: any) {
    console.error("[runAudit] fetch() rejected before a response was received:", err);
    if (err?.name === "AbortError") {
      throw new Error("Upload timed out — check your connection and try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
  if (!r.ok) {
    const bodyText = await r.text();
    let detail = "Audit failed";
    try {
      detail = JSON.parse(bodyText).detail || detail;
    } catch (parseErr) {
      console.error("[runAudit] non-JSON error response", { status: r.status, bodyText, parseErr });
    }
    console.error(`[runAudit] server responded ${r.status}:`, detail);
    throw new Error(detail);
  }
  return r.json();
}

export async function runJdMatch(form: FormData): Promise<{ jdMatchResult: JdMatchResult }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 45_000);
  let r: Response;
  try {
    r = await fetch(`${BASE}/api/jd-match`, { method: "POST", body: form, signal: controller.signal });
  } catch (err: any) {
    console.error("[runJdMatch] fetch() rejected before a response was received:", err);
    if (err?.name === "AbortError") {
      throw new Error("Analysis timed out — check your connection and try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
  if (!r.ok) {
    const bodyText = await r.text();
    let detail = "JD match failed";
    try {
      detail = JSON.parse(bodyText).detail || detail;
    } catch (parseErr) {
      console.error("[runJdMatch] non-JSON error response", { status: r.status, bodyText, parseErr });
    }
    console.error(`[runJdMatch] server responded ${r.status}:`, detail);
    throw new Error(detail);
  }
  return r.json();
}

export async function adminLogin(email: string, password: string): Promise<string> {
  const r = await fetch(`${BASE}/api/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error("Invalid credentials");
  const d = await r.json();
  return d.token as string;
}

/** Thrown whenever an authenticated admin request comes back 401 — missing
 * or expired token. Callers should catch this specifically and redirect to
 * the login screen rather than showing a generic error. */
export class SessionExpiredError extends Error {
  constructor() {
    super("Session expired");
    this.name = "SessionExpiredError";
  }
}

/** Every admin request goes through here so the Bearer token and the
 * 401 -> SessionExpiredError translation happen in exactly one place. */
async function authFetch(token: string, path: string, init: RequestInit = {}): Promise<Response> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...(init.headers || {}), Authorization: `Bearer ${token}` },
  });
  if (r.status === 401) throw new SessionExpiredError();
  return r;
}

export async function listCandidates(token: string): Promise<{ count: number; candidates: CandidateSummary[] }> {
  const r = await authFetch(token, "/api/admin/candidates");
  if (!r.ok) throw new Error("Could not load candidates");
  return r.json();
}

export async function getCandidate(token: string, id: string): Promise<any> {
  const r = await authFetch(token, `/api/admin/candidates/${id}`);
  if (!r.ok) throw new Error("Not found");
  return r.json();
}

export async function listJdMatchAnalyses(token: string): Promise<{ count: number; analyses: JdMatchSummary[] }> {
  const r = await authFetch(token, "/api/admin/jd-match-analyses");
  if (!r.ok) throw new Error("Could not load JD matches");
  return r.json();
}

export async function getJdMatchAnalysis(token: string, id: string): Promise<JdMatchDetail> {
  const r = await authFetch(token, `/api/admin/jd-match-analyses/${id}`);
  if (!r.ok) throw new Error("Not found");
  return r.json();
}

/** Fetches the resume PDF with the Bearer token attached and triggers a
 * client-side download via an object URL — never navigates the browser
 * to the protected URL directly (which can't carry an Authorization
 * header and would 401). */
export async function downloadResume(token: string, id: string, fileName: string): Promise<void> {
  const r = await authFetch(token, `/api/admin/resume/${id}`);
  if (!r.ok) throw new Error("Could not download resume");
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName || "resume.pdf";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function downloadJdMatchFile(
  token: string,
  id: string,
  kind: "resume" | "jd",
  fileName: string,
): Promise<void> {
  const endpoint = kind === "resume"
    ? `/api/admin/jd-match-resume/${id}`
    : `/api/admin/jd-match-jd/${id}`;
  const r = await authFetch(token, endpoint);
  if (!r.ok) throw new Error("Could not download file");
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName || `${kind}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
