import type { AuditResult, CandidateSummary } from "./types";

const BASE = import.meta.env.VITE_API_BASE || "";

export async function getRoles(): Promise<{ roles: string[]; experienceLevels: string[] }> {
  const r = await fetch(`${BASE}/api/roles`);
  if (!r.ok) throw new Error("Could not load roles");
  return r.json();
}

export async function runAudit(form: FormData): Promise<{ id: string; auditResult: AuditResult }> {
  const r = await fetch(`${BASE}/api/audit`, { method: "POST", body: form });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Audit failed" }));
    throw new Error(e.detail || "Audit failed");
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
