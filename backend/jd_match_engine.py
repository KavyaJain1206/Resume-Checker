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
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

import playbook as PB
from pdf_extract import ExtractedResume
from rule_engine import BULLET_RE, NUMBER_RE, detect_sections, extract_bullets, section_text

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
ZONE_WEIGHT = {"required": 3.0, "preferred": 1.5}

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

CATEGORY_WEIGHTS = {
    "keywordMatch": 0.30, "skillsMatch": 0.25, "experienceMatch": 0.20,
    "educationMatch": 0.15, "certificationMatch": 0.10,
}


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


def _dedupe_subsumed(candidates: Dict[str, dict]) -> Dict[str, dict]:
    """Drop a shorter n-gram if a longer n-gram containing it accounts for
    (almost) all its occurrences — e.g. don't list "google" AND "google ads"
    AND "google ads campaign" as three separate gaps."""
    by_len_desc = sorted(candidates.keys(), key=lambda k: -len(k.split()))
    removed: set = set()
    for i, longer in enumerate(by_len_desc):
        if longer in removed:
            continue
        long_weight = candidates[longer]["weight"]
        for shorter in by_len_desc[i + 1:]:
            if shorter in removed or shorter == longer:
                continue
            if f" {shorter} " in f" {longer} " and candidates[shorter]["weight"] <= long_weight * 1.5:
                removed.add(shorter)
    return {k: v for k, v in candidates.items() if k not in removed}


def extract_keyphrases(jd_lines: List[str], jd_sections: Dict[str, int]) -> List[dict]:
    """Position/pattern-weighted keyphrase extraction — NOT raw frequency
    (a single JD is too short for frequency alone to mean anything). A term
    inside a Requirements bullet outweighs one repeated in filler prose."""
    bullet_lines = {i for i, ln in enumerate(jd_lines) if BULLET_RE.match(ln)}
    candidates: Dict[str, dict] = {}

    for i, line in enumerate(jd_lines):
        zone = _zone_for_line(i, jd_sections)
        zone_weight = ZONE_WEIGHT.get(zone, 1.0)
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

    candidates = _dedupe_subsumed(candidates)
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
        score -= 40
        risks.append("Multi-column / sidebar layout detected — a common cause of ATS parser failure.")
    if extracted.has_images:
        score -= 30
        risks.append("Images, icons, or skill-rating bars detected — invisible to most parsers.")
    std = sum(1 for k in ("experience", "education", "skills") if k in resume_sections)
    if std < 2:
        score -= 15
        risks.append("Missing standard section headings (Experience / Education / Skills).")
    return max(0, min(100, score)), risks


def _compose_recruiter_view(scores: Dict[str, int], missing_required_count: int, recommendation: str) -> str:
    """Composed from the computed numbers via simple rules — not generated
    prose — so it stays deterministic and reproducible."""
    labels = {
        "keywordMatch": "keyword alignment", "skillsMatch": "skills alignment",
        "educationMatch": "education fit", "experienceMatch": "experience fit",
        "certificationMatch": "certification fit",
    }
    best_key = max(scores, key=scores.get)
    worst_key = min(scores, key=scores.get)
    parts = [f"A recruiter scanning this resume against the JD would notice strong "
             f"{labels[best_key]} ({scores[best_key]}%)."]
    if missing_required_count:
        parts.append(f"{missing_required_count} required qualification(s) aren't clearly "
                      f"demonstrated — that's the biggest risk to address first.")
    elif scores[worst_key] < 60:
        parts.append(f"The weakest area is {labels[worst_key]} ({scores[worst_key]}%), worth "
                      f"strengthening before applying.")
    parts.append(f"Overall: {recommendation}.")
    return " ".join(parts)


