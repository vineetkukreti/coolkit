"""
Multi-Source Job Scrapers
--------------------------
Scrapes hiring posts from DuckDuckGo web search, Wellfound, and YC Jobs.
All scrapers output the same dict format as LinkedIn post scraper
so they feed into the same DB pipeline.

Usage:
    Called from server.py via scraper endpoints.
    Each scraper takes a Playwright page + DB connection.
"""

import os
import re
import time
import random
from urllib.parse import quote_plus
from rich.console import Console

from db import content_hash, DedupCache, post_exists
from post_parser import (
    llm_extract, extract_roles, extract_location, extract_experience,
    extract_emails, score_domain_relevance, is_hiring_post,
    is_good_fit, normalize_experience, DOMAIN_KEYWORDS,
)

console = Console()


# ─── Shared helpers ──────────────────────────────────────────────────────────

def _process_job_into_post(job: dict, source: str, term: str, dedup, all_posts: list, emit) -> bool:
    """Shared logic: take a raw job dict, run fitness checks, build post dict.
    Returns True if post was added."""
    job_url = job.get("jobUrl", "")
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    desc = job.get("desc", "")
    content = f"{title} at {company}. {desc}. Location: {location}".strip()

    if len(content) < 20:
        return False

    c_hash = content_hash(content)
    if dedup.exists(job_url, c_hash, content):
        return False

    domain = score_domain_relevance(content)

    # Try LLM extraction for richer data
    llm = {}
    if len(content) > 50:
        llm = llm_extract(content)

    roles = llm.get("role") or extract_roles(content)
    if roles == "Not specified":
        roles = title  # Use job title as role fallback
    loc = llm.get("location") or extract_location(content) or location
    comp = llm.get("company") or company
    exp = llm.get("experience", "")
    emails = extract_emails(content)

    fit, reason = is_good_fit(roles, exp)
    if not fit:
        emit({"type": "skip", "author": (comp or title)[:20], "reason": reason})
        return False

    data = {
        "sno": len(all_posts) + 1,
        "author_name": comp or "Unknown",
        "author_profile": job_url,
        "author_headline": f"Found via {source}",
        "post_url": job_url,
        "content": content,
        "role_hiring_for": roles,
        "company": comp,
        "email": emails or "",
        "location": loc,
        "experience": exp,
        "domain_relevance": domain,
        "post_date": "",
        "keyword_matched": term,
        "is_hiring": True,
        "source": source.lower(),
    }

    all_posts.append(data)
    dedup.add(job_url, c_hash, content)

    emit({
        "type": "found",
        "sno": data["sno"],
        "author": (comp or title)[:25],
        "role": roles[:25],
        "company": comp[:20],
        "email": (emails or "")[:25],
        "domain": domain,
        "source": source,
    })
    return True


# ─── DuckDuckGo Web Search Scraper ──────────────────────────────────────────
# Uses DuckDuckGo instead of Google to avoid CAPTCHAs

def _build_search_queries() -> list[str]:
    """Build web search queries targeting healthcare AI hiring posts."""
    roles = [
        "clinical AI engineer", "AI engineer", "ML engineer", "GenAI engineer",
        "LLM engineer", "agentic AI", "AI/ML engineer",
    ]
    domains = [
        "healthcare", "clinical", "medical", "health tech",
        "pharma", "biotech", "digital health", "oncology",
        "radiology", "hospital",
    ]
    queries = []

    for role in roles:
        for domain in domains[:5]:
            queries.append(f'{role} {domain} hiring')
        queries.append(f'{role} hiring India 2025')

    # Clinical AI specific
    queries.append("clinical AI engineer job opening")
    queries.append("clinical AI engineer hiring India remote")
    queries.append("clinical ML engineer healthcare hiring")
    queries.append("AI engineer radiology oncology hiring")
    queries.append("healthcare AI startup hiring India")
    queries.append("agentic AI engineer healthcare")
    queries.append("LLM healthcare hiring remote India")
    queries.append("medical AI engineer hiring recruiter email")
    queries.append("clinical data scientist AI hiring")

    random.shuffle(queries)
    return queries


