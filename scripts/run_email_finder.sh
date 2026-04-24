#!/bin/bash
# Email Finder Cron Script
# Runs every 2 hours to find verified emails for posts & leads without them
# Logs to data/logs/email_finder.log

# Navigate to project root (one level up from scripts/)
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"

source "$DIR/venv/bin/activate"
export PYTHONPATH="$DIR/backend"

# Run the email finder (20 items per run, both posts and leads)
python3 -m email_finder.cron --max 20 --target both

# Every 6th run (roughly once per 12 hours), verify existing emails
HOUR=$(date +%H)
if [ "$HOUR" = "03" ] || [ "$HOUR" = "15" ]; then
    python3 -m email_finder.cron --verify-only --max 50
fi
