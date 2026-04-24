#!/usr/bin/env python3
"""Open browser to LinkedIn login — log in manually, session is saved."""

from pathlib import Path
from playwright.sync_api import sync_playwright

session_dir = Path(__file__).parent / "browser_session"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(session_dir),
        headless=False,
        slow_mo=50,
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = context.new_page()
    page.goto("https://www.linkedin.com/login")

    print("\n  Browser opened. Log in with your account.")
    print("  Waiting until you reach the LinkedIn feed (max 5 min)...")

    # Wait until redirected to feed — no fixed sleep
    page.wait_for_url("**/feed**", timeout=300_000)

    context.close()
    print("\n  Session saved! Run post_parser.py now.")
