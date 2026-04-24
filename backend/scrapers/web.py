"""Web scrapers — DuckDuckGo, Wellfound, YC Jobs, career link follower."""

from scrapers.web_scrapers import (
    scrape_google,
    scrape_wellfound,
    scrape_yc_jobs,
    scrape_all_sources,
    follow_career_links,
)

__all__ = [
    "scrape_google",
    "scrape_wellfound",
    "scrape_yc_jobs",
    "scrape_all_sources",
    "follow_career_links",
]