def scrape_google(page, conn, max_posts: int = 200, on_event=None) -> list[dict]:
    """Scrape DuckDuckGo search results for healthcare AI hiring posts."""

    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    all_posts = []
    dedup = DedupCache(conn)
    queries = _build_search_queries()

    emit({"type": "info", "message": f"Web search scraper: {len(queries)} queries, target {max_posts} posts"})

    for qi, query in enumerate(queries):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"[WebSearch] {query[:60]}", "index": qi + 1, "total": len(queries)})

        try:
            url = f"https://duckduckgo.com/?q={quote_plus(query)}&ia=web"
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            time.sleep(random.uniform(2, 4))
        except Exception as e:
            emit({"type": "error", "message": f"DuckDuckGo nav failed: {str(e)[:100]}"})
            time.sleep(3)
            continue

        # Extract search results — DuckDuckGo uses article elements
        results = page.evaluate("""
        () => {
            const items = [];
            // DuckDuckGo result selectors
            document.querySelectorAll('article[data-testid="result"], li[data-layout="organic"], .result, .nrn-react-div').forEach(el => {
                const linkEl = el.querySelector('a[data-testid="result-title-a"], a[href]:not([href*="duckduckgo"])');
                const titleEl = el.querySelector('h2, [data-testid="result-title-a"], a > span');
                const snippetEl = el.querySelector('[data-result="snippet"], .result__snippet, span[class*="snippet"]');
                if (linkEl && (titleEl || linkEl)) {
                    const url = linkEl.href || '';
                    if (url && !url.includes('duckduckgo.com') && url.startsWith('http')) {
                        items.push({
                            url: url,
                            title: (titleEl || linkEl).innerText.trim(),
                            snippet: snippetEl ? snippetEl.innerText.trim() : '',
                        });
                    }
                }
            });
            return items;
        }
        """)

        emit({"type": "extract", "count": len(results)})

        new_this_query = 0
        for result in results:
            if len(all_posts) >= max_posts:
                break

            url = result.get("url", "")
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            content = f"{title}\n{snippet}"

            if len(content) < 30:
                continue

            c_hash = content_hash(content)
            if dedup.exists(url, c_hash, content):
                continue

            # Must be hiring-related
            if not is_hiring_post(content) and not any(kw in content.lower() for kw in ["hiring", "job", "role", "position", "opening", "career"]):
                continue

            # Determine source from URL
            source = "Web"
            if "linkedin.com" in url:
                source = "LinkedIn"
            elif "twitter.com" in url or "x.com" in url:
                source = "Twitter/X"
            elif "wellfound.com" in url or "angel.co" in url:
                source = "Wellfound"

            emails = extract_emails(content)
            domain = score_domain_relevance(content)

            llm = llm_extract(content) if len(content) > 50 else {}
            roles = llm.get("role") or extract_roles(content)
            location = llm.get("location") or extract_location(content)
            company = llm.get("company", "")

            fit, reason = is_good_fit(roles, llm.get("experience", ""))
            if not fit:
                emit({"type": "skip", "author": title[:30], "reason": reason})
                continue

            data = {
                "sno": len(all_posts) + 1,
                "author_name": company or title[:40],
                "author_profile": url,
                "author_headline": f"Found via Web Search ({source})",
                "post_url": url,
                "content": content,
                "role_hiring_for": roles,
                "company": company,
                "email": emails or "",
                "location": location,
                "experience": llm.get("experience", ""),
                "domain_relevance": domain,
                "post_date": "",
                "keyword_matched": query[:50],
                "is_hiring": True,
                "source": source.lower(),
            }

            all_posts.append(data)
            dedup.add(url, c_hash, content)
            new_this_query += 1

            emit({
                "type": "found",
                "sno": data["sno"],
                "author": data["author_name"][:25],
                "role": roles[:25],
                "company": company[:20],
                "email": (emails or "")[:25],
                "domain": domain,
                "source": source,
            })

        emit({"type": "query_done", "query": f"[WebSearch] {query[:40]}", "found_count": len(all_posts), "query_new": new_this_query})
        time.sleep(random.uniform(2, 4))

    return all_posts


# ─── Wellfound (AngelList) Scraper ───────────────────────────────────────────

