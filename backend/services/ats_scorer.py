"""ATS Resume Scorer — scores resume-to-JD keyword match and ATS compatibility."""

import re
from collections import Counter

# Import profile config
try:
    from config import RESUME_SKILLS, PROFILE
except ImportError:
    RESUME_SKILLS = {}
    PROFILE = {}


# Common ATS-relevant section headers
ATS_SECTIONS = [
    "experience", "education", "skills", "certifications", "projects",
    "summary", "objective", "achievements", "publications"
]

# Common skill categories for tech roles
SKILL_CATEGORIES = {
    "languages": ["python", "java", "javascript", "typescript", "go", "rust", "c++", "r", "sql", "scala"],
    "ml_frameworks": ["pytorch", "tensorflow", "keras", "scikit-learn", "xgboost", "huggingface", "transformers", "langchain", "llamaindex"],
    "cloud": ["aws", "gcp", "azure", "s3", "ec2", "lambda", "sagemaker", "vertex ai", "bigquery"],
    "databases": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch", "neo4j", "pinecone", "chromadb", "weaviate"],
    "tools": ["docker", "kubernetes", "git", "ci/cd", "jenkins", "github actions", "terraform", "airflow", "mlflow"],
    "ai_concepts": ["llm", "rag", "fine-tuning", "prompt engineering", "embeddings", "vector database", "knowledge graph",
                    "agents", "agentic", "multi-agent", "chain of thought", "retrieval augmented"],
    "domains": ["healthcare", "clinical", "medical", "pharma", "biotech", "fintech", "nlp", "computer vision", "speech"],
}

ALL_KNOWN_SKILLS = set()
for skills in SKILL_CATEGORIES.values():
    ALL_KNOWN_SKILLS.update(skills)


def extract_jd_keywords(jd_text: str) -> dict:
    """Extract skills, tools, and requirements from a job description."""
    text_lower = jd_text.lower()

    found_skills = {}
    # Check known skills
    for category, skills in SKILL_CATEGORIES.items():
        for skill in skills:
            # Use word boundary matching for short skills
            if len(skill) <= 3:
                pattern = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern, text_lower):
                    found_skills[skill] = category
            else:
                if skill in text_lower:
                    found_skills[skill] = category

    # Extract experience requirements
    exp_patterns = re.findall(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)', text_lower)
    experience_years = [int(y) for y in exp_patterns] if exp_patterns else []

    # Extract education requirements
    edu_keywords = []
    for edu in ["bachelor", "master", "phd", "ph.d", "doctorate", "bs", "ms", "mba", "b.tech", "m.tech"]:
        if edu in text_lower:
            edu_keywords.append(edu)

    # Extract certifications
    cert_patterns = ["aws certified", "google certified", "azure certified", "pmp", "cissp",
                    "hipaa", "gdpr", "sox", "iso 27001"]
    found_certs = [c for c in cert_patterns if c in text_lower]

    return {
        "skills": found_skills,
        "experience_years": experience_years,
        "education": edu_keywords,
        "certifications": found_certs,
        "total_keywords": len(found_skills),
    }


