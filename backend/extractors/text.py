"""Pure text extraction functions — no external dependencies beyond re."""

import re
from datetime import datetime, timedelta

from config import DOMAIN_KEYWORDS, ROLE_KEYWORDS


def parse_relative_time(text: str) -> str:
    """Parse LinkedIn-style relative timestamps like '3d', '1w', '2mo', '5h', '1m' into ISO date strings.

    Returns approximate posted date as 'YYYY-MM-DD' or empty string if not parseable.
    Handles: 3d, 1w, 2mo, 5h, 1m (minutes), 3m (months based on context), 2 days, 1 week, etc.
    """
    if not text:
        return ""
    text = text.strip().lower()
    now = datetime.now()

    # Try patterns: "3d", "1w", "2mo", "5h", "30m", "2 days", "1 week ago", etc.
    patterns = [
        (r'(\d+)\s*mo(?:nths?)?', "months"),
        (r'(\d+)\s*w(?:eeks?)?', "weeks"),
        (r'(\d+)\s*d(?:ays?)?', "days"),
        (r'(\d+)\s*h(?:ours?|rs?)?', "hours"),
        (r'(\d+)\s*min(?:utes?)?', "minutes"),
        (r'(\d+)\s*yr?s?', "years"),
    ]

    for pattern, unit in patterns:
        m = re.search(pattern, text)
        if m:
            n = int(m.group(1))
            if unit == "months":
                dt = now - timedelta(days=n * 30)
            elif unit == "weeks":
                dt = now - timedelta(weeks=n)
            elif unit == "days":
                dt = now - timedelta(days=n)
            elif unit == "hours":
                dt = now - timedelta(hours=n)
            elif unit == "minutes":
                dt = now - timedelta(minutes=n)
            elif unit == "years":
                dt = now - timedelta(days=n * 365)
            else:
                return ""
            return dt.strftime("%Y-%m-%d")

    # Handle bare "3m" — ambiguous (3 minutes or 3 months). If <= 12, treat as months.
    m = re.search(r'^(\d+)\s*m$', text)
    if m:
        n = int(m.group(1))
        dt = now - timedelta(days=n * 30) if n <= 12 else now - timedelta(minutes=n)
        return dt.strftime("%Y-%m-%d")

    return ""

EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
HASHTAG_RE = re.compile(r'#([A-Za-z]\w{1,})')


def extract_hashtags(text: str) -> str:
    """Return comma-separated unique hashtags found in text (without #), or empty string."""
    found = HASHTAG_RE.findall(text)
    seen = set()
    unique = []
    for tag in found:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            unique.append(tag)
    return ", ".join(unique)

# Phone regex: handles Indian numbers with spaces/dashes, international formats, numbers in brackets
# Examples: +91 76529 32771, +91-9876543210, (123) 456-7890, 9414339193, [9414339193]
PHONE_RE = re.compile(
    r'(?:\+?\d{1,3}[\s\-.]?)?'     # optional country code: +91, +1, etc.
    r'\(?\d{2,5}\)?'                # area/first group: (022), 91, 87803
    r'[\s\-.]?'                     # separator
    r'\d{2,5}'                      # middle group
    r'[\s\-.]?'                     # separator
    r'\d{2,6}'                      # last group
)


def extract_phones(text: str) -> str:
    """Return comma-separated phone numbers found in text, or empty string."""
    # Also catch numbers inside brackets like [9414339193]
    bracket_phones = re.findall(r'\[(\d{7,15})\]', text)
    # Also catch standalone 10-digit Indian numbers
    standalone = re.findall(r'(?<!\w)(\d{10})(?!\w)', text)
    found = PHONE_RE.findall(text) + bracket_phones + standalone

    unique = []
    seen = set()
    for p in found:
        digits = re.sub(r'\D', '', p)
        # Need 10+ digits for phone numbers
        if len(digits) >= 10 and digits not in seen:
            # Also mark the last 10 digits as seen to dedup +91XXXXXXXXXX vs XXXXXXXXXX
            seen.add(digits)
            seen.add(digits[-10:])
            unique.append(p.strip())
    return ", ".join(unique)


def extract_emails(text: str) -> str:
    """Return comma-separated emails found in text, or empty string."""
    found = EMAIL_RE.findall(text)
    seen = set()
    unique = []
    for e in found:
        if e.lower() not in seen:
            seen.add(e.lower())
            unique.append(e)
    return ", ".join(unique)


def extract_roles(text: str) -> str:
    """Return comma-separated roles detected in text via keyword matching."""
    lower = text.lower()
    found = []
    for role, keywords in ROLE_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            found.append(role)
    return ", ".join(found) if found else "Not specified"