def scrape_wellfound(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Wellfound (AngelList) for healthcare AI startup jobs."""

    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    all_posts = []
    dedup = DedupCache(conn)

    search_terms = [
        "ai engineer healthcare",
        "machine learning engineer health",
        "genai engineer",
        "llm engineer",
        "ai engineer medical",
        "ai engineer biotech",
        "agentic ai engineer",
        "ml engineer clinical",
    ]

    emit({"type": "info", "message": f"Wellfound scraper: {len(search_terms)} searches"})

    captcha_detected = False

    for si, term in enumerate(search_terms):
        if len(all_posts) >= max_posts:
            break
        if captcha_detected:
            break

        emit({"type": "search", "query": f"[Wellfound] {term}", "index": si + 1, "total": len(search_terms)})

        # Wellfound uses /jobs with query params now
        try:
            url = f"https://wellfound.com/jobs?query={quote_plus(term)}"
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(random.uniform(4, 6))
        except Exception as e:
            emit({"type": "error", "message": f"Wellfound nav failed: {str(e)[:100]}"})
            continue

        # Check for CAPTCHA/bot challenge (Wellfound blocks with slider CAPTCHA)
        try:
            body_html_len = page.evaluate("() => document.body?.innerHTML?.length || 0")
            has_challenge = page.evaluate("() => (document.body?.innerHTML || '').includes('challenge') || (document.body?.innerHTML || '').includes('Verification')")
            has_iframes = page.evaluate("() => document.querySelectorAll('iframe').length")
            if body_html_len < 5000 and (has_challenge or has_iframes >= 2):
                emit({"type": "error", "message": "Wellfound CAPTCHA/bot challenge detected — your IP is blocked. Skipping all searches."})
                captcha_detected = True
                break
        except Exception:
            pass

        # Scroll to load lazy content
        for _ in range(4):
            page.evaluate("window.scrollBy(0, 1000)")
            time.sleep(1.5)

        # Broad extraction — try multiple selector strategies for React SPA
        jobs = page.evaluate("""
        () => {
            const cards = [];

            // Strategy 1: look for any link that goes to a job page
            document.querySelectorAll('a[href*="/jobs/"], a[href*="/l/"]').forEach(a => {
                // Walk up to find the card container
                let card = a.closest('[class*="card"], [class*="Card"], [class*="result"], [class*="Result"], [class*="listing"], [class*="Listing"]') || a.parentElement?.parentElement;
                if (!card) return;

                const title = card.querySelector('h2, h3, h4, [class*="title"], [class*="Title"], [class*="name"], [class*="Name"]');
                const company = card.querySelector('[class*="company"], [class*="Company"], [class*="startup"], [class*="Startup"], [class*="org"]');
                const loc = card.querySelector('[class*="location"], [class*="Location"]');

                const titleText = title ? title.innerText.trim() : a.innerText.trim();
                const companyText = company ? company.innerText.trim() : '';
                const locText = loc ? loc.innerText.trim() : '';

                if (titleText && titleText.length > 3) {
                    cards.push({
                        title: titleText.slice(0, 100),
                        company: companyText.slice(0, 80),
                        location: locText.slice(0, 60),
                        jobUrl: a.href.startsWith('http') ? a.href.split('?')[0] : 'https://wellfound.com' + a.getAttribute('href'),
                        desc: ''
                    });
                }
            });

            // Strategy 2: If strategy 1 found nothing, try getting all visible text blocks
            if (cards.length === 0) {
                document.querySelectorAll('[role="listitem"], [class*="job"], [class*="Job"]').forEach(el => {
                    const link = el.querySelector('a[href]');
                    const text = el.innerText.trim();
                    if (link && text.length > 10) {
                        cards.push({
                            title: text.split('\\n')[0].slice(0, 100),
                            company: text.split('\\n')[1]?.slice(0, 80) || '',
                            location: '',
                            jobUrl: link.href,
                            desc: text.slice(0, 200)
                        });
                    }
                });
            }

            // Deduplicate by URL
            const seen = new Set();
            return cards.filter(c => {
                if (seen.has(c.jobUrl)) return false;
                seen.add(c.jobUrl);
                return true;
            });
        }
        """)

        emit({"type": "extract", "count": len(jobs)})

        for job in jobs:
            if len(all_posts) >= max_posts:
                break
            _process_job_into_post(job, "Wellfound", term, dedup, all_posts, emit)

        time.sleep(random.uniform(2, 4))

    return all_posts


# ─── YC Jobs (Work at a Startup) Scraper ─────────────────────────────────────

def scrape_yc_jobs(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Y Combinator's Work at a Startup job board."""

    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    all_posts = []
    dedup = DedupCache(conn)

    search_terms = [
        "ai engineer",
        "machine learning",
        "llm",
        "generative ai",
        "healthcare ai",
        "agentic",
        "ml engineer",
    ]

    emit({"type": "info", "message": f"YC Jobs scraper: {len(search_terms)} searches"})

    for si, term in enumerate(search_terms):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"[YC Jobs] {term}", "index": si + 1, "total": len(search_terms)})

        try:
            url = f"https://www.workatastartup.com/jobs?query={quote_plus(term)}"
            page.goto(url, timeout=30000, wait_until="networkidle")
            time.sleep(random.uniform(4, 7))
        except Exception as e:
            emit({"type": "error", "message": f"YC Jobs nav failed: {str(e)[:100]}"})
            continue

        # Scroll aggressively — React SPA lazy-loads
        for _ in range(6):
            page.evaluate("window.scrollBy(0, 1200)")
            time.sleep(1.5)

        # Wait for any loading spinners to disappear
        time.sleep(2)

        # Broad extraction — multiple strategies for React SPA
        jobs = page.evaluate("""
        () => {
            const cards = [];

            // Strategy 1: job listing links
            document.querySelectorAll('a[href*="/jobs/"], a[href*="/company/"]').forEach(a => {
                let card = a.closest('[class*="job"], [class*="Job"], [class*="listing"], [class*="Listing"], [class*="card"], [class*="Card"], tr, [class*="row"], [class*="Row"]') || a.parentElement?.parentElement;
                if (!card) return;

                const allText = card.innerText.trim();
                const lines = allText.split('\\n').filter(l => l.trim().length > 0);
                if (lines.length === 0) return;

                // First meaningful line is usually the job title or company
                const title = lines[0].slice(0, 100);
                const company = lines.length > 1 ? lines[1].slice(0, 80) : '';
                const loc = lines.find(l => /remote|san francisco|new york|india|bangalore/i.test(l)) || '';

                if (title.length > 3) {
                    cards.push({
                        title,
                        company,
                        location: loc.slice(0, 60),
                        jobUrl: a.href.startsWith('http') ? a.href.split('?')[0] : 'https://www.workatastartup.com' + a.getAttribute('href'),
                        desc: lines.slice(2, 5).join(' ').slice(0, 300)
                    });
                }
            });

            // Strategy 2: visible list items
            if (cards.length === 0) {
                document.querySelectorAll('[role="listitem"], [class*="result"], li').forEach(el => {
                    const link = el.querySelector('a[href]');
                    const text = el.innerText.trim();
                    if (link && text.length > 10) {
                        cards.push({
                            title: text.split('\\n')[0].slice(0, 100),
                            company: text.split('\\n')[1]?.slice(0, 80) || '',
                            location: '',
                            jobUrl: link.href,
                            desc: text.slice(0, 300)
                        });
                    }
                });
            }

            // Deduplicate
            const seen = new Set();
            return cards.filter(c => {
                if (seen.has(c.jobUrl)) return false;
                seen.add(c.jobUrl);
                return true;
            });
        }
        """)

        emit({"type": "extract", "count": len(jobs)})

        for job in jobs:
            if len(all_posts) >= max_posts:
                break
            _process_job_into_post(job, "YC Jobs", term, dedup, all_posts, emit)

        time.sleep(random.uniform(2, 4))

    return all_posts


# ─── Indeed Scraper (via jp.indeed.com — only unblocked domain) ──────────────
# Indeed.com and all country variants block Playwright with Cloudflare EXCEPT
# jp.indeed.com (Japan). Tested 2026-04-24: 21 domains tested, only Japan works.
# jp.indeed.com supports English searches and returns global remote jobs.
#
# Verified selectors (from live test):
#   Cards:   .tapItem, .job_seen_beacon
#   Title:   h2.jobTitle span (or .jobTitle a)
#   Company: [data-testid="company-name"], .css-*  company div
#   Location: [data-testid="text-location"], .css-* location div

