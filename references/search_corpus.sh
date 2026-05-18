#!/usr/bin/env bash
# Smart search wrapper for Dao-Skill corpus.
# Usage: bash references/search_corpus.sh "keyword1" "keyword2" [--collection maozedong|wang_yangming|zeng_guofan] [--hybrid]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ "$#" -eq 0 ]; then
    echo "Usage: bash references/search_corpus.sh <keyword1> [keyword2 ...]"
    exit 1
fi

if command -v python3 >/dev/null 2>&1; then
    python3 scripts/search.py "$@"
else
    python scripts/search.py "$@"
fi
