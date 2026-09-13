#!/bin/bash
set -euo pipefail

case "${APP_COMPONENT:-}" in
  relay)
    exec uv run --no-sync python -m relay.main
    ;;
  *)
    echo "Bootstrap - Unknown APP_COMPONENT: ${APP_COMPONENT:-<unset>}"
    exit 1
    ;;
esac
