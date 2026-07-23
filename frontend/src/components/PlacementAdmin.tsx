import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Lock, ArrowLeft, LogOut, Search, Terminal, Download } from "lucide-react";
import { adminLogin, listCandidates, getCandidate, downloadResume, SessionExpiredError } from "../api";
import type { CandidateSummary } from "../types";

const TOKEN_KEY = "arsenal_token";

export default function PlacementAdmin() {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY));
  const logout = () => { sessionStorage.removeItem(TOKEN_KEY); setToken(null); };

  if (!token) return <LoginGate onAuth={(t) => { sessionStorage.setItem(TOKEN_KEY, t); setToken(t); }} />;
  // onSessionExpired reuses the same reset as a manual sign-out: clearing the
  // token flips this component back to LoginGate above — an expired or
  // missing token always lands the user back on the login screen, never on
  // the protected endpoint itself.
  return <Arsenal token={token} onLogout={logout} onSessionExpired={logout} />;
}

function LoginGate({ onAuth }: { onAuth: (t: string) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try { onAuth(await adminLogin(email, password)); }
    catch { setErr("Invalid credentials. Try the demo login below."); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid-bg min-h-screen flex flex-col items-center justify-center px-6">
      <Link to="/" className="mono-label flex items-center gap-1 mb-8 hover:text-flame">
        <ArrowLeft size={13} /> Back to Intake
      </Link>
      <motion.form onSubmit={submit} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md border-2 border-ink bg-white p-8">
        <div className="flex items-center gap-3">
          <div className="bg-flame/15 p-3"><Lock className="text-flame" size={20} /></div>
          <div>
            <p className="mono-label">Restricted</p>
            <h1 className="text-2xl font-900 tracking-tight">PLACEMENT ADMIN</h1>
          </div>
        </div>
        <p className="text-sm text-ink/70 mt-4">
          The Student Arsenal contains uploaded resumes and personal contact details.
          Sign in with your placement-team credentials to continue.
        </p>
        <label className="block mt-6">
          <span className="mono-label !text-[0.58rem]">Email</span>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="admin@placement.team"
            className="mt-1 w-full border-b-2 border-ink/40 bg-transparent py-2 focus:border-flame focus:outline-none" />
        </label>
        <label className="block mt-5">
          <span className="mono-label !text-[0.58rem]">Password</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••"
            className="mt-1 w-full border-b-2 border-ink/40 bg-transparent py-2 focus:border-flame focus:outline-none" />
        </label>
        {err && <p className="text-flame text-sm mt-3 font-600">{err}</p>}
        <button disabled={busy}
          className="mt-6 w-full bg-ink text-white py-4 font-800 tracking-wide flex items-center justify-center gap-2 hover:bg-flame transition-colors disabled:opacity-60">
          <Lock size={15} /> {busy ? "SIGNING IN…" : "SIGN IN"}
        </button>
        <p className="text-[11px] text-smoke mt-4 text-center">
          Contact your administrator for login credentials. Sessions expire after 24 hours.
        </p>
      </motion.form>
    </div>
  );
}

function Arsenal({ token, onLogout, onSessionExpired }: {
  token: string; onLogout: () => void; onSessionExpired: () => void;
}) {
  const [rows, setRows] = useState<CandidateSummary[]>([]);
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");
  const [detail, setDetail] = useState<any | null>(null);

  useEffect(() => {
    listCandidates(token).then((d) => setRows(d.candidates)).catch((e) => {
      if (e instanceof SessionExpiredError) return onSessionExpired();
      console.error("[Arsenal] listCandidates failed:", e);
      setErr("Could not load candidates. Is the backend running?");
    });
  }, [token]);

  function openCandidate(id: string) {
    getCandidate(token, id).then(setDetail).catch((e) => {
      if (e instanceof SessionExpiredError) return onSessionExpired();
      console.error("[Arsenal] getCandidate failed:", e);
      setErr("Could not load candidate detail.");
    });
  }

  const filtered = rows.filter((r) =>
    [r.fullName, r.email, r.college, r.targetRole].join(" ").toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="min-h-screen">
      <header className="grid-bg border-b border-ink/10 px-6 lg:px-10 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2 mono-label !text-ink">
          <Terminal size={16} className="text-flame" /> STUDENT_ARSENAL
        </div>
        <div className="flex items-center gap-4">
          <Link to="/" className="mono-label hover:text-flame">Intake</Link>
          <button onClick={onLogout} className="mono-label flex items-center gap-1 hover:text-flame">
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </header>

      <div className="px-6 lg:px-10 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mono-label">Candidate Directory</p>
            <h1 className="text-4xl lg:text-5xl font-900 tracking-tight mt-1">THE STUDENT ARSENAL</h1>
            <p className="text-sm text-smoke mt-2">{rows.length} audited candidate{rows.length === 1 ? "" : "s"} captured.</p>
          </div>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-smoke" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, college, role…"
              aria-label="Search candidates"
              className="border border-ink pl-9 pr-4 py-2.5 text-sm w-72 focus:outline-none focus:border-flame" />
          </div>
        </div>

        {err && <p className="text-flame mt-6">{err}</p>}

        <div className="mt-6 border border-ink overflow-x-auto">
          <table className="w-full text-sm min-w-[820px]">
            <thead>
              <tr className="bg-ink text-white text-left">
                {["Name", "Target Role", "Level", "College", "Score", "ATS", "7-Sec", "Captured"].map((h) => (
                  <th key={h} className="px-4 py-3 mono-label !text-white !text-[0.56rem]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.id} onClick={() => openCandidate(r.id)}
                  className="border-t border-ink/10 hover:bg-paper cursor-pointer">
                  <td className="px-4 py-3 font-600">
                    {r.fullName}<div className="text-xs text-smoke font-400">{r.email}</div>
                  </td>
                  <td className="px-4 py-3">{r.targetRole}</td>
                  <td className="px-4 py-3 text-xs">{r.experienceLevel}</td>
                  <td className="px-4 py-3 text-xs">{r.college || "—"}</td>
                  <td className="px-4 py-3 font-900" style={{ color: r.overallScore >= 75 ? "#16a34a" : r.overallScore >= 50 ? "#f97316" : "#dc2626" }}>
                    {r.overallScore}
                  </td>
                  <td className="px-4 py-3"><Pill v={r.atsRiskLevel} good={r.atsRiskLevel === "LOW"} warn={r.atsRiskLevel === "MED"} /></td>
                  <td className="px-4 py-3"><Pill v={r.recruiter7SecScan} good={r.recruiter7SecScan === "PASS"} /></td>
                  <td className="px-4 py-3 text-xs text-smoke">{new Date(r.createdAt).toLocaleDateString()}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-smoke">
                  No candidates yet. Run a diagnostic from the intake page to populate the Arsenal.
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {detail && (
        <DetailDrawer
          rec={detail}
          token={token}
          onClose={() => setDetail(null)}
          onSessionExpired={onSessionExpired}
        />
      )}
    </div>
  );
}

function Pill({ v, good, warn }: { v: string; good?: boolean; warn?: boolean }) {
  const c = good ? "#16a34a" : warn ? "#f97316" : "#dc2626";
  return <span className="text-[0.62rem] font-700 border px-2 py-0.5" style={{ color: c, borderColor: c }}>{v}</span>;
}

function DetailDrawer({ rec, token, onClose, onSessionExpired }: {
  rec: any; token: string; onClose: () => void; onSessionExpired: () => void;
}) {
  const p = rec.profile, a = rec.auditResult;
  const [downloading, setDownloading] = useState(false);
  const [downloadErr, setDownloadErr] = useState("");

  async function handleDownload() {
    setDownloadErr("");
    setDownloading(true);
    try {
      await downloadResume(token, rec.id, rec.resumeArtifact?.fileName || "resume.pdf");
    } catch (e) {
      if (e instanceof SessionExpiredError) return onSessionExpired();
      console.error("[DetailDrawer] downloadResume failed:", e);
      setDownloadErr("Could not download resume.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-ink/40 flex justify-end z-50" onClick={onClose}>
      <motion.div initial={{ x: 400 }} animate={{ x: 0 }} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg bg-white h-full overflow-y-auto border-l-4 border-flame p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-900">{p.fullName || "(unnamed)"}</h2>
          <button onClick={onClose} className="mono-label hover:text-flame">Close ✕</button>
        </div>
        <p className="text-sm text-smoke">{p.targetRole} · {p.experienceLevel}</p>
        <div className="grid grid-cols-3 gap-2 mt-4">
          <Stat k="Overall" v={a.overallScore} />
          <Stat k="ATS" v={a.atsRiskLevel} />
          <Stat k="7-Sec" v={a.recruiter7SecScan} />
        </div>
        <Section title="Contact">
          <KV k="Email" v={p.email} /><KV k="Phone" v={p.phone} /><KV k="Location" v={p.location} />
          <KV k="LinkedIn" v={p.socials?.linkedin} /><KV k="GitHub" v={p.socials?.github} />
        </Section>
        <Section title="Academics">
          <KV k="College" v={p.college} /><KV k="Degree" v={`${p.degree} ${p.branch}`} />
          <KV k="Grad Year" v={p.gradYear} /><KV k="CGPA" v={p.cgpa} />
        </Section>
        <Section title="Skills">
          <div className="flex flex-wrap gap-2">
            {(p.skills || []).map((s: string) => <span key={s} className="text-xs border border-ink/30 px-2 py-0.5">{s}</span>)}
            {(!p.skills || !p.skills.length) && <span className="text-xs text-smoke">—</span>}
          </div>
        </Section>
        <Section title={`Critical Fixes (${a.criticalFixes.length})`}>
          {a.criticalFixes.map((f: any) => (
            <div key={f.id} className="text-sm mb-2 border-l-2 border-red-500 pl-3">
              <b>{f.title}</b><div className="text-smoke text-xs">{f.description}</div>
            </div>
          ))}
          {a.criticalFixes.length === 0 && <span className="text-xs text-smoke">None 🎉</span>}
        </Section>
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading}
          className="w-full flex items-center justify-center gap-2 text-center border-2 border-ink py-3 font-800 hover:bg-ink hover:text-white transition-colors disabled:opacity-60"
        >
          <Download size={16} />
          {downloading ? "Downloading…" : `View original resume: ${rec.resumeArtifact?.fileName}`}
        </button>
        {downloadErr && <p className="text-flame text-sm mt-2 text-center font-600">{downloadErr}</p>}
      </motion.div>
    </div>
  );
}

function Stat({ k, v }: { k: string; v: any }) {
  return <div className="border border-ink/20 p-3 text-center"><div className="mono-label !text-[0.52rem]">{k}</div><div className="text-xl font-900">{v}</div></div>;
}
function Section({ title, children }: any) {
  return <div className="mt-6"><p className="mono-label mb-2">{title}</p>{children}</div>;
}
function KV({ k, v }: { k: string; v?: string }) {
  return <div className="flex justify-between text-sm py-1 border-b border-ink/5"><span className="text-smoke">{k}</span><span className="font-500 text-right">{v || "—"}</span></div>;
}
