#!/usr/bin/env bash
set -euo pipefail

PORT=8778
BASE="http://localhost:$PORT"
PASS=0
FAIL=0

check() {
  local desc="$1" expected="$2"
  shift 2
  local actual
  actual=$(curl -s -o /dev/null -w "%{http_code}" "$@")
  if [ "$actual" = "$expected" ]; then
    echo "  PASS [$actual] $desc"
    ((PASS++))
  else
    echo "  FAIL [$actual != $expected] $desc"
    ((FAIL++))
  fi
}

check_body() {
  local desc="$1" pattern="$2"
  shift 2
  local body
  body=$(curl -fsS "$@" 2>/dev/null || true)
  if echo "$body" | grep -qi "$pattern"; then
    echo "  PASS [body~=$pattern] $desc"
    ((PASS++))
  else
    echo "  FAIL [pattern '$pattern' not found] $desc"
    echo "    body: ${body:0:200}"
    ((FAIL++))
  fi
}

export OPENROUTER_API_KEY=dummy RR_BASE_URL=http://localhost RR_API_TOKEN=dummy

echo "Starting server on port $PORT..."
uv run uvicorn cv_tailor.main:app --port "$PORT" --log-level warning &
SERVER_PID=$!
sleep 5

echo ""
echo "Running smoke tests..."

check "GET /healthz → 200"          200  "$BASE/healthz"
check "GET / → 200"                 200  "$BASE/"
check "GET /history → 200"         200  "$BASE/history"
check "GET /resumes → 200"         200  "$BASE/resumes"
check "GET /pdf/999 → 404"         404  "$BASE/pdf/999"
check "GET /version/999 → 404"     404  "$BASE/version/999"
check "GET /diff/1/999 → 404"      404  "$BASE/diff/1/999"
check "POST /generate (no RR) → 502" 502 -X POST "$BASE/generate" \
  -d "job_description=Engineer&base_resume_id=test"
check_body "GET / has textarea"     "textarea"  "$BASE/"
check_body "GET /history has nav"   "History"   "$BASE/history"
check_body "GET /healthz has ok"    "ok"        "$BASE/healthz"

echo ""
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

echo "Results: $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
echo "ALL SMOKE TESTS PASSED"
