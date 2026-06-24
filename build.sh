#!/usr/bin/env bash
set -euo pipefail

APP_NAME="TermLink"
DIST_DIR="dist/${APP_NAME}"
PYTHON_BIN="${PYTHON:-python3}"

cd "$(dirname "$0")"

echo "========================================"
echo "  ${APP_NAME} Build"
echo "========================================"
echo

echo "[1/4] Checking build environment..."
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "[ERROR] Python was not found: ${PYTHON_BIN}"
    echo "[HINT] Install Python 3, or set PYTHON=/path/to/python."
    exit 1
fi
if ! "${PYTHON_BIN}" -m PyInstaller --version >/dev/null 2>&1; then
    echo "[ERROR] PyInstaller is not installed for ${PYTHON_BIN}."
    echo "[HINT] Run: ${PYTHON_BIN} -m pip install -r requirements.txt pyinstaller"
    exit 1
fi

echo "[2/4] Stopping running process..."
pkill -f "${DIST_DIR}/${APP_NAME}" >/dev/null 2>&1 || true
sleep 1

echo "[3/4] Cleaning build output..."
rm -rf dist build

echo "[4/4] Building executable package..."
"${PYTHON_BIN}" -m PyInstaller --noconfirm TermLink.spec

if [ ! -x "${DIST_DIR}/${APP_NAME}" ]; then
    echo "[ERROR] Missing executable after build: ${DIST_DIR}/${APP_NAME}"
    exit 1
fi

mkdir -p "${DIST_DIR}/logs"
chmod +x "${DIST_DIR}/${APP_NAME}"

echo
echo "========================================"
echo "Build complete."
echo "Executable: ${DIST_DIR}/${APP_NAME}"
echo "Run command: ./run.sh"
echo "========================================"
