#!/usr/bin/env bash
# Start the Linux save-mode helper. Use --game /path/to/TotK if the recomp
# install is not at ../game.
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
if [[ -x "$HERE/.venv/bin/python" ]]; then
    PY="$HERE/.venv/bin/python"
else
    PY="${PYTHON:-python3}"
fi
exec "$PY" cook_helper_linux.py "$@"
