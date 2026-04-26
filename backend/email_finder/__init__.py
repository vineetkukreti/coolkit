"""Unified email discovery — merges cron.py + enrich.py via shared strategies.py.

This package provides a single interface for finding emails via:
- Hunter.io API (free tier, 25/month)
- Website scraping (contact, about, careers pages)
- DuckDuckGo search (via duckduckgo-search package)
- Google search fallback
- Person-name email patterns (firstname@, first.last@, etc.)
- Generic email patterns (info@, hr@, careers@)
- Domain inference from company name
- MX record + SMTP RCPT TO verification

Usage:
    from email_finder import find_emails, enrich_leads

    # Quick find (verifies pattern guesses only) — used by leads endpoints
    emails = find_emails(company="Acme Corp", website="https://acme.com")

    # Full find with SMTP verify on ALL emails — used by cron job
    emails = find_emails(company="Acme Corp", website="https://acme.com", verify_smtp=True)

    # With person name for better results
    emails = find_emails(company="Acme Corp", website="https://acme.com", author_name="John Doe")

    # Bulk enrichment
    enriched = enrich_leads(conn, max_leads=50, on_progress=callback)
"""

# Lazy imports to avoid circular import warnings when running `python -m email_finder.cron`


def _lazy_cron():
    from email_finder.cron import find_verified_emails, verify_email_full, verify_existing, run_cron
    return find_verified_emails, verify_email_full, verify_existing, run_cron


def _lazy_enrich():
    from email_finder.enrich import find_emails_for_company, enrich_leads
    return find_emails_for_company, enrich_leads


def _lazy_strategies():
    from email_finder.strategies import verify_mx, score_email, verify_email_full
    return verify_mx, score_email, verify_email_full


def find_verified_emails(*a, **kw):
    return _lazy_cron()[0](*a, **kw)

def verify_email_full(*a, **kw):
    return _lazy_strategies()[2](*a, **kw)

def verify_mx(*a, **kw):
    return _lazy_strategies()[0](*a, **kw)

def score_email_full(*a, **kw):
    return _lazy_strategies()[1](*a, **kw)

def run_cron(*a, **kw):
    return _lazy_cron()[3](*a, **kw)

def find_emails_for_company(*a, **kw):
    return _lazy_enrich()[0](*a, **kw)

def enrich_leads(*a, **kw):
    return _lazy_enrich()[1](*a, **kw)


def find_emails(
    company: str,
    website: str = "",
    location: str = "",
    linkedin_url: str = "",
    author_name: str = "",
    verify_smtp: bool = False,
) -> list[dict]:
    """Unified email finder interface.

    Args:
        company: Company name
        website: Company website URL
        location: Company location
        linkedin_url: LinkedIn company page URL
        author_name: Contact person name (for person-specific email patterns)
        verify_smtp: If True, run full SMTP verification on all emails (slower, more accurate)

    Returns:
        List of dicts with keys: email, score, source, verified
    """
    if verify_smtp:
        return find_verified_emails(
            company=company,
            website=website,
            location=location,
            linkedin_url=linkedin_url,
            author_name=author_name,
        )
    else:
        return find_emails_for_company(
            company_name=company,
            website=website,
            location=location,
            author_name=author_name,
        )


__all__ = [
    "find_emails",
    "find_verified_emails",
    "find_emails_for_company",
    "enrich_leads",
    "verify_email_full",
    "verify_mx",
    "score_email_full",
    "run_cron",
]
