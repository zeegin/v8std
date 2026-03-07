#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/zensical-version.sh"

python - "${ZENSICAL_VERSION_PYTHON}" <<'PY'
import importlib.metadata
import sys

expected = sys.argv[1]

try:
    actual = importlib.metadata.version("zensical")
except importlib.metadata.PackageNotFoundError:
    raise SystemExit("error: Zensical is not installed. Run ./scripts/install_zensical.sh first.")

if actual != expected:
    raise SystemExit(
        f"error: expected Zensical {expected}, found {actual}. Run ./scripts/install_zensical.sh to install the pinned version."
    )
PY

python "${SCRIPT_DIR}/generate_social_cards.py"
exec zensical "$@"
