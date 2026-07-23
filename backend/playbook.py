"""
playbook.py
Canonical constants distilled directly from "The Resume Playbook 2026".
These lists are the ground-truth taxonomies the rule engine checks against.
"""

# ---------------------------------------------------------------------------
# Chapter 7 / 13 / Appendix C  -  soft-skill buzzwords that must NEVER be listed
# ---------------------------------------------------------------------------
BANNED_SOFT_SKILLS = [
    "hardworking", "hard working", "hard-working", "dedicated", "motivated",
    "self-motivated", "self motivated", "punctual", "sincere", "dynamic",
    "enthusiastic", "team player", "good communication skills", "communication skills",
    "quick learner", "fast learner", "multitasker", "multi-tasker", "detail-oriented",
    "detail oriented", "out-of-the-box", "out of the box", "people person",
    "go-getter", "go getter", "results-oriented", "results oriented", "passionate",
    "think outside the box", "proactive", "flexible", "responsible person",
]

# Standalone soft skills that are fine as a trait but worthless as a keyword
STANDALONE_SOFT_SKILLS = [
    "leadership", "communication", "teamwork", "problem-solving", "problem solving",
    "collaboration", "adaptability", "time management", "critical thinking",
    "attention to detail", "resilience", "creativity", "interpersonal skills",
]

# ---------------------------------------------------------------------------
# Chapter 9 / 13  -  weak / passive bullet openers
# ---------------------------------------------------------------------------
WEAK_STARTERS = [
    "responsible for", "worked on", "helped with", "was tasked with", "tasked with",
    "involved in", "assisted with", "assisted in", "participated in", "handled",
    "was responsible", "in charge of", "duties included", "helped to", "worked with",
]

# Filler words that subtract credibility (Chapter 9 / Appendix C)
FILLER_WORDS = [
    "successfully", "various", "several", "etc", "and more", "many", "different",
    "synergy", "synergistic", "spearheaded", "innovative solutions",
]

# ---------------------------------------------------------------------------
# Appendix B  -  strong action verbs
# ---------------------------------------------------------------------------
STRONG_VERBS = set(w.lower() for w in [
    "Built", "Created", "Programmed", "Developed", "Prototyped", "Assembled",
    "Designed", "Architected", "Formulated", "Engineered", "Implemented", "Devised",
    "Optimized", "Streamlined", "Enhanced", "Improved", "Accelerated", "Boosted",
    "Increased", "Automated", "Cut", "Reduced", "Refactored", "Scaled", "Led",
    "Owned", "Delegated", "Managed", "Drove", "Oversaw", "Coordinated", "Organized",
    "Championed", "Directed", "Mentored", "Facilitated", "Analyzed", "Modeled",
    "Diagnosed", "Researched", "Measured", "Forecasted", "Evaluated", "Assessed",
    "Tested", "Investigated", "Identified", "Validated", "Launched", "Released",
    "Presented", "Shipped", "Executed", "Published", "Delivered", "Completed",
    "Achieved", "Deployed", "Produced", "Won", "Grew", "Migrated", "Trained",
    "Integrated", "Debugged", "Merged", "Onboarded", "Deployed",
])

# ---------------------------------------------------------------------------
# Chapters 4 / 10  -  forbidden personal details & legacy artifacts
# ---------------------------------------------------------------------------
FORBIDDEN_PERSONAL = [
    "marital status", "date of birth", "d.o.b", "dob", "father's name",
    "fathers name", "mother's name", "religion", "nationality", "gender",
    "sex:", "age:", "caste", "blood group",
]
DECLARATION_MARKERS = [
    "i hereby declare", "hereby declare", "declaration", "i solemnly declare",
    "the above information is true", "references available on request",
    "references available upon request",
]

