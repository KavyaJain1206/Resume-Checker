"""
rule_engine.py
Deterministic resume diagnostic engine. Every rule maps to a specific chapter
of "The Resume Playbook 2026". Produces the exact JSON contract the dashboard
consumes. No LLM, no randomness  -  same resume always yields the same score.
"""
from __future__ import annotations
import re
import uuid
from typing import Dict, List, Optional

from pdf_extract import ExtractedResume
import playbook as PB

# ---------------------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------------------
NUMBER_RE = re.compile(
    r"(\d+\.?\d*\s?%|\$\s?\d|₹\s?\d|\d+\s?x\b|\d[\d,]{2,}|\b\d+\+|"
    r"\b\d+\s?(?:users|customers|hours?|hrs?|days?|weeks?|months?|k\b|million|"
    r"teams?|people|records?|rows?|apis?|projects?|followers|downloads|"
    r"students|clients|seconds?|minutes?))",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w\-%]+", re.IGNORECASE)
GITHUB_RE = re.compile(r"(github\.com/[\w\-]+|[\w\-]+\.(?:vercel|netlify|github\.io|dev))", re.IGNORECASE)
PHONE_RE = re.compile(r"(\+?\d[\d\s\-]{8,}\d)")
BULLET_RE = re.compile(r"^\s*[•\-\*•▪–›●>]\s+(.*)$")
UNPROFESSIONAL_EMAIL_RE = re.compile(
    r"(cool|hot|sexy|cute|angel|devil|killer|rockstar|gamer|xxx|69|420|007|"
    r"princess|prince|boss|king|queen|dude|guy|babe)\w*\d*@",
    re.IGNORECASE,
)


def _new_id(prefix: str, n: int) -> str:
    return f"{prefix}-{n}"


# ---------------------------------------------------------------------------
# Parsing helpers — module-level and parameterized (by heading_map) so any
# caller can reuse section/bullet detection against a different heading
# vocabulary, e.g. jd_match_engine.py parsing a job description instead of
# a resume. ParsedResume below is a thin, behavior-preserving wrapper around
# these for the existing resume-audit flow.
# ---------------------------------------------------------------------------
def is_heading(line: str, heading_map: Dict[str, List[str]]) -> Optional[str]:
    s = line.strip().lower().strip(":").strip()
    if len(s) > 40 or len(s.split()) > 5:
        return None
    for canon, variants in heading_map.items():
        for v in variants:
            if s == v or s.startswith(v):
                return canon
    return None


def detect_sections(lines: List[str], heading_map: Dict[str, List[str]]) -> Dict[str, int]:
    """Return {canonical_section: line_index_of_heading} in document order."""
    found: Dict[str, int] = {}
    for i, ln in enumerate(lines):
        canon = is_heading(ln, heading_map)
        if canon and canon not in found:
            found[canon] = i
    return found


def extract_bullets(lines: List[str]) -> List[str]:
    bullets = []
    for ln in lines:
        m = BULLET_RE.match(ln)
        if m:
            b = m.group(1).strip()
            if len(b) > 3:
                bullets.append(b)
    # Fallback: if no bullet glyphs found, treat lines under experience/projects
    # that look like achievements (verb-led, > 5 words) as bullets.
    if not bullets:
        for ln in lines:
            words = ln.split()
            if 5 <= len(words) <= 40 and words[0][0:1].isalpha():
                if words[0].lower().rstrip("s,.") in {v.rstrip("s") for v in PB.STRONG_VERBS} \
                   or ln.lower().startswith(tuple(PB.WEAK_STARTERS)):
                    bullets.append(ln.strip())
    return bullets


def section_text(lines: List[str], sections: Dict[str, int], canon: str) -> Optional[str]:
    if canon not in sections:
        return None
    start = sections[canon]
    after = [idx for name, idx in sections.items() if idx > start]
    end = min(after) if after else len(lines)
    return "\n".join(lines[start:end]).lower()


