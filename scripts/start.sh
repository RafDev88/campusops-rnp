#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose config --quiet
docker compose up --build -d
printf 'CampusOps: http://localhost:8080\n'
