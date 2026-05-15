#!/usr/bin/env python3
"""Repository sanity checks for chinese-thought-corpus-skill."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "SKILL.md",
    "README.md",
    "config/sources.yaml",
    "scripts/scraper.py",
    "scripts/build_references.py"
]
LEGACY_MARKERS = [
    "Zhihu scraper",
    "ZHIHU_COOKIE",
    "XVI Robotics",
    "Humanoid Foundation Model",
    "xvi-robotics"
]
SKIP_DIRS = {".git", ".venv", "__pycache__"}
CHECK_PATH_PREFIXES = {
    "SKILL.md",
    "README.md",
    "config/",
    "data/corpus/",
    "references/core_concepts.md",
    "references/quote_index.md",
    "references/reading_workflow.md",
    "references/search_corpus.sh",
    "references/source_index.md",
    "scripts/build_references.py",
    "scripts/check_repo.py",
    "scripts/scraper.py",
}


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        rel_posix = rel.as_posix()
        if not any(rel_posix == prefix.rstrip("/") or rel_posix.startswith(prefix) for prefix in CHECK_PATH_PREFIXES):
            continue
        if path.name == "check_repo.py":
            continue
        if path.suffix.lower() in {".md", ".py", ".yaml", ".yml", ".txt", ""}:
            files.append(path)
    return files


def main() -> None:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")
    for path in iter_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in LEGACY_MARKERS:
            if marker in text:
                errors.append(f"legacy marker {marker!r} found in {path.relative_to(ROOT)}")
    corpus = ROOT / "data" / "corpus" / "all.json"
    if corpus.exists():
        data = json.loads(corpus.read_text(encoding="utf-8"))
        for i, item in enumerate(data):
            for key in ["id", "title", "source_url", "license_note", "text"]:
                if not item.get(key):
                    errors.append(f"all.json[{i}] missing {key}")
    if errors:
        print("FAILED")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)
    print("OK: repository layout, legacy markers, and JSON checks passed")


if __name__ == "__main__":
    main()
