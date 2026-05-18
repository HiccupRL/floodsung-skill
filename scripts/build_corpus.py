#!/usr/bin/env python3
"""Build curated Dao-Skill corpus from data/raw."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from corpus_lib import (
    COLLECTIONS,
    CORPUS_DIR,
    RAW_DIR,
    checksum,
    clean_text,
    configure_utf8_stdio,
    derive_work,
    load_sources,
    normalise_space,
    quality_flags,
    read_json,
    sha1_text,
    write_json,
)


def source_map() -> dict[str, dict]:
    config = load_sources()
    return {source["id"]: source for source in config.get("sources", [])}


def iter_raw(input_dir: Path):
    for path in sorted(input_dir.glob("*.json")):
        if path.name == "manifest.json":
            continue
        for item in read_json(path, default=[]):
            yield item


def trim_to_title_anchor(text: str, title: str) -> str:
    markers = [
        title,
        title.split("（", 1)[0],
        title.split("_", 1)[0],
        title.split("·", 1)[-1],
    ]
    for marker in dict.fromkeys(markers):
        marker = normalise_space(marker)
        if len(marker) < 4:
            continue
        idx = text.find(marker)
        if idx >= 0 and "_古文岛" in text[idx : idx + len(marker) + 20]:
            next_idx = text.find(marker, idx + len(marker))
            if next_idx >= 0:
                idx = next_idx
        if 0 < idx < 2000:
            return text[idx:]
    return text


def collapse_repeated_title(text: str, title: str) -> str:
    title = normalise_space(title)
    if not title or not text.startswith(title):
        return text
    rest = text[len(title) :].lstrip()
    if rest.startswith(title):
        return f"{title} {rest[len(title):].lstrip()}".strip()
    return text


def build_entry(raw: dict, source: dict | None) -> dict:
    title = normalise_space(raw.get("title"))
    text_clean = clean_text(raw.get("raw_text") or raw.get("text") or "")
    text_clean = trim_to_title_anchor(text_clean, title)
    text_clean = collapse_repeated_title(text_clean, title)
    collection = raw.get("collection", "")
    work, section = derive_work(collection, title, raw.get("source_work") or (source or {}).get("work", ""))
    source_url = raw.get("source_url", "")
    entry_id = sha1_text(collection, work, title, source_url, text_clean)
    item = {
        "id": entry_id,
        "collection": collection,
        "group": raw.get("group") or (source or {}).get("group", ""),
        "author": raw.get("author") or (source or {}).get("author", ""),
        "work": work,
        "title": title,
        "section": section,
        "source_id": raw.get("source_id", ""),
        "source_type": raw.get("source_type", ""),
        "source_url": source_url,
        "license_note": raw.get("license_note") or (source or {}).get("license_note", ""),
        "risk_note": raw.get("risk_note") or (source or {}).get("risk_note", ""),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "text": raw.get("raw_text", ""),
        "text_clean": text_clean,
        "checksum": checksum(text_clean),
        "quality_flags": [],
    }
    item["quality_flags"] = quality_flags(item, source)
    return item


def write_markdown(output_dir: Path, collection: str, entries: list[dict]) -> None:
    lines = [f"# {collection}", ""]
    for item in entries:
        lines.extend(
            [
                f"## {item['title']}",
                "",
                f"- author: {item['author']}",
                f"- work: {item['work']}",
                f"- source: {item['source_url']}",
                "",
                item["text_clean"],
                "",
                "---",
                "",
            ]
        )
    (output_dir / f"{collection}.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Build curated corpus from raw fetches.")
    parser.add_argument("--input", default=str(RAW_DIR), help="Raw input directory.")
    parser.add_argument("--output", default=str(CORPUS_DIR), help="Corpus output directory.")
    parser.add_argument("--keep-flagged", action="store_true", help="Keep entries with quality flags.")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = source_map()

    clean_entries = []
    rejected = []
    seen_checksums = set()
    for raw in iter_raw(input_dir):
        source = sources.get(raw.get("source_id", ""))
        item = build_entry(raw, source)
        if item["checksum"] in seen_checksums:
            item["quality_flags"].append("duplicate_checksum")
        if item["quality_flags"] and not args.keep_flagged:
            rejected.append(item)
            continue
        seen_checksums.add(item["checksum"])
        clean_entries.append(item)

    clean_entries.sort(key=lambda item: (item["collection"], item["work"], item["title"], item["source_url"]))
    write_json(output_dir / "all.json", clean_entries)
    counts = {}
    for collection in COLLECTIONS:
        subset = [item for item in clean_entries if item["collection"] == collection]
        counts[collection] = len(subset)
        write_json(output_dir / f"{collection}.json", subset)
        write_markdown(output_dir, collection, subset)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_items": len(clean_entries),
        "counts_by_collection": counts,
        "source_ids": sorted({item["source_id"] for item in clean_entries}),
        "rejected_items": len(rejected),
        "rejected_by_flag": {},
        "note": "Curated corpus built from book-level allowlisted sources. Raw fetches are reproducible and intentionally ignored by git.",
    }
    for item in rejected:
        for flag in item["quality_flags"]:
            summary["rejected_by_flag"][flag] = summary["rejected_by_flag"].get(flag, 0) + 1
    raw_manifest = read_json(input_dir / "manifest.json", default={})
    summary["source_errors"] = raw_manifest.get("source_errors", [])
    write_json(output_dir.parent / "summary.json", summary)


if __name__ == "__main__":
    main()