class ParsedResume:
    def __init__(self, ex: ExtractedResume):
        self.ex = ex
        self.text = ex.raw_text
        self.lower = ex.raw_text.lower()
        self.lines = ex.lines
        self.sections = detect_sections(self.lines, PB.STANDARD_HEADINGS)
        self.bullets = extract_bullets(self.lines)
        self.emails = EMAIL_RE.findall(self.text)
        self.links = {
            "linkedin": (LINKEDIN_RE.search(self.text) or [None]) and
                        (LINKEDIN_RE.search(self.text).group(0) if LINKEDIN_RE.search(self.text) else None),
            "github": (GITHUB_RE.search(self.text).group(0) if GITHUB_RE.search(self.text) else None),
        }


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------
class DiagnosticEngine:
    def __init__(self, parsed: ParsedResume, target_role: str,
                 experience_level: str, file_name: str = "resume.pdf"):
        self.p = parsed
        self.role = target_role
        self.exp = experience_level
        self.file_name = file_name or "resume.pdf"
        self.is_fresher = experience_level in ("Fresher", "Internship")
        self.critical: List[dict] = []
        self.important: List[dict] = []
        self.passed: List[str] = []
        self.scores: Dict[str, int] = {}

    # -- dim 1 -------------------------------------------------------------
    def dim_ats_safety(self) -> int:
        score = 100
        ex = self.p.ex
        if ex.is_multi_column:
            score -= 40
            self.critical.append(self._fix(
                "ATS Safety", "Multi-column / sidebar layout detected",
                "A two-column layout is the #1 cause of parser failure. The ATS reads "
                "across columns and merges unrelated text, scrambling your experience.",
                location="Whole document",
                why="Per Playbook Ch.11, two-column templates are the single most common "
                    "reason qualified candidates get auto-rejected before a human sees them.",
                original="Two-column / sidebar template",
                fix="Rebuild in a single-column layout  -  no tables, text boxes or sidebars.",
            ))
        else:
            self.passed.append("Single-column ATS layout confirmed")
        if ex.has_images:
            score -= 30
            self.critical.append(self._fix(
                "ATS Safety", "Images / graphics detected in the PDF",
                "Photos, logos, icons and skill-rating bars are invisible to the parser and "
                "flag the file as ATS-hostile.",
                location="Whole document",
                why="Playbook Ch.11: the ATS can't read an image, so a '4/5 stars in Python' "
                    "bar conveys nothing and can break parsing.",
                original="Embedded image / icon / progress bar",
                fix="Remove all photos, icons, logos and rating bars. Use plain text only.",
            ))
        else:
            self.passed.append("No parsing-blocker images or skill bars detected")
        # standard headings reward
        std = sum(1 for k in ("experience", "education", "skills", "projects")
                  if k in self.p.sections)
        if std >= 3:
            self.passed.append("Standard section headings match Playbook standards")
        else:
            score -= 10
            self.important.append(self._tweak(
                "ATS Safety", "Non-standard or missing section headings",
                f"Only {std} of 4 core headings (Experience, Education, Skills, Projects) "
                "were detected.",
                why="Playbook Ch.11: the parser searches for the exact standard words. "
                    "Clever labels like 'My Journey' get skipped.",
                action="Use standard headings: Experience, Education, Skills, Projects.",
            ))
        # file naming convention
        fn = self.file_name.lower()
        if fn in ("resume.pdf", "cv.pdf") or re.search(r"(final|v\d|\(\d\)|copy)", fn):
            self.important.append(self._tweak(
                "ATS Safety", "Unprofessional file name",
                f"File is named '{self.file_name}'.",
                why="Playbook Ch.11 requires a clean, professional filename.",
                action="Rename to Firstname_Lastname_Resume.pdf.",
            ))
        else:
            self.passed.append("Professional file naming convention")
        return max(0, min(100, score))

    # -- dim 2 -------------------------------------------------------------
    def dim_contact(self) -> int:
        score = 100
        low = self.p.lower
        # forbidden personal details
        found_personal = [t for t in PB.FORBIDDEN_PERSONAL if t in low]
        if found_personal:
            score -= 25
            self.critical.append(self._fix(
                "Professionalism", "Forbidden personal details present",
                f"Detected: {', '.join(sorted(set(found_personal))[:4])}.",
                location="Header / footer",
                why="Playbook Ch.4 & 10: DOB, marital status, gender, religion and father's "
                    "name are outdated, add risk and zero value  -  some trigger bias filters.",
                original=", ".join(sorted(set(found_personal))[:4]),
                fix="Delete all personal details. Keep only name, phone, email, city, links.",
            ))
        else:
            self.passed.append("No forbidden personal details (DOB, gender, etc.)")
        # declaration line
        if any(m in low for m in PB.DECLARATION_MARKERS):
            score -= 20
            self.critical.append(self._fix(
                "Professionalism", "Legacy declaration / references line found",
                "An 'I hereby declare...' statement or 'references on request' line is present.",
                location="Bottom of resume",
                why="Playbook Ch.10: modern ATS resumes omit the declaration and signature  -  "
                    "it wastes a line and adds nothing.",
                original="I hereby declare that the above information is true...",
                fix="Delete the declaration, signature and 'references available on request'.",
            ))
        else:
            self.passed.append("No legacy declaration line found")
        # email quality
        if self.p.emails:
            if any(UNPROFESSIONAL_EMAIL_RE.search(e) for e in self.p.emails):
                score -= 20
                bad = next(e for e in self.p.emails if UNPROFESSIONAL_EMAIL_RE.search(e))
                self.important.append(self._tweak(
                    "Professionalism", "Unprofessional email address",
                    f"Found: {bad}",
                    why="Playbook Ch.4: recruiters read a 'coolguy123@' address as carelessness.",
                    action="Use a professional address, e.g. firstname.lastname@gmail.com.",
                ))
            else:
                self.passed.append("Professional email address")
        else:
            score -= 15
            self.important.append(self._tweak(
                "Professionalism", "No email address detected",
                "The parser could not find a contact email in the body.",
                why="Playbook Ch.4: contact info must sit in the body, not the header margin "
                    "which many ATS skip.",
                action="Add a professional email in the body text of the header.",
            ))
        # links
        if self.p.links.get("linkedin"):
            self.passed.append("Clean LinkedIn URL present")
        else:
            score -= 10
            self.important.append(self._tweak(
                "Professionalism", "Missing / non-custom LinkedIn URL",
                "No customized linkedin.com/in/ URL detected.",
                why="Playbook Ch.4 & 16: a custom LinkedIn URL is expected and cross-checked.",
                action="Add a customized URL: linkedin.com/in/yourname.",
            ))
        return max(0, min(100, score))

    # -- dim 3 -------------------------------------------------------------
    def dim_hierarchy(self) -> int:
        order = PB.FRESHER_ORDER if self.is_fresher else PB.EXPERIENCED_ORDER
        present = [(name, idx) for name, idx in self.p.sections.items()]
        present.sort(key=lambda x: x[1])
        actual = [name for name, _ in present]
        # score by how well actual order respects the ideal relative order
        ideal_rank = {s: i for i, s in enumerate(order)}
        ranks = [ideal_rank[s] for s in actual if s in ideal_rank]
        inversions = sum(
            1 for i in range(len(ranks)) for j in range(i + 1, len(ranks))
            if ranks[i] > ranks[j]
        )
        max_inv = max(len(ranks) * (len(ranks) - 1) / 2, 1)
        score = round(100 * (1 - inversions / max_inv))
        # fresher-specific: education must sit above experience
        if self.is_fresher and "education" in self.p.sections and "experience" in self.p.sections:
            if self.p.sections["education"] > self.p.sections["experience"]:
                score -= 15
                self.important.append(self._tweak(
                    "Section Hierarchy", "Education is below Experience (fresher)",
                    "For freshers, Education should sit high  -  above Experience.",
                    why="Playbook Ch.3 & 15: freshers lead with Skills/Projects then Education; "
                        "reader weights the top third most.",
                    action="Move Education above the Experience/Internship section.",
                ))
        if not self.is_fresher and "education" in self.p.sections and "experience" in self.p.sections:
            if self.p.sections["education"] < self.p.sections["experience"]:
                score -= 15
                self.important.append(self._tweak(
                    "Section Hierarchy", "Education sits above Experience (experienced)",
                    "With 1+ years' experience, work history should lead and education drop below it.",
                    why="Playbook Ch.15: shift from 'what I studied' to 'what I've delivered'.",
                    action="Move the Experience section above Education.",
                ))
        if inversions == 0 and len(ranks) >= 3:
            self.passed.append("Section order matches the Playbook for your profile")
        return max(0, min(100, score))

    # -- dim 4 -------------------------------------------------------------
    def dim_metrics(self) -> int:
        bullets = self.p.bullets
        total = len(bullets)
        if total == 0:
            self.critical.append(self._fix(
                "Metric Quantification", "No achievement bullets detected",
                "The parser found no bullet points. Experience and projects should be written "
                "as quantified bullets, not paragraphs.",
                location="Experience / Projects",
                why="Playbook Ch.9: experience should be bullets, 1-2 lines each, not blocks of prose.",
                original="Paragraph-style descriptions",
                fix="Convert each responsibility into a bullet: action verb + what + tool + number.",
            ))
            return 20
        quantified = [b for b in bullets if NUMBER_RE.search(b)]
        density = len(quantified) / total
        score = round(min(100, density / 0.60 * 100))  # 60% target = 100
        if density < 0.60:
            unq = [b for b in bullets if not NUMBER_RE.search(b)][:3]
            for b in unq:
                self.critical.append(self._fix(
                    "Metric Quantification", "Unquantified bullet  -  add a hard number",
                    f"Only {len(quantified)} of {total} bullets ({round(density*100)}%) carry a "
                    "measurable result; the Playbook target is 60%+.",
                    location="Experience / Projects",
                    why="Playbook Ch.9: numbers are the fastest way to earn credibility in a "
                        "7-second scan. Recruiters skip bullets that lack quantified impact.",
                    original=b,
                    fix=self._suggest_metric(b),
                ))
        else:
            self.passed.append(f"Strong metric density ({round(density*100)}% of bullets quantified)")
        return max(0, min(100, score))

    def _suggest_metric(self, bullet: str) -> str:
        b = bullet.rstrip(".")
        low = b.lower()
        if any(w in low for w in ("react", "frontend", "web", "site", "app", "ui")):
            return b + ", reducing page-load time 35% and supporting 1,000+ active users."
        if any(w in low for w in ("api", "backend", "server", "node", "endpoint")):
            return b + " across 6 REST APIs, cutting response time 35%."
        if any(w in low for w in ("model", "ml", "data", "classifier", "dataset")):
            return b + ", reaching 94% accuracy on a 5,000-record dataset."
        if any(w in low for w in ("report", "dashboard", "automat")):
            return b + ", saving the team ~5 hours per week."
        return b + " for 200+ users, cutting task time 40%."

    # -- dim 5 -------------------------------------------------------------
    def dim_verbs(self) -> int:
        score = 100
        bullets = self.p.bullets
        weak = [b for b in bullets if b.lower().startswith(tuple(PB.WEAK_STARTERS))]
        if weak:
            score -= min(40, len(weak) * 12)
            for b in weak[:2]:
                self.important.append(self._tweak(
                    "Action Verbs", "Weak / passive bullet opener",
                    f'Bullet starts passively: "{b[:70]}..."',
                    why="Playbook Ch.9: never open with 'Responsible for' or 'Worked on'  -  "
                        "open with a verb that shows ownership.",
                    action="Rewrite starting with a strong verb (Built, Led, Automated, Reduced).",
                    original=b,
                    fix=self._rewrite_weak(b),
                ))
        else:
            if bullets:
                self.passed.append("Bullets open with strong action verbs")
        # buzzword soft-skill dumping
        low = self.p.lower
        skills_zone = self._section_text("skills")
        banned = [w for w in PB.BANNED_SOFT_SKILLS if w in (skills_zone or low)]
        standalone = [w for w in PB.STANDALONE_SOFT_SKILLS if skills_zone and w in skills_zone]
        hits = sorted(set(banned + standalone))
        if hits:
            score -= min(35, len(hits) * 10)
            self.important.append(self._tweak(
                "Soft Skill Buzzwords", "Unproven soft skills / buzzwords listed",
                f"Found: {', '.join(hits[:6])}.",
                why="Playbook Ch.7: standalone soft skills are worthless as keywords  -  the ATS "
                    "gives them little weight and recruiters skip them. Prove them in bullets instead.",
                action="Remove these from Skills; demonstrate them inside quantified achievements.",
            ))
        else:
            self.passed.append("No unproven soft-skill buzzwords in Skills")
        # filler words
        filler = [w for w in PB.FILLER_WORDS if re.search(rf"\b{re.escape(w)}\b", low)]
        if filler:
            score -= min(15, len(filler) * 5)
            self.important.append(self._tweak(
                "Action Verbs", "Filler words weaken your bullets",
                f"Found: {', '.join(sorted(set(filler))[:6])}.",
                why="Playbook Ch.9: filler like 'successfully' and 'various' adds length and "
                    "subtracts credibility.",
                action="Delete filler words  -  'Successfully completed' becomes 'Completed'.",
            ))
        return max(0, min(100, score))

    def _rewrite_weak(self, b: str) -> str:
        low = b.lower()
        for w in PB.WEAK_STARTERS:
            if low.startswith(w):
                rest = b[len(w):].strip().lstrip(":").strip()
                verb = "Built"
                if "manage" in low or "team" in low or "lead" in low:
                    verb = "Led"
                elif "data" in low or "report" in low:
                    verb = "Automated"
                elif "test" in low:
                    verb = "Tested"
                return f"{verb} {rest}" + ("" if rest.endswith(".") else ".")
        return b

    # -- dim 6 -------------------------------------------------------------
    def dim_projects(self) -> int:
        if not self.is_fresher and "projects" not in self.p.sections:
            self.passed.append("Projects optional for experienced profile  -  not penalized")
            return 85
        if "projects" not in self.p.sections:
            self.critical.append(self._fix(
                "Project Strength", "No Projects section  -  a fresher's strongest asset",
                "Freshers should lead with 2-4 real projects with quantified outcomes.",
                location="Projects",
                why="Playbook Ch.8: in the Indian market, strong projects with quantified "
                    "outcomes are the single biggest fresher differentiator.",
                original="(missing Projects section)",
                fix="Add 2-4 projects: Title, tech stack, problem, quantified result, live/GitHub link.",
            ))
            return 25
        zone = self._section_text("projects") or ""
        score = 60
        has_stack = bool(re.search(
            r"(react|node|python|java|sql|mongodb|tensorflow|flask|django|docker|"
            r"figma|power bi|·|—|\|)", zone, re.IGNORECASE))
        has_link = bool(re.search(r"(github|live|demo|link|http|vercel|netlify)", zone, re.IGNORECASE))
        has_metric = bool(NUMBER_RE.search(zone))
        if has_stack:
            score += 12; self.passed.append("Projects list a tech stack (doubles as ATS keywords)")
        else:
            self.important.append(self._tweak(
                "Project Strength", "Projects missing a tech stack",
                "No tools/frameworks listed with your projects.",
                why="Playbook Ch.8: the stack doubles as ATS keywords and signals depth.",
                action="Add the tech stack to each project, e.g. 'React, Node.js, MongoDB'.",
            ))
        if has_metric:
            score += 16; self.passed.append("Projects include quantified outcomes")
        else:
            self.critical.append(self._fix(
                "Project Strength", "Projects lack a measurable outcome",
                "No users, performance gain, accuracy or time-saved metric found in projects.",
                location="Projects",
                why="Playbook Ch.8: the measurable outcome is what students skip and recruiters "
                    "most want  -  users, % faster, accuracy, a live link.",
                original="Built an e-commerce website using HTML, CSS and JavaScript.",
                fix="Onboarded 220+ users; integrated Razorpay; cut page-load time 40% via lazy loading. [live · github]",
            ))
        if has_link:
            score += 12; self.passed.append("Projects link to a live demo or GitHub repo")
        else:
            self.important.append(self._tweak(
                "Project Strength", "Projects have no live / GitHub link",
                "No working demo or repository link detected.",
                why="Playbook Ch.8: if you list a project, a working link is proof recruiters verify.",
                action="Add a live demo and/or GitHub link to each project.",
            ))
        return max(0, min(100, score))

    # -- dim 7 -------------------------------------------------------------
    def dim_keywords(self) -> Dict:
        bench = PB.ROLE_KEYWORDS.get(self.role, [])
        low = self.p.lower
        found = [k for k in bench if k in low]
        missing = [k for k in bench if k not in low]
        score = round(100 * len(found) / max(len(bench), 1))
        if missing:
            self.important.append(self._tweak(
                "Keyword Tailoring", f"Missing high-priority keywords for {self.role}",
                f"Top gaps: {', '.join(missing[:5])}.",
                why="Playbook Ch.14: mirror the JD's exact terms  -  the ranking algorithm weighs "
                    "how many required keywords you match.",
                action=f"Weave these into real bullets where you genuinely have them: "
                       f"{', '.join(missing[:5])}.",
            ))
        else:
            self.passed.append(f"Strong keyword match for {self.role}")
        self._keyword_gaps = {"found": found[:12], "missingHighPriority": missing[:6]}
        return {"score": max(0, min(100, score)), "found": found, "missing": missing}

    # -- dim 8 -------------------------------------------------------------
    def dim_scan(self) -> int:
        score = 100
        # length: freshers -> 1 page
        if self.is_fresher and self.p.ex.page_count > 1:
            score -= 30
            self.important.append(self._tweak(
                "Recruiter Scan", "Resume exceeds one page (fresher)",
                f"Detected {self.p.ex.page_count} pages.",
                why="Playbook Ch.12: fresher resumes must be a single page  -  recruiters spending "
                    "7 seconds never reach a rambling page two.",
                action="Cut to one tight page; trim the least-relevant bullets.",
            ))
        # long bullets (> 2 lines ~ > 32 words)
        long_bullets = [b for b in self.p.bullets if len(b.split()) > 32]
        if long_bullets:
            score -= min(30, len(long_bullets) * 10)
            self.important.append(self._tweak(
                "Recruiter Scan", "Bullets run longer than two lines",
                f"{len(long_bullets)} bullet(s) exceed ~2 lines.",
                why="Playbook Ch.9 & 8: keep bullets to 1-2 lines for skimmability.",
                action="Tighten each long bullet to one crisp line with a number.",
            ))
        if score >= 90:
            self.passed.append("Concise, skimmable layout for the 7-second scan")
        return max(0, min(100, score))

    # -- dim 9 -------------------------------------------------------------
    def dim_summary(self) -> int:
        if "summary" not in self.p.sections:
            if self.is_fresher:
                self.important.append(self._tweak(
                    "Summary Quality", "No summary / objective line",
                    "A specific 2-3 line objective naming role, stack and proof is recommended.",
                    why="Playbook Ch.5: a specific objective plants your top keywords where the "
                        "algorithm and recruiter look first.",
                    action="Add: '[who you are] + [top 2-3 skills] + [strongest proof / target role]'.",
                ))
                return 50
            else:
                self.important.append(self._tweak(
                    "Summary Quality", "No professional summary",
                    "With experience, a 2-3 line summary is the stronger choice.",
                    why="Playbook Ch.5: summarize identity, top skills and a headline achievement.",
                    action="Add a 2-3 line professional summary naming the target role.",
                ))
                return 45
        zone = self._section_text("summary") or ""
        low = zone.lower()
        vague = [w for w in ("seeking a challenging", "reputed organization", "utilize my skills",
                             "grow with the company", "dynamic", "hardworking", "team player")
                 if w in low]
        has_number = bool(NUMBER_RE.search(zone))
        score = 100
        if vague:
            score -= 40
            self.important.append(self._tweak(
                "Summary Quality", "Vague / clichéd summary",
                f"Contains cliché(s): {', '.join(vague[:3])}.",
                why="Playbook Ch.5: 'seeking a challenging role in a reputed organization' says "
                    "nothing and is worse than no objective.",
                action="Replace with role + stack + a quantified proof point.",
                original="Hardworking individual seeking a challenging position in a reputed organization.",
                fix="Final-year CS student skilled in Python, SQL and React. Built 3 full-stack "
                    "projects, incl. an app used by 200+ classmates. Seeking a software developer role.",
            ))
        if not has_number:
            score -= 20
        if score >= 80 and not vague:
            self.passed.append("Summary is specific and value-driven")
        return max(0, min(100, score))

    # -- helpers -----------------------------------------------------------
    def _section_text(self, canon: str) -> Optional[str]:
        return section_text(self.p.lines, self.p.sections, canon)

    def _fix(self, category, title, description, location="", why="", original="", fix=""):
        return {
            "id": _new_id("fix", len(self.critical) + 1),
            "category": category, "title": title, "description": description,
            "whyItMatters": why, "location": location,
            "originalText": original, "suggestedFix": fix,
        }

    def _tweak(self, category, title, description, why="", action="", original="", fix=""):
        item = {
            "id": _new_id("tweak", len(self.important) + 1),
            "category": category, "title": title, "description": description,
            "whyItMatters": why, "action": action,
        }
        if original:
            item["originalText"] = original
        if fix:
            item["suggestedFix"] = fix
        return item

    # -- orchestration -----------------------------------------------------
    def run(self) -> dict:
        self.scores["atsSafety"] = self.dim_ats_safety()
        self.scores["contactProfessionalism"] = self.dim_contact()
        self.scores["sectionHierarchy"] = self.dim_hierarchy()
        self.scores["metricQuantification"] = self.dim_metrics()
        self.scores["verbAndBuzzwordQuality"] = self.dim_verbs()
        self.scores["projectStrength"] = self.dim_projects()
        kw = self.dim_keywords()
        self.scores["keywordTailoring"] = kw["score"]
        self.scores["recruiterScan"] = self.dim_scan()
        self.scores["summaryQuality"] = self.dim_summary()

        overall = round(sum(self.scores[k] * PB.WEIGHTS[k] for k in PB.WEIGHTS) /
                        sum(PB.WEIGHTS.values()))

        ats_risk = "LOW" if self.scores["atsSafety"] >= 80 else \
                   "MED" if self.scores["atsSafety"] >= 55 else "HIGH"
        scan = "PASS" if self.scores["recruiterScan"] >= 70 and overall >= 60 else "FAIL"

        return {
            "overallScore": overall,
            "recruiter7SecScan": scan,
            "atsRiskLevel": ats_risk,
            "categoryScores": self.scores,
            "criticalFixes": self.critical,
            "importantTweaks": self.important,
            "keywordGaps": getattr(self, "_keyword_gaps", {"found": [], "missingHighPriority": []}),
            "passedChecks": self.passed,
            "meta": {
                "targetRole": self.role,
                "experienceLevel": self.exp,
                "bulletCount": len(self.p.bullets),
                "pageCount": self.p.ex.page_count,
                "fileName": self.file_name,
            },
        }


def audit(extracted: ExtractedResume, target_role: str,
          experience_level: str, file_name: str = "resume.pdf") -> dict:
    parsed = ParsedResume(extracted)
    engine = DiagnosticEngine(parsed, target_role, experience_level, file_name)
    return engine.run()
