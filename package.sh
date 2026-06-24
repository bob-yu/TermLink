#!/usr/bin/env bash
set -euo pipefail

APP_NAME="TermLink"
VERSION="1.0.5"
DIST_DIR="dist/${APP_NAME}"
PORTABLE_ROOT="portable"
OS_NAME="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH_NAME="$(uname -m)"
case "${ARCH_NAME}" in
    x86_64|amd64) ARCH_NAME="amd64" ;;
    aarch64|arm64) ARCH_NAME="arm64" ;;
esac
TS="$(date +%Y%m%d_%H%M%S)"
PORTABLE_DIR="${PORTABLE_ROOT}/${APP_NAME}_v${VERSION}_${OS_NAME}_${ARCH_NAME}_${TS}"
ARCHIVE_FILE="${PORTABLE_ROOT}/${APP_NAME}_v${VERSION}_${OS_NAME}_${ARCH_NAME}_${TS}.tar.gz"

cd "$(dirname "$0")"

echo "========================================"
echo "  ${APP_NAME} v${VERSION} Package"
echo "========================================"
echo

echo "[1/5] Building latest executable package..."
bash ./build.sh

if [ ! -x "${DIST_DIR}/${APP_NAME}" ]; then
    echo "[ERROR] Built executable was not found after build: ${DIST_DIR}/${APP_NAME}"
    exit 1
fi

echo "[2/5] Stopping running process..."
pkill -f "${DIST_DIR}/${APP_NAME}" >/dev/null 2>&1 || true
sleep 1

echo "[3/5] Creating portable folder..."
mkdir -p "${PORTABLE_ROOT}"
rm -rf "${PORTABLE_DIR}"
mkdir -p "${PORTABLE_DIR}"
cp -a "${DIST_DIR}/." "${PORTABLE_DIR}/"
rm -rf "${PORTABLE_DIR}/logs"
find "${PORTABLE_DIR}" -type f -name "*.log" -delete
mkdir -p "${PORTABLE_DIR}/logs"

echo "[4/5] Writing portable launcher..."
cat > "${PORTABLE_DIR}/run.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
./TermLink &
EOF
chmod +x "${PORTABLE_DIR}/run.sh" "${PORTABLE_DIR}/${APP_NAME}"

echo "[5/5] Creating tar.gz package..."
tar -C "${PORTABLE_ROOT}" -czf "${ARCHIVE_FILE}" "$(basename "${PORTABLE_DIR}")"

echo
echo "========================================"
echo "Package complete."
echo "Portable folder: ${PORTABLE_DIR}"
echo "Portable archive: ${ARCHIVE_FILE}"
echo "========================================"
