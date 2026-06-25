#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-}"

case "$ROLE" in
  central)
    shift
    exec "$(dirname "$0")/central-down.sh" "$@"
    ;;
  edge)
    shift
    exec "$(dirname "$0")/edge-down.sh" "$@"
    ;;
  *)
    echo "Usage: $0 central|edge"
    echo
    echo "Examples:"
    echo "  $0 central"
    echo "  $0 edge"
    exit 1
    ;;
esac
