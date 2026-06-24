#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON:-python3}"

cd "$(dirname "$0")"

echo "========================================"
echo "  TermLink Development Run"
echo "========================================"
echo
echo "Running from Python source: ${PYTHON_BIN} main.py"
echo

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "[ERROR] Python was not found: ${PYTHON_BIN}"
    echo "[HINT] Install Python 3, or set PYTHON=/path/to/python."
    exit 1
fi

"${PYTHON_BIN}" main.py
