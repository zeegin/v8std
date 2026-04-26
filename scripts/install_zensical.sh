#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/zensical-version.sh"

python_supports_project() {
  "$1" - <<'PY'
import sys

raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
}

find_python() {
  local candidate

  if [ -n "${VIRTUAL_ENV:-}" ]; then
    candidate="${VIRTUAL_ENV}/bin/python"
    if [ -x "${candidate}" ] && python_supports_project "${candidate}"; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  fi

  for candidate in python python3.12; do
    if command -v "${candidate}" >/dev/null 2>&1 && python_supports_project "${candidate}"; then
      command -v "${candidate}"
      return 0
    fi
  done

  printf 'error: Python 3.12+ is required to install Zensical. Activate a Python 3.12 virtual environment or install python3.12.\n' >&2
  return 1
}

PYTHON_BIN="$(find_python)"

printf 'Installing pinned Zensical %s from PyPI\n' "${ZENSICAL_VERSION_PYTHON}"
"${PYTHON_BIN}" -m pip install --upgrade pip
"${PYTHON_BIN}" -m pip install --force-reinstall "zensical==${ZENSICAL_VERSION_PYTHON}"

printf 'Installing project Python dependencies\n'
"${PYTHON_BIN}" -m pip install --upgrade -r "${REPO_ROOT}/requirements.txt"