def extract_location(text: str) -> str:
    """Detect common location mentions in post content."""
    patterns = [
        r'\b(remote|work from home|wfh)\b',
        r'\b(india|bangalore|bengaluru|mumbai|delhi|hyderabad|pune|chennai|kolkata|noida|gurgaon)\b',
        r'\b(usa|united states|new york|san francisco|boston|seattle|chicago|los angeles)\b',
        r'\b(uk|london|manchester|edinburgh)\b',
        r'\b(canada|toronto|vancouver|montreal)\b',
        r'\b(hybrid|on.?site|in.?office)\b',
    ]
    found = []
    lower = text.lower()
    for pattern in patterns:
        matches = re.findall(pattern, lower, re.IGNORECASE)
        found.extend(matches)

    seen = set()
    result = []
    for m in found:
        key = m.lower()
        if key not in seen:
            seen.add(key)
            result.append(m.title())
    return ", ".join(result) if result else ""


def normalize_experience(raw: str) -> str:
    """Normalize experience to clean format: '2 years', '3-5 years', etc."""
    if not raw:
        return ""
    raw = raw.lower().strip()

    if any(kw in raw for kw in ["fresher", "entry", "junior", "0 year", "no experience"]):
        return "0 years (Fresher)"

    m = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)', raw)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return f"{lo}-{hi} years"

    m = re.search(r'(\d+)\+?', raw)
    if m:
        n = int(m.group(1))
        suffix = "year" if n == 1 else "years"
        plus = "+" if "+" in raw else ""
        return f"{n}{plus} {suffix}"

    return raw


