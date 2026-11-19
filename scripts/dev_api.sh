#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

if ! .venv/bin/python -c 'import watchfiles' 2>/dev/null; then
  printf '%s\n' 'Install the local development dependencies from requirements-dev.txt first.' >&2
  exit 1
fi

exec .venv/bin/python -m uvicorn asgi:create_app --factory \
  --host 127.0.0.1 --port 8000 --reload --reload-dir "$PWD" \
  --reload-exclude "$PWD/.git" --reload-exclude "$PWD/.venv" \
  --reload-exclude "$PWD/frontend" --reload-exclude "$PWD/downloads" \
  --reload-exclude "$PWD/output"
