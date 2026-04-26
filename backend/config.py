"""User profile & search config — edit your details here."""
import random
PROFILE = {
    "name": "Vineet Kukreti",
    "first_name": "Vineet",
    "last_name": "Kukreti",
    "email": "vineetkukreti34@gmail.com",
    "phone": "+91-7983207219",
    "resume_path": "assets/resumes/default/vineet_kukreti_resume.pdf",
    "location": "India",
    "experience_years": 2,
    "current_title": "AI Engineer",
    "linkedin": "https://linkedin.com/in/vineetkukreti",
    "github": "https://github.com/vineetkukreti",
    "website": "https://github.com/vineetkukreti",
    "notice_period_days": 30,
    "desired_salary": 1200000,
    "current_salary": 800000,
    "require_visa": "No",
    "us_citizenship": "Not Applicable",
    "willing_to_relocate": "Yes",
    "previously_worked_here": "No",
    "education_level": "Bachelor's Degree",
    "certifications": "None",
    "gender": "Decline to self-identify",
    "ethnicity": "Decline to self-identify",
    "disability_status": "I don't wish to answer",
    "veteran_status": "I am not a protected veteran",
}

RESUME_SKILLS = {
    # core skills (high weight)
    "python": 3, "neo4j": 4, "knowledge graph": 4, "fastapi": 3,
    "docker": 2, "llm": 4, "nlp": 3, "prompt engineering": 3,
    # domain (high weight)
    "healthcare": 4, "oncology": 5, "dermatopathology": 5,
    "clinical": 3, "medical": 3, "biomedical": 3, "pathology": 4,
    "ehr": 2, "fhir": 2, "hipaa": 2,
    # general AI
    "ai engineer": 4, "machine learning": 3, "deep learning": 2,
    "data pipeline": 3, "etl": 3, "microservice": 2,
    # databases
    "postgresql": 2, "mongodb": 2, "graph database": 3,
    # APIs & LLMs
    "openai": 2, "claude": 3, "cohere": 2, "generative ai": 3,
    "asyncio": 2, "async": 1,
}

# ─── Randomized keyword engine ────────────────────────────────────────────────
# Every scraping run picks a fresh combo so LinkedIn sees different searches.
# Tier 1 (preferred): healthcare/biotech domain
# Tier 2 (fallback):  broader AI/ML domains — still great jobs for 2yr exp

_ROLE_KEYWORDS = [
    "AI Engineer", "ML Engineer", "Machine Learning Engineer",
    "GenAI Engineer", "LLM Engineer", "AI/ML Engineer",
    "Deep Learning Engineer", "NLP Engineer", "Applied AI Engineer",
    "AI Developer", "Data Scientist", "Computer Vision Engineer",
]

_DOMAIN_TIER1 = [
    "healthcare", "clinical", "medical", "biomedical", "health tech",
    "pharma", "biotech", "digital health", "life sciences",
]

_DOMAIN_TIER2 = [
    "fintech", "edtech", "SaaS", "e-commerce", "startup",
    "logistics", "agritech", "climate tech", "cybersecurity",
    "autonomous", "robotics", "conversational AI",
]

_EXP_TAGS = ["", "0-3 years", "entry level", "junior", "mid level"]


def random_search_keywords() -> str:
    """Return a randomized search keyword string for each scraping run."""
    role = random.choice(_ROLE_KEYWORDS)
    # 60% chance healthcare domain, 40% broader domain
    if random.random() < 0.6:
        domain = random.choice(_DOMAIN_TIER1)
    else:
        domain = random.choice(_DOMAIN_TIER2)
    exp = random.choice(_EXP_TAGS)
    parts = [role, domain]
    if exp:
        parts.append(exp)
    return " ".join(parts)


# Default search settings
DEFAULTS = {
    "keywords": random_search_keywords(),  # randomized every run
    "location": "India",
    "max_jobs": 25,
    "mode": "semi",  # "semi" = approve each, "auto" = apply all
}

# ─── Target Roles (ordered by priority) ──────────────────────────────────────
TARGET_ROLES = [
    "AI Engineer",
    "ML Engineer",
    "GenAI Engineer",
    "LLM Engineer",
    "Agentic AI Engineer",
]

