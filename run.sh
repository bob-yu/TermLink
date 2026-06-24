#!/usr/bin/env bash
set -euo pipefail

APP_NAME="TermLink"
DIST_EXE="$(cd "$(dirname "$0")" && pwd)/dist/${APP_NAME}/${APP_NAME}"

if [ -x "${DIST_EXE}" ]; then
    echo "Running packaged executable: ${DIST_EXE}"
    nohup "${DIST_EXE}" >/dev/null 2>&1 &
    exit 0
fi

echo "[ERROR] Built executable was not found:"
echo "        ${DIST_EXE}"
echo "[HINT] Run ./build.sh first."
echo "[HINT] For source development, run ./dev.sh."
exit 1
