#!/usr/bin/env bash
# Copy the captured Sample data into the hosted example (docs/try/data) and the Streamlit app bundle (app/sample),
# and write docs/.nojekyll so GitHub Pages serves the folder as-is.
# Run with: bash scripts/build_example.sh
set -euo pipefail
cd "$(dirname "$0")/.."
for d in docs/try/data app/sample; do
  mkdir -p "$d"
  cp data/sample/banks.json data/sample/metrics.json data/sample/notes.json data/sample/agent.json "$d/"
done
touch docs/.nojekyll
echo "Sample data copied to docs/try/data and app/sample; docs/.nojekyll written."
