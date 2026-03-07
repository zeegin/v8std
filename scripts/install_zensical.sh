#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/zensical-version.sh"
CACHE_ROOT="${ZENSICAL_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/v8std/zensical}"
SOURCE_DIR="${CACHE_ROOT}/${ZENSICAL_VERSION_TAG}-${ZENSICAL_COMMIT_SHORT}"

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
  printf 'Cloning pinned Zensical %s (%s) into %s\n' "${ZENSICAL_VERSION_TAG}" "${ZENSICAL_COMMIT_SHORT}" "${SOURCE_DIR}"
  git clone --branch "${ZENSICAL_VERSION_TAG}" --depth 1 https://github.com/zensical/zensical.git "${SOURCE_DIR}"
fi

ACTUAL_COMMIT="$(cd "${SOURCE_DIR}" && git rev-parse HEAD)"
if [ "${ACTUAL_COMMIT}" != "${ZENSICAL_COMMIT_SHA}" ]; then
  printf 'error: expected Zensical %s at commit %s, got %s\n' "${ZENSICAL_VERSION_TAG}" "${ZENSICAL_COMMIT_SHA}" "${ACTUAL_COMMIT}" >&2
  exit 1
fi

printf 'Preparing pinned Zensical %s (%s)\n' "${ZENSICAL_VERSION_TAG}" "${ZENSICAL_COMMIT_SHORT}"
(
  cd "${SOURCE_DIR}"
  python scripts/prepare.py
  python -m pip install --upgrade pip
  python -m pip install --force-reinstall .
)

printf 'Installing project Python dependencies\n'
python -m pip install --upgrade -r "${REPO_ROOT}/requirements.txt"
