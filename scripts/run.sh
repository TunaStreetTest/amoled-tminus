#!/usr/bin/env bash
# T-MINUS backend on :8092 — Launch Library 2, no API keys.
# LAN contract the panel speaks: http://192.168.1.121:8092
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${TMINUS_PORT:-8092}"
VENV="${TMINUS_VENV:-/home/tunas/tuna-starlink-app/backend/.venv}"

if [[ ! -x "$VENV/bin/uvicorn" ]]; then
  echo "missing $VENV — set TMINUS_VENV to a venv with fastapi/uvicorn/httpx" >&2
  exit 1
fi

export TMINUS_ROOT="$ROOT"
cd "$ROOT/backend"
exec "$VENV/bin/uvicorn" server:app --host 0.0.0.0 --port "$PORT" --log-level info
