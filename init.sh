#!/usr/bin/env bash
# init.sh — Start both the Backend API and Web App for local development
#
# Usage:
#   ./init.sh          # Start both services
#   ./init.sh --build  # Build shared packages first, then start
#
# Services:
#   Backend API  → http://localhost:8000  (FastAPI + Socket.IO)
#   Web App      → http://localhost:3001  (Next.js)

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cleanup() {
  echo -e "\n${YELLOW}Shutting down services...${NC}"
  if [ -n "${BACKEND_PID:-}" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "${WEB_PID:-}" ]; then
    kill "$WEB_PID" 2>/dev/null || true
    wait "$WEB_PID" 2>/dev/null || true
  fi
  echo -e "${GREEN}All services stopped.${NC}"
}

trap cleanup EXIT INT TERM

# ── Build shared packages (optional) ──────────────────────────────

if [[ "${1:-}" == "--build" ]]; then
  echo -e "${BLUE}Building shared packages...${NC}"
  (cd "$ROOT_DIR/packages/types" && npm run build)
  (cd "$ROOT_DIR/packages/ui" && npm run build)
  echo -e "${GREEN}Shared packages built.${NC}\n"
fi

# ── Verify prerequisites ─────────────────────────────────────────

if [ ! -d "$ROOT_DIR/apps/backend/.venv" ]; then
  echo -e "${RED}Error: Python venv not found at apps/backend/.venv${NC}"
  echo "Run: cd apps/backend && uv venv && uv pip install -r requirements.txt"
  exit 1
fi

if [ ! -d "$ROOT_DIR/node_modules" ]; then
  echo -e "${RED}Error: node_modules not found. Run 'npm install' first.${NC}"
  exit 1
fi

# ── Start Backend API ─────────────────────────────────────────────

echo -e "${BLUE}Starting Backend API on http://localhost:8000 ...${NC}"
(
  cd "$ROOT_DIR/apps/backend"
  # Ensure NODE_ENV doesn't leak into the Python process
  unset NODE_ENV 2>/dev/null || true
  .venv/bin/uvicorn api.main:sio_asgi_app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir api
) &
BACKEND_PID=$!

# ── Start Web App ─────────────────────────────────────────────────

echo -e "${BLUE}Starting Web App on http://localhost:3001 ...${NC}"
(
  cd "$ROOT_DIR/apps/web"
  # Ensure NODE_ENV is not overridden (Next.js manages it)
  unset NODE_ENV 2>/dev/null || true
  npx next dev --port 3001
) &
WEB_PID=$!

# ── Wait for services ─────────────────────────────────────────────

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Auto Claude Web — Local Development${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "  Backend API:  ${BLUE}http://localhost:8000${NC}"
echo -e "  Web App:      ${BLUE}http://localhost:3001${NC}"
echo -e "  Health Check: ${BLUE}http://localhost:8000/api/health${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services"
echo ""

wait
