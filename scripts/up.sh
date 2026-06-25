#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-}"

case "$ROLE" in
  central)
    COMPOSE_FILE="docker-compose.central.yml"
    ;;
  edge)
    COMPOSE_FILE="docker-compose.edge.yml"
    ;;
  *)
    echo "Usage: $0 central|edge [service...]"
    exit 1
    ;;
esac

shift || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STACK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${STACK_DIR}"

docker compose -f "${COMPOSE_FILE}" up -d "$@"
docker compose -f "${COMPOSE_FILE}" ps
