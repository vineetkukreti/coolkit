"""Browser service — all Playwright browser management runs here."""

import os
import queue as _queue
import random
import time
import threading
from pathlib import Path


# ───────────────────────────────────────────────
# Browser thread infrastructure
# ───────────────────────────────────────────────
# Playwright requires ALL operations on the same thread that created the context.
# FastAPI runs sync endpoints in a threadpool, causing "Cannot switch to a different thread".
# Fix: a dedicated browser thread with a command queue.

_browser_cmd_q = _queue.Queue()   # (command, args, result_queue)
_browser_thread = None


def _get_browser_locale() -> str:
    try:
        from config import REGIONS, ACTIVE_REGIONS
        return REGIONS.get(ACTIVE_REGIONS[0], {}).get("locale", "en-US")
    except Exception:
        return "en-US"


def _get_browser_timezone() -> str:
    try:
        from config import REGIONS, ACTIVE_REGIONS
        return REGIONS.get(ACTIVE_REGIONS[0], {}).get("timezone", "Asia/Kolkata")
    except Exception:
        return "Asia/Kolkata"


def _get_browser_geolocation() -> dict:
    try:
        from config import REGIONS, ACTIVE_REGIONS
        return REGIONS.get(ACTIVE_REGIONS[0], {}).get("geolocation", {"latitude": 12.97, "longitude": 77.59})
    except Exception:
        return {"latitude": 12.97, "longitude": 77.59}


def _browser_worker():
    """Dedicated thread that owns all Playwright objects."""
    while True:
        cmd, args, result_q = _browser_cmd_q.get()
        if cmd == "__stop_thread__":
            result_q.put(None)
            break
        try:
            rv = cmd(*args)
            result_q.put(("ok", rv))
        except Exception as e:
            result_q.put(("error", e))


def _run_on_browser_thread(fn, *args, timeout=60):
    """Execute fn on the browser thread and return the result."""
    global _browser_thread
    if _browser_thread is None or not _browser_thread.is_alive():
        _browser_thread = threading.Thread(target=_browser_worker, daemon=True)
        _browser_thread.start()
    rq = _queue.Queue()
    _browser_cmd_q.put((fn, args, rq))
    status, result = rq.get(timeout=timeout)
    if status == "error":
        raise result
    return result


# ───────────────────────────────────────────────
# Browser state
# ───────────────────────────────────────────────

browser_state = {
    "pw": None,
    "browser": None,
    "page": None,
    "running": False,
    "logged_in": False,
    "status": "stopped",       # stopped | starting | ready | error
}


# ───────────────────────────────────────────────
# Playwright browser engine
# ───────────────────────────────────────────────

def _start_browser():
    """Launch Playwright browser with strong anti-detection measures.

    Uses a persistent profile so LinkedIn remembers the session between runs.
    All fingerprinting mitigations are applied to look like a real Chrome browser.
    """
    from playwright.sync_api import sync_playwright
    import glob as _glob
    profile_dir = str(Path("data/browser_profiles/main").resolve())
    os.makedirs(profile_dir, exist_ok=True)
    # Clean stale lock files from crashed sessions
    for lock in _glob.glob(os.path.join(profile_dir, "Singleton*")):
        try:
            os.remove(lock)
        except OSError:
            pass
    pw = sync_playwright().start()

    # Randomize viewport slightly each session (real users have varied screens)
    vp_width = random.choice([1280, 1366, 1440, 1536, 1600])
    vp_height = random.choice([800, 900, 960, 1024])

    context = pw.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,
        slow_mo=random.randint(600, 1200),  # slower — mimics human typing/clicking
        viewport={"width": vp_width, "height": vp_height},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        locale=_get_browser_locale(),
        timezone_id=_get_browser_timezone(),
        geolocation=_get_browser_geolocation(),
        permissions=["geolocation"],
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
        ],
        ignore_default_args=["--enable-automation"],
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.add_init_script("""
        // Hide webdriver flag
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

        // Fake realistic plugin list (Chrome on Linux)
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' },
                ];
                plugins.length = 3;
                return plugins;
            }
        });

        // Fake Chrome runtime
        window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){} };

        // Fix permissions API (Playwright leaves fingerprints here)
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) =>
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters);

        // Realistic screen properties
        Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });

        // Hide automation-related properties
        delete navigator.__proto__.webdriver;
    """)
    browser_state["pw"] = pw
    browser_state["browser"] = context
    browser_state["page"] = page
    browser_state["running"] = True
    browser_state["status"] = "ready"


def _stop_browser():
    try:
        ctx = browser_state["browser"]
        if ctx:
            ctx.close()
        if browser_state["pw"]:
            browser_state["pw"].stop()
    except Exception:
        pass
    browser_state["pw"] = None
    browser_state["browser"] = None
    browser_state["page"] = None
    browser_state["running"] = False
    browser_state["logged_in"] = False
    browser_state["status"] = "stopped"


# ───────────────────────────────────────────────
# Browser thread commands (run on dedicated thread)
# ───────────────────────────────────────────────

def _do_start_browser():
    """Runs on the browser thread."""
    _start_browser()
    page = browser_state["page"]
    if page:
        try:
            page.goto("https://www.linkedin.com/login", timeout=15000)
        except Exception:
            pass


def _do_open_login():
    """Runs on the browser thread."""
    page = browser_state["page"]
    if not page:
        raise RuntimeError("No page available")
    page.goto("https://www.linkedin.com/login", timeout=15000)


def _do_check_login():
    """Runs on the browser thread."""
    page = browser_state["page"]
    if not page:
        return False
    page.goto("https://www.linkedin.com/feed/", timeout=10000)
    time.sleep(2)
    is_logged = "/feed" in page.url or "/in/" in page.url
    browser_state["logged_in"] = is_logged
    return is_logged


def _do_stop_browser():
    """Runs on the browser thread."""
    _stop_browser()
