import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Terminal, ArrowRight, ArrowUpRight, ShieldCheck, Zap, ListChecks,
  UploadCloud, ClipboardList, FileText, ChevronDown, X, Loader2, FileSearch,
} from "lucide-react";
import { getRoles, runAudit, runJdMatch } from "../api";
import type { AuditResult, JdMatchResult, Profile } from "../types";

const FALLBACK_ROLES = [
  "Frontend Developer", "Backend Developer", "Full Stack Developer",
  "Data Analyst", "Data Scientist", "Product Manager", "UI/UX Designer",
  "Software Engineer", "Machine Learning Engineer", "Marketing",
];
const LEVELS = ["Fresher", "Internship", "1-3 Years", "Career Switcher"];

const emptyProfile: Profile = {
  fullName: "", email: "", phone: "", location: "", college: "", degree: "",
  branch: "", gradYear: "", cgpa: "", targetRole: "Frontend Developer",
  experienceLevel: "Fresher", skills: "", linkedin: "", github: "",
};

export default function IntakePortal({
  onComplete,
  onJdComplete,
}: {
  onComplete: (r: AuditResult, p: Profile) => void;
  onJdComplete: (r: JdMatchResult) => void;
}) {
  const [roles, setRoles] = useState<string[]>(FALLBACK_ROLES);
  const [mode, setMode] = useState<"upload" | "form" | "jdMatch">("upload");
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [file, setFile] = useState<File | null>(null);
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getRoles().then((d) => setRoles(d.roles)).catch(() => {});
  }, []);

  const set = (k: keyof Profile, v: string) =>
    setProfile((p) => ({ ...p, [k]: v }));

  function validatePdf(f: File | null): boolean {
    if (!f) return false;
    if (!f.name.toLowerCase().endsWith(".pdf")) { setError("Please upload a PDF file."); return false; }
    if (f.size > 5 * 1024 * 1024) { setError("File exceeds the 5MB limit."); return false; }
    return true;
  }

  function pickFile(f: File | null) {
    setError("");
    if (validatePdf(f)) setFile(f);
  }

  function pickJdFile(f: File | null) {
    setError("");
    if (validatePdf(f)) setJdFile(f);
  }

  async function submit() {
    setError("");
    if (mode === "jdMatch") {
      if (!file) return setError("Attach your resume PDF to compare.");
      if (!jdFile) return setError("Attach the job description PDF to compare.");
    } else {
      if (!file) return setError("Attach your resume PDF to run the diagnostic.");
      if (mode === "form" && !profile.fullName)
        return setError("Enter your name for the tailored audit.");
    }
    setLoading(true);
    const MIN_LOADING_MS = 2500;
    const started = Date.now();
    try {
      if (mode === "jdMatch") {
        const fd = new FormData();
        fd.append("resumeFile", file as File);
        fd.append("jdFile", jdFile as File);
        const { jdMatchResult } = await runJdMatch(fd);
        const remaining = MIN_LOADING_MS - (Date.now() - started);
        if (remaining > 0) await new Promise((r) => setTimeout(r, remaining));
        onJdComplete(jdMatchResult);
        return;
      }

      const fd = new FormData();
      fd.append("resumeFile", file as File);
      fd.append("targetRole", profile.targetRole);
      fd.append("experienceLevel", profile.experienceLevel);
      (["fullName", "email", "phone", "location", "college", "degree", "branch",
        "gradYear", "cgpa", "skills", "linkedin", "github"] as (keyof Profile)[])
        .forEach((k) => fd.append(k, profile[k]));

      const { auditResult } = await runAudit(fd);
      const remaining = MIN_LOADING_MS - (Date.now() - started);
      if (remaining > 0) await new Promise((r) => setTimeout(r, remaining));
      onComplete(auditResult, profile);
    } catch (e: any) {
      console.error("[IntakePortal.submit] request failed:", e);
      const remaining = MIN_LOADING_MS - (Date.now() - started);
      if (remaining > 0) await new Promise((r) => setTimeout(r, remaining));
      setError(e?.message || "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen w-full lg:grid lg:grid-cols-2">
      {/* ================= LEFT — EDITORIAL ================= */}
      <aside className="grid-bg relative flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-ink/10 px-7 py-8 lg:h-screen lg:sticky lg:top-0">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2 mono-label !text-ink min-w-0">
            <Terminal size={16} className="text-flame" />
            RESUME_PLAYBOOK_2026
          </div>
          <div className="flex flex-wrap items-center gap-3 sm:gap-4">
            <Link to="/arsenal" className="mono-label hover:text-ink flex items-center gap-1 underline underline-offset-4 decoration-ink/30 whitespace-nowrap">
              Placement View <ArrowRight size={12} />
            </Link>
            <span className="tag-rotate bg-flame text-white text-[10px] font-800 px-2 py-1 tracking-widest whitespace-nowrap">
              ISSUE 01 · 2026
            </span>
          </div>
        </div>

        <div className="max-w-xl py-10">
          <p className="mono-label mb-6">A diagnostic engine — not a resume builder.</p>
          <h1 className="font-900 leading-[0.92] tracking-tight text-[13vw] sm:text-6xl lg:text-[5.4rem]">
            READ YOUR<br />RESUME THE WAY{" "}
            <span className="text-flame">RECRUITERS</span> DO.
          </h1>
          <p className="mt-8 text-ink/70 max-w-md leading-relaxed">
            Drop a PDF or fill the essentials. We benchmark line-by-line against{" "}
            <strong className="text-ink">The Resume Playbook 2026</strong> — ATS
            safety, metric density, keyword tailoring, buzzword decay, project depth.
          </p>
        </div>

        <div>
          <div className="grid grid-cols-3 gap-3 max-w-lg">
            {[
              { icon: ShieldCheck, k: "ATS SAFE", v: "9 checks" },
              { icon: Zap, k: "FAST", v: "<3s audit" },
              { icon: ListChecks, k: "RULES", v: "Playbook 2026" },
            ].map((s) => (
              <div key={s.k} className="border border-ink/15 bg-white/60 p-3">
                <s.icon size={16} className="text-flame mb-4" />
                <div className="mono-label !text-[0.6rem]">{s.k}</div>
                <div className="text-sm font-700">{s.v}</div>
              </div>
            ))}
          </div>
          <div className="mt-5 flex items-center gap-2 text-xs text-smoke">
            <span className="w-2 h-2 bg-flame inline-block" />
            Benchmarked against 9 Playbook dimensions
          </div>
        </div>
      </aside>

      {/* ================= RIGHT — INTAKE ================= */}
      <main className="px-7 py-8 lg:h-screen lg:overflow-y-auto">
        <div className="flex items-start justify-between">
          <div>
            <p className="mono-label">Step 01 / Intake</p>
            <h2 className="text-4xl lg:text-5xl font-900 tracking-tight mt-1">FEED THE MACHINE</h2>
          </div>
          <span className="mono-label mt-2">// Three ways in</span>
        </div>

        {/* mode toggle */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-7">
          <ModeCard active={mode === "upload"} onClick={() => setMode("upload")}
            icon={UploadCloud} title="JUST UPLOAD" sub="Drop the PDF. We parse your details." />
          <ModeCard active={mode === "form"} onClick={() => setMode("form")}
            icon={ClipboardList} title="FILL QUICK FORM" sub="Type the basics for tighter tailoring." />
          <ModeCard active={mode === "jdMatch"} onClick={() => setMode("jdMatch")}
            icon={FileSearch} title="COMPARE TO A JD" sub="See how your resume matches a specific job." />
        </div>

        {mode !== "jdMatch" && (
          <>
            {/* target role */}
            <Field label="Target Position" className="mt-8">
              <div className="relative">
                <select
                  aria-label="Target Position"
                  value={profile.targetRole}
                  onChange={(e) => set("targetRole", e.target.value)}
                  className="w-full appearance-none border-b-2 border-ink bg-transparent py-3 pr-8 text-lg font-600 focus:outline-none"
                >
                  {roles.map((r) => <option key={r}>{r}</option>)}
                </select>
                <ChevronDown size={18} className="absolute right-1 top-1/2 -translate-y-1/2 pointer-events-none text-smoke" />
              </div>
              <p className="mt-2 text-xs text-smoke">Uses the Playbook's canonical keyword benchmark for that role.</p>
            </Field>

            {/* experience level */}
            <Field label="Experience Level" className="mt-7">
              <div role="group" aria-label="Experience Level" className="grid grid-cols-2 sm:grid-cols-4 border border-ink">
                {LEVELS.map((lv) => (
                  <button key={lv} onClick={() => set("experienceLevel", lv)}
                    aria-pressed={profile.experienceLevel === lv}
                    className={`py-3 text-xs font-700 tracking-wide border-ink transition-colors ${
                      profile.experienceLevel === lv ? "bg-flame text-white" : "bg-white hover:bg-paper"
                    } [&:not(:last-child)]:border-r`}>
                    {lv.toUpperCase()}
                  </button>
                ))}
              </div>
            </Field>
          </>
        )}

        {/* quick form fields */}
        <AnimatePresence>
          {mode === "form" && (
            <motion.div
              initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <div className="grid sm:grid-cols-2 gap-x-6 gap-y-5 mt-7">
                <Line label="Full Name" v={profile.fullName} on={(v) => set("fullName", v)} />
                <Line label="Email" v={profile.email} on={(v) => set("email", v)} />
                <Line label="Phone" v={profile.phone} on={(v) => set("phone", v)} />
                <Line label="Location" v={profile.location} on={(v) => set("location", v)} />
                <Line label="College" v={profile.college} on={(v) => set("college", v)} />
                <Line label="Degree" v={profile.degree} on={(v) => set("degree", v)} />
                <Line label="Branch" v={profile.branch} on={(v) => set("branch", v)} />
                <Line label="Graduation Year" v={profile.gradYear} on={(v) => set("gradYear", v)} />
                <Line label="CGPA / %" v={profile.cgpa} on={(v) => set("cgpa", v)} />
                <Line label="Skills (comma-sep)" v={profile.skills} on={(v) => set("skills", v)} />
                <Line label="LinkedIn URL" v={profile.linkedin} on={(v) => set("linkedin", v)} />
                <Line label="GitHub / Portfolio" v={profile.github} on={(v) => set("github", v)} />
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* dropzone(s) */}
        {mode === "jdMatch" ? (
          <div className="mt-8 space-y-4">
            <Dropzone label="Resume PDF" file={file} onPick={pickFile} onClear={() => setFile(null)} />
            <Dropzone label="Job Description PDF" file={jdFile} onPick={pickJdFile} onClear={() => setJdFile(null)} />
          </div>
        ) : (
          <div className="mt-8">
            <Dropzone file={file} onPick={pickFile} onClear={() => setFile(null)} />
          </div>
        )}

        {error && <p className="mt-4 text-sm text-flame font-600">{error}</p>}

        <button
          onClick={submit} disabled={loading}
          className="mt-6 w-full bg-ink text-white py-5 font-800 tracking-wide flex items-center justify-center gap-3 hover:bg-flame transition-colors disabled:opacity-60">
          {loading && <Loader2 size={18} className="animate-spin" />}
          {loading ? "RUNNING DIAGNOSTIC…" : mode === "jdMatch" ? "RUN MATCH ANALYSIS" : "RUN DIAGNOSTIC"}
          {!loading && <ArrowRight size={18} />}
        </button>
        <p className="mt-4 mb-10 text-[11px] text-smoke leading-relaxed">
          {mode === "jdMatch"
            ? "This comparison is saved for admin review along with both PDFs and extracted text."
            : "Your profile and resume are saved to the placement team's Student Arsenal for review."}
        </p>
      </main>
    </div>
  );
}

function ModeCard({ active, onClick, icon: Icon, title, sub }: any) {
  return (
    <button onClick={onClick}
      className={`text-left p-4 border transition-colors ${
        active ? "bg-flame text-white border-flame" : "bg-white border-ink/20 hover:border-ink"
      }`}>
      <div className="flex items-center gap-2 font-800">
        <Icon size={18} /> {title}
      </div>
      <p className={`text-xs mt-1 ${active ? "text-white/85" : "text-smoke"}`}>{sub}</p>
    </button>
  );
}

function Dropzone({ label, file, onPick, onClear }: {
  label?: string; file: File | null; onPick: (f: File | null) => void; onClear: () => void;
}) {
  const [drag, setDrag] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  return (
    <div>
      {label && <p className="mono-label mb-2">{label}</p>}
      <input ref={inputRef} type="file" accept="application/pdf" hidden
        onChange={(e) => onPick(e.target.files?.[0] || null)} />
      {!file ? (
        <button type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); onPick(e.dataTransfer.files?.[0] || null); }}
          className={`w-full border-2 border-dashed py-14 flex flex-col items-center gap-2 transition-colors ${
            drag ? "border-flame bg-flame/5" : "border-ink/30 hover:border-ink"
          }`}>
          <UploadCloud size={30} className="text-flame" />
          <span className="font-600">Drop your {label ? label : "resume PDF"} here</span>
          <span className="text-xs text-smoke">or click to browse — max 5MB</span>
        </button>
      ) : (
        <div className="flex items-center justify-between border-2 border-ink bg-white px-4 py-4">
          <div className="flex items-center gap-3">
            <FileText className="text-flame" />
            <div>
              <div className="font-600 text-sm">{file.name}</div>
              <div className="text-xs text-smoke">{(file.size / 1024).toFixed(0)} KB · PDF</div>
            </div>
          </div>
          <button type="button" onClick={onClear} className="text-smoke hover:text-ink"><X size={18} /></button>
        </div>
      )}
    </div>
  );
}

function Field({ label, children, className = "" }: any) {
  return (
    <div className={className}>
      <p className="mono-label mb-3">{label}</p>
      {children}
    </div>
  );
}

function Line({ label, v, on }: { label: string; v: string; on: (v: string) => void }) {
  return (
    <label className="block">
      <span className="mono-label !text-[0.6rem]">{label}</span>
      <input value={v} onChange={(e) => on(e.target.value)}
        className="mt-1 w-full border-b border-ink/40 bg-transparent py-2 text-sm focus:border-flame focus:outline-none" />
    </label>
  );
}
