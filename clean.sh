#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"

show_help() {
    cat <<'EOF'
Usage:
  ./clean.sh
    Clean build/release artifacts: build, dist, portable, release, installer_output

  ./clean.sh all
    Same as above, plus remove logs folder

  ./clean.sh help
    Show this help
EOF
}

case "${MODE}" in
    help|-h|--help)
        show_help
        exit 0
        ;;
    ""|all)
        ;;
    *)
        echo "[ERROR] Unknown mode: ${MODE}"
        show_help
        exit 1
        ;;
esac

cd "$(dirname "$0")"

echo "========================================"
echo "  TermLink Clean Script"
echo "========================================"
echo

for dir in build dist portable release installer_output; do
    if [ -d "${dir}" ]; then
        rm -rf "${dir}"
        echo "[OK] Removed ${dir}"
    else
        echo "[SKIP] ${dir} (not found)"
    fi
done

if [ "${MODE}" = "all" ]; then
    if [ -d "logs" ]; then
        rm -rf logs
        echo "[OK] Removed logs"
    else
        echo "[SKIP] logs (not found)"
    fi
else
    echo "[SKIP] logs (use './clean.sh all' to remove logs)"
fi

echo "[INFO] Removing Python cache files..."
find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

echo
echo "[DONE] Clean complete."
