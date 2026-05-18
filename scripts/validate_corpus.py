#!/usr/bin/env python3
"""Validate Dao-Skill curated corpus quality."""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from corpus_lib import ALL_CORPUS_FILE, COLLECTIONS, configure_utf8_stdio, quality_flags, read_json

REQUIRED_FIELDS = (
    "id",
    "collection",
    "author",
    "work",
    "title",
    "source_url",
    "license_note",
    "risk_note",
    "checksum",
    "text_clean",
)


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Validate curated Dao-Skill corpus.")
    parser.add_argument("--corpus", default=str(ALL_CORPUS_FILE))
    parser.add_argument("--fail-on-noise", action="store_true")
    args = parser.parse_args()

    data = read_json(Path(args.corpus), default=[])
    errors = []
    counts = Counter(item.get("collection") for item in data)

    for collection in COLLECTIONS:
        if counts[collection] <= 0:
            errors.append(f"collection {collection} has no entries")

    seen_ids = set()
    seen_checksums = set()
    for index, item in enumerate(data, 1):
        missing = [field for field in REQUIRED_FIELDS if not item.get(field)]
        if missing:
            errors.append(f"item {index} missing required fields: {missing}")
        if item.get("id") in seen_ids:
            errors.append(f"duplicate id: {item.get('id')}")
        seen_ids.add(item.get("id"))
        if item.get("checksum") in seen_checksums:
            errors.append(f"duplicate checksum: {item.get('title')}")
        seen_checksums.add(item.get("checksum"))

        flags = quality_flags(item)
        if flags:
            errors.append(f"{item.get('collection')} / {item.get('title')}: {', '.join(flags)}")

        title = item.get("title", "")
        if item.get("collection") == "wang_yangming" and re.search(r"孙子兵法|孫子兵法|格言联璧|格言聯璧", title):
            errors.append(f"known Wang pollution found: {title}")
        if item.get("collection") == "zeng_guofan" and re.search(r"西厢记|西廂記|第[一二三四五六七八九十百零〇]+回", title):
            errors.append(f"known Zeng pollution found: {title}")
        if item.get("collection") == "maozedong" and "全部导航" in (title + item.get("text_clean", "")):
            errors.append(f"known Mao navigation pollution found: {title}")

    print("Corpus counts:")
    for collection in COLLECTIONS:
        print(f"  {collection}: {counts[collection]}")
    print(f"  total: {len(data)}")

    if errors:
        print("\nValidation errors:")
        for error in errors[:100]:
            print(f"  - {error}")
        if len(errors) > 100:
            print(f"  ... {len(errors) - 100} more")
        if args.fail_on_noise:
            sys.exit(1)
    else:
        print("\nValidation passed.")


if __name__ == "__main__":
    main()