# ─── Domain keywords for healthcare/medical/clinical scoring ──────────────────
DOMAIN_KEYWORDS = [
    "healthcare", "health care", "healthtech", "health tech",
    "medical", "medtech", "med tech", "biomedical",
    "clinical", "clinician", "clinic",
    "hospital", "patient", "ehr", "electronic health record",
    "pharma", "pharmaceutical", "drug discovery",
    "fda", "hipaa", "hl7", "fhir", "dicom",
    "radiology", "pathology", "oncology", "genomics",
    "telehealth", "telemedicine", "digital health",
    "life sciences", "biotech", "biotechnology",
]

# ─── Smart Query Engine components ───────────────────────────────────────────
ROLE_STEMS = [
    "AI engineer", "ML engineer", "GenAI engineer",
    "LLM engineer", "agentic AI engineer", "AI agent developer", "AI/ML engineer",
    "deep learning engineer", "applied AI engineer", "NLP engineer",
    "computer vision engineer", "AI developer", "data scientist",
    "machine learning developer", "Python developer",
]

DOMAIN_STEMS_HEALTHCARE = [
    "healthcare", "clinical", "medical", "biomedical",
    "health tech", "pharma", "oncology", "hospital",
    "life sciences", "digital health", "medtech",
    "genomics", "radiology", "drug discovery", "biotech",
]

DOMAIN_STEMS_GENERAL = [
    "fintech", "edtech", "SaaS", "e-commerce", "startup",
    "logistics", "agritech", "climate tech", "cybersecurity",
    "autonomous", "robotics", "conversational AI", "proptech",
    "insurtech", "legaltech", "martech", "supply chain",
]

DOMAIN_STEMS = DOMAIN_STEMS_HEALTHCARE + DOMAIN_STEMS_GENERAL

# ─── Multi-region targeting ─────────────────────────────────────────────────
REGIONS = {
    "india": {
        "locations": ["India", "Bangalore", "Mumbai", "Hyderabad", "Delhi", "Pune", "Chennai", "Noida", "Gurgaon"],
        "timezone": "Asia/Kolkata",
        "geolocation": {"latitude": 12.97, "longitude": 77.59},
        "locale": "en-IN",
    },
    "japan": {
        "locations": ["Japan", "Tokyo", "Osaka", "Kyoto", "Yokohama"],
        "timezone": "Asia/Tokyo",
        "geolocation": {"latitude": 35.68, "longitude": 139.69},
        "locale": "en-US",
    },
    "europe": {
        "locations": ["Europe", "Germany", "UK", "United Kingdom", "Netherlands", "France",
                       "Berlin", "London", "Amsterdam", "Paris", "Dublin", "Zurich",
                       "Stockholm", "Barcelona", "Munich", "Hamburg", "Copenhagen"],
        "timezone": "Europe/Berlin",
        "geolocation": {"latitude": 52.52, "longitude": 13.40},
        "locale": "en-US",
    },
    "uae": {
        "locations": ["Dubai", "UAE", "Abu Dhabi", "Middle East", "MENA"],
        "timezone": "Asia/Dubai",
        "geolocation": {"latitude": 25.20, "longitude": 55.27},
        "locale": "en-US",
    },
    "us": {
        "locations": ["United States", "USA", "New York", "San Francisco", "Austin",
                       "Seattle", "Boston", "Los Angeles", "Chicago", "Denver",
                       "Washington DC", "Atlanta", "Miami"],
        "timezone": "America/New_York",
        "geolocation": {"latitude": 40.71, "longitude": -74.01},
        "locale": "en-US",
    },
    "singapore": {
        "locations": ["Singapore", "Southeast Asia"],
        "timezone": "Asia/Singapore",
        "geolocation": {"latitude": 1.35, "longitude": 103.82},
        "locale": "en-US",
    },
}

ACTIVE_REGIONS = ["india", "japan", "europe", "uae", "us", "singapore"]

# Build location stems dynamically from active regions
LOCATION_STEMS = ["remote", "Remote", "worldwide", "anywhere", "global", ""]
for _region in ACTIVE_REGIONS:
    LOCATION_STEMS.extend(REGIONS[_region]["locations"])

ACTION_STEMS = ["hiring", "job opening", "looking for", "we're hiring", "join our team"]

EXP_STEMS = ["0-3 years", "entry level", "junior", "mid level", ""]

