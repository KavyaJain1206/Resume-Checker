import type { AuditResult, CandidateSummary } from "./types";

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

export async function listCandidates(token: string): Promise<{ count: number; candidates: CandidateSummary[] }> {
  const r = await fetch(`${BASE}/api/admin/candidates`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error("Session expired");
  return r.json();
}

export async function getCandidate(token: string, id: string): Promise<any> {
  const r = await fetch(`${BASE}/api/admin/candidates/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok) throw new Error("Not found");
  return r.json();
}
