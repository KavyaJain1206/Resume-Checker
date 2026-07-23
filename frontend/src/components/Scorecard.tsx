import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Terminal, RotateCcw, ArrowRight, ShieldCheck, Gauge, Target, LayoutList,
  FolderGit2, UserCheck, ScanLine, FileText, AlertTriangle, TriangleAlert,
  CheckCircle2, ArrowDownRight, ArrowUpRight, GraduationCap, Briefcase, Award,
} from "lucide-react";
import type { AuditResult, Profile, FixItem, CategoryScores, JdMatchResult, JdCategoryScores, ScoreBreakdownItem } from "../types";

const CAT_META: { key: keyof CategoryScores; label: string; icon: any }[] = [
  { key: "atsSafety", label: "ATS Safety", icon: ShieldCheck },
  { key: "metricQuantification", label: "Metric Density", icon: Gauge },
  { key: "keywordTailoring", label: "Keyword Alignment", icon: Target },
  { key: "sectionHierarchy", label: "Formatting & Hierarchy", icon: LayoutList },
  { key: "projectStrength", label: "Project Strength", icon: FolderGit2 },
  { key: "contactProfessionalism", label: "Professionalism", icon: UserCheck },
  { key: "verbAndBuzzwordQuality", label: "Verbs & Buzzwords", icon: ScanLine },
  { key: "summaryQuality", label: "Summary Quality", icon: FileText },
];

function useCountUp(target: number, ms = 900) {
  const [n, setN] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / ms);
      setN(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return n;
}

const scoreColor = (s: number) => (s >= 75 ? "#16a34a" : s >= 50 ? "#f97316" : "#dc2626");

