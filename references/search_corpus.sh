#!/usr/bin/env bash
# Search generated corpus markdown. Usage: bash references/search_corpus.sh "关键词"
set -euo pipefail
KEYWORD="${1:?need keyword}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if ! compgen -G "data/corpus/*.md" > /dev/null; then
  echo "No corpus markdown found. Run: python scripts/scraper.py --config config/sources.yaml --out data/corpus" >&2
  exit 1
fi
grep -Rni --color=never "$KEYWORD" data/corpus/*.md | head -120 || true