def scrape_indeed(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Indeed via jp.indeed.com (only unblocked domain). No login needed."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = lambda e: on_event(e) if on_event else None

    search_terms = [
        "AI Engineer remote",
        "Machine Learning Engineer remote",
        "Data Scientist remote",
        "NLP Engineer",
        "GenAI Engineer",
        "LLM Engineer",
        "Deep Learning Engineer remote",
        "Python AI developer",
        "AI Engineer English",
    ]

    emit({"type": "info", "message": "Starting Indeed scraper (via jp.indeed.com — only unblocked domain)..."})

    for si, term in enumerate(search_terms):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"Indeed JP: {term}", "index": si + 1, "total": len(search_terms)})

        url = f"https://jp.indeed.com/jobs?q={quote_plus(term)}&sort=date&fromage=14"
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except Exception as e:
            emit({"type": "error", "message": f"Indeed JP navigation error: {str(e)[:200]}"})
            continue

        time.sleep(random.uniform(3, 5))

        # Check for Cloudflare block
        title = page.title()
        if "moment" in title.lower() or "verification" in title.lower():
            emit({"type": "error", "message": "Indeed JP blocked by Cloudflare — aborting"})
            break

        # Scroll to load all cards
        for _ in range(4):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(random.uniform(1, 1.5))

        # Verified selectors from live testing (2026-04-24):
        # .tapItem = clickable job card (64 found per page)
        # .job_seen_beacon = same cards, alternate selector
        # h2.jobTitle / h2[class*="jobTitle"] = job title
        # [data-testid="company-name"] or div[class*="company"] = company
        # [data-testid="text-location"] or div[class*="company"] sibling = location
        jobs = page.evaluate("""() => {
            const cards = [];
            const cardEls = document.querySelectorAll('.tapItem, .job_seen_beacon');
            const seen = new Set();

            cardEls.forEach(el => {
                // Title: h2 with jobTitle class, get the inner span or a text
                const titleEl = el.querySelector('h2[class*="jobTitle"] span, h2[class*="jobTitle"] a, h2.jobTitle span, .jobTitle span, .jobTitle a');
                const title = titleEl ? titleEl.innerText.trim() : '';

                // Job URL: the main link with /rc/clk or /viewjob
                const linkEl = el.querySelector('a[href*="/rc/clk"], a[href*="/viewjob"], h2[class*="jobTitle"] a, .jobTitle a');
                const jobUrl = linkEl ? linkEl.href : '';

                // Company: data-testid or css class
                const companyEl = el.querySelector('[data-testid="company-name"], [class*="company"][class*="name"], [class*="companyName"]');
                const company = companyEl ? companyEl.innerText.trim() : '';

                // Location
                const locEl = el.querySelector('[data-testid="text-location"], [class*="companyLocation"], [class*="location"]');
                const location = locEl ? locEl.innerText.trim() : '';

                // Salary (if shown)
                const salEl = el.querySelector('[class*="salary"], [class*="metadata"][class*="salary"], [data-testid="attribute_snippet_testid"]');
                const salary = salEl ? salEl.innerText.trim() : '';

                if (title && jobUrl && !seen.has(jobUrl)) {
                    seen.add(jobUrl);
                    let desc = '';
                    if (salary) desc += `Salary: ${salary}. `;
                    if (location) desc += `Location: ${location}`;

                    cards.push({ title, company, location: location || 'Japan', jobUrl, desc: desc.trim() });
                }
            });

            return cards;
        }""")

        emit({"type": "extract", "count": len(jobs)})

        for job in jobs:
            if len(all_posts) >= max_posts:
                break
            _process_job_into_post(job, "Indeed", term, dedup, all_posts, emit)

        time.sleep(random.uniform(3, 5))

    return all_posts


# ─── Naukri Scraper (verified selectors 2026-04-24) ──────────────────────────
# Tested live: .srp-jobtuple-wrapper (20 cards), .title, .comp-name,
# .locWdth, .expwdth, .sal all confirmed working. No login needed.

def _first_scrapling_text(node, selector: str) -> str:
    """Return text from the first matching Scrapling element."""
    try:
        match = node.css(selector)
        if not match:
            return ""
        item = match[0]
        if hasattr(item, "get_all_text"):
            return item.get_all_text(strip=True)
        value = item.get()
        return value.clean() if hasattr(value, "clean") else str(value).strip()
    except Exception:
        return ""


def _first_scrapling_attr(node, selector: str, attr: str) -> str:
    """Return an attribute from the first matching Scrapling element."""
    try:
        match = node.css(selector)
        if not match:
            return ""
        return (match[0].attrib or {}).get(attr, "").strip()
    except Exception:
        return ""


def _extract_naukri_jobs_from_scrapling(page) -> list[dict]:
    """Extract normalized Naukri jobs from a Scrapling Response."""
    jobs = []
    seen = set()

    for card in page.css(".srp-jobtuple-wrapper"):
        title = _first_scrapling_text(card, "a.title")
        job_url = _first_scrapling_attr(card, "a.title", "href")
        if not title or not job_url or job_url in seen:
            continue

        seen.add(job_url)
        company = _first_scrapling_text(card, "a.comp-name")
        location = _first_scrapling_text(card, ".locWdth")
        experience = _first_scrapling_text(card, ".expwdth")
        salary = _first_scrapling_text(card, ".sal")

        skills = []
        for skill in card.css(".tag-li, .dot-gt .tag-li, .tags-gt span"):
            try:
                text = skill.get_all_text(strip=True)
            except Exception:
                text = ""
            if text and len(text) < 40 and text not in skills:
                skills.append(text)

        desc_parts = []
        if experience:
            desc_parts.append(f"Experience: {experience}.")
        if salary:
            desc_parts.append(f"Salary: {salary}.")
        if skills:
            desc_parts.append(f"Skills: {', '.join(skills)}")

        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "jobUrl": job_url,
            "desc": " ".join(desc_parts).strip(),
        })

    return jobs


