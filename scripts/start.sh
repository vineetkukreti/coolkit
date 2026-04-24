#!/bin/bash
# ──────────────────────────────────────────────
# Healthcare AI Job Applier — Start Script
# ──────────────────────────────────────────────

set -e

# Navigate to project root (one level up from scripts/)
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"

VENV="$DIR/venv"
PORT=8000

# Kill any existing process on the port
if lsof -ti:$PORT &>/dev/null; then
    echo "[*] Killing existing process on port $PORT..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    sleep 1
fi

echo "╔══════════════════════════════════════════╗"
echo "║  Healthcare AI Job Applier               ║"
echo "║  Indeed · Naukri · Wellfound              ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check venv
if [ ! -d "$VENV" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$VENV"
fi

# Activate
source "$VENV/bin/activate"

# Install deps
echo "[*] Checking dependencies..."
pip install -q requests beautifulsoup4 lxml fastapi uvicorn python-multipart rich playwright 2>/dev/null

# Start backend
echo ""
echo "[*] Starting server on http://localhost:$PORT"
echo "[*] Press Ctrl+C to stop"
echo ""

PYTHONPATH="$DIR/backend" uvicorn backend.server:app --host 0.0.0.0 --port "$PORT" &
BACKEND_PID=$!

# Wait for server to be ready
sleep 2

# Open browser
if command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:$PORT" 2>/dev/null &
elif command -v open &>/dev/null; then
    open "http://localhost:$PORT" &
fi

echo "[*] Backend running (PID: $BACKEND_PID)"
echo "[*] Open http://localhost:$PORT in your browser"
echo ""

# Wait for Ctrl+C
trap "echo ''; echo '[*] Shutting down...'; kill $BACKEND_PID 2>/dev/null; exit 0" INT TERM
wait $BACKEND_PID
