#!/usr/bin/env sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
exec uv run --extra gcp python -m scripts.gcp.control plan "$@"