def _scrape_naukri_with_scrapling(url: str) -> list[dict]:
    from scrapling.fetchers import StealthyFetcher

    response = StealthyFetcher.fetch(
        url,
        headless=False,
        wait=1000,
        timeout=45000,
        wait_selector=".srp-jobtuple-wrapper",
    )
    return _extract_naukri_jobs_from_scrapling(response)


def _scrape_naukri_with_playwright(page, url: str, emit) -> list[dict]:
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
    except Exception as e:
        emit({"type": "error", "message": f"Naukri navigation error: {str(e)[:200]}"})
        return []

    time.sleep(random.uniform(3, 5))

    # Dismiss any login popups or chatbot overlays
    for popup_sel in ['#login-layer button.crossIcon', 'button[class*="close"]', '.chatbot_closeBtn']:
        try:
            btn = page.query_selector(popup_sel)
            if btn:
                btn.click()
                time.sleep(0.5)
        except Exception:
            pass

    # Scroll to load all 20 cards
    for _ in range(4):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(random.uniform(1, 1.5))

    # Verified selectors from live testing (2026-04-24):
    # Container: .srp-jobtuple-wrapper (20 per page)
    # Title: a.title (class="title ") — also in h2
    # Company: a.comp-name (class=" comp-name " or " comp-name mw-25")
    # Location: span.locWdth
    # Experience: span.expwdth (e.g., "0-5 Yrs", "1-4 Yrs")
    # Salary: span.sal (e.g., "2-5 Lacs PA") — present on ~30% of cards
    # Skills: span.tag-li (e.g., "Python", "Machine Learning") — job tags
    return page.evaluate("""() => {
        const cards = [];
        document.querySelectorAll('.srp-jobtuple-wrapper').forEach(el => {
            const titleEl = el.querySelector('a.title');
            const companyEl = el.querySelector('a.comp-name');
            const locEl = el.querySelector('.locWdth');
            const expEl = el.querySelector('.expwdth');
            const salEl = el.querySelector('.sal');
            const title = titleEl ? titleEl.innerText.trim() : '';
            const jobUrl = titleEl ? titleEl.href : '';
            const company = companyEl ? companyEl.innerText.trim() : '';
            const location = locEl ? locEl.innerText.trim() : '';
            const experience = expEl ? expEl.innerText.trim() : '';
            const salary = salEl ? salEl.innerText.trim() : '';

            // Extract skill tags
            const skills = [];
            el.querySelectorAll('.tag-li, .dot-gt .tag-li, .tags-gt span').forEach(s => {
                const t = s.innerText.trim();
                if (t && t.length < 40) skills.push(t);
            });

            if (title && jobUrl) {
                let desc = '';
                if (experience) desc += `Experience: ${experience}. `;
                if (salary) desc += `Salary: ${salary}. `;
                if (skills.length) desc += `Skills: ${skills.join(', ')}`;

                cards.push({ title, company, location, jobUrl, desc: desc.trim() });
            }
        });
        const seen = new Set();
        return cards.filter(c => { if (seen.has(c.jobUrl)) return false; seen.add(c.jobUrl); return true; });
    }""")

def scrape_naukri(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Naukri.com job listings via Scrapling, with Playwright fallback."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = lambda e: on_event(e) if on_event else None

    search_terms = [
        "AI engineer", "machine learning engineer", "data scientist",
        "NLP engineer", "GenAI engineer", "LLM engineer",
        "deep learning engineer", "python AI developer",
        "agentic AI engineer", "healthcare AI",
    ]

    emit({"type": "info", "message": "Starting Naukri scraper with Scrapling..."})

    for si, term in enumerate(search_terms):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"Naukri: {term}", "index": si + 1, "total": len(search_terms)})

        kw = term.replace(" ", "-")
        url = f"https://www.naukri.com/{kw}-jobs?experience=1&experience=3&jobAge=7"
        try:
            jobs = _scrape_naukri_with_scrapling(url)
        except ModuleNotFoundError:
            emit({"type": "error", "message": "Scrapling is not installed. Install requirements and retrying with Playwright fallback."})
            jobs = _scrape_naukri_with_playwright(page, url, emit) if page else []
        except Exception as e:
            emit({"type": "error", "message": f"Naukri Scrapling error: {str(e)[:200]}. Retrying with Playwright fallback."})
            jobs = _scrape_naukri_with_playwright(page, url, emit) if page else []

        emit({"type": "extract", "count": len(jobs)})

        for job in jobs:
            if len(all_posts) >= max_posts:
                break
            _process_job_into_post(job, "Naukri", term, dedup, all_posts, emit)

        time.sleep(random.uniform(2, 4))

    return all_posts


# ─── Arc.dev Scraper ─────────────────────────────────────────────────────────

