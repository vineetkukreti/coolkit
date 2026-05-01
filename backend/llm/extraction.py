"""LLM-powered extraction functions — job info, email deobfuscation, deep analysis."""

import json
import re

from extractors.text import EMAIL_RE, normalize_experience
from llm.client import llm, OLLAMA_MODEL, GEMINI_MODEL

# ─── Prompts ─────────────────────────────────────────────────────────────────

_LLM_PROMPT = (
    "Extract hiring information from this LinkedIn job post.\n"
    "Rules:\n"
    "- role: The EXACT job title being hired for. E.g. 'AI Engineer', 'GenAI Engineer', 'ML Engineer', 'Agentic AI Engineer'. Use the title from the post.\n"
    "- company: Company name that is hiring. Look for 'at', '@', company names before 'is hiring'. Leave empty if unclear.\n"
    "- location: City name, 'Remote', 'Hybrid', or 'Pan India'. Extract ALL mentioned cities separated by ' / '. E.g. 'Pune / Bangalore / Remote'. Common Indian cities: Bangalore, Mumbai, Delhi, Hyderabad, Pune, Chennai, Noida, Gurgaon, Ahmedabad, Surat, Trivandrum, Gandhinagar, Kolkata. Leave empty if not mentioned.\n"
    "- experience: Extract ONLY if explicitly stated. Write as '2+ years' or '3-5 years'. Look for patterns like '2–3 Years', '4-6Years', '2+ years', 'Experience: 3+'. If 'fresher' or 'entry level', write '0 years'. If NOT mentioned, leave EMPTY string. Do NOT guess.\n"
    "- work_mode: 'Remote', 'Hybrid', 'WFO' (work from office), 'On-site', or empty. Look for keywords like 'Work From Office', 'WFO', 'On-site', 'Hybrid', 'Remote'.\n"
    "Reply ONLY with valid JSON: {\"role\":\"\",\"company\":\"\",\"location\":\"\",\"experience\":\"\",\"work_mode\":\"\"}\n\n"
)

_EMAIL_DEOBFUSCATION_PROMPT = (
    "Extract ALL email addresses from this text. People often hide emails like:\n"
    "- 'send to careers at company dot com'\n"
    "- 'email: hr[at]company[dot]com'\n"
    "- 'reach out firstname.lastname @ company .com'\n"
    "- 'gmail: username'\n"
    "- 'email id - someone at gmail'\n\n"
    "Return ONLY a JSON array of email strings. If no emails found, return [].\n"
    "Examples:\n"
    "  Input: 'Send resume to hr at acme dot com'\n"
    "  Output: [\"hr@acme.com\"]\n"
    "  Input: 'No contact info here'\n"
    "  Output: []\n\n"
)

_DEEP_ANALYSIS_PROMPT = (
    "Analyze this job posting in detail. Extract ALL of the following.\n"
    "Rules:\n"
    "- role: exact job title from the posting\n"
    "- company: company name\n"
    "- location: city/country or Remote\n"
    "- experience: years required, e.g. '2-3 years'. Empty if not stated.\n"
    "- salary: salary/compensation if mentioned. Empty if not.\n"
    "- tech_stack: comma-separated list of technologies/tools mentioned\n"
    "- emails: any email addresses found (including obfuscated like 'hr at company dot com')\n"
    "- apply_url: application URL if mentioned\n"
    "- fit_score: 1-10 score. This candidate: AI Engineer, 2yr exp, healthcare AI, RAG, LLMs, Python, FastAPI\n"
    "- fit_reasons: 2-3 short reasons why good/bad fit\n"
    "- talking_points: 2-3 specific things from this JD to mention in a cold email\n"
    "Reply ONLY with valid JSON, nothing else.\n\n"
)

# ─── Response parsers ─────────────────────────────────────────────────────────


def _parse_llm_response(raw: str) -> dict:
    """Extract JSON from LLM response text and normalize fields."""
    m = re.search(r'\{[^}]+\}', raw, re.DOTALL)
    if m:
        parsed = json.loads(m.group())
        if parsed.get("experience"):
            parsed["experience"] = normalize_experience(parsed["experience"])
        return parsed
    return {}


