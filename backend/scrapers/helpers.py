"""Shared scraper helpers — eliminates copy-paste across all scrapers."""

import random
import time


def make_emit(on_event):
    """Create a safe emit wrapper. Replaces 7+ copy-pasted emit() closures."""
    def emit(event):
        if on_event:
            try:
                on_event(event)
            except Exception:
                pass
    return emit


def click_see_more(page, max_buttons=5):
    """Click 'see more' expansion buttons on LinkedIn pages."""
    try:
        btns = page.query_selector_all(
            "button[aria-label*='see more'], button[aria-label*='See more'], "
            "button.see-more-less-button, button[class*='see-more'], "
            "button[class*='show-more']"
        )
        for btn in btns[:max_buttons]:
            try:
                btn.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.3, 0.7))
                btn.click()
            except Exception:
                pass
        if btns:
            time.sleep(0.5)
    except Exception:
        pass


def scroll_human_like(page, scrolls=5, scroll_min=400, scroll_max=900,
                      pause_min=0.8, pause_max=2.0):
    """Variable human-like scrolling to trigger lazy loading."""
    for _ in range(scrolls):
        page.evaluate(f"window.scrollBy(0, {random.randint(scroll_min, scroll_max)})")
        time.sleep(random.uniform(pause_min, pause_max))
    # Scroll back to top so all posts are in DOM
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(random.uniform(0.5, 1.0))