# ---------------------------------------------------------------------------
# Chapter 11  -  standard section headings the parser looks for
# ---------------------------------------------------------------------------
STANDARD_HEADINGS = {
    "summary": ["summary", "professional summary", "objective", "profile", "about"],
    "skills": ["skills", "technical skills", "core skills", "key skills"],
    "education": ["education", "academics", "academic background"],
    "projects": ["projects", "personal projects", "academic projects", "key projects"],
    "experience": ["experience", "work experience", "professional experience",
                   "internships", "internship", "employment"],
    "certifications": ["certifications", "certificates", "licenses"],
    "achievements": ["achievements", "awards", "accomplishments", "extracurricular",
                     "positions of responsibility", "activities"],
}

# Section order per situation (Appendix C  -  Section-order quick reference)
FRESHER_ORDER = ["header", "summary", "skills", "projects", "education",
                 "certifications", "achievements"]
EXPERIENCED_ORDER = ["header", "summary", "skills", "experience", "projects",
                     "education", "certifications"]

# ---------------------------------------------------------------------------
# Chapter 14 / Appendix D  -  canonical keyword benchmark per target role
# ---------------------------------------------------------------------------
ROLE_KEYWORDS = {
    "Frontend Developer": [
        "javascript", "typescript", "react", "html", "css", "tailwind css",
        "redux", "zustand", "rest api", "jest", "testing", "web vitals",
        "responsive design", "git", "webpack", "accessibility",
    ],
    "Backend Developer": [
        "node.js", "python", "java", "rest api", "sql", "postgresql", "mongodb",
        "docker", "microservices", "redis", "ci/cd", "authentication",
        "system design", "kubernetes", "graphql", "git",
    ],
    "Full Stack Developer": [
        "react", "node.js", "typescript", "javascript", "rest api", "sql",
        "mongodb", "docker", "git", "ci/cd", "tailwind css", "express",
        "authentication", "testing", "aws",
    ],
    "Data Analyst": [
        "sql", "python", "pandas", "power bi", "tableau", "excel", "statistics",
        "data cleaning", "a/b testing", "etl", "bigquery", "data visualization",
        "dashboards", "reporting",
    ],
    "Data Scientist": [
        "python", "pandas", "numpy", "scikit-learn", "machine learning",
        "sql", "statistics", "deep learning", "tensorflow", "pytorch",
        "feature engineering", "nlp", "data visualization", "a/b testing",
    ],
    "Product Manager": [
        "roadmap", "user research", "a/b testing", "agile", "scrum", "stakeholder",
        "wireframing", "analytics", "prioritization", "kpis", "product strategy",
        "user stories", "sql", "figma",
    ],
    "UI/UX Designer": [
        "figma", "adobe xd", "wireframing", "prototyping", "design systems",
        "user research", "usability testing", "interaction design", "accessibility",
        "responsive design", "photoshop", "illustrator",
    ],
    "Software Engineer": [
        "data structures", "algorithms", "python", "java", "c++", "git",
        "rest api", "sql", "docker", "system design", "oop", "testing",
        "ci/cd", "javascript",
    ],
    "Machine Learning Engineer": [
        "python", "tensorflow", "pytorch", "scikit-learn", "machine learning",
        "deep learning", "mlops", "docker", "kubernetes", "sql", "nlp",
        "model deployment", "feature engineering", "aws",
    ],
    "Marketing": [
        "seo", "google ads", "meta ads", "ga4", "content strategy",
        "email marketing", "hubspot", "semrush", "funnel analysis",
        "copywriting", "a/b testing", "social media", "roas", "campaigns",
    ],
}

EXPERIENCE_LEVELS = ["Fresher", "Internship", "1-3 Years", "Career Switcher"]

# Dimension weights (sum = 100) from the validation rubric
WEIGHTS = {
    "atsSafety": 15,
    "contactProfessionalism": 10,
    "sectionHierarchy": 10,
    "metricQuantification": 20,
    "verbAndBuzzwordQuality": 10,
    "projectStrength": 15,
    "keywordTailoring": 10,
    "recruiterScan": 5,
    "summaryQuality": 5,
}
