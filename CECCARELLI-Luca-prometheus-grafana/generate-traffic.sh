#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"

echo "[info] Base URL: ${BASE_URL}"

for _ in {1..60}; do
  curl -s -o /dev/null "${BASE_URL}/ok"
done

for _ in {1..25}; do
  curl -s -o /dev/null -w "%{http_code}\n" "${BASE_URL}/not-found" >/dev/null || true
done

for _ in {1..30}; do
  curl -s -o /dev/null -w "%{http_code}\n" "${BASE_URL}/error" >/dev/null || true
done

for _ in {1..8}; do
  curl -s -o /dev/null -X POST "${BASE_URL}/process?items=30&delay_ms=150"
done

echo "[ok] Traffic generated: 2xx, 4xx, 5xx and business metric updates."
