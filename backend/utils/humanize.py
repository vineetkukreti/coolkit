"""Human-like behavior simulation — based on GodsScion & AmmarAR97 patterns."""

import random
import time
from playwright.sync_api import Page


# ── Delays ────────────────────────────────────────────────────────────────────

def random_sleep(min_s: float = 1.5, max_s: float = 3.5):
    """Beta-skewed sleep — biased toward shorter waits, occasional longer ones."""
    u = random.random()
    bias = u ** 1.4          # skews distribution toward minimum
    wait = min_s + bias * (max_s - min_s)
    time.sleep(wait)
    return wait


def short_pause():
    """0.6 – 1.0s (between small interactions within same page)."""
    time.sleep(random.uniform(0.6, 1.0))


def medium_pause():
    """1.8 – 3.0s (page loads, modal opens)."""
    time.sleep(random.uniform(1.8, 3.0))


def read_pause(text_length: int = 500):
    """Simulate reading time proportional to JD length (200 wpm)."""
    words = text_length / 5
    seconds = (words / 200) * 60 * random.uniform(0.5, 0.9)  # read fast-ish
    time.sleep(max(1.5, min(seconds, 12)))  # cap at 12s


def between_applications():
    """60 – 180s gap between applications — the #1 ban prevention measure."""
    delay = random.uniform(60, 180)
    print(f"  [humanize] Cooling down {delay:.0f}s before next application...")
    time.sleep(delay)


def page_load_pause():
    """2.5 – 5.0s after any full navigation (AmmarAR97 pattern)."""
    time.sleep(random.uniform(2.5, 5.0))


# ── Typing ────────────────────────────────────────────────────────────────────

def human_type(page: Page, selector: str, text: str):
    """Type using Playwright's per-char delay — mirrors AmmarAR97's approach."""
    try:
        locator = page.locator(selector).first
        locator.wait_for(state="visible", timeout=5000)
        locator.click()
        random_sleep(0.05, 0.2)
        delay_ms = random.randint(60, 180)   # ms per character
        locator.type(text, delay=delay_ms)
        short_pause()
    except Exception:
        pass


# ── Clicking ──────────────────────────────────────────────────────────────────

def human_click(page: Page, selector: str, timeout: int = 10000) -> bool:
    """Wait for element, then click — mirrors AmmarAR97 human_click."""
    try:
        random_sleep(0.5, 1.0)
        locator = page.locator(selector).first
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()
        random_sleep()
        return True
    except Exception:
        return False


# ── Scrolling ─────────────────────────────────────────────────────────────────

def human_scroll(page: Page, direction: str = "down", steps: int = 3):
    """Scroll in random increments."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        for _ in range(steps):
            amount = random.randint(250, 500) * (1 if direction == "down" else -1)
            page.mouse.wheel(0, amount)
            time.sleep(random.uniform(0.3, 0.8))
    except Exception:
        pass


# ── Daily cap ─────────────────────────────────────────────────────────────────

class DailyCap:
    """Hard stop at 12 Easy Apply/day — LinkedIn's safe zone is < 15."""

    SAFE_LIMIT = 25

    def __init__(self):
        self._count = 0

    def check(self) -> bool:
        if self._count >= self.SAFE_LIMIT:
            print(f"  [DailyCap] Reached {self.SAFE_LIMIT} applications. Stopping for today.")
            return False
        return True

    def increment(self):
        self._count += 1
        print(f"  [DailyCap] {self._count}/{self.SAFE_LIMIT} applied today")

    @property
    def count(self):
        return self._count
