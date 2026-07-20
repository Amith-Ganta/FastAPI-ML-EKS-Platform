#!/usr/bin/env bash
# Minimal load generator for the insurance-api /predict endpoint.
# Usage: ./run.sh [BASE_URL] [CONCURRENCY] [DURATION]
#   ./run.sh http://localhost:8080 50 5m
#
# Requires `hey` (https://github.com/rakyll/hey). For a no-install option, use
# the in-cluster kubectl one-liner in this directory's README instead.
set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"
CONCURRENCY="${2:-50}"
DURATION="${3:-5m}"

PAYLOAD='{"age":40,"bmi":27.5,"children":1,"smoker":"no","region":"southwest","sex":"male"}'

echo "Load: ${CONCURRENCY} concurrent for ${DURATION} against ${BASE_URL}/predict"
echo "Watch scaling in another terminal:  kubectl get hpa insurance-api -w"

hey -z "${DURATION}" -c "${CONCURRENCY}" -m POST \
  -H 'Content-Type: application/json' \
  -d "${PAYLOAD}" \
  "${BASE_URL}/predict"