export default function Scorecard({
  result, profile, onReset,
}: {
  result: AuditResult; profile: Profile; onReset: () => void;
}) {
  const [tab, setTab] = useState<"critical" | "important" | "passed">("critical");
  const overall = useCountUp(result.overallScore);

  const tabs = [
    { id: "critical" as const, label: "Critical Fixes", emoji: "🔴", count: result.criticalFixes.length },
    { id: "important" as const, label: "Important Improvements", emoji: "🟡", count: result.importantTweaks.length },
    { id: "passed" as const, label: "Strengths & Passed", emoji: "🟢", count: result.passedChecks.length },
  ];

  return (
    <div className="min-h-screen">
      {/* ============ HEADER ============ */}
      <header className="grid-bg border-b border-ink/10 px-6 lg:px-10 pt-7 pb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 mono-label !text-ink">
            <Terminal size={16} className="text-flame" /> RESUME_PLAYBOOK_2026
          </div>
          <div className="flex items-center gap-4">
            <Link to="/arsenal" className="mono-label hover:text-ink flex items-center gap-1 underline underline-offset-4 decoration-ink/30">
              Placement View <ArrowRight size={12} />
            </Link>
            <button onClick={onReset} className="mono-label flex items-center gap-1 hover:text-flame">
              <RotateCcw size={13} /> New Audit
            </button>
          </div>
        </div>

        <div className="mt-8 grid lg:grid-cols-[1fr_auto] gap-8 items-end">
          {/* profile summary */}
          <div>
            <p className="mono-label">Diagnostic Result</p>
            <h1 className="text-4xl lg:text-6xl font-900 tracking-tight mt-1">
              {profile.fullName || "YOUR RESUME"}
            </h1>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink/70">
              <span><b className="text-ink">Target:</b> {result.meta.targetRole}</span>
              <span><b className="text-ink">Level:</b> {result.meta.experienceLevel}</span>
              {profile.college && <span><b className="text-ink">College:</b> {profile.college}</span>}
              <span><b className="text-ink">File:</b> {result.meta.fileName}</span>
            </div>
          </div>

          {/* hero readiness badges */}
          <div className="flex items-stretch gap-3">
            <div className="border-2 border-ink bg-white px-6 py-4 text-center min-w-[130px]">
              <div className="mono-label !text-[0.58rem]">Overall</div>
              <div className="text-5xl font-900 leading-none mt-1" style={{ color: scoreColor(result.overallScore) }}>
                {overall}
              </div>
              <div className="text-[0.6rem] text-smoke mt-1">/ 100</div>
            </div>
            <Badge label="7-Sec Scan" value={result.recruiter7SecScan}
              good={result.recruiter7SecScan === "PASS"} />
            <Badge label="ATS Risk" value={result.atsRiskLevel}
              good={result.atsRiskLevel === "LOW"} warn={result.atsRiskLevel === "MED"} />
          </div>
        </div>
      </header>

      {/* ============ MAIN GRID ============ */}
      <div className="px-6 lg:px-10 py-8 grid lg:grid-cols-[1fr_1.1fr] gap-8">
        {/* LEFT — category breakdown */}
        <section>
          <p className="mono-label mb-4">Category Breakdown</p>
          <div className="grid sm:grid-cols-2 gap-3">
            {CAT_META.map((c, i) => {
              const s = result.categoryScores[c.key];
              return (
                <motion.div key={c.key} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="border border-ink/15 bg-white p-4">
                  <div className="flex items-center justify-between">
                    <c.icon size={16} className="text-flame" />
                    <span className="text-2xl font-900" style={{ color: scoreColor(s) }}>{s}</span>
                  </div>
                  <div className="mono-label !text-[0.58rem] mt-3">{c.label}</div>
                  <div className="mt-2 h-1.5 bg-ink/10">
                    <motion.div className="h-full" style={{ background: scoreColor(s) }}
                      initial={{ width: 0 }} animate={{ width: `${s}%` }}
                      transition={{ delay: 0.2 + i * 0.05, duration: 0.7 }} />
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* keyword gaps */}
          <p className="mono-label mt-8 mb-3">Keyword Coverage · {result.meta.targetRole}</p>
          <div className="border border-ink/15 bg-white p-4">
            <div className="flex items-center gap-2 mb-2">
              <ArrowUpRight size={14} className="text-green-600" />
              <span className="mono-label !text-[0.58rem] !text-green-700">Matched</span>
            </div>
            <div className="flex flex-wrap gap-2 mb-4">
              {result.keywordGaps.found.length
                ? result.keywordGaps.found.map((k) => (
                    <span key={k} className="text-xs border border-green-600/40 text-green-700 px-2 py-0.5">{k}</span>))
                : <span className="text-xs text-smoke">None detected</span>}
            </div>
            <div className="flex items-center gap-2 mb-2">
              <ArrowDownRight size={14} className="text-flame" />
              <span className="mono-label !text-[0.58rem] !text-flame">Missing · high priority</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {result.keywordGaps.missingHighPriority.length
                ? result.keywordGaps.missingHighPriority.map((k) => (
                    <span key={k} className="text-xs border border-flame/50 text-flame px-2 py-0.5">{k}</span>))
                : <span className="text-xs text-smoke">Full coverage 🎉</span>}
            </div>
          </div>
        </section>

        {/* RIGHT — priority action center */}
        <section>
          <p className="mono-label mb-4">Priority Action Center</p>
          <div className="grid grid-cols-3 border border-ink">
            {tabs.map((t, i) => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`py-3 px-2 text-center transition-colors ${i < 2 ? "border-r border-ink" : ""} ${
                  tab === t.id ? "bg-ink text-white" : "bg-white hover:bg-paper"
                }`}>
                <div className="text-lg font-900">{t.count}</div>
                <div className="text-[0.6rem] font-600 tracking-wide leading-tight mt-0.5">
                  {t.emoji} {t.label}
                </div>
              </button>
            ))}
          </div>

          <div className="feed mt-4 space-y-3 lg:max-h-[70vh] lg:overflow-y-auto lg:pr-1">
            {tab === "critical" && result.criticalFixes.map((f) => <FixCard key={f.id} f={f} tone="critical" />)}
            {tab === "critical" && result.criticalFixes.length === 0 && <Empty msg="No critical fixes — strong foundation." />}
            {tab === "important" && result.importantTweaks.map((f) => <FixCard key={f.id} f={f} tone="important" />)}
            {tab === "important" && result.importantTweaks.length === 0 && <Empty msg="No important tweaks queued." />}
            {tab === "passed" && (
              <div className="grid gap-2">
                {result.passedChecks.map((p, i) => (
                  <div key={i} className="flex items-start gap-3 border border-green-600/30 bg-green-50/50 p-3">
                    <CheckCircle2 size={18} className="text-green-600 mt-0.5 shrink-0" />
                    <span className="text-sm">{p}</span>
                  </div>
                ))}
                {result.passedChecks.length === 0 && <Empty msg="No checks passed yet — start with the critical fixes." />}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

const JD_CAT_META: { key: keyof JdCategoryScores; label: string; icon: any }[] = [
  { key: "keywordMatch", label: "Keyword Match", icon: Target },
  { key: "skillsMatch", label: "Skills Match", icon: ScanLine },
  { key: "educationMatch", label: "Education Match", icon: GraduationCap },
  { key: "experienceMatch", label: "Experience Match", icon: Briefcase },
  { key: "certificationMatch", label: "Certification Match", icon: Award },
  { key: "responsibilitiesMatch", label: "Responsibilities", icon: LayoutList },
  { key: "projectsMatch", label: "Projects Match", icon: FolderGit2 },
];

const JD_SCORE_META: { key: keyof JdMatchResult["scoreBreakdown"]; label: string; icon: any }[] = [
  { key: "overallMatch", label: "Overall Match", icon: Target },
  { key: "resumeAtsScore", label: "Resume ATS Score", icon: ShieldCheck },
  { key: "keywordMatch", label: "Keyword Match", icon: Target },
  { key: "skillsMatch", label: "Skills Match", icon: ScanLine },
  { key: "educationMatch", label: "Education Match", icon: GraduationCap },
  { key: "experienceMatch", label: "Experience Match", icon: Briefcase },
  { key: "certificationMatch", label: "Certification Match", icon: Award },
  { key: "responsibilitiesMatch", label: "Responsibilities", icon: LayoutList },
  { key: "projectsMatch", label: "Projects Match", icon: FolderGit2 },
];

export function JdScorecard({ result, onReset }: { result: JdMatchResult; onReset: () => void }) {
  const [tab, setTab] = useState<"critical" | "important" | "strengths">("critical");
  const jdScore = useCountUp(result.jdMatchScore);
  const atsScore = useCountUp(result.resumeAtsScore);
  const overallScore = useCountUp(result.overallMatchScore ?? result.jdMatchScore);
  const good = result.finalRecommendation === "Strong Match";
  const warn = result.finalRecommendation === "Moderate Match";

  const tabs = [
    { id: "critical" as const, label: "Missing Requirements", emoji: "🔴", count: result.criticalFixes.length },
    { id: "important" as const, label: "Suggested Changes", emoji: "🟡", count: result.importantTweaks.length },
    { id: "strengths" as const, label: "Strengths", emoji: "🟢", count: result.strengths.length },
  ];

  const confidenceTag = (c: string) =>
    c !== "Verified" && (
      <span className="text-[0.5rem] font-700 tracking-wide text-smoke border border-ink/20 px-1 ml-1 align-middle">
        {c.toUpperCase()}
      </span>
    );

  return (
    <div className="min-h-screen">
      {/* ============ HEADER ============ */}
      <header className="grid-bg border-b border-ink/10 px-6 lg:px-10 pt-7 pb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 mono-label !text-ink">
            <Terminal size={16} className="text-flame" /> RESUME_PLAYBOOK_2026
          </div>
          <div className="flex items-center gap-4">
            <Link to="/arsenal" className="mono-label hover:text-ink flex items-center gap-1 underline underline-offset-4 decoration-ink/30">
              Placement View <ArrowRight size={12} />
            </Link>
            <button onClick={onReset} className="mono-label flex items-center gap-1 hover:text-flame">
              <RotateCcw size={13} /> New Comparison
            </button>
          </div>
        </div>

        <div className="mt-8 grid lg:grid-cols-[1fr_auto] gap-8 items-end">
          <div>
            <p className="mono-label">JD Comparison Result</p>
            <h1 className="text-4xl lg:text-6xl font-900 tracking-tight mt-1">
              {result.meta.resumeFileName}
            </h1>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink/70">
              <span><b className="text-ink">Compared against:</b> {result.meta.jdFileName}</span>
              {result.meta.requiredExperienceYears != null && (
                <span><b className="text-ink">JD requires:</b> {result.meta.requiredExperienceYears}+ years</span>
              )}
            </div>
          </div>

          <div className="flex items-stretch gap-3">
            <div className="border-2 border-ink bg-white px-6 py-4 text-center min-w-[130px]">
              <div className="mono-label !text-[0.58rem]">Overall Match</div>
              <div className="text-5xl font-900 leading-none mt-1" style={{ color: scoreColor(result.overallMatchScore ?? result.jdMatchScore) }}>
                {overallScore}
              </div>
              <div className="text-[0.6rem] text-smoke mt-1">/ 100</div>
            </div>
            <div className="border-2 border-ink bg-white px-6 py-4 text-center min-w-[130px]">
              <div className="mono-label !text-[0.58rem]">Resume ATS Score</div>
              <div className="text-5xl font-900 leading-none mt-1" style={{ color: scoreColor(result.resumeAtsScore) }}>
                {atsScore}
              </div>
              <div className="text-[0.6rem] text-smoke mt-1">/ 100</div>
            </div>
            <Badge label="Recommendation" value={result.finalRecommendation} good={good} warn={warn} />
          </div>
        </div>
      </header>

      {/* ============ MAIN GRID ============ */}
      <div className="px-6 lg:px-10 py-8 grid lg:grid-cols-[1fr_1.1fr] gap-8">
        {/* LEFT — category breakdown */}
        <section>
          <p className="mono-label mb-4">Category Breakdown</p>
          <div className="grid sm:grid-cols-2 gap-3">
            {JD_CAT_META.map((c, i) => {
              const s = result.categoryScores[c.key] ?? 0;
              const breakdown = result.scoreBreakdown[c.key];
              const confidence = breakdown?.confidence || (result.confidence as any)[c.key] as string | undefined;
              return (
                <motion.div key={c.key} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="border border-ink/15 bg-white p-4">
                  <div className="flex items-center justify-between">
                    <c.icon size={16} className="text-flame" />
                    <span className="text-2xl font-900" style={{ color: scoreColor(s) }}>{s}</span>
                  </div>
                  <div className="mono-label !text-[0.58rem] mt-3">
                    {c.label}
                    {confidence && confidenceTag(confidence)}
                  </div>
                  <div className="mt-2 h-1.5 bg-ink/10">
                    <motion.div className="h-full" style={{ background: scoreColor(s) }}
                      initial={{ width: 0 }} animate={{ width: `${s}%` }}
                      transition={{ delay: 0.2 + i * 0.05, duration: 0.7 }} />
                  </div>
                  <p className="text-[0.68rem] text-smoke mt-2 leading-snug">{result.categoryDetails[c.key] || breakdown?.reasonForDeductions || "No additional detail."}</p>
                </motion.div>
              );
            })}
          </div>

          <p className="mono-label mt-8 mb-3">Score Details</p>
          <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {JD_SCORE_META.map((item, i) => {
              const breakdown = result.scoreBreakdown[item.key] as ScoreBreakdownItem;
              return (
                <motion.div key={item.key} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 * i }}
                  className="border border-ink/15 bg-white p-4">
                  <div className="flex items-center justify-between gap-3">
                    <item.icon size={16} className="text-flame" />
                    <span className="text-2xl font-900" style={{ color: scoreColor(breakdown.percentage) }}>{breakdown.percentage}</span>
                  </div>
                  <div className="mono-label !text-[0.58rem] mt-3">{item.label}</div>
                  <p className="text-[0.68rem] text-smoke mt-2 leading-snug">
                    {breakdown.matchedCount} matched / {breakdown.totalCount} total · {breakdown.confidence}
                  </p>
                  <p className="text-[0.68rem] text-smoke mt-2 leading-snug">{breakdown.reasonForDeductions}</p>
                </motion.div>
              );
            })}
          </div>

          <p className="mono-label mt-8 mb-3">Recruiter View</p>
          <div className="border border-ink/15 bg-white p-4 text-sm text-ink/80 leading-relaxed">
            {result.recruiterView}
          </div>

          {result.atsRisks.length > 0 && (
            <>
              <p className="mono-label mt-8 mb-3">ATS Risks</p>
              <div className="border border-ink/15 bg-white p-4 space-y-2">
                {result.atsRisks.map((r, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-ink/80">
                    <TriangleAlert size={14} className="text-flame mt-0.5 shrink-0" />
                    <span>{r}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>

        {/* RIGHT — priority action center */}
        <section>
          <p className="mono-label mb-4">Priority Action Center</p>
          <div className="grid grid-cols-3 border border-ink">
            {tabs.map((t, i) => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`py-3 px-2 text-center transition-colors ${i < 2 ? "border-r border-ink" : ""} ${
                  tab === t.id ? "bg-ink text-white" : "bg-white hover:bg-paper"
                }`}>
                <div className="text-lg font-900">{t.count}</div>
                <div className="text-[0.6rem] font-600 tracking-wide leading-tight mt-0.5">
                  {t.emoji} {t.label}
                </div>
              </button>
            ))}
          </div>

          <div className="feed mt-4 space-y-3 lg:max-h-[70vh] lg:overflow-y-auto lg:pr-1">
            {tab === "critical" && result.criticalFixes.map((f) => <FixCard key={f.id} f={f} tone="critical" />)}
            {tab === "critical" && result.criticalFixes.length === 0 && <Empty msg="No missing required qualifications — strong alignment." />}
            {tab === "important" && result.importantTweaks.map((f) => <FixCard key={f.id} f={f} tone="important" />)}
            {tab === "important" && result.importantTweaks.length === 0 && <Empty msg="No suggested changes queued." />}
            {tab === "strengths" && (
              <div className="grid gap-2">
                {result.strengths.map((p, i) => (
                  <div key={i} className="flex items-start gap-3 border border-green-600/30 bg-green-50/50 p-3">
                    <CheckCircle2 size={18} className="text-green-600 mt-0.5 shrink-0" />
                    <span className="text-sm">{p}</span>
                  </div>
                ))}
                {result.strengths.length === 0 && <Empty msg="No standout strengths detected yet." />}
                {result.weaknesses.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="mono-label !text-[0.58rem] !text-flame">Weaknesses</p>
                    {result.weaknesses.map((w, i) => (
                      <div key={i} className="flex items-start gap-3 border border-flame/30 bg-flame/5 p-3">
                        <AlertTriangle size={16} className="text-flame mt-0.5 shrink-0" />
                        <span className="text-sm">{w}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {result.topImprovements.length > 0 && (
            <div className="mt-6 border-2 border-ink bg-white p-4">
              <p className="mono-label mb-3">Top Improvements</p>
              <div className="space-y-2">
                {result.topImprovements.map((t, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <ArrowRight size={15} className="text-flame mt-0.5 shrink-0" />
                    <span>{t}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function Badge({ label, value, good, warn }: { label: string; value: string; good?: boolean; warn?: boolean }) {
  const color = good ? "#16a34a" : warn ? "#f97316" : "#dc2626";
  return (
    <div className="border-2 px-5 py-4 text-center min-w-[110px] bg-white" style={{ borderColor: color }}>
      <div className="mono-label !text-[0.58rem]">{label}</div>
      <div className="text-2xl font-900 leading-none mt-2" style={{ color }}>{value}</div>
    </div>
  );
}

function FixCard({ f, tone }: { f: FixItem; tone: "critical" | "important" }) {
  const isCrit = tone === "critical";
  const Icon = isCrit ? TriangleAlert : AlertTriangle;
  const accent = isCrit ? "#dc2626" : "#f97316";
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className="border border-ink/15 bg-white p-4" style={{ borderLeft: `4px solid ${accent}` }}>
      <div className="flex items-center justify-between">
        <span className="mono-label !text-[0.56rem]" style={{ color: accent }}>{f.category}</span>
        <Icon size={15} style={{ color: accent }} />
      </div>
      <h3 className="font-800 mt-2 leading-snug">{f.title}</h3>
      <p className="text-sm text-ink/75 mt-1">{f.description}</p>
      {f.location && <p className="text-[0.7rem] text-smoke mt-1">↳ {f.location}</p>}
      <p className="text-xs text-smoke mt-2 italic">{f.whyItMatters}</p>

      {f.originalText && (
        <div className="mt-3 border border-red-200 bg-red-50 p-2 text-sm">
          <span className="mono-label !text-[0.52rem] !text-red-600">Original</span>
          <p className="text-red-900 mt-1 line-through decoration-red-400/60">{f.originalText}</p>
        </div>
      )}
      {f.suggestedFix && (
        <div className="mt-2 border border-green-200 bg-green-50 p-2 text-sm">
          <span className="mono-label !text-[0.52rem] !text-green-700">Playbook-compliant rewrite</span>
          <p className="text-green-900 mt-1">{f.suggestedFix}</p>
        </div>
      )}
      {f.action && !f.suggestedFix && (
        <div className="mt-2 flex items-start gap-2 text-sm">
          <ArrowRight size={15} className="text-flame mt-0.5 shrink-0" />
          <span>{f.action}</span>
        </div>
      )}
    </motion.div>
  );
}

function Empty({ msg }: { msg: string }) {
  return (
    <div className="border border-dashed border-ink/25 p-8 text-center text-sm text-smoke">{msg}</div>
  );
}
