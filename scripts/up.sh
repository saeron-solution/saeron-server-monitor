#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-}"

case "$ROLE" in
  central)
    shift
    exec "$(dirname "$0")/central-up.sh" "$@"
    ;;
  edge)
    shift
    exec "$(dirname "$0")/edge-up.sh" "$@"
    ;;
  *)
    echo "Usage: $0 central|edge [service...]"
    echo
    echo "Examples:"
    echo "  $0 central"
    echo "  $0 edge"
    echo "  $0 central prometheus"
    echo "  $0 edge node-exporter"
    exit 1
    ;;
esac
