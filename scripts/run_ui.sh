#!/usr/bin/env bash
# Launch Streamlit using the project's virtual environment on Windows (Git Bash) or Unix
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -x "$ROOT_DIR/.venv/Scripts/python.exe" ]; then
  "$ROOT_DIR/.venv/Scripts/python.exe" -m streamlit run "$ROOT_DIR/app.py" "$@"
else
  # Fallback to current python
  python -m streamlit run "$ROOT_DIR/app.py" "$@"
fi
