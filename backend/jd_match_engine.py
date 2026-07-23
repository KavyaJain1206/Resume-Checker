"""
jd_match_engine.py
Deterministic Resume-vs-Job-Description matcher. Works for any profession:
expected keywords/skills/education/experience/certifications are mined
from the uploaded JD's own text — never from a fixed per-role list (see
playbook.ROLE_KEYWORDS, which this module deliberately does not use).

No LLM, no randomness: the same resume+JD pair always produces the same
report. Reuses rule_engine's section/bullet parsing and regexes, and
playbook's soft-skill/strong-verb constants, rather than reimplementing
them.

ANTI-HALLUCINATION RULE: never assert a fact this module cannot point to
a specific piece of extracted text for. Where a value can't be verified,
the field is None/"Unknown" — never a guessed default presented as fact.
Every phrase-triggered inference (candidate type beyond the structural
fresher/experienced fallback) is tagged confidence "Estimated", never
"Verified" — it's a conclusion about a whole person from a text match,
not a checkable fact.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

import playbook as PB
from pdf_extract import ExtractedResume
from rule_engine import (
    BULLET_RE, EMAIL_RE, GITHUB_RE, LINKEDIN_RE, NUMBER_RE, PHONE_RE,
    detect_sections, extract_bullets, is_heading, section_text,
)

# ---------------------------------------------------------------------------
# SCORING CONFIGURATION — every tunable weight/threshold/deduction lives
# here. Tuning the engine later means changing this block only.
# ---------------------------------------------------------------------------
SCORING_CONFIG = {
    "zone_weight": {"required": 3.0, "preferred": 1.5},
    "dedup_dominance_ratio": 1.5,
    "fresher_weights": {
        "keywordMatch": 0.20, "skillsMatch": 0.20, "projectsMatch": 0.20,
        "educationMatch": 0.15, "experienceMatch": 0.10,
        "responsibilitiesMatch": 0.05, "certificationMatch": 0.10,
    },
    "experienced_weights": {
        "keywordMatch": 0.20, "experienceMatch": 0.20, "responsibilitiesMatch": 0.15,
        "skillsMatch": 0.15, "certificationMatch": 0.15,
        "educationMatch": 0.10, "projectsMatch": 0.05,
    },
    "education_score_full": 100,
    "education_score_mismatch": 30,
    "certification_score_full": 100,
    "certification_score_absent": 20,
    "ats_deduction_multi_column": 40,
    "ats_deduction_images": 30,
    "ats_deduction_missing_headings": 15,
    "recommendation_strong_threshold": 80,
    "recommendation_moderate_threshold": 55,
    "recommendation_strong_max_missing_required": 2,
    "intern_ratio_threshold": 0.70,
}

SCORE_DESCRIPTIONS = {
    "resumeAtsScore": (
        "Evaluates only ATS readability and parser friendliness — formatting, "
        "layout, section structure. Independent of any specific job."
    ),
    "jdMatchScore": (
        "Evaluates compatibility between this resume and the uploaded job "
        "description specifically."
    ),
}

FRESHER_LIKE_TYPES = {"fresher", "student", "intern", "researcher"}

# ---------------------------------------------------------------------------
# JD-specific section headings (distinct from playbook.STANDARD_HEADINGS,
# which is scoped to resume sections). "required"/"preferred" drive keyword
# weighting; the rest drive keyword categorization.
# ---------------------------------------------------------------------------
JD_SECTION_HEADINGS: Dict[str, List[str]] = {
    "required": [
        "required qualifications", "requirements", "must have", "must-have",
        "minimum qualifications", "basic qualifications", "what you'll need",
        "who you are",
    ],
    "preferred": [
        "preferred qualifications", "nice to have", "nice-to-have",
        "bonus points", "preferred skills", "good to have",
    ],
    "responsibilities": [
        "responsibilities", "what you'll do", "key responsibilities",
        "duties", "role overview", "the role", "job duties",
    ],
    "tools": ["tools", "technologies", "tech stack", "software", "systems used"],
    "education": ["education", "educational qualifications", "academic requirements"],
    "certifications": ["certifications", "certification", "licensure", "licenses"],
}

# A plain English stopword list plus common JD boilerplate — no NLP
# dependency, just a hardcoded constant in the same style as playbook.py.
STOPWORDS = {
    "a", "about", "above", "after", "again", "all", "also", "an", "and", "any",
    "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "can", "could", "did", "do", "does",
    "doing", "down", "during", "each", "few", "for", "from", "further", "had",
    "has", "have", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its",
    "itself", "just", "me", "more", "most", "my", "myself", "no", "nor",
    "not", "now", "of", "off", "on", "once", "only", "or", "other", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "you", "your", "yours", "yourself", "yourselves",
    # JD boilerplate — near-universal across postings regardless of field
    "job", "role", "position", "candidate", "candidates", "applicant",
    "opportunity", "join", "team", "company", "organization", "looking",
    "seeking", "ideal", "strong", "excellent", "ability", "able", "including",
    "etc", "years", "year", "work", "working", "experience", "skills",
    "knowledge", "understanding", "please", "apply", "requirement",
    "requirements", "qualification", "qualifications", "preferred",
    "required", "proficiency", "related", "field", "equivalent", "basic",
    "minimum", "plus", "responsibilities", "responsibility",
}

ACRONYM_MAP = {
    "oop": "object oriented programming", "ai": "artificial intelligence",
    "ml": "machine learning", "hr": "human resources",
    "qa": "quality assurance", "ui": "user interface",
    "ux": "user experience", "seo": "search engine optimization",
    "sem": "search engine marketing", "crm": "customer relationship management",
    "erp": "enterprise resource planning", "kpi": "key performance indicator",
    "roi": "return on investment", "cpa": "certified public accountant",
    "cfa": "chartered financial analyst", "pmp": "project management professional",
    "cpc": "cost per click", "b2b": "business to business",
    "b2c": "business to consumer", "p&l": "profit and loss",
    "gaap": "generally accepted accounting principles", "kyc": "know your customer",
    "aml": "anti money laundering", "sop": "standard operating procedure",
    "sla": "service level agreement", "nda": "non disclosure agreement",
    "hipaa": "health insurance portability and accountability act",
    "emr": "electronic medical records", "ehr": "electronic health records",
    "cad": "computer aided design", "bim": "building information modeling",
    "llb": "bachelor of laws", "llm": "master of laws",
    "cme": "continuing medical education", "cle": "continuing legal education",
    "shrm": "society for human resource management", "phr": "professional in human resources",
    "ga4": "google analytics", "ppc": "pay per click", "ctr": "click through rate",
}

DEGREE_RE = re.compile(
    r"\b(b\.?\s?tech|b\.?\s?e\.?|b\.?\s?sc|b\.?\s?a\b|b\.?\s?com|bba|bca|llb|llm|"
    r"mbbs|m\.?\s?d\b|d\.?\s?o\b|m\.?\s?tech|mba|mca|m\.?\s?s\b|m\.?\s?a\b|"
    r"ph\.?\s?d|j\.?\s?d\b|rn|bsn|msn|cpa|cfa|"
    r"bachelor'?s?(?:\s+degree)?|master'?s?(?:\s+degree)?|doctorate|diploma|"
    r"associate'?s?\s+degree)\b",
    re.IGNORECASE,
)
YEARS_REQUIRED_RE = re.compile(
    r"(\d{1,2})\+?\s*years?\s+(?:of\s+)?(?:[a-z]+\s+){0,1}experience", re.IGNORECASE
)
_WORD_RE = re.compile(r"[a-z][a-z0-9+/#.\-]*")

# Candidate-type trigger phrases — high-precision, checked before falling
# through to the structural fresher/experienced cascade. Every hit is
# tagged confidence "Estimated" (see module docstring).
CANDIDATE_TYPE_TRIGGERS = [
    ("career_changer", re.compile(r"career\s+chang\w*|transitioning\s+into", re.IGNORECASE)),
    ("student", re.compile(r"currently\s+pursuing|student\s+at", re.IGNORECASE)),
    ("researcher", re.compile(r"research\s+assistant|phd\s+candidate", re.IGNORECASE)),
    ("returning", re.compile(r"career\s+break|sabbatical|returning\s+to\s+the\s+workforce", re.IGNORECASE)),
]
# Freelancer is precision-guarded separately (see _infer_candidate_type) —
# a single old "Freelance Designer" job title several roles back must not
# relabel the whole candidate, so it's only checked in the Summary or the
# most-recently-listed Experience entry, not the whole document.
FREELANCER_RE = re.compile(r"freelance|independent\s+contractor|self[\s\-]employed", re.IGNORECASE)
INTERN_LINE_RE = re.compile(r"\bintern(ship)?\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Normalization: lowercase, acronym-canonicalize, light stemming. Applied to
# both the JD-derived phrases and the resume text so "OOP" on a resume
# matches "Object Oriented Programming" in a JD, and "skills"/"skill" match.
# ---------------------------------------------------------------------------
def _stem(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    # Only strip "-es" after the letters that actually trigger it in English
    # plurals (boxes, watches, glasses) — NOT after e.g. "kubernetes".
    if len(word) > 4 and word.endswith("es") and word[-3] in ("s", "x", "z", "h"):
        return word[:-2]
    if word.endswith("s") and len(word) > 3 and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def _expand_acronyms(text: str) -> str:
    low = text.lower()
    for acro, expansion in ACRONYM_MAP.items():
        low = re.sub(rf"\b{re.escape(acro)}\b", expansion, low)
    return low


def _tokenize(text: str) -> tuple[List[str], List[str]]:
    """Returns (raw_words, stemmed_words), positionally aligned. raw_words
    (acronym-expanded, lowercased, but NOT stemmed) is what gets shown to
    the user; stemmed_words is only ever used for matching, never display —
    a lightweight stemmer occasionally mangles a proper noun ("kubernetes"
    -> "kubernete"), which is harmless for matching (both sides of the
    comparison go through the same stemming) but must never leak into
    output text."""
    raw = _WORD_RE.findall(_expand_acronyms(text))
    return raw, [_stem(w) for w in raw]


def normalize(text: str) -> str:
    """Stemmed, space-joined form used for substring/containment matching."""
    return " ".join(_tokenize(text)[1])


def _zone_for_line(idx: int, sections: Dict[str, int]) -> Optional[str]:
    """Which canonical JD heading zone contains line idx, if any (the
    nearest preceding heading — sections are non-overlapping spans)."""
    containing, containing_start = None, -1
    for canon, start in sections.items():
        if start <= idx and start > containing_start:
            containing, containing_start = canon, start
    return containing


def _classify(phrase_key: str, zone: Optional[str]) -> str:
    if phrase_key in PB.STANDALONE_SOFT_SKILLS:
        return "soft_skills"
    if "certif" in phrase_key or "licens" in phrase_key or zone == "certifications":
        return "certifications"
    if zone == "tools":
        return "tools"
    if zone == "education" or DEGREE_RE.search(phrase_key):
        return "education"
    if zone == "responsibilities":
        return "responsibilities"
    return "skills_domain"


def _dedupe_subsumed(candidates: Dict[str, dict], parent_edges: Dict[str, set]) -> Dict[str, dict]:
    """O(n) dedup: drop a shorter n-gram if a longer n-gram containing it
    is dominant. Extraction never builds n-grams beyond n=3, so the deepest
    containment chain is trigram->bigram->unigram (2 hops) — processing
    candidates longest-first and propagating a `dominant_ancestor_weight`
    (each node's parents are already resolved by the time we reach it)
    is transitively equivalent to an all-pairs comparison for this depth,
    without the O(n^2) cost."""
    ratio = SCORING_CONFIG["dedup_dominance_ratio"]
    by_len_desc = sorted(candidates.keys(), key=lambda k: -len(k.split()))
    dominant: Dict[str, float] = {}
    for key in by_len_desc:
        own_weight = candidates[key]["weight"]
        parent_dominant = max((dominant[p] for p in parent_edges.get(key, ()) if p in dominant), default=0.0)
        dominant[key] = max(own_weight, parent_dominant)

    removed = set()
    for key in candidates:
        own_weight = candidates[key]["weight"]
        for parent in parent_edges.get(key, ()):
            if parent in dominant and dominant[parent] >= ratio * own_weight:
                removed.add(key)
                break
    return {k: v for k, v in candidates.items() if k not in removed}


def extract_keyphrases(jd_lines: List[str], jd_sections: Dict[str, int]) -> List[dict]:
    """Position/pattern-weighted keyphrase extraction — NOT raw frequency
    (a single JD is too short for frequency alone to mean anything). A term
    inside a Requirements bullet outweighs one repeated in filler prose."""
    bullet_lines = {i for i, ln in enumerate(jd_lines) if BULLET_RE.match(ln)}
    candidates: Dict[str, dict] = {}
    parent_edges: Dict[str, set] = {}

    for i, line in enumerate(jd_lines):
        zone = _zone_for_line(i, jd_sections)
        zone_weight = SCORING_CONFIG["zone_weight"].get(zone, 1.0)
        in_bullet = i in bullet_lines
        # Segment on list separators BEFORE normalizing — comma/semicolon-
        # separated list items (very common in JDs: "SEO, content strategy,
        # and social media") must not bleed into each other as false n-grams.
        for segment in re.split(r"[,;]", line):
            raw_words, stemmed_words = _tokenize(segment)
            for n in (1, 2, 3):
                for start in range(len(stemmed_words) - n + 1):
                    stem_slice = stemmed_words[start:start + n]
                    if any(w in STOPWORDS for w in stem_slice) or any(len(w) <= 1 for w in stem_slice):
                        continue
                    key = " ".join(stem_slice)
                    if key in PB.BANNED_SOFT_SKILLS:
                        continue
                    if key not in candidates:
                        candidates[key] = {
                            "key": key, "display": " ".join(raw_words[start:start + n]),
                            "weight": 0.0, "zone": zone, "category": _classify(key, zone),
                        }
                    candidates[key]["weight"] += zone_weight + (1.0 if in_bullet else 0.0)

                    if n > 1:
                        for child_slice in (stem_slice[1:], stem_slice[:-1]):
                            if any(w in STOPWORDS for w in child_slice) or any(len(w) <= 1 for w in child_slice):
                                continue
                            child_key = " ".join(child_slice)
                            if child_key != key:
                                parent_edges.setdefault(child_key, set()).add(key)

    candidates = _dedupe_subsumed(candidates, parent_edges)
    ranked = sorted(candidates.values(), key=lambda c: -c["weight"])
    return ranked[:25]


def resume_ats_score(extracted: ExtractedResume, resume_sections: Dict[str, int]) -> tuple[int, List[str]]:
    """Independent of DiagnosticEngine.dim_ats_safety by design (that method
    mutates instance state rather than returning pure data, so extracting it
    would be a riskier change to a working, tested method for no real
    benefit here). Reuses the same underlying signals from pdf_extract."""
    score = 100
    risks: List[str] = []
    if extracted.is_multi_column:
        score -= SCORING_CONFIG["ats_deduction_multi_column"]
        risks.append("Multi-column / sidebar layout detected — a common cause of ATS parser failure.")
    if extracted.has_images:
        score -= SCORING_CONFIG["ats_deduction_images"]
        risks.append("Images, icons, or skill-rating bars detected — invisible to most parsers.")
    std = sum(1 for k in ("experience", "education", "skills") if k in resume_sections)
    if std < 2:
        score -= SCORING_CONFIG["ats_deduction_missing_headings"]
        risks.append("Missing standard section headings (Experience / Education / Skills).")
    return max(0, min(100, score)), risks


# ---------------------------------------------------------------------------
# Name extraction — scans only the header block (first 6 lines), rejects
# contact-info/bullet/heading lines via already-existing regexes, requires
# 2-4 alpha-only tokens. Returns None (not an error) when nothing survives —
# the frontend renders that as "Not Provided", same convention as every
# other optional field.
# ---------------------------------------------------------------------------
def _extract_name(resume_lines: List[str]) -> Optional[str]:
    for line in resume_lines[:6]:
        s = line.strip()
        if not s or len(s) > 60:
            continue
        if EMAIL_RE.search(s) or PHONE_RE.search(s) or LINKEDIN_RE.search(s) or GITHUB_RE.search(s):
            continue
        if BULLET_RE.match(s):
            continue
        if is_heading(s, PB.STANDARD_HEADINGS):
            continue
        words = s.split()
        if not (2 <= len(words) <= 4):
            continue
        if any(re.search(r"\d", w) for w in words):
            continue
        if not all(re.fullmatch(r"[A-Za-z][A-Za-z'.\-]*\.?", w) for w in words):
            continue
        return s.title() if s.isupper() else s
    return None


def _extract_optional_profile(resume_extracted: ExtractedResume) -> dict:
    """Purely informational — never feeds into any score. None means
    "Not Provided", never "Missing", and is never penalized."""
    text = resume_extracted.raw_text
    email_m = EMAIL_RE.search(text)
    phone_m = PHONE_RE.search(text)
    linkedin_m = LINKEDIN_RE.search(text)
    github_m = GITHUB_RE.search(text)
    return {
        "email": email_m.group(0) if email_m else None,
        "phone": phone_m.group(0).strip() if phone_m else None,
        "linkedin": linkedin_m.group(0) if linkedin_m else None,
        "github": github_m.group(0) if github_m else None,
    }


def _optional_field_gap_tweaks(optional_profile: dict, jd_text: str, start_idx: int) -> List[dict]:
    """Only flags an optional field's absence if the JD itself signals it
    matters (e.g. a Software JD mentioning GitHub) — a Law JD that never
    mentions GitHub never triggers this, per the requirement that optional
    fields are only evaluated when the JD explicitly cares."""
    jd_low = jd_text.lower()
    checks = [
        ("github", ("github", "portfolio", "repo"), "GitHub/portfolio link"),
        ("linkedin", ("linkedin",), "LinkedIn profile"),
    ]
    gaps = []
    for field, hints, label in checks:
        if optional_profile.get(field):
            continue
        if any(h in jd_low for h in hints):
            gaps.append(_fix_item(
                start_idx + len(gaps) + 1, "jd-imp", "Optional Profile Field",
                f"Missing {label}",
                f"The job description suggests {label.lower()}-related expectations, but none was found on the resume.",
                f"This JD signals a {label.lower()} may matter for this role.",
                f"Consider adding your {label.lower()} if you have one.",
            ))
    return gaps


# ---------------------------------------------------------------------------
# Candidate-type inference. See module docstring for the confidence rule:
# every phrase-triggered type is "Estimated", never "Verified". Structural
# fresher/experienced classification is the default fallback.
# ---------------------------------------------------------------------------
def _infer_candidate_type(resume_extracted: ExtractedResume, resume_sections: Dict[str, int],
                          resume_lines: List[str]) -> dict:
    text = resume_extracted.raw_text
    summary_zone = section_text(resume_lines, resume_sections, "summary") or ""
    exp_zone = section_text(resume_lines, resume_sections, "experience") or ""
    signals: List[str] = []
    matched_type: Optional[str] = None
    matched_phrase: Optional[str] = None

    for type_name, pattern in CANDIDATE_TYPE_TRIGGERS:
        m = pattern.search(text)
        if m:
            signals.append(f'{type_name}: matched "{m.group(0)}"')
            if matched_type is None:
                matched_type, matched_phrase = type_name, m.group(0)

    if "publications" in resume_sections:
        signals.append("researcher: Publications section present")
        if matched_type is None:
            matched_type, matched_phrase = "researcher", "Publications section"

    # Freelancer: precision-guarded to Summary + most-recent (first-listed)
    # Experience entry only, so one old job title several roles back can't
    # relabel the whole candidate.
    recent_experience = exp_zone[:400]
    freelancer_hit = FREELANCER_RE.search(summary_zone) or FREELANCER_RE.search(recent_experience)
    if freelancer_hit:
        signals.append(f'freelancer: matched "{freelancer_hit.group(0)}"')
        if matched_type is None:
            matched_type, matched_phrase = "freelancer", freelancer_hit.group(0)

    if matched_type is not None:
        label = matched_type.replace("_", " ").title()
        return {
            "type": matched_type, "confidence": "Estimated",
            "detail": f'Classified as {label} — matched "{matched_phrase}".',
            "signals": signals,
        }

    # Structural fallback: fresher vs. experienced.
    years_hit = YEARS_REQUIRED_RE.search(text)
    if years_hit:
        years = int(years_hit.group(1))
        if years >= 2:
            base_type, base_conf = "experienced", "Verified"
            base_detail = f"Resume states {years} years of experience."
        else:
            base_type, base_conf = "fresher", "Verified"
            base_detail = f"Resume states {years} years of experience."
    elif "experience" not in resume_sections:
        base_type, base_conf = "fresher", "Unknown"
        base_detail = "No Experience section found on resume."
    else:
        proj_zone = section_text(resume_lines, resume_sections, "projects") or ""
        exp_words, proj_words = len(exp_zone.split()), len(proj_zone.split())
        if exp_words >= proj_words:
            base_type, base_conf = "experienced", "Estimated"
            base_detail = (f"Experience section ({exp_words} words) is at least as substantial as "
                            f"Projects ({proj_words} words); no explicit years-of-experience phrase found.")
        else:
            base_type, base_conf = "fresher", "Estimated"
            base_detail = (f"Projects section ({proj_words} words) dominates over Experience "
                            f"({exp_words} words); no explicit years-of-experience phrase found.")

    if base_type == "fresher" and exp_zone.strip():
        exp_lines = [ln for ln in exp_zone.splitlines() if ln.strip()]
        intern_lines = [ln for ln in exp_lines if INTERN_LINE_RE.search(ln)]
        if exp_lines and len(intern_lines) / len(exp_lines) >= SCORING_CONFIG["intern_ratio_threshold"]:
            signals.append(f"intern: {len(intern_lines)}/{len(exp_lines)} Experience lines mention internship")
            return {
                "type": "intern", "confidence": "Estimated",
                "detail": (f"Classified as Intern — {len(intern_lines)} of {len(exp_lines)} "
                           f"Experience lines mention an internship."),
                "signals": signals,
            }

    return {"type": base_type, "confidence": base_conf, "detail": base_detail, "signals": signals}


def _compose_recruiter_view(scores: Dict[str, Optional[int]], missing_required_count: int,
                             recommendation: str) -> str:
    """Composed from the computed numbers via simple rules — not generated
    prose — so it stays deterministic and reproducible."""
    labels = {
        "keywordMatch": "keyword alignment", "skillsMatch": "skills alignment",
        "educationMatch": "education fit", "experienceMatch": "experience fit",
        "certificationMatch": "certification fit", "responsibilitiesMatch": "responsibilities alignment",
        "projectsMatch": "project alignment",
    }
    active = {k: v for k, v in scores.items() if v is not None}
    best_key = max(active, key=active.get)
    worst_key = min(active, key=active.get)
    parts = [f"A recruiter scanning this resume against the JD would notice strong "
             f"{labels[best_key]} ({active[best_key]}%)."]
    if missing_required_count:
        parts.append(f"{missing_required_count} required qualification(s) aren't clearly "
                      f"demonstrated — that's the biggest risk to address first.")
    elif active[worst_key] < 60:
        parts.append(f"The weakest area is {labels[worst_key]} ({active[worst_key]}%), worth "
                      f"strengthening before applying.")
    parts.append(f"Overall: {recommendation}.")
    return " ".join(parts)


def _fix_item(idx: int, prefix: str, category: str, title: str, description: str,
              why: str, action: str) -> dict:
    return {
        "id": f"{prefix}-{idx}", "category": category, "title": title,
        "description": description, "whyItMatters": why, "action": action,
    }


def _category(score: Optional[int], matched: int, total: int, confidence: str,
              detail: str, rules: List[str]) -> dict:
    return {"score": score, "matched": matched, "total": total,
            "confidence": confidence, "detail": detail, "rules": rules}


def _score_breakdown(percentage: int, matched: int, total: int, confidence: str, reason: str) -> dict:
    return {
        "percentage": percentage,
        "matchedCount": matched,
        "totalCount": total,
        "confidence": confidence,
        "reasonForDeductions": reason,
    }


def _missing_item(kp: dict) -> dict:
    importance = "Required" if kp["zone"] == "required" else ("Preferred" if kp["zone"] == "preferred" else "Nice to Have")
    section_label = {
        "soft_skills": "Skills", "certifications": "Certifications", "tools": "Tools",
        "education": "Education", "responsibilities": "Responsibilities", "skills_domain": "Skills",
    }.get(kp["category"], "General")
    return {
        "term": kp["display"], "importance": importance, "sectionExpected": section_label,
        "reason": f'This term appears in the job description ({importance.lower()}) but was not found on the resume.',
    }


def analyze(resume_extracted: ExtractedResume, jd_extracted: ExtractedResume,
            resume_file_name: str, jd_file_name: str) -> dict:
    resume_lines = resume_extracted.lines
    resume_sections = detect_sections(resume_lines, PB.STANDARD_HEADINGS)
    resume_bullets = extract_bullets(resume_lines)
    resume_text_norm = normalize(resume_extracted.raw_text)
    resume_skills_zone_norm = normalize(section_text(resume_lines, resume_sections, "skills") or "")

    jd_lines = jd_extracted.lines
    jd_sections = detect_sections(jd_lines, JD_SECTION_HEADINGS)
    keyphrases = extract_keyphrases(jd_lines, jd_sections)

    candidate_name = _extract_name(resume_lines)
    candidate_info = _infer_candidate_type(resume_extracted, resume_sections, resume_lines)
    optional_profile = _extract_optional_profile(resume_extracted)

    # --- keyword match (all keyphrases) ------------------------------------
    total_weight = sum(kp["weight"] for kp in keyphrases) or 1.0
    matched_weight = 0.0
    found_keywords: List[str] = []
    missing_required_kps: List[dict] = []
    missing_other_kps: List[dict] = []

    # --- skills match (skills_domain/tools category, vs. Skills zone) ------
    skills_kps = [kp for kp in keyphrases if kp["category"] in ("skills_domain", "tools")]
    skills_total_weight = sum(kp["weight"] for kp in skills_kps) or 1.0
    skills_matched_weight = 0.0
    skills_matched_count = 0

    # --- responsibilities match (vs. whole resume text) ---------------------
    responsibilities_kps = [kp for kp in keyphrases if kp["category"] == "responsibilities"]
    resp_total_weight = sum(kp["weight"] for kp in responsibilities_kps) or 1.0
    resp_matched_weight = 0.0
    resp_matched_count = 0

    for kp in keyphrases:
        present_anywhere = kp["key"] in resume_text_norm
        if present_anywhere:
            matched_weight += kp["weight"]
            found_keywords.append(kp["display"])
        elif kp["zone"] == "required":
            missing_required_kps.append(kp)
        else:
            missing_other_kps.append(kp)

        if kp["category"] in ("skills_domain", "tools"):
            if kp["key"] in resume_skills_zone_norm:
                skills_matched_weight += kp["weight"]
                skills_matched_count += 1
        if kp["category"] == "responsibilities" and present_anywhere:
            resp_matched_weight += kp["weight"]
            resp_matched_count += 1

    keyword_match = round(100 * matched_weight / total_weight)

    if skills_kps:
        skills_match = round(100 * skills_matched_weight / skills_total_weight)
        skills_confidence = "Verified"
        skills_detail = f"Matched {skills_matched_count} of {len(skills_kps)} JD skills/tools terms in your Skills section."
    else:
        skills_match, skills_confidence = 100, "Unknown"
        skills_detail = "JD does not list distinct skills/tools terms to compare."

    if responsibilities_kps:
        responsibilities_match = round(100 * resp_matched_weight / resp_total_weight)
        responsibilities_confidence = "Verified"
        responsibilities_detail = f"Matched {resp_matched_count} of {len(responsibilities_kps)} JD responsibility terms."
    else:
        responsibilities_match, responsibilities_confidence = 100, "Unknown"
        responsibilities_detail = "JD does not list distinct responsibilities to compare."

    # --- projects match (skills/tools category, vs. Projects zone; N/A if none) ---
    if "projects" not in resume_sections:
        projects_match, projects_confidence = None, "Unknown"
        projects_matched_count, projects_total_count = 0, len(skills_kps)
        projects_detail = "No Projects section found on resume — not applicable."
    else:
        proj_zone_norm = normalize(section_text(resume_lines, resume_sections, "projects") or "")
        projects_total_weight = sum(kp["weight"] for kp in skills_kps) or 1.0
        projects_matched_weight = sum(kp["weight"] for kp in skills_kps if kp["key"] in proj_zone_norm)
        projects_matched_count = sum(1 for kp in skills_kps if kp["key"] in proj_zone_norm)
        projects_total_count = len(skills_kps)
        if skills_kps:
            projects_match = round(100 * projects_matched_weight / projects_total_weight)
            projects_confidence = "Verified"
            projects_detail = f"Matched {projects_matched_count} of {projects_total_count} JD skills/tools terms in your Projects section."
        else:
            projects_match, projects_confidence = 100, "Unknown"
            projects_detail = "JD does not list distinct skills/tools terms to compare."

    # --- education ----------------------------------------------------
    jd_degree_hit = DEGREE_RE.search(jd_extracted.raw_text)
    resume_edu_zone = section_text(resume_lines, resume_sections, "education") or resume_extracted.raw_text
    resume_degree_hit = DEGREE_RE.search(resume_edu_zone)
    if not jd_degree_hit:
        education_match, education_confidence = SCORING_CONFIG["education_score_full"], "Verified"
        education_detail = "JD does not specify a degree requirement."
        education_matched, education_total = 0, 0
    elif resume_degree_hit:
        education_match, education_confidence = SCORING_CONFIG["education_score_full"], "Verified"
        education_detail = f"\"{jd_degree_hit.group(0).strip()}\" required; matching degree found on resume."
        education_matched, education_total = 1, 1
    else:
        education_match, education_confidence = SCORING_CONFIG["education_score_mismatch"], "Verified"
        education_detail = f"\"{jd_degree_hit.group(0).strip()}\" required; no matching degree found on resume."
        education_matched, education_total = 0, 1

    # --- experience -----------------------------------------------------
    jd_years_hit = YEARS_REQUIRED_RE.search(jd_extracted.raw_text)
    required_years = int(jd_years_hit.group(1)) if jd_years_hit else None
    resume_years_hit = YEARS_REQUIRED_RE.search(resume_extracted.raw_text)
    estimated_years = int(resume_years_hit.group(1)) if resume_years_hit else None
    if required_years is None:
        experience_match, experience_confidence = 100, "Verified"
        experience_detail = "JD does not specify a minimum years-of-experience requirement."
        experience_matched, experience_total = 0, 0
    elif estimated_years is not None:
        experience_confidence = "Verified"
        experience_match = 100 if estimated_years >= required_years else round(100 * estimated_years / required_years)
        experience_detail = f"JD requires {required_years}+ years; resume states {estimated_years} years."
        experience_matched, experience_total = (1 if estimated_years >= required_years else 0), 1
    else:
        experience_match, experience_confidence = 50, "Unknown"
        experience_detail = (f"JD requires {required_years}+ years; could not reliably verify total "
                              f"experience from the resume — please confirm manually.")
        experience_matched, experience_total = 0, 1

    # --- certifications ---------------------------------------------------
    jd_wants_cert = bool(re.search(r"certif|licens", jd_extracted.raw_text, re.IGNORECASE))
    cert_zone_text = (section_text(resume_lines, resume_sections, "certifications") or "").strip()
    if not jd_wants_cert:
        certification_match, certification_confidence = SCORING_CONFIG["certification_score_full"], "Verified"
        certification_detail = "JD does not require a certification or license."
        certification_matched, certification_total = 0, 0
    elif cert_zone_text:
        certification_match, certification_confidence = SCORING_CONFIG["certification_score_full"], "Verified"
        certification_detail = "JD references a certification/license; resume has a Certifications section."
        certification_matched, certification_total = 1, 1
    else:
        certification_match, certification_confidence = SCORING_CONFIG["certification_score_absent"], "Unknown"
        certification_detail = "JD references a certification/license; no Certifications section found on resume."
        certification_matched, certification_total = 0, 1

    resume_ats, ats_risks = resume_ats_score(resume_extracted, resume_sections)

    category_scores_raw = {
        "keywordMatch": keyword_match, "skillsMatch": skills_match,
        "educationMatch": education_match, "experienceMatch": experience_match,
        "certificationMatch": certification_match,
        "responsibilitiesMatch": responsibilities_match, "projectsMatch": projects_match,
    }

    weights = (SCORING_CONFIG["fresher_weights"] if candidate_info["type"] in FRESHER_LIKE_TYPES
               else SCORING_CONFIG["experienced_weights"])
    active = {k: v for k, v in category_scores_raw.items() if v is not None}
    weight_sum = sum(weights[k] for k in active) or 1.0
    jd_match_score = round(sum(active[k] * weights[k] for k in active) / weight_sum)

    missing_required_count = len(missing_required_kps)
    cfg = SCORING_CONFIG
    if jd_match_score >= cfg["recommendation_strong_threshold"] and missing_required_count <= cfg["recommendation_strong_max_missing_required"]:
        final_recommendation = "Strong Match"
    elif jd_match_score >= cfg["recommendation_moderate_threshold"]:
        final_recommendation = "Moderate Match"
    else:
        final_recommendation = "Weak Match"

    # --- action verbs / measurable achievements (reused, not reimplemented) ---
    weak_bullets = [b for b in resume_bullets if b.lower().startswith(tuple(PB.WEAK_STARTERS))]
    quantified_bullets = [b for b in resume_bullets if NUMBER_RE.search(b)]

    strengths: List[str] = []
    weaknesses: List[str] = []
    if keyword_match >= 75:
        strengths.append(f"Strong keyword alignment with the job description ({keyword_match}%).")
    if resume_bullets and not weak_bullets:
        strengths.append("Bullets consistently open with strong action verbs.")
    if resume_bullets and quantified_bullets and len(quantified_bullets) / len(resume_bullets) >= 0.5:
        strengths.append("Good use of measurable, quantified achievements.")
    if not strengths:
        strengths.append("No standout strengths detected relative to this JD yet.")

    if missing_required_kps:
        weaknesses.append(f"Missing {missing_required_count} required JD keyword(s): "
                           f"{', '.join(kp['display'] for kp in missing_required_kps[:5])}.")
    if weak_bullets:
        weaknesses.append(f"{len(weak_bullets)} bullet(s) open with a weak/passive phrase "
                           f"(e.g. \"Responsible for\").")
    if not quantified_bullets:
        weaknesses.append("No measurable, quantified achievements detected in bullets.")
    if resume_ats < 70:
        weaknesses.append("Resume formatting may cause ATS parsing issues — see Resume ATS Score.")

    critical_fixes = [
        _fix_item(i + 1, "jd-crit", "Missing Requirement",
                  f'Missing required keyword: "{kp["display"]}"',
                  "This term appears in the JD's required qualifications but was not found "
                  "anywhere in the resume.",
                  "Required qualifications are typically hard filters — an ATS or recruiter "
                  "often screens out resumes missing these terms outright.",
                  f'If you have genuine experience with "{kp["display"]}", add it explicitly to your '
                  f"Skills or Experience section.")
        for i, kp in enumerate(missing_required_kps[:8])
    ]
    important_tweaks = [
        _fix_item(i + 1, "jd-imp", "Missing Preferred Keyword",
                  f'Missing preferred keyword: "{kp["display"]}"',
                  "This term appears in the JD but is not a hard requirement.",
                  "Preferred/nice-to-have terms still influence ranking and recruiter impression.",
                  f'Consider adding "{kp["display"]}" if genuinely applicable.')
        for i, kp in enumerate(missing_other_kps[:8])
    ]
    if weak_bullets:
        important_tweaks.append(_fix_item(
            len(important_tweaks) + 1, "jd-imp", "Action Verbs", "Weak / passive bullet opener",
            f'Bullet starts passively: "{weak_bullets[0][:70]}..."',
            "Open with a verb that shows ownership instead of a passive phrase.",
            "Rewrite starting with a strong verb (Built, Led, Managed, Delivered).",
        ))
    important_tweaks.extend(_optional_field_gap_tweaks(optional_profile, jd_extracted.raw_text, len(important_tweaks)))

    top_improvements = [f'Add "{kp["display"]}" if applicable — required by the JD.' for kp in missing_required_kps[:3]]
    if not quantified_bullets:
        top_improvements.append("Add at least one measurable number (%, count, or amount) to your top bullets.")
    if weak_bullets:
        top_improvements.append("Replace passive bullet openers with strong action verbs.")
    if not top_improvements:
        top_improvements.append("No high-priority gaps detected — this resume aligns well with the JD.")

    category_breakdown = {
        "keywordMatch": _category(
            keyword_match, len(found_keywords), len(keyphrases), "Verified",
            f"Matched {len(found_keywords)} of {len(keyphrases)} important JD terms (weighted).",
            ["Position/zone-weighted extraction, not raw frequency",
             "Required-zone terms weighted 3x, preferred 1.5x, others 1x"],
        ),
        "skillsMatch": _category(
            skills_match, skills_matched_count, len(skills_kps), skills_confidence, skills_detail,
            ["Checked against the resume's Skills section specifically, not the whole document"],
        ),
        "educationMatch": _category(
            education_match, education_matched, education_total, education_confidence, education_detail,
            ["Degree-vocabulary regex match against the JD and the resume's Education section"],
        ),
        "experienceMatch": _category(
            experience_match, experience_matched, experience_total, experience_confidence, experience_detail,
            ["Explicit \"N years experience\" phrase match only — no résumé date-range reconstruction"],
        ),
        "certificationMatch": _category(
            certification_match, certification_matched, certification_total, certification_confidence, certification_detail,
            ["Certification/license mention in JD checked against presence of a resume Certifications section"],
        ),
        "responsibilitiesMatch": _category(
            responsibilities_match, resp_matched_count, len(responsibilities_kps),
            responsibilities_confidence, responsibilities_detail,
            ["JD terms from Responsibilities-zone checked against the whole resume text"],
        ),
        "projectsMatch": _category(
            projects_match, projects_matched_count, projects_total_count, projects_confidence, projects_detail,
            ["Checked against the resume's Projects section specifically — N/A if no such section exists"],
        ),
    }

    recruiter_view = _compose_recruiter_view(category_scores_raw, missing_required_count, final_recommendation)

    category_scores = {
        "keywordMatch": keyword_match,
        "skillsMatch": skills_match,
        "educationMatch": education_match,
        "experienceMatch": experience_match,
        "certificationMatch": certification_match,
        "responsibilitiesMatch": responsibilities_match,
        "projectsMatch": projects_match,
    }
    category_details = {
        "keywordMatch": category_breakdown["keywordMatch"]["detail"],
        "skillsMatch": category_breakdown["skillsMatch"]["detail"],
        "educationMatch": category_breakdown["educationMatch"]["detail"],
        "experienceMatch": category_breakdown["experienceMatch"]["detail"],
        "certificationMatch": category_breakdown["certificationMatch"]["detail"],
        "responsibilitiesMatch": category_breakdown["responsibilitiesMatch"]["detail"],
        "projectsMatch": category_breakdown["projectsMatch"]["detail"],
    }
    confidence = {
        "keywordMatch": "Verified",
        "skillsMatch": skills_confidence,
        "educationMatch": education_confidence,
        "experienceMatch": experience_confidence,
        "certificationMatch": certification_confidence,
        "responsibilitiesMatch": responsibilities_confidence,
        "projectsMatch": projects_confidence,
    }
    score_breakdown = {
        "overallMatch": _score_breakdown(
            jd_match_score, jd_match_score, 100, "Verified",
            f"Weighted average across JD categories; strongest risks are {', '.join(kp['display'] for kp in missing_required_kps[:3]) or 'none'}.",
        ),
        "resumeAtsScore": _score_breakdown(
            resume_ats, max(resume_ats - len(ats_risks) * 10, 0), 100, "Verified",
            "; ".join(ats_risks) if ats_risks else "No ATS readability deductions.",
        ),
        "keywordMatch": _score_breakdown(
            keyword_match, len(found_keywords), len(keyphrases), "Verified",
            f"Missing high-priority JD terms: {', '.join(kp['display'] for kp in missing_required_kps[:5]) or 'none detected'}.",
        ),
        "skillsMatch": _score_breakdown(
            skills_match, skills_matched_count, len(skills_kps), skills_confidence, skills_detail,
        ),
        "educationMatch": _score_breakdown(
            education_match, education_matched, education_total, education_confidence, education_detail,
        ),
        "experienceMatch": _score_breakdown(
            experience_match, experience_matched, experience_total, experience_confidence, experience_detail,
        ),
        "certificationMatch": _score_breakdown(
            certification_match, certification_matched, certification_total, certification_confidence, certification_detail,
        ),
        "responsibilitiesMatch": _score_breakdown(
            responsibilities_match, resp_matched_count, len(responsibilities_kps), responsibilities_confidence, responsibilities_detail,
        ),
        "projectsMatch": _score_breakdown(
            projects_match if projects_match is not None else 100,
            projects_matched_count,
            projects_total_count,
            projects_confidence,
            projects_detail,
        ),
    }

    return {
        "overallMatchScore": jd_match_score,
        "jdMatchScore": jd_match_score,
        "resumeAtsScore": resume_ats,
        "scoreDescriptions": SCORE_DESCRIPTIONS,
        "finalRecommendation": final_recommendation,
        "categoryScores": category_scores,
        "categoryDetails": category_details,
        "confidence": confidence,
        "scoreBreakdown": score_breakdown,
        "categoryBreakdown": category_breakdown,
        "candidateName": candidate_name,
        "candidateType": candidate_info["type"],
        "candidateTypeConfidence": candidate_info["confidence"],
        "candidateTypeDetail": candidate_info["detail"],
        "candidateTypeSignals": candidate_info["signals"],
        "optionalProfile": optional_profile,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "criticalFixes": critical_fixes,
        "importantTweaks": important_tweaks,
        "missingKeywords": [_missing_item(kp) for kp in (missing_required_kps + missing_other_kps)],
        "missingSkills": [_missing_item(kp) for kp in (missing_required_kps + missing_other_kps)
                          if kp["category"] in ("skills_domain", "tools")],
        "atsRisks": ats_risks,
        "recruiterView": recruiter_view,
        "topImprovements": top_improvements,
        "meta": {
            "resumeFileName": resume_file_name,
            "jdFileName": jd_file_name,
            "requiredExperienceYears": required_years,
            "estimatedExperienceYears": estimated_years,
        },
    }
