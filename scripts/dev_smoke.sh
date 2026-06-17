#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
HOST="${API_HOST:-127.0.0.1}"
PORT="${API_PORT:-8000}"
LOG_FILE="${TMPDIR:-/tmp}/trading-project-dev-smoke.log"
UVICORN_BIN="${UVICORN_BIN:-uvicorn}"

cd "$ROOT_DIR"

cleanup() {
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID"
    wait "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

export APP_SEED_DEMO_DATA=true
export PYTHONPATH="${PYTHONPATH:-packages:.}"

"$UVICORN_BIN" apps.api.main:app --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
API_PID="$!"

ready=false
for _attempt in {1..30}; do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done

if [[ "$ready" != "true" ]]; then
  echo "Backend did not become healthy. Log:"
  cat "$LOG_FILE"
  exit 1
fi

check_non_empty_array() {
  local path="$1"
  local body
  body="$(curl -fsS "$BASE_URL$path")"
  if [[ "$body" == "[]" ]]; then
    echo "Expected non-empty response from $path"
    exit 1
  fi
  echo "OK $path"
}

curl -fsS "$BASE_URL/health" >/dev/null
echo "OK /health"
check_non_empty_array "/api/instruments"
check_non_empty_array "/api/research/runs"
check_non_empty_array "/api/continuous-series"

echo "dev smoke passed"