def extract_experience(text: str) -> str:
    """Extract experience requirements like '3+ years', '2-5 years'."""
    patterns = [
        r'(\d+\+?\s*(?:to|-)\s*\d*\+?\s*years?\s+(?:of\s+)?experience)',
        r'(\d+\+?\s*years?\s+(?:of\s+)?experience)',
        r'(experience[:\s]+\d+\+?\s*(?:to|-)\s*\d*\+?\s*years?)',
        r'(freshers?\s+welcome|entry.?level)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return normalize_experience(m.group(1).strip())
    return ""


def score_domain_relevance(text: str) -> str:
    """Score how relevant a post is to healthcare/medical/clinical domain."""
    lower = text.lower()
    matches = sum(1 for kw in DOMAIN_KEYWORDS if kw in lower)
    if matches >= 3:
        return "High"
    elif matches >= 1:
        return "Medium"
    return "Low"


def is_hiring_post(text: str) -> bool:
    """Quick check if a post is actually about hiring."""
    hiring_signals = [
        "we are hiring", "we're hiring", "now hiring", "job opening",
        "open position", "looking for", "join our team", "join us",
        "send your resume", "send resume", "send cv", "apply now",
        "dm me", "direct message", "reach out", "email us", "email at",
        "@gmail", "@yahoo", "@outlook", "careers@", "hr@", "jobs@",
        "talent@", "recruiting", "recruiter", "opportunity",
    ]
    lower = text.lower()
    return any(signal in lower for signal in hiring_signals)


def is_feed_job_post(text: str) -> bool:
    """Broader check for job-related posts in the LinkedIn feed.

    Feed posts are already curated by LinkedIn's algorithm, so we use a wider
    net than is_hiring_post() to catch:
    - Soft hiring signals ("my team is growing", "excited to share this role")
    - AI/ML and healthcare-specific job mentions
    - Job link shares (linkedin.com/jobs, greenhouse, lever, etc.)
    - Role title mentions combined with action words
    """
    lower = text.lower()

    # First check: explicit hiring signals (superset of is_hiring_post)
    if is_hiring_post(text):
        return True

    # Job board / ATS links in the post
    job_link_signals = [
        "linkedin.com/jobs", "jobs.lever.co", "boards.greenhouse.io",
        "ashbyhq.com", "workable.com", "apply.workable", "myworkdayjobs.com",
        "jobs.smartrecruiters", "careers.", "jobs.", "/careers/", "/jobs/",
        "angel.co/l/", "wellfound.com",
    ]
    if any(sig in lower for sig in job_link_signals):
        return True

    # Soft hiring signals — people sharing roles without explicit "hiring" keyword
    soft_signals = [
        "my team is hiring", "our team is hiring", "team is growing",
        "we need a", "we need an", "looking to hire", "looking to add",
        "come work with", "come join", "excited to share this role",
        "check out this role", "open role", "new role", "hot job",
        "know anyone who", "know someone who", "refer someone",
        "interested in this role", "amazing opportunity",
        "full-time", "full time", "part-time", "part time", "contract role",
        "remote role", "hybrid role", "onsite role",
        "years of experience", "years experience", "yoe",
        "#hiring", "#opentowork", "#jobopening", "#techjobs", "#aijobs",
        "#machinelearning", "#datascience", "#healthtech", "#healthcare",
        "#genai", "#llm",
    ]
    if any(sig in lower for sig in soft_signals):
        return True

    # AI/ML + healthcare role titles combined with action verbs
    role_keywords = [
        "machine learning engineer", "ml engineer", "data scientist",
        "ai engineer", "deep learning", "nlp engineer", "cv engineer",
        "computer vision", "mlops", "data engineer", "applied scientist",
        "research scientist", "research engineer", "genai", "gen ai",
        "llm engineer", "prompt engineer", "ai/ml", "ai & ml",
        "healthcare ai", "health ai", "healthtech", "clinical ai",
        "biomedical", "bioinformatics", "clinical data",
        "platform engineer", "backend engineer", "software engineer",
    ]
    action_words = [
        "hiring", "opening", "role", "position", "job", "apply",
        "join", "looking for", "needed", "wanted", "seeking",
        "opportunity", "vacancy", "openings",
    ]
    has_role = any(r in lower for r in role_keywords)
    has_action = any(a in lower for a in action_words)
    if has_role and has_action:
        return True

    return False


# ─── Skill Taxonomy ─────────────────────────────────────────────────────────

SKILL_TAXONOMY = {
    "language": [
        "python", "java", "javascript", "typescript", "r", "c++", "c#", "go", "golang",
        "rust", "scala", "julia", "ruby", "php", "swift", "kotlin", "sql", "bash",
    ],
    "ai_ml": [
        "langchain", "langgraph", "llamaindex", "llama-index", "openai", "anthropic",
        "hugging face", "huggingface", "transformers", "bert", "gpt", "llm", "llms",
        "rag", "retrieval augmented", "fine-tuning", "fine tuning", "lora", "qlora",
        "prompt engineering", "embeddings", "semantic search", "vector database", "vector db",
        "agentic ai", "ai agents", "multi-agent", "crewai", "autogen",
        "langserve", "dspy", "mcp", "tool calling", "function calling",
        "generative ai", "genai", "gen ai",
    ],
    "ml_framework": [
        "pytorch", "tensorflow", "keras", "scikit-learn", "sklearn", "xgboost",
        "lightgbm", "numpy", "pandas", "scipy", "spacy", "nltk", "opencv",
        "jax", "mlflow", "weights & biases", "wandb",
    ],
    "deep_learning": [
        "cnn", "rnn", "transformer", "attention mechanism", "gan", "diffusion model",
        "stable diffusion", "deep learning", "neural network", "nlp",
        "computer vision", "object detection", "segmentation", "ner",
        "sentiment analysis", "text summarization", "image processing",
    ],
    "backend": [
        "fastapi", "flask", "django", "express", "node.js", "nodejs",
        "rest api", "graphql", "grpc", "microservices", "api development",
        "pydantic", "asyncio", "celery", "redis",
    ],
    "frontend": [
        "react", "next.js", "nextjs", "vue", "angular", "svelte",
        "tailwind", "css", "html", "streamlit", "gradio",
    ],
    "database": [
        "postgresql", "postgres", "mysql", "mongodb", "sqlite", "dynamodb",
        "pinecone", "weaviate", "qdrant", "milvus", "chromadb", "chroma",
        "faiss", "pgvector", "neo4j", "elasticsearch",
    ],
    "cloud": [
        "aws", "azure", "gcp", "google cloud", "sagemaker", "bedrock",
        "vertex ai", "azure openai", "azure ml", "lambda", "s3",
        "ec2", "ecs", "eks", "fargate",
    ],
    "devops": [
        "docker", "kubernetes", "k8s", "ci/cd", "github actions",
        "terraform", "ansible", "jenkins", "gitlab ci", "argocd",
        "helm", "prometheus", "grafana",
    ],
    "data_engineering": [
        "spark", "hadoop", "airflow", "kafka", "flink", "dbt",
        "etl", "data pipeline", "data warehouse", "databricks",
        "snowflake", "bigquery", "redshift",
    ],
    "mlops": [
        "mlops", "ml ops", "mlflow", "kubeflow", "model monitoring",
        "model serving", "model deployment", "feature store",
        "experiment tracking", "a/b testing",
    ],
    "tools": [
        "git", "github", "gitlab", "jira", "confluence", "notion",
        "cursor", "windsurf", "copilot", "vscode",
        "jupyter", "colab", "postman",
    ],
}

# Flatten for quick lookup: skill_lower → category
_SKILL_LOOKUP = {}
for cat, skills in SKILL_TAXONOMY.items():
    for skill in skills:
        _SKILL_LOOKUP[skill.lower()] = cat


def extract_skills(text: str) -> dict:
    """Extract categorized skills from post text.

    Returns dict like:
    {
        "language": ["Python", "SQL"],
        "ai_ml": ["LangChain", "RAG", "LLMs"],
        "backend": ["FastAPI"],
        ...
    }
    """
    lower = text.lower()
    found = {}  # category -> set of skills

    for skill, category in _SKILL_LOOKUP.items():
        # Word boundary check to avoid partial matches
        # For short skills (<=3 chars), require exact word boundary
        if len(skill) <= 3:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, lower, re.IGNORECASE):
                found.setdefault(category, set()).add(skill)
        else:
            if skill in lower:
                found.setdefault(category, set()).add(skill)

    # Convert sets to sorted lists with proper casing
    CASE_MAP = {
        "python": "Python", "java": "Java", "javascript": "JavaScript", "typescript": "TypeScript",
        "sql": "SQL", "r": "R", "c++": "C++", "c#": "C#", "go": "Go", "golang": "Go",
        "rust": "Rust", "ruby": "Ruby", "php": "PHP", "bash": "Bash",
        "langchain": "LangChain", "langgraph": "LangGraph", "llamaindex": "LlamaIndex",
        "openai": "OpenAI", "anthropic": "Anthropic", "hugging face": "Hugging Face", "huggingface": "HuggingFace",
        "llm": "LLMs", "llms": "LLMs", "rag": "RAG", "genai": "GenAI", "gen ai": "GenAI",
        "generative ai": "GenAI", "fine-tuning": "Fine-tuning", "fine tuning": "Fine-tuning",
        "lora": "LoRA", "qlora": "QLoRA", "prompt engineering": "Prompt Engineering",
        "embeddings": "Embeddings", "semantic search": "Semantic Search",
        "vector database": "Vector DB", "vector db": "Vector DB",
        "agentic ai": "Agentic AI", "ai agents": "AI Agents", "multi-agent": "Multi-Agent",
        "crewai": "CrewAI", "autogen": "AutoGen", "dspy": "DSPy", "mcp": "MCP",
        "tool calling": "Tool Calling", "function calling": "Function Calling",
        "pytorch": "PyTorch", "tensorflow": "TensorFlow", "keras": "Keras",
        "scikit-learn": "Scikit-learn", "sklearn": "Scikit-learn",
        "xgboost": "XGBoost", "numpy": "NumPy", "pandas": "Pandas",
        "spacy": "spaCy", "nltk": "NLTK", "opencv": "OpenCV", "mlflow": "MLflow",
        "cnn": "CNN", "rnn": "RNN", "transformer": "Transformers", "gan": "GAN",
        "nlp": "NLP", "ner": "NER", "deep learning": "Deep Learning",
        "computer vision": "Computer Vision", "neural network": "Neural Networks",
        "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
        "node.js": "Node.js", "nodejs": "Node.js", "express": "Express",
        "rest api": "REST API", "graphql": "GraphQL", "grpc": "gRPC",
        "microservices": "Microservices", "pydantic": "Pydantic", "asyncio": "AsyncIO",
        "celery": "Celery", "redis": "Redis",
        "react": "React", "next.js": "Next.js", "nextjs": "Next.js",
        "streamlit": "Streamlit", "gradio": "Gradio", "tailwind": "Tailwind",
        "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "mysql": "MySQL",
        "mongodb": "MongoDB", "pinecone": "Pinecone", "weaviate": "Weaviate",
        "qdrant": "Qdrant", "milvus": "Milvus", "chromadb": "ChromaDB", "chroma": "ChromaDB",
        "faiss": "FAISS", "pgvector": "pgvector", "neo4j": "Neo4j", "elasticsearch": "Elasticsearch",
        "aws": "AWS", "azure": "Azure", "gcp": "GCP", "google cloud": "GCP",
        "sagemaker": "SageMaker", "bedrock": "Bedrock", "vertex ai": "Vertex AI",
        "azure openai": "Azure OpenAI", "azure ml": "Azure ML",
        "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
        "ci/cd": "CI/CD", "terraform": "Terraform", "jenkins": "Jenkins",
        "spark": "Spark", "hadoop": "Hadoop", "airflow": "Airflow", "kafka": "Kafka",
        "databricks": "Databricks", "etl": "ETL", "dbt": "dbt",
        "mlops": "MLOps", "ml ops": "MLOps", "kubeflow": "Kubeflow",
        "git": "Git", "github": "GitHub", "jira": "Jira", "cursor": "Cursor",
        "wandb": "W&B", "weights & biases": "W&B",
    }
    result = {}
    for cat, skills in found.items():
        seen = set()
        cased = []
        for s in sorted(skills):
            proper = CASE_MAP.get(s, s.title())
            if proper not in seen:
                seen.add(proper)
                cased.append(proper)
        result[cat] = cased

    return result
