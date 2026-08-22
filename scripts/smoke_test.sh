#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "ETF DSS smoke test"
echo "API_BASE_URL=${API_BASE_URL}"

echo
echo "Checking Docker Compose service status..."
docker compose ps postgres

check_endpoint() {
  local path="$1"
  local expected_status="${2:-200}"
  local status

  status="$(curl -s -o /dev/null -w "%{http_code}" "${API_BASE_URL}${path}")"
  if [[ "${status}" != "${expected_status}" ]]; then
    echo "FAIL ${path}: expected HTTP ${expected_status}, got HTTP ${status}"
    exit 1
  fi
  echo "OK   ${path}: HTTP ${status}"
}

echo
echo "Checking backend endpoints..."
check_endpoint "/health"
check_endpoint "/api/dss/ranking"
check_endpoint "/api/dss/sensitivity"
check_endpoint "/api/analysis/ranking"
check_endpoint "/api/etfs/E1VFVN30/prices?days=5"

echo
echo "Smoke test passed."
