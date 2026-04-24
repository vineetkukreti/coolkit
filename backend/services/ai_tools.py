"""Gemini-powered AI tools for job search assistance."""

import json
import os

import requests

from config import RESUME_SKILLS, get_profile_context

VINEET_PROFILE = get_profile_context()
RESUME_SKILLS_LIST = ", ".join(RESUME_SKILLS.keys())

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _call_gemini(prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
    """Call Gemini API and return text response."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}",
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens, "topP": 0.9},
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def _parse_json_response(text: str) -> dict:
    """Extract JSON from Gemini response that may have markdown code blocks."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return json.loads(text.strip())


# ---------------------------------------------------------------------------
# 1. Evaluate Job
# ---------------------------------------------------------------------------


def evaluate_job(jd_text: str) -> dict:
    """Evaluate a job description against Vineet's profile and return a structured assessment."""
    prompt = f"""You are a career-match analyst. Evaluate the following job description against the candidate profile below.

━━━ CANDIDATE PROFILE ━━━
{VINEET_PROFILE}
Resume Skills (with weight): {json.dumps(RESUME_SKILLS, indent=2)}

━━━ JOB DESCRIPTION ━━━
{jd_text}

━━━ INSTRUCTIONS ━━━
Produce a JSON object with EXACTLY this structure (no extra keys, no markdown outside the JSON):

{{
    "summary": {{
        "archetype": "<role archetype, e.g. 'Backend ML Engineer'>",
        "domain": "<industry domain>",
        "seniority": "<junior/mid/senior/lead>",
        "remote": "<remote/hybrid/onsite/unknown>",
        "location": "<location or 'Not specified'>",
        "tldr": "<one-sentence summary of the role>"
    }},
    "cv_match": {{
        "matched": [
            {{"requirement": "<JD requirement>", "vineet_has": "<matching experience>", "strength": "strong|partial|gap"}}
        ],
        "match_pct": <0-100 integer>
    }},
    "gaps": [
        {{"skill": "<missing skill>", "severity": "hard_blocker|learnable|nice_to_have", "mitigation": "<how to address>"}}
    ],
    "score": <1.0-5.0 float>,
    "verdict": "APPLY|CONSIDER|SKIP",
    "personalization": ["<top 5 CV changes to make for this role>"],
    "interview_topics": ["<likely interview areas>"]
}}

Be honest and precise. Return ONLY valid JSON."""

    try:
        text = _call_gemini(prompt, max_tokens=2000, temperature=0.4)
        return _parse_json_response(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return {"error": f"Failed to parse Gemini response: {exc}", "raw": text if "text" in dir() else ""}
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 2. Generate Outreach
# ---------------------------------------------------------------------------


def generate_outreach(company: str, role: str, recruiter_name: str = "", context: str = "") -> dict:
    """Generate personalized cold outreach messages for a target company/role."""
    recruiter_line = f"Recruiter/Hiring Manager: {recruiter_name}" if recruiter_name else "Recruiter name: unknown (use generic greeting)"
    context_line = f"Additional context: {context}" if context else ""

    prompt = f"""You are an expert cold-outreach copywriter for tech job seekers.

━━━ CANDIDATE ━━━
{VINEET_PROFILE}

━━━ TARGET ━━━
Company: {company}
Role: {role}
{recruiter_line}
{context_line}

━━━ RULES ━━━
- Reference something SPECIFIC about the company (product, recent news, tech stack)
- Lead with VALUE the candidate brings, not an ask
- Include quantified proof points from Vineet's experience (e.g. "built a knowledge-graph pipeline processing 50K+ clinical records")
- NEVER use "I'm passionate about" or "caught my eye" or similar clichés
- Cold email: under 150 words, punchy, clear CTA
- LinkedIn message: under 300 characters
- Follow-up email: for 7 days later, add new value/insight

Return ONLY a JSON object with this structure:

{{
    "cold_email": {{"subject": "<subject line>", "body": "<email body>"}},
    "linkedin_message": "<LinkedIn connection message under 300 chars>",
    "followup_email": {{"subject": "<follow-up subject>", "body": "<follow-up body>"}},
    "tips": "<brief tactical tips for this specific outreach>"
}}

Return ONLY valid JSON."""

    try:
        text = _call_gemini(prompt, max_tokens=1500, temperature=0.7)
        return _parse_json_response(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return {"error": f"Failed to parse Gemini response: {exc}", "raw": text if "text" in dir() else ""}
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 3. Deep Dive Company
# ---------------------------------------------------------------------------


def deep_dive_company(company: str, role: str = "") -> dict:
    """Research a company and generate strategic intelligence for job applications."""
    role_line = f"Target role: {role}" if role else ""

    prompt = f"""You are a competitive intelligence analyst helping a job seeker.

━━━ CANDIDATE ━━━
{VINEET_PROFILE}

━━━ COMPANY TO RESEARCH ━━━
Company: {company}
{role_line}

━━━ INSTRUCTIONS ━━━
Based on your knowledge of this company, produce a JSON object with this structure:

{{
    "ai_strategy": "<company's AI/ML strategy and investments>",
    "recent_moves": "<recent news, product launches, acquisitions, funding>",
    "engineering_culture": "<engineering culture, tech stack, development practices>",
    "challenges": "<key business/technical challenges the company likely faces>",
    "competitive_position": "<where they stand vs competitors>",
    "your_angle": "<how Vineet's specific skills map to their needs>",
    "outreach_hook": "<a specific, non-generic hook for cold outreach>",
    "suggested_opening": "<opening line for a cold email or interview>"
}}

Be specific and actionable. If you lack information on the company, say so honestly rather than fabricating.
Return ONLY valid JSON."""

    try:
        text = _call_gemini(prompt, max_tokens=1500, temperature=0.5)
        return _parse_json_response(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return {"error": f"Failed to parse Gemini response: {exc}", "raw": text if "text" in dir() else ""}
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 4. Tailor CV
# ---------------------------------------------------------------------------


def tailor_cv(jd_text: str) -> dict:
    """Generate tailored CV sections for a specific job description."""
    prompt = f"""You are an expert CV/resume writer specializing in ATS optimization.

━━━ CANDIDATE PROFILE ━━━
{VINEET_PROFILE}
Resume Skills: {RESUME_SKILLS_LIST}

━━━ JOB DESCRIPTION ━━━
{jd_text}

━━━ RULES ━━━
- NEVER invent skills or experience Vineet does not have
- Only reformulate and reorder existing experience using the JD's vocabulary
- Prioritize keywords from the JD that Vineet genuinely possesses
- Professional summary: 2-3 sentences, tailored to this specific role

Return ONLY a JSON object with this structure:

{{
    "professional_summary": "<2-3 sentence tailored summary>",
    "core_competencies": ["<skill 1>", "<skill 2>", "...up to 10 most relevant skills"],
    "experience_bullets": [
        "<reworded/reordered bullet point using JD vocabulary>",
        "...5-8 bullets"
    ],
    "keyword_coverage": {{
        "matched": ["<JD keywords Vineet has>"],
        "gaps": ["<JD keywords Vineet lacks>"],
        "coverage_pct": <0-100 integer>
    }},
    "suggested_filename": "<suggested resume filename e.g. Vineet_Kukreti_AI_Engineer_CompanyName.pdf>"
}}

Return ONLY valid JSON."""

    try:
        text = _call_gemini(prompt, max_tokens=1500, temperature=0.4)
        return _parse_json_response(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return {"error": f"Failed to parse Gemini response: {exc}", "raw": text if "text" in dir() else ""}
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 5. Interview Prep
# ---------------------------------------------------------------------------


def interview_prep(company: str, role: str) -> dict:
    """Generate comprehensive interview preparation material."""
    prompt = f"""You are a senior technical interview coach.

━━━ CANDIDATE ━━━
{VINEET_PROFILE}
Resume Skills: {RESUME_SKILLS_LIST}

━━━ TARGET ━━━
Company: {company}
Role: {role}

━━━ INSTRUCTIONS ━━━
Generate interview preparation material. Return ONLY a JSON object:

{{
    "process_overview": "<expected interview process for this company/role>",
    "rounds": [
        {{
            "name": "<round name, e.g. 'Phone Screen'>",
            "duration": "<estimated duration>",
            "focus": "<what this round tests>",
            "likely_questions": ["<question 1>", "<question 2>", "...3-5 questions"]
        }}
    ],
    "star_stories": [
        {{
            "title": "<story title>",
            "situation": "<context>",
            "task": "<what needed to be done>",
            "action": "<what Vineet did>",
            "result": "<outcome with metrics if possible>",
            "reflection": "<what was learned>",
            "maps_to": ["<competency 1>", "<competency 2>"]
        }}
    ],
    "technical_checklist": ["<topic to review>", "...8-12 items"],
    "questions_to_ask": ["<smart question to ask interviewer>", "...5-8 questions"],
    "red_flags": [
        {{
            "question": "<tricky or sensitive question>",
            "how_to_answer": "<suggested approach>"
        }}
    ]
}}

Base STAR stories on Vineet's actual experience (healthcare AI, knowledge graphs, clinical NLP, Neo4j pipelines). Do NOT invent projects he hasn't done.
Return ONLY valid JSON."""

    try:
        text = _call_gemini(prompt, max_tokens=2500, temperature=0.5)
        return _parse_json_response(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return {"error": f"Failed to parse Gemini response: {exc}", "raw": text if "text" in dir() else ""}
    except Exception as exc:
        return {"error": str(exc)}