def scrape_arcdev(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Arc.dev remote job listings."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = lambda e: on_event(e) if on_event else None

    search_paths = [
        "machine-learning", "artificial-intelligence", "python",
        "data-science", "nlp", "deep-learning",
    ]

    emit({"type": "info", "message": "Starting Arc.dev scraper..."})

    for si, path in enumerate(search_paths):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"Arc.dev: {path}", "index": si + 1, "total": len(search_paths)})

        url = f"https://arc.dev/remote-jobs/{path}"
        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
        except Exception as e:
            emit({"type": "error", "message": f"Arc.dev error: {str(e)[:200]}"})
            continue

        time.sleep(random.uniform(2, 4))

        for _ in range(3):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(1)

        jobs = page.evaluate("""() => {
            const cards = [];
            document.querySelectorAll('a[href*="/remote-jobs/"]').forEach(a => {
                const card = a.closest('[class*="card"], [class*="job"], li, article') || a.parentElement;
                if (!card) return;
                const title = card.querySelector('h2, h3, [class*="title"]');
                const company = card.querySelector('[class*="company"], [class*="org"]');
                const loc = card.querySelector('[class*="location"], [class*="loc"]');
                const jobUrl = a.href;
                if (title && jobUrl.includes('/remote-jobs/')) {
                    cards.push({
                        title: title.innerText.trim(),
                        company: company ? company.innerText.trim() : '',
                        location: loc ? loc.innerText.trim() : 'Remote',
                        jobUrl,
                        desc: ''
                    });
                }
            });
            const seen = new Set();
            return cards.filter(c => { if (seen.has(c.jobUrl)) return false; seen.add(c.jobUrl); return true; });
        }""")

        emit({"type": "extract", "count": len(jobs)})

        for job in jobs:
            if len(all_posts) >= max_posts:
                break
            _process_job_into_post(job, "Arc.dev", path, dedup, all_posts, emit)

        time.sleep(random.uniform(2, 3))

    return all_posts


# ─── WeWorkRemotely Scraper ──────────────────────────────────────────────────

def scrape_weworkremotely(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape WeWorkRemotely job listings."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = lambda e: on_event(e) if on_event else None

    categories = [
        "programming", "design", "devops-sysadmin",
    ]

    emit({"type": "info", "message": "Starting WeWorkRemotely scraper..."})

    for si, cat in enumerate(categories):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"WWR: {cat}", "index": si + 1, "total": len(categories)})

        url = f"https://weworkremotely.com/categories/remote-{cat}-jobs"
        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
        except Exception as e:
            emit({"type": "error", "message": f"WWR error: {str(e)[:200]}"})
            continue

        time.sleep(random.uniform(2, 3))

        jobs = page.evaluate("""() => {
            const cards = [];
            document.querySelectorAll('li.feature, section.jobs li').forEach(el => {
                const link = el.querySelector('a[href*="/remote-jobs/"]');
                const titleEl = el.querySelector('.title, h3');
                const companyEl = el.querySelector('.company, span.company');
                const locEl = el.querySelector('.region, .location');
                if (link && titleEl) {
                    cards.push({
                        title: titleEl.innerText.trim(),
                        company: companyEl ? companyEl.innerText.trim() : '',
                        location: locEl ? locEl.innerText.trim() : 'Remote',
                        jobUrl: link.href.startsWith('http') ? link.href : 'https://weworkremotely.com' + link.getAttribute('href'),
                        desc: ''
                    });
                }
            });
            const seen = new Set();
            return cards.filter(c => { if (seen.has(c.jobUrl)) return false; seen.add(c.jobUrl); return true; });
        }""")

        emit({"type": "extract", "count": len(jobs)})

        for job in jobs:
            if len(all_posts) >= max_posts:
                break
            _process_job_into_post(job, "WeWorkRemotely", cat, dedup, all_posts, emit)

        time.sleep(random.uniform(2, 3))

    return all_posts


# ─── JapanDev Scraper ────────────────────────────────────────────────────────