def compute_ats_score(jd_text: str, resume_skills: dict = None) -> dict:
    """Compute ATS compatibility score (0-100) between JD and resume.

    Scoring breakdown:
    - Keyword match (50 points): % of JD skills found in resume
    - Skill weight bonus (20 points): high-weight skills matched
    - Category coverage (15 points): skills across multiple categories
    - Experience fit (15 points): years match
    """
    if resume_skills is None:
        resume_skills = RESUME_SKILLS

    resume_skills_lower = {k.lower(): v for k, v in resume_skills.items()}

    jd_data = extract_jd_keywords(jd_text)
    jd_skills = jd_data["skills"]  # {skill: category}

    if not jd_skills:
        return {
            "ats_score": 50,
            "verdict": "unknown",
            "label": "Cannot score — no skills detected in JD",
            "matched": [],
            "missing": [],
            "categories_covered": [],
            "suggestions": ["The job description doesn't contain enough technical keywords to score."],
        }

    # 1. Keyword match (50 points)
    matched = []
    missing = []
    for skill, category in jd_skills.items():
        # Check if skill or close variant is in resume
        skill_found = False
        for rs in resume_skills_lower:
            if skill in rs or rs in skill:
                matched.append({"skill": skill, "category": category, "resume_weight": resume_skills_lower.get(rs, 1)})
                skill_found = True
                break
        if not skill_found:
            missing.append({"skill": skill, "category": category})

    match_pct = len(matched) / len(jd_skills) if jd_skills else 0
    keyword_score = int(match_pct * 50)

    # 2. Skill weight bonus (20 points) — high-weight matched skills matter more
    if matched:
        avg_weight = sum(m["resume_weight"] for m in matched) / len(matched)
        weight_score = min(20, int(avg_weight * 5))
    else:
        weight_score = 0

    # 3. Category coverage (15 points)
    matched_categories = set(m["category"] for m in matched)
    jd_categories = set(jd_skills.values())
    cat_coverage = len(matched_categories) / max(len(jd_categories), 1)
    category_score = int(cat_coverage * 15)

    # 4. Experience fit (15 points)
    exp_years = jd_data.get("experience_years", [])
    my_years = PROFILE.get("experience_years", 0)
    if exp_years:
        min_req = min(exp_years)
        max_req = max(exp_years) if len(exp_years) > 1 else min_req + 2
        if min_req <= my_years <= max_req:
            exp_score = 15
        elif my_years >= min_req:
            exp_score = 12  # Overqualified slightly
        elif my_years >= min_req - 1:
            exp_score = 8  # Close enough
        else:
            exp_score = 3  # Under-qualified
    else:
        exp_score = 10  # No requirement stated, neutral

    total_score = keyword_score + weight_score + category_score + exp_score
    total_score = max(0, min(100, total_score))

    # Verdict
    if total_score >= 75:
        verdict = "strong_match"
        label = "Strong Match"
    elif total_score >= 55:
        verdict = "good_match"
        label = "Good Match"
    elif total_score >= 35:
        verdict = "partial_match"
        label = "Partial Match"
    else:
        verdict = "weak_match"
        label = "Weak Match"

    # Suggestions
    suggestions = []
    if missing:
        top_missing = [m["skill"] for m in missing[:5]]
        suggestions.append(f"Add these keywords to your resume: {', '.join(top_missing)}")
    if match_pct < 0.5:
        suggestions.append("Less than 50% keyword match — consider tailoring your resume for this role")
    if match_pct >= 0.7:
        suggestions.append("Good keyword coverage! Focus on quantifying achievements with these skills")
    missing_cats = jd_categories - matched_categories
    if missing_cats:
        suggestions.append(f"Missing skill categories: {', '.join(missing_cats)}")

    return {
        "ats_score": total_score,
        "verdict": verdict,
        "label": label,
        "match_percentage": round(match_pct * 100, 1),
        "breakdown": {
            "keyword_match": {"score": keyword_score, "max": 50},
            "skill_weight": {"score": weight_score, "max": 20},
            "category_coverage": {"score": category_score, "max": 15},
            "experience_fit": {"score": exp_score, "max": 15},
        },
        "matched": [m["skill"] for m in matched],
        "missing": [m["skill"] for m in missing],
        "categories_covered": list(matched_categories),
        "categories_missing": list(jd_categories - matched_categories),
        "jd_keywords_total": len(jd_skills),
        "suggestions": suggestions,
    }


def score_job_ats(conn, post_id: int) -> dict:
    """Score a specific job posting from the database."""
    row = conn.execute(
        "SELECT p.content, j.role, j.company, j.experience FROM posts p LEFT JOIN jobs j ON j.post_id = p.id WHERE p.id = ?",
        (post_id,)
    ).fetchone()
    if not row:
        return {"error": "Post not found"}

    content = row["content"] or ""
    result = compute_ats_score(content)
    result["post_id"] = post_id
    result["role"] = row["role"] or ""
    result["company"] = row["company"] or ""
    return result
