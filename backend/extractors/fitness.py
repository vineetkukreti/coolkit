"""Fitness checks — is a job post relevant to the user's profile?"""

import re


# Roles that ARE relevant (whitelist)
KEEP_ROLES = [
    "ai engineer", "ml engineer", "machine learning engineer",
    "genai engineer", "generative ai", "llm engineer", "llm", "nlp",
    "deep learning engineer", "computer vision",
    "ai/ml", "ai & ml", "artificial intelligence",
    "ai researcher", "applied scientist",
    "mlops", "ml ops",
    "agentic ai", "ai agent", "agent developer", "autonomous agent",
    "multi-agent", "agent framework",
    "ai backend", "backend ai", "ai full stack", "full stack ai",
    "cv engineer",
    "clinical ai", "healthcare ai", "medical ai", "health ai",
    "biomedical ai", "clinical ml",
    # Python developer roles
    "python developer", "python engineer",
    "not specified",
]

# Roles that look relevant but are actually irrelevant
FALSE_POSITIVE_ROLES = [
    "java", "ruby", "golang", "go developer", "c++", "c#", ".net",
    "ios", "android", "mobile", "flutter", "react native",
    "frontend", "front end", "backend", "full stack", "fullstack",
    "devops", "sre", "cloud engineer", "infrastructure",
    "hardware", "embedded", "firmware", "electrical",
    "sales", "marketing", "hr", "recruiter", "talent",
    "product manager", "project manager", "scrum",
    "qa", "quality assurance", "sdet",
    "ui designer", "ux designer", "graphic design",
    "sme", "n/a",
    "nurse", "doctor", "physician", "therapist", "technician",
    "pharmacist", "radiologist", "pathologist", "surgeon",
    "dietitian", "physiotherapist", "dentist", "optometrist",
    "data scientist", "data science", "data analyst", "data analytics",
    "business analyst", "analytics engineer", "bi analyst",
    "data engineer", "etl engineer", "data architect", "data platform",
    "research analyst", "statistician",
]


def is_relevant_role(role: str) -> bool:
    """Check if the role is relevant to the user's AI/ML profile.

    Direct keep-list matches are checked first. As a fallback, any role that
    contains a core AI/ML term (ai, ml, llm, nlp, cv, genai, machine learning,
    computer vision, deep learning) together with an engineering/research term
    is considered relevant, unless it also contains a strong non-technical
    false-positive signal.
    """
    role_lower = role.lower()

    # 1. Explicit keep-list matches (e.g. "AI Engineer", "MLOps Engineer")
    if any(keep in role_lower for keep in KEEP_ROLES):
        return True

    # 2. Generic AI/ML + role-term fallback for compound titles like
    #    "AI Backend Engineer", "Python AI Developer", "LLM Research Scientist".
    has_core = bool(
        re.search(r'\b(ai|ml|llm|nlp|cv|genai)\b', role_lower)
        or 'machine learning' in role_lower
        or 'computer vision' in role_lower
        or 'deep learning' in role_lower
        or 'artificial intelligence' in role_lower
    )
    has_role = bool(re.search(r'\b(engineer|developer|scientist|researcher|specialist|architect)\b', role_lower))

    if has_core and has_role:
        strong_fps = [
            'product manager', 'project manager', 'program manager',
            'sales', 'marketing', 'business development',
            'hr ', 'human resources', 'recruiter', 'talent',
            'nurse', 'doctor', 'physician', 'therapist',
        ]
        if any(fp in role_lower for fp in strong_fps):
            return False
        return True

    # 3. Explicit false-positive list (e.g. "Java Developer", "Data Scientist")
    if any(fp in role_lower for fp in FALSE_POSITIVE_ROLES):
        return False

    return False


def experience_to_years(exp: str) -> tuple[int | None, int | None]:
    """Parse experience string to (min_years, max_years). None if not mentioned."""
    if not exp:
        return None, None
    exp = exp.lower()
    # Check range pattern first (e.g. "0-2 years") before fresher check
    m = re.search(r'(\d+)\s*[-\u2013to]+\s*(\d+)', exp)
    if m:
        return int(m.group(1)), int(m.group(2))
    if "fresher" in exp or (exp.startswith("0") and "+" not in exp):
        return 0, 0
    m = re.search(r'(\d+)\+?', exp)
    if m:
        n = int(m.group(1))
        return n, n + 2 if "+" in exp else n
    return None, None


def is_good_fit(role: str, experience: str) -> tuple[bool, str]:
    """Check if a post is a good fit (2yr AI Engineer, healthcare).
    Returns (keep, reason)."""
    if not is_relevant_role(role):
        return False, f"irrelevant-role:{role[:25]}"

    min_yr, max_yr = experience_to_years(experience)
    if min_yr is not None:
        if max_yr == 0:
            return False, "fresher-only"
        if min_yr >= 6:
            return False, f"too-senior:{min_yr}yr+"

    return True, "ok"
