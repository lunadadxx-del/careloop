#!/usr/bin/env bash
# CareLoop one-command demo launcher (for recording the demo video).
# Usage: ./demo.sh [grace_minutes]   (default 30; pass 1 for the escalation shot)
set -e
GRACE="${1:-30}"
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Backend (grace ${GRACE} min)..."
if [ ! -d "$ROOT/backend/.venv" ]; then
  python3 -m venv "$ROOT/backend/.venv"
fi
"$ROOT/backend/.venv/bin/pip" install -q -r "$ROOT/backend/requirements.txt"
export CARELOOP_GRACE_MINUTES="$GRACE"
(cd "$ROOT/backend" && "$ROOT/backend/.venv/bin/uvicorn" app.main:app --port 8000) &
BACK_PID=$!

echo "==> Frontend..."
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm install)
fi
(cd "$ROOT/frontend" && npm run dev) &
FRONT_PID=$!

trap "kill $BACK_PID $FRONT_PID 2>/dev/null" EXIT
echo ""
echo "CareLoop is up:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "Press Ctrl+C to stop both."
wait
