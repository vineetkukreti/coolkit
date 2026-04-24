#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  LinkedIn Job Parser — Run Everything
#
#  Usage:  ./run.sh              backend + frontend dev (parallel)
#          ./run.sh --prod       backend only (serves built frontend)
#          ./run.sh --back       backend only
#          ./run.sh --front      frontend dev only
# ══════════════════════════════════════════════════════════════

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

BACKEND_PORT=8000
FRONTEND_PORT=5173
VENV="$DIR/venv"
LOG_DIR="$DIR/data/logs"
MODE="${1:-dev}"

mkdir -p "$LOG_DIR"

# ─── Colors ──────────────────────────────────────
G='\033[0;32m' C='\033[0;36m' Y='\033[1;33m' R='\033[0;31m'
B='\033[1m' D='\033[2m' NC='\033[0m'

# ─── Kill anything on our ports ──────────────────
for port in $BACKEND_PORT $FRONTEND_PORT; do
    pids=$(lsof -ti:"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo -e "${Y}[!] Killing process on port $port${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null
    fi
done
sleep 1

# ─── Cleanup on Ctrl+C ──────────────────────────
cleanup() {
    echo ""
    echo -e "${Y}[*] Shutting down...${NC}"
    jobs -p | xargs kill 2>/dev/null
    sleep 1
    jobs -p | xargs kill -9 2>/dev/null
    for port in $BACKEND_PORT $FRONTEND_PORT; do
        lsof -ti:"$port" 2>/dev/null | xargs kill -9 2>/dev/null
    done
    echo -e "${G}[*] Done.${NC}"
    exit 0
}
trap cleanup INT TERM

# ─── Banner ──────────────────────────────────────
echo ""
echo -e "${C}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${C}║${NC}  ${B}LinkedIn Job Parser${NC}                            ${C}║${NC}"
echo -e "${C}║${NC}  ${D}Healthcare AI Job Auto-Applier${NC}                  ${C}║${NC}"
echo -e "${C}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Venv ────────────────────────────────────────
if [ ! -d "$VENV" ]; then
    echo -e "${Y}[*] Creating virtual environment...${NC}"
    python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
export PYTHONPATH="$DIR/backend"

# ─── Start backend ───────────────────────────────
start_backend() {
    echo -e "${G}[*] Starting backend on :$BACKEND_PORT${NC}"
    uvicorn backend.server:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        >> "$LOG_DIR/backend.log" 2>&1 &

    # Wait until it responds
    for i in $(seq 1 15); do
        if curl -sf http://localhost:$BACKEND_PORT/api/db/stats > /dev/null 2>&1; then
            echo -e "  ${G}Backend ready!${NC}"
            return 0
        fi
        sleep 1
    done
    echo -e "  ${R}Backend failed to start — check:${NC} tail -f $LOG_DIR/backend.log"
    return 1
}

# ─── Start frontend dev ─────────────────────────
start_frontend() {
    if [ ! -d "$DIR/frontend-src/node_modules" ]; then
        echo -e "${Y}[*] Installing frontend deps...${NC}"
        (cd "$DIR/frontend-src" && npm install --silent)
    fi

    echo -e "${G}[*] Starting frontend on :$FRONTEND_PORT${NC}"
    (cd "$DIR/frontend-src" && npx vite --port $FRONTEND_PORT --host) \
        >> "$LOG_DIR/frontend.log" 2>&1 &
}

# ─── Launch based on mode ────────────────────────
case "$MODE" in
    --prod)
        echo -e "${B}Mode:${NC} Production (backend + built frontend)"
        echo ""
        start_backend
        ;;
    --back)
        echo -e "${B}Mode:${NC} Backend only"
        echo ""
        start_backend
        ;;
    --front)
        echo -e "${B}Mode:${NC} Frontend only (needs backend on :$BACKEND_PORT)"
        echo ""
        start_frontend
        ;;
    dev|*)
        echo -e "${B}Mode:${NC} Development (backend + frontend in parallel)"
        echo ""
        start_backend
        start_frontend
        ;;
esac

# ─── Print status ───────────────────────────────
sleep 1
echo ""
echo -e "${C}══════════════════════════════════════════════════${NC}"
if [ "$MODE" != "--front" ]; then
    echo -e "  ${B}API:${NC}       http://localhost:$BACKEND_PORT/api/db/stats"
fi
if [ "$MODE" = "dev" ] || [ "$MODE" = "--front" ]; then
    echo -e "  ${B}Frontend:${NC}  http://localhost:$FRONTEND_PORT"
fi
if [ "$MODE" = "--prod" ]; then
    echo -e "  ${B}App:${NC}       http://localhost:$BACKEND_PORT"
fi
echo -e "${C}──────────────────────────────────────────────────${NC}"
echo -e "  ${D}Logs:  tail -f $LOG_DIR/backend.log${NC}"
echo -e "  ${D}       tail -f $LOG_DIR/frontend.log${NC}"
echo -e "${C}══════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${D}Ctrl+C to stop${NC}"
echo ""

# ─── Keep alive ──────────────────────────────────
wait