# ─── Role keyword mapping ────────────────────────────────────────────────────
ROLE_KEYWORDS = {
    "AI Engineer":    ["ai engineer", "artificial intelligence engineer", "ai developer",
                       "deep learning engineer", "ai/ml engineer", "ai & ml engineer",
                       "applied ai", "clinical ai", "healthcare ai", "medical ai",
                       "ai researcher", "applied scientist"],
    "ML Engineer":    ["ml engineer", "machine learning engineer", "ml developer",
                       "mlops", "ml ops", "model deployment engineer"],
    "GenAI Engineer": ["genai engineer", "generative ai", "llm engineer", "llm developer",
                       "large language model", "prompt engineer", "gen ai"],
    "Agentic AI Engineer": ["agentic ai", "ai agent", "agent developer", "ai agents",
                            "autonomous agent", "multi-agent", "agent framework",
                            "crewai", "autogen", "langgraph"],
}

# ─── Hashtag feeds for LinkedIn scraping ─────────────────────────────────────
HASHTAG_FEEDS = [
    "hiring", "wearehiring", "nowhiring", "jobopening", "jobalert",
    "AIjobs", "AIhiring", "healthcareAI", "healthtech",
    "machinelearning", "artificialintelligence", "genai",
    "remotejobs", "techhiring", "startupjobs",
]

# ─── LinkedIn Job Search queries ─────────────────────────────────────────────
JOB_SEARCH_QUERIES = [
    "AI Engineer healthcare", "ML Engineer healthcare",
    "Data Scientist healthcare", "GenAI Engineer healthcare",
    "NLP Engineer healthcare", "Data Engineer healthcare",
    "AI Engineer clinical", "AI Engineer medical",
    "AI Engineer pharma", "AI Engineer biotech",
    "AI Engineer", "ML Engineer", "GenAI Engineer",
    "LLM Engineer", "NLP Engineer", "Data Scientist AI",
    "MLOps Engineer", "Data Engineer AI", "Deep Learning Engineer",
    "Computer Vision Engineer", "Knowledge Graph Engineer",
    "Applied AI Engineer", "AI Python Engineer",
]

# LinkedIn experience level: 2=Entry, 3=Associate (for 2yr exp)
JOB_EXP_LEVELS = "2%2C3"
JOB_TYPE = "F"  # Full-time


# ─── Smart Query Builder ─────────────────────────────────────────────────────

MAX_QUERIES = 150  # Cap total queries to avoid rate-limiting and wasted scrapes

def build_smart_queries() -> list[str]:
    """Build ranked, deduplicated query list. Capped at MAX_QUERIES, shuffled each run."""
    tier1, tier2, tier3, tier4 = [], [], [], []

    for role in ROLE_STEMS:
        for domain in DOMAIN_STEMS_HEALTHCARE:
            tier1.append(f"{role} {domain} hiring")
        for domain in DOMAIN_STEMS_GENERAL:
            tier2.append(f"{role} {domain} hiring")
        for action in ACTION_STEMS:
            tier3.append(f"{role} {action}")
        for loc in LOCATION_STEMS:
            if loc:
                exp = random.choice(EXP_STEMS)
                parts = [role, "hiring", loc]
                if exp:
                    parts.append(exp)
                tier4.append(" ".join(parts))

    random.shuffle(tier1)
    random.shuffle(tier2)
    random.shuffle(tier3)
    random.shuffle(tier4)

    seen = set()
    result = []
    for q in tier1 + tier2 + tier3 + tier4:
        key = " ".join(sorted(q.lower().split()))
        if key not in seen:
            seen.add(key)
            result.append(q)
        if len(result) >= MAX_QUERIES:
            break

    return result


# ─── Profile context for AI prompts ──────────────────────────────────────────

def get_profile_context() -> str:
    """Generate profile text block from PROFILE dict. Used in AI prompts."""
    skills = ", ".join(RESUME_SKILLS.keys())
    return (
        f"Name: {PROFILE['name']}\n"
        f"Experience: {PROFILE['experience_years']} years as {PROFILE['current_title']} at Southguild Technologies\n"
        f"Core Stack: Python, FastAPI, Neo4j, LLMs (Claude, OpenAI, Cohere), Docker, knowledge graphs\n"
        f"Domain Expertise: Healthcare AI, oncology, dermatopathology, NLP-to-Cypher, biomedical ETL\n"
        f"Key Achievement: PathAssist system — 98.8% accuracy, 5x faster clinical insight retrieval\n"
        f"Publications: 2 IEEE papers, 3 patents in AI/ML\n"
        f"Technical Skills: {skills}\n"
        f"Education: B.Tech (Hons.) CS Engineering, 8.5 CGPA, ML & AI specialization\n"
        f"Location: {PROFILE['location']} (willing to relocate)\n"
        f"LinkedIn: {PROFILE['linkedin']}\n"
        f"GitHub: {PROFILE['github']}\n"
    )