def _fix_item(idx: int, prefix: str, category: str, title: str, description: str,
              why: str, action: str) -> dict:
    return {
        "id": f"{prefix}-{idx}", "category": category, "title": title,
        "description": description, "whyItMatters": why, "action": action,
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

    total_weight = sum(kp["weight"] for kp in keyphrases) or 1.0
    matched_weight = 0.0
    skills_total_weight = 0.0
    skills_matched_weight = 0.0
    found_keywords: List[str] = []
    missing_required: List[str] = []
    missing_other: List[str] = []

    for kp in keyphrases:
        present_anywhere = kp["key"] in resume_text_norm
        in_skills_category = kp["category"] in ("skills_domain", "tools")
        if in_skills_category:
            skills_total_weight += kp["weight"]
            if kp["key"] in resume_skills_zone_norm:
                skills_matched_weight += kp["weight"]
        if present_anywhere:
            matched_weight += kp["weight"]
            found_keywords.append(kp["display"])
        elif kp["zone"] == "required":
            missing_required.append(kp["display"])
        else:
            missing_other.append(kp["display"])

    keyword_match = round(100 * matched_weight / total_weight)
    skills_match = round(100 * skills_matched_weight / skills_total_weight) if skills_total_weight else 100

    # --- education ----------------------------------------------------
    jd_degree_hit = DEGREE_RE.search(jd_extracted.raw_text)
    resume_edu_zone = section_text(resume_lines, resume_sections, "education") or resume_extracted.raw_text
    resume_degree_hit = DEGREE_RE.search(resume_edu_zone)
    if not jd_degree_hit:
        education_match, education_confidence = 100, "Verified"
        education_detail = "JD does not specify a degree requirement."
    elif resume_degree_hit:
        education_match, education_confidence = 100, "Verified"
        education_detail = f"\"{jd_degree_hit.group(0).strip()}\" required; matching degree found on resume."
    else:
        education_match, education_confidence = 30, "Verified"
        education_detail = f"\"{jd_degree_hit.group(0).strip()}\" required; no matching degree found on resume."

    # --- experience -----------------------------------------------------
    jd_years_hit = YEARS_REQUIRED_RE.search(jd_extracted.raw_text)
    required_years = int(jd_years_hit.group(1)) if jd_years_hit else None
    resume_years_hit = YEARS_REQUIRED_RE.search(resume_extracted.raw_text)
    estimated_years = int(resume_years_hit.group(1)) if resume_years_hit else None
    if required_years is None:
        experience_match, experience_confidence = 100, "Verified"
        experience_detail = "JD does not specify a minimum years-of-experience requirement."
    elif estimated_years is not None:
        experience_confidence = "Verified"
        experience_match = 100 if estimated_years >= required_years else round(100 * estimated_years / required_years)
        experience_detail = f"JD requires {required_years}+ years; resume states {estimated_years} years."
    else:
        experience_match, experience_confidence = 50, "Unknown"
        experience_detail = (f"JD requires {required_years}+ years; could not reliably verify total "
                              f"experience from the resume — please confirm manually.")

    # --- certifications ---------------------------------------------------
    jd_wants_cert = bool(re.search(r"certif|licens", jd_extracted.raw_text, re.IGNORECASE))
    cert_zone_text = (section_text(resume_lines, resume_sections, "certifications") or "").strip()
    if not jd_wants_cert:
        certification_match, certification_confidence = 100, "Verified"
        certification_detail = "JD does not require a certification or license."
    elif cert_zone_text:
        certification_match, certification_confidence = 100, "Verified"
        certification_detail = "JD references a certification/license; resume has a Certifications section."
    else:
        certification_match, certification_confidence = 20, "Unknown"
        certification_detail = "JD references a certification/license; no Certifications section found on resume."

    resume_ats, ats_risks = resume_ats_score(resume_extracted, resume_sections)

    category_scores = {
        "keywordMatch": keyword_match, "skillsMatch": skills_match,
        "educationMatch": education_match, "experienceMatch": experience_match,
        "certificationMatch": certification_match,
    }
    jd_match_score = round(sum(category_scores[k] * CATEGORY_WEIGHTS[k] for k in CATEGORY_WEIGHTS))

    missing_required_count = len(missing_required)
    if jd_match_score >= 80 and missing_required_count <= 2:
        final_recommendation = "Strong Match"
    elif jd_match_score >= 55:
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

    if missing_required:
        weaknesses.append(f"Missing {missing_required_count} required JD keyword(s): "
                           f"{', '.join(missing_required[:5])}.")
    if weak_bullets:
        weaknesses.append(f"{len(weak_bullets)} bullet(s) open with a weak/passive phrase "
                           f"(e.g. \"Responsible for\").")
    if not quantified_bullets:
        weaknesses.append("No measurable, quantified achievements detected in bullets.")
    if resume_ats < 70:
        weaknesses.append("Resume formatting may cause ATS parsing issues — see Resume ATS Score.")

    critical_fixes = [
        _fix_item(i + 1, "jd-crit", "Missing Requirement",
                  f'Missing required keyword: "{phrase}"',
                  "This term appears in the JD's required qualifications but was not found "
                  "anywhere in the resume.",
                  "Required qualifications are typically hard filters — an ATS or recruiter "
                  "often screens out resumes missing these terms outright.",
                  f'If you have genuine experience with "{phrase}", add it explicitly to your '
                  f"Skills or Experience section.")
        for i, phrase in enumerate(missing_required[:8])
    ]
    important_tweaks = [
        _fix_item(i + 1, "jd-imp", "Missing Preferred Keyword",
                  f'Missing preferred keyword: "{phrase}"',
                  "This term appears in the JD but is not a hard requirement.",
                  "Preferred/nice-to-have terms still influence ranking and recruiter impression.",
                  f'Consider adding "{phrase}" if genuinely applicable.')
        for i, phrase in enumerate(missing_other[:8])
    ]
    if weak_bullets:
        important_tweaks.append(_fix_item(
            len(important_tweaks) + 1, "jd-imp", "Action Verbs", "Weak / passive bullet opener",
            f'Bullet starts passively: "{weak_bullets[0][:70]}..."',
            "Open with a verb that shows ownership instead of a passive phrase.",
            "Rewrite starting with a strong verb (Built, Led, Managed, Delivered).",
        ))

    top_improvements = [f'Add "{p}" if applicable — required by the JD.' for p in missing_required[:3]]
    if not quantified_bullets:
        top_improvements.append("Add at least one measurable number (%, count, or amount) to your top bullets.")
    if weak_bullets:
        top_improvements.append("Replace passive bullet openers with strong action verbs.")
    if not top_improvements:
        top_improvements.append("No high-priority gaps detected — this resume aligns well with the JD.")

    confidence = {
        "experienceMatch": experience_confidence,
        "educationMatch": education_confidence,
        "certificationMatch": certification_confidence,
    }
    category_details = {
        "keywordMatch": f"Matched {len(found_keywords)} of {len(keyphrases)} important JD terms (weighted).",
        "skillsMatch": (f"{round(100*skills_matched_weight/skills_total_weight) if skills_total_weight else 100}% "
                        f"of JD skills/tools terms found in your Skills section." if skills_total_weight
                        else "JD does not list distinct skills/tools terms to compare."),
        "educationMatch": education_detail,
        "experienceMatch": experience_detail,
        "certificationMatch": certification_detail,
    }

    recruiter_view = _compose_recruiter_view(category_scores, missing_required_count, final_recommendation)

    return {
        "jdMatchScore": jd_match_score,
        "resumeAtsScore": resume_ats,
        "finalRecommendation": final_recommendation,
        "categoryScores": category_scores,
        "categoryDetails": category_details,
        "confidence": confidence,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "criticalFixes": critical_fixes,
        "importantTweaks": important_tweaks,
        "missingKeywords": missing_required + missing_other,
        "missingSkills": [p for p in missing_required + missing_other
                          if p in {c["display"] for c in keyphrases if c["category"] in ("skills_domain", "tools")}],
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
