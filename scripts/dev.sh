#!/usr/bin/env bash
# Chạy backend + frontend song song cho môi trường dev (Ctrl+C dừng cả hai).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -q -r requirements.txt
cd "$ROOT/frontend"
npm install --silent
cd "$ROOT"
trap 'kill 0' EXIT
# Uvicorn reload cổng 8000.
( cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 ) &
# Vite dev server cổng 5173 (proxy /api → 8000).
( cd frontend && npm run dev ) &
wait