def _parse_deep_analysis(raw: str) -> dict:
    """Parse deep analysis JSON response."""
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if not m:
        return {}
    try:
        parsed = json.loads(m.group())
        if parsed.get("experience"):
            parsed["experience"] = normalize_experience(parsed["experience"])
        if isinstance(parsed.get("tech_stack"), list):
            parsed["tech_stack"] = ", ".join(parsed["tech_stack"])
        if isinstance(parsed.get("fit_reasons"), list):
            parsed["fit_reasons"] = json.dumps(parsed["fit_reasons"])
        if isinstance(parsed.get("talking_points"), list):
            parsed["talking_points"] = json.dumps(parsed["talking_points"])
        if isinstance(parsed.get("emails"), list):
            parsed["emails"] = ", ".join(parsed["emails"])
        if isinstance(parsed.get("fit_score"), (int, float)):
            parsed["fit_score"] = float(parsed["fit_score"])
        return parsed
    except (json.JSONDecodeError, ValueError):
        return {}


# ─── Public extraction functions ──────────────────────────────────────────────


def ollama_available() -> bool:
    """Check if Ollama is running. Delegates to LLMClient singleton."""
    return llm.ollama_available()


def ollama_extract(content: str) -> dict:
    """Extract job info using local Ollama."""
    prompt = _LLM_PROMPT + f"Post: {content[:500]}\n\n" + 'JSON: {"role":"","company":"","location":"","experience":"","work_mode":""}'
    raw = llm.call_ollama(prompt, max_tokens=120)
    return _parse_llm_response(raw) if raw else {}


def gemini_extract(content: str) -> dict:
    """Extract job info using Gemini API."""
    prompt = _LLM_PROMPT + f"Post: {content[:1500]}\n\n" + 'JSON: {"role":"","company":"","location":"","experience":"","work_mode":""}'
    raw = llm.call_gemini(prompt, max_tokens=200)
    return _parse_llm_response(raw) if raw else {}


def llm_extract(content: str) -> dict:
    """Extract job info using Ollama (primary) or Gemini (fallback)."""
    result = ollama_extract(content)
    if result:
        return result

    from llm.client import GEMINI_API_KEY
    if GEMINI_API_KEY and llm.gemini_ok is not False:
        result = gemini_extract(content)
        if result:
            return result

    return {}


def llm_extract_emails(content: str) -> list[str]:
    """Use LLM to find obfuscated/hidden emails that regex misses."""
    lower = content.lower()
    signals = ["@", " at ", "[at]", "(at)", "dot com", "dot in", "dot org",
               "gmail", "yahoo", "outlook", "email", "mail to", "mail us",
               "send resume", "send cv", "reach out", "contact"]
    if not any(s in lower for s in signals):
        return []

    regex_emails = EMAIL_RE.findall(content)
    if len(regex_emails) >= 2:
        return []

    prompt = _EMAIL_DEOBFUSCATION_PROMPT + f"Text: {content[:800]}\n\nJSON:"
    raw = llm.call_gemini(prompt, max_tokens=100)

    if raw:
        try:
            m = re.search(r'\[.*?\]', raw, re.DOTALL)
            if m:
                emails = json.loads(m.group())
                return [e for e in emails if isinstance(e, str) and EMAIL_RE.match(e)]
        except Exception:
            pass

    return []


def llm_deep_analyze(content: str) -> dict:
    """Rich LLM analysis of full job description."""
    if not content or len(content) < 50:
        return {}

    prompt = _DEEP_ANALYSIS_PROMPT + f"Job posting:\n{content[:2000]}\n\nJSON:"

    # Try Ollama first
    raw = llm.call_ollama(prompt, max_tokens=400)
    if raw:
        parsed = _parse_deep_analysis(raw)
        if parsed:
            return parsed

    # Fallback to Gemini
    raw = llm.call_gemini(prompt, max_tokens=400)
    if raw:
        parsed = _parse_deep_analysis(raw)
        if parsed:
            return parsed

    return {}
