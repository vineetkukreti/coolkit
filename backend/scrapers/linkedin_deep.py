"""LinkedIn deep extraction — profile emails, deep content extraction, backfill.

These functions require a Playwright page with an active LinkedIn session.
"""

# Re-export from post_parser (will be migrated here in a future pass)
from post_parser import (
    extract_profile_email,
    enrich_posts_with_profile_emails,
    deep_extract_post,
    backfill_deep_extract,
)

__all__ = [
    "extract_profile_email",
    "enrich_posts_with_profile_emails",
    "deep_extract_post",
    "backfill_deep_extract",
]
