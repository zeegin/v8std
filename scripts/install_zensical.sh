#!/usr/bin/env bash

set -euo pipefail

ZENSICAL_VERSION="${ZENSICAL_VERSION:-v0.0.24}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CACHE_ROOT="${ZENSICAL_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/v8std/zensical}"
SOURCE_DIR="${CACHE_ROOT}/${ZENSICAL_VERSION}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'error: required command not found: %s\n' "$1" >&2
    exit 1
  fi
}

python - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit("error: Python 3.10+ is required to install Zensical.")
PY

require_command git
require_command cargo
require_command rustc

mkdir -p "${CACHE_ROOT}"

if [ ! -d "${SOURCE_DIR}/.git" ]; then
  printf 'Cloning Zensical %s into %s\n' "${ZENSICAL_VERSION}" "${SOURCE_DIR}"
  git clone --branch "${ZENSICAL_VERSION}" --depth 1 https://github.com/zensical/zensical.git "${SOURCE_DIR}"
fi

printf 'Preparing Zensical templates\n'
(
  cd "${SOURCE_DIR}"
  python scripts/prepare.py
  python -m pip install --upgrade pip
  python -m pip install --force-reinstall .
)

printf 'Installing project plugins\n'
python -m pip install --upgrade -r "${REPO_ROOT}/requirements.txt"