def scrape_japandev(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape JapanDev for remote tech jobs in Japan."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = lambda e: on_event(e) if on_event else None

    emit({"type": "info", "message": "Starting JapanDev scraper..."})
    emit({"type": "search", "query": "JapanDev remote jobs", "index": 1, "total": 1})

    url = "https://japan-dev.com/remote-jobs-in-japan"
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
    except Exception as e:
        emit({"type": "error", "message": f"JapanDev error: {str(e)[:200]}"})
        return all_posts

    time.sleep(random.uniform(2, 4))

    for _ in range(5):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(1)

    jobs = page.evaluate("""() => {
        const cards = [];
        document.querySelectorAll('a[href*="/companies/"]').forEach(a => {
            const card = a.closest('[class*="job"], [class*="card"], li, article, div') || a.parentElement;
            if (!card) return;
            const title = card.querySelector('h2, h3, [class*="title"], [class*="position"]');
            const company = card.querySelector('[class*="company"], [class*="org"]');
            const loc = card.querySelector('[class*="location"], [class*="tag"]');
            if (title) {
                cards.push({
                    title: title.innerText.trim(),
                    company: company ? company.innerText.trim() : '',
                    location: loc ? loc.innerText.trim() : 'Japan (Remote)',
                    jobUrl: a.href,
                    desc: ''
                });
            }
        });
        const seen = new Set();
        return cards.filter(c => { if (seen.has(c.jobUrl)) return false; seen.add(c.jobUrl); return true; });
    }""")

    emit({"type": "extract", "count": len(jobs)})

    for job in jobs:
        if len(all_posts) >= max_posts:
            break
        _process_job_into_post(job, "JapanDev", "japan-remote", dedup, all_posts, emit)

    return all_posts


# ─── EU Remote Jobs Scraper ──────────────────────────────────────────────────

def scrape_euremotejobs(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape EU Remote Jobs for European remote positions."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = lambda e: on_event(e) if on_event else None

    emit({"type": "info", "message": "Starting EU Remote Jobs scraper..."})
    emit({"type": "search", "query": "EU Remote Jobs", "index": 1, "total": 1})

    url = "https://euremotejobs.com/engineering/"
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
    except Exception as e:
        emit({"type": "error", "message": f"EU Remote Jobs error: {str(e)[:200]}"})
        return all_posts

    time.sleep(random.uniform(2, 4))

    for _ in range(4):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(1)

    jobs = page.evaluate("""() => {
        const cards = [];
        document.querySelectorAll('article, .job-listing, [class*="job"], li[class*="post"]').forEach(el => {
            const link = el.querySelector('a[href]');
            const title = el.querySelector('h2, h3, .entry-title, [class*="title"]');
            const company = el.querySelector('[class*="company"], [class*="org"], .meta');
            if (link && title) {
                cards.push({
                    title: title.innerText.trim(),
                    company: company ? company.innerText.trim().split('\\n')[0] : '',
                    location: 'Europe (Remote)',
                    jobUrl: link.href,
                    desc: ''
                });
            }
        });
        const seen = new Set();
        return cards.filter(c => { if (seen.has(c.jobUrl)) return false; seen.add(c.jobUrl); return true; });
    }""")

    emit({"type": "extract", "count": len(jobs)})

    for job in jobs:
        if len(all_posts) >= max_posts:
            break
        _process_job_into_post(job, "EURemoteJobs", "europe-remote", dedup, all_posts, emit)

    return all_posts


# ─── Bayt.com Scraper (UAE/Middle East) ──────────────────────────────────────

def scrape_bayt(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape Bayt.com for UAE/Middle East tech jobs."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = lambda e: on_event(e) if on_event else None

    search_terms = [
        "AI engineer", "machine learning", "data scientist",
        "python developer", "software engineer AI",
    ]

    emit({"type": "info", "message": "Starting Bayt scraper..."})

    for si, term in enumerate(search_terms):
        if len(all_posts) >= max_posts:
            break

        emit({"type": "search", "query": f"Bayt: {term}", "index": si + 1, "total": len(search_terms)})

        url = f"https://www.bayt.com/en/uae/jobs/?keyword={quote_plus(term)}&filters%5Bjb_remote%5D%5B%5D=1"
        try:
            page.goto(url, timeout=30000, wait_until="networkidle")
        except Exception as e:
            emit({"type": "error", "message": f"Bayt error: {str(e)[:200]}"})
            continue

        time.sleep(random.uniform(3, 5))

        for _ in range(3):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(1)

        jobs = page.evaluate("""() => {
            const cards = [];
            document.querySelectorAll('[data-js-job], .has-overlay-on-hover, li[class*="job"]').forEach(el => {
                const titleEl = el.querySelector('h2 a, .jb-title a, [class*="title"] a');
                const companyEl = el.querySelector('[class*="company"], .jb-company');
                const locEl = el.querySelector('[class*="location"], .jb-loc');
                if (titleEl) {
                    cards.push({
                        title: titleEl.innerText.trim(),
                        company: companyEl ? companyEl.innerText.trim() : '',
                        location: locEl ? locEl.innerText.trim() : 'UAE',
                        jobUrl: titleEl.href.startsWith('http') ? titleEl.href : 'https://www.bayt.com' + titleEl.getAttribute('href'),
                        desc: ''
                    });
                }
            });
            const seen = new Set();
            return cards.filter(c => { if (seen.has(c.jobUrl)) return false; seen.add(c.jobUrl); return true; });
        }""")

        emit({"type": "extract", "count": len(jobs)})

        for job in jobs:
            if len(all_posts) >= max_posts:
                break
            _process_job_into_post(job, "Bayt", term, dedup, all_posts, emit)

        time.sleep(random.uniform(2, 4))

    return all_posts


# ─── RemoteAI Scraper ────────────────────────────────────────────────────────

def scrape_remoteai(page, conn, max_posts: int = 100, on_event=None) -> list[dict]:
    """Scrape RemoteAI.io for remote AI/ML jobs."""
    all_posts = []
    dedup = DedupCache(conn)
    emit = lambda e: on_event(e) if on_event else None

    emit({"type": "info", "message": "Starting RemoteAI scraper..."})
    emit({"type": "search", "query": "RemoteAI all listings", "index": 1, "total": 1})

    url = "https://remoteai.io/"
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
    except Exception as e:
        emit({"type": "error", "message": f"RemoteAI error: {str(e)[:200]}"})
        return all_posts

    time.sleep(random.uniform(2, 4))

    for _ in range(5):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(1)

    jobs = page.evaluate("""() => {
        const cards = [];
        document.querySelectorAll('a[href*="/jobs/"]').forEach(a => {
            const card = a.closest('[class*="card"], [class*="job"], li, article, tr') || a.parentElement;
            if (!card) return;
            const title = card.querySelector('h2, h3, [class*="title"], td:first-child');
            const company = card.querySelector('[class*="company"], [class*="org"], td:nth-child(2)');
            const loc = card.querySelector('[class*="location"], [class*="tag"], td:nth-child(3)');
            if (title) {
                cards.push({
                    title: title.innerText.trim(),
                    company: company ? company.innerText.trim() : '',
                    location: loc ? loc.innerText.trim() : 'Remote',
                    jobUrl: a.href.startsWith('http') ? a.href : 'https://remoteai.io' + a.getAttribute('href'),
                    desc: ''
                });
            }
        });
        const seen = new Set();
        return cards.filter(c => { if (seen.has(c.jobUrl)) return false; seen.add(c.jobUrl); return true; });
    }""")

    emit({"type": "extract", "count": len(jobs)})

    for job in jobs:
        if len(all_posts) >= max_posts:
            break
        _process_job_into_post(job, "RemoteAI", "ai-remote", dedup, all_posts, emit)

    return all_posts


# ─── Multi-source orchestrator ───────────────────────────────────────────────

def scrape_all_sources(page, conn, max_posts: int = 500, on_event=None,
                       sources: list[str] = None) -> list[dict]:
    """Run multiple scrapers and combine results.

    Args:
        sources: list of source names to scrape. Default: all.
                 Options: "google", "wellfound", "yc"
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    if sources is None:
        sources = ["google", "wellfound", "yc"]

    all_posts = []
    # Distribute budget across sources
    per_source = max(50, max_posts // len(sources))

    for source in sources:
        remaining = max_posts - len(all_posts)
        if remaining <= 0:
            break

        budget = min(per_source, remaining)
        emit({"type": "info", "message": f"Starting {source} scraper (budget: {budget})"})

        try:
            if source == "google":
                posts = scrape_google(page, conn, max_posts=budget, on_event=on_event)
            elif source == "wellfound":
                posts = scrape_wellfound(page, conn, max_posts=budget, on_event=on_event)
            elif source == "yc":
                posts = scrape_yc_jobs(page, conn, max_posts=budget, on_event=on_event)
            else:
                emit({"type": "error", "message": f"Unknown source: {source}"})
                continue

            all_posts.extend(posts)
            emit({"type": "info", "message": f"{source} done: {len(posts)} posts found"})

        except Exception as e:
            emit({"type": "error", "message": f"{source} scraper failed: {str(e)[:200]}"})

    return all_posts


# ─── Career Link Follower ────────────────────────────────────────────────────

_CAREER_PATTERNS = re.compile(
    r'(career|jobs|hiring|apply|talent|recruit|openings|positions|work-with-us|join-us)',
    re.IGNORECASE,
)


def follow_career_links(page, conn, max_visits: int = 50, on_event=None) -> int:
    """Follow external links from DB posts to extract emails from career pages.

    Queries posts that have external links but no email, visits those links,
    and extracts emails from the career/jobs pages.

    Returns count of posts enriched with new emails.
    """
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass

    # Find posts with external links but no email
    rows = conn.execute(
        """SELECT id, author_name, links, post_url FROM posts
           WHERE links IS NOT NULL AND links != ''
             AND (email IS NULL OR email = '')
             AND is_hiring = 1
           ORDER BY
             CASE domain_relevance WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END,
             created_at DESC
           LIMIT ?""",
        (max_visits * 3,),  # fetch more since many links won't be career pages
    ).fetchall()

    if not rows:
        emit({"type": "info", "message": "No posts with career links to follow"})
        return 0

    emit({"type": "info", "message": f"Career link follower: checking {len(rows)} posts for career links"})

    enriched = 0
    visited = 0
    visited_domains = set()

    for row in rows:
        if visited >= max_visits:
            break

        post_id = row["id"]
        author = row["author_name"] or "Unknown"
        links = (row["links"] or "").split(", ")

        # Filter to career-like links
        career_links = [l for l in links if l.startswith("http") and _CAREER_PATTERNS.search(l)]

        # Also include links from known job board domains
        for l in links:
            if any(d in l for d in ["lever.co", "greenhouse.io", "workable.com", "ashbyhq.com",
                                     "bamboohr.com", "smartrecruiters.com", "breezy.hr"]):
                career_links.append(l)

        if not career_links:
            continue

        for link in career_links[:2]:  # max 2 links per post
            if visited >= max_visits:
                break

            # Skip if we already visited this domain
            try:
                from urllib.parse import urlparse
                domain = urlparse(link).netloc
                if domain in visited_domains:
                    continue
                visited_domains.add(domain)
            except Exception:
                pass

            visited += 1
            emit({"type": "search", "query": f"Career: {link[:50]}",
                  "index": visited, "total": max_visits})

            try:
                page.goto(link, timeout=15000, wait_until="domcontentloaded")
                time.sleep(random.uniform(2, 4))

                # Extract emails from the career page
                page_text = page.evaluate("() => document.body ? document.body.innerText : ''") or ""

                if len(page_text) < 50:
                    emit({"type": "skip", "author": author[:20], "reason": "Page too short"})
                    continue

                # Find emails via regex
                found_emails = extract_emails(page_text)

                # Also check mailto links
                mailto_emails = page.evaluate("""
                () => {
                    const emails = [];
                    document.querySelectorAll('a[href^="mailto:"]').forEach(a => {
                        const e = a.href.replace('mailto:', '').split('?')[0].trim();
                        if (e && e.includes('@')) emails.push(e);
                    });
                    return [...new Set(emails)].join(', ');
                }
                """) or ""

                all_emails = ", ".join(filter(None, [found_emails, mailto_emails]))

                if all_emails:
                    conn.execute(
                        "UPDATE posts SET email = ?, updated_at = datetime('now') WHERE id = ?",
                        (all_emails, post_id),
                    )
                    conn.commit()
                    enriched += 1
                    emit({"type": "found", "sno": enriched, "author": author[:25],
                          "role": "career-link", "company": domain[:20],
                          "email": all_emails[:30], "domain": "career"})
                else:
                    emit({"type": "skip", "author": author[:20],
                          "reason": f"No email on {domain[:25]}"})

            except Exception as e:
                emit({"type": "error", "message": f"Career page failed ({link[:40]}): {str(e)[:80]}"})

            time.sleep(random.uniform(1, 3))

    emit({"type": "done", "total": enriched,
          "queries_searched": visited,
          "message": f"Career links done: {enriched} posts enriched from {visited} pages visited"})
    return enriched
