#!/usr/bin/env bash
# generate-traffic.sh — Send HTTP requests to the app to produce observable logs
# Usage: ./generate-traffic.sh [APP_URL]
# Default URL: http://localhost:8080

set -euo pipefail

APP_URL="${1:-http://localhost:8080}"

echo "==> Generating traffic against ${APP_URL}"
echo ""

# Helper: print what we're doing
req() {
  local label="$1"; shift
  echo -n "  [${label}] "
  curl -s -o /dev/null -w "%{http_code}" "$@"
  echo ""
}

# --- Nominal traffic ---
echo "--- Nominal traffic ---"
for i in $(seq 1 10); do
  req "GET /ok            " "${APP_URL}/ok"
  req "GET /health        " "${APP_URL}/health"
done

# --- Business traffic ---
echo ""
echo "--- Business traffic (orders & processing) ---"
for i in $(seq 1 5); do
  req "POST /order        " -X POST "${APP_URL}/order?product_id=PROD-00${i}&quantity=${i}"
  req "POST /process      " -X POST "${APP_URL}/process?items=${i}&delay_ms=20"
done
# Bad order (quantity out of range) — 400
req "POST /order (bad qty)" -X POST "${APP_URL}/order?product_id=PROD-999&quantity=200"
# Bad process — 400
req "POST /process (bad) " -X POST "${APP_URL}/process?items=0"

# --- Client errors (4xx) ---
echo ""
echo "--- Client errors (4xx) ---"
for i in $(seq 1 5); do
  req "GET /not-found     " "${APP_URL}/not-found"
done

# --- Server errors (5xx) ---
echo ""
echo "--- Server errors (5xx) ---"
for i in $(seq 1 3); do
  req "GET /error         " "${APP_URL}/error"
done

echo ""
echo "==> Done. Check Kibana at http://localhost:5601"
echo "    Index pattern: app-logs-*"
echo ""
echo "Tip: capture a specific request_id for traceability:"
echo "  curl -v ${APP_URL}/ok 2>&1 | grep -i request_id || true"
