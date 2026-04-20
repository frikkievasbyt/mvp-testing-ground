#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
python -m pip install -r scripts/requirements.txt >/dev/null

python scripts/enrich_free_sources.py

# Optional paid enrichment layer if key is available
if [ -n "${GOOGLE_MAPS_API_KEY:-}" ]; then
  python scripts/google_places_enrich.py || true
fi

python scripts/quality_gate.py || true

echo "Refresh complete. See data/quality-report.md"