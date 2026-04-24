"""Unified email discovery — merges email_finder_cron.py + enrich_emails.py.

This package provides a single interface for finding emails via:
- Website scraping (contact, about, careers pages)
- DuckDuckGo search
- LinkedIn company pages
- Pattern generation + SMTP verification
- MX record validation

Usage:
    from email_finder import find_emails, enrich_leads

    # Quick find (no SMTP verify) — used by leads endpoints
    emails = find_emails(company="Acme Corp", website="https://acme.com")

    # Full find with SMTP verify — used by cron job
    emails = find_emails(company="Acme Corp", website="https://acme.com", verify_smtp=True)

    # Bulk enrichment
    enriched = enrich_leads(conn, max_leads=50, on_progress=callback)
"""

# Lazy imports to avoid circular import warnings when running `python -m email_finder.cron`


def _lazy_cron():
    from email_finder.cron import find_verified_emails, verify_email_full, verify_mx, score_email, run_cron
    return find_verified_emails, verify_email_full, verify_mx, score_email, run_cron


def _lazy_enrich():
    from email_finder.enrich import find_emails_for_company, enrich_leads
    return find_emails_for_company, enrich_leads


def find_verified_emails(*a, **kw):
    return _lazy_cron()[0](*a, **kw)

def verify_email_full(*a, **kw):
    return _lazy_cron()[1](*a, **kw)

def verify_mx(*a, **kw):
    return _lazy_cron()[2](*a, **kw)

def score_email_full(*a, **kw):
    return _lazy_cron()[3](*a, **kw)

def run_cron(*a, **kw):
    return _lazy_cron()[4](*a, **kw)

def find_emails_for_company(*a, **kw):
    return _lazy_enrich()[0](*a, **kw)

def enrich_leads(*a, **kw):
    return _lazy_enrich()[1](*a, **kw)


def find_emails(company: str, website: str = "", location: str = "",
                linkedin_url: str = "", verify_smtp: bool = False) -> list[dict]:
    """Unified email finder interface.

    Args:
        company: Company name
        website: Company website URL
        location: Company location
        linkedin_url: LinkedIn company page URL
        verify_smtp: If True, run full SMTP verification (slower, more accurate)

    Returns:
        List of dicts with keys: email, score, source
    """
    if verify_smtp:
        return find_verified_emails(
            company_name=company,
            website=website,
            location=location,
            linkedin_url=linkedin_url,
        )
    else:
        return find_emails_for_company(
            company_name=company,
            website=website,
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
