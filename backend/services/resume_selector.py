"""
Resume Selector — Pick the best resume variant based on job archetype.

Maps job archetypes (detected by smart_filter) to resume variants.
Falls back to the default resume if no variant matches.

Usage:
    from services.resume_selector import select_resume, RESUME_VARIANTS

    # Auto-select based on job content
    path = select_resume(role="AI Engineer", content="clinical NLP pipeline...", domain="High")

    # Get all configured variants
    for name, info in RESUME_VARIANTS.items():
        print(f"{name}: {info['path']} — {info['description']}")
"""

from pathlib import Path

# ─── Resume Variants Configuration ──────────────────────────────────────────
#
# Add new variants by:
# 1. Creating the PDF in assets/ (use /tailor-cv skill to generate content)
# 2. Adding an entry here with keywords that trigger selection
#
# The selector scores each variant against the job content and picks the best.

RESUME_VARIANTS = {
    "healthcare-ai": {
        "path": "assets/resumes/healthcare-ai/vineet_kukreti_resume.pdf",
        "description": "Healthcare AI focus — oncology, clinical NLP, HIPAA, medical pipelines",
        "keywords": [
            "healthcare", "clinical", "medical", "hospital", "patient",
            "oncology", "pathology", "ehr", "fhir", "hipaa", "dicom",
            "pharma", "biomedical", "biotech", "drug discovery",
            "life sciences", "radiology", "genomics", "telehealth",
            "health tech", "digital health", "clinical trial",
        ],
        "weight": 1.5,  # Boost for domain specialty
    },
    "genai-platform": {
        "path": "assets/resumes/genai-platform/vineet_kukreti_resume.pdf",
        "description": "GenAI/LLM focus — RAG, agents, prompt engineering, LLM systems",
        "keywords": [
            "llm", "large language model", "genai", "generative ai",
            "rag", "retrieval", "prompt engineering", "langchain", "langgraph",
            "agent", "agentic", "multi-agent", "autonomous",
            "chatbot", "conversational", "nlp", "natural language",
            "transformer", "gpt", "claude", "fine-tuning", "embedding",
            "vector", "semantic search",
        ],
        "weight": 1.3,
    },
    "data-engineering": {
        "path": "assets/resumes/data-engineering/vineet_kukreti_resume.pdf",
        "description": "Data/ML engineering focus — pipelines, ETL, MLOps, infrastructure",
        "keywords": [
            "data engineer", "data pipeline", "etl", "data warehouse",
            "mlops", "ml ops", "model deployment", "airflow", "spark",
            "kafka", "streaming", "batch processing", "data lake",
            "infrastructure", "devops", "kubernetes", "docker",
            "ci/cd", "monitoring", "observability",
        ],
        "weight": 1.0,
    },
    "default": {
        "path": "assets/resumes/default/vineet_kukreti_resume.pdf",
        "description": "General AI/ML engineer — balanced across all skills (uses GenAI variant)",
        "keywords": [],  # Matches everything as fallback
        "weight": 0.5,
    },
}


def select_resume(
    role: str = "",
    content: str = "",
    domain_relevance: str = "",
    company: str = "",
) -> str:
    """Select the best resume variant for a job.

    Returns the file path to the best-matching resume.
    Falls back to default if no variant file exists or no strong match.
    """
    text = f"{role} {content} {company}".lower()

    # Score each variant
    scores = {}
    for name, variant in RESUME_VARIANTS.items():
        if name == "default":
            continue
        hits = sum(1 for kw in variant["keywords"] if kw in text)
        score = hits * variant.get("weight", 1.0)

        # Boost if domain_relevance matches
        if name == "healthcare-ai" and domain_relevance == "High":
            score += 5.0
        elif name == "healthcare-ai" and domain_relevance == "Medium":
            score += 2.0

        scores[name] = score

    # Pick the best variant (must have at least 2 keyword hits)
    if scores:
        best_name = max(scores, key=scores.get)
        if scores[best_name] >= 2.0:
            best_path = RESUME_VARIANTS[best_name]["path"]
            if Path(best_path).exists():
                return best_path

    # Fallback to default
    return RESUME_VARIANTS["default"]["path"]


def get_resume_for_job(job: dict) -> str:
    """Convenience wrapper — pass a job dict from the DB."""
    return select_resume(
        role=job.get("role", ""),
        content=job.get("content", ""),
        domain_relevance=job.get("domain_relevance", ""),
        company=job.get("company", ""),
    )


def list_variants() -> list[dict]:
    """List all configured resume variants with existence status."""
    result = []
    for name, variant in RESUME_VARIANTS.items():
        path = Path(variant["path"])
        result.append({
            "name": name,
            "path": str(path),
            "description": variant["description"],
            "exists": path.exists(),
            "keywords_count": len(variant["keywords"]),
        })
    return result
