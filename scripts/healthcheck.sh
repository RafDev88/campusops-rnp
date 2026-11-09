#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose ps
curl --fail --silent --show-error http://127.0.0.1:8080/api/health
printf '\n'
