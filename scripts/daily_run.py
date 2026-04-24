#!/usr/bin/env python3
"""
Daily Job Application Cycle
----------------------------
Entry point for cron-based scheduling.

Cron setup (run at 8 AM on weekdays):
    0 8 * * 1-5 cd /home/vineet/Desktop/projects/linkedin-job-parser && ./venv/bin/python scripts/daily_run.py >> data/logs/daily.log 2>&1

Or run manually:
    python scripts/daily_run.py [--max 500] [--no-scrape]
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Daily job application cycle")
    parser.add_argument("--max", type=int, default=500, help="Max applications (default: 500)")
    parser.add_argument("--no-scrape", action="store_true", help="Skip scraping, just apply to existing jobs")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Daily Job Application Cycle — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {args.max} applications")
    print(f"Scraping: {'disabled' if args.no_scrape else 'enabled'}")
    print(f"{'='*60}\n")

    # Ensure log directory exists
    (PROJECT_ROOT / "data" / "logs").mkdir(parents=True, exist_ok=True)

    from services.orchestrator import run_daily_cycle
    run_daily_cycle(
        max_applications=args.max,
        run_scrapers=not args.no_scrape,
    )

    print(f"\nDaily cycle completed at {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
