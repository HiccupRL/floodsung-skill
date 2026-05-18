#!/usr/bin/env python3
"""Backward-compatible keyword search wrapper for Dao-Skill hybrid retrieval."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from corpus_lib import ALL_CORPUS_FILE, configure_utf8_stdio, load_corpus, make_snippet, normalise_for_search
from retrieve import retrieve


def legacy_search(keywords: list[str], collection: str | None, limit: int, mode: str, corpus: Path) -> list[dict]:
    terms = keywords
    items = load_corpus(corpus)
    if collection:
        items = [item for item in items if item.get("collection") == collection]
    results = []
    for item in items:
        haystack = normalise_for_search(
            " ".join([item.get("collection", ""), item.get("group", ""), item.get("author", ""), item.get("work", ""), item.get("title", ""), item.get("text_clean", "")])
        )
        checks = [normalise_for_search(term) in haystack for term in terms]
        if (mode == "and" and not all(checks)) or (mode == "or" and not any(checks)):
            continue
        score = sum(1 for ok in checks if ok) * 10
        title_norm = normalise_for_search(item.get("title", ""))
        score += sum(5 for term in terms if normalise_for_search(term) in title_norm)
        results.append(
            {
                "collection": item.get("collection", ""),
                "group": item.get("group", ""),
                "author": item.get("author", ""),
                "work": item.get("work", ""),
                "title": item.get("title", ""),
                "source": item.get("source_url", "Unknown"),
                "snippet": make_snippet(item.get("text_clean", ""), terms),
                "score": score,
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:limit]


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Search Dao-Skill corpus")
    parser.add_argument("keywords", nargs="+", help="Keywords or short query to search for")
    parser.add_argument("--mode", choices=["and", "or"], default="or")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--collection", choices=["maozedong", "wang_yangming", "zeng_guofan"])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--hybrid", action="store_true", help="Treat all keywords as one semantic query and use retrieve.py.")
    parser.add_argument("--corpus", default=str(ALL_CORPUS_FILE))
    args = parser.parse_args()

    corpus = Path(args.corpus)
    if args.hybrid:
        result = retrieve(" ".join(args.keywords), top_k=args.limit, require_collections=args.collection or "", corpus_path=corpus)
        if args.json:
            print(json.dumps(result["results"], ensure_ascii=False, indent=2))
        else:
            from retrieve import print_text

            print_text(result)
        return

    results = legacy_search(args.keywords, args.collection, args.limit, args.mode, corpus)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    scope = f" in {args.collection}" if args.collection else ""
    if not results:
        print(f"No results found{scope} for keywords: {args.keywords}")
        return
    print(f"Found {len(results)} results{scope} (showing top {len(results)}):\n")
    for index, result in enumerate(results, 1):
        print(f"[{index}] {result['title']}")
        print(f"    Group: {result['group']}")
        print(f"    Author: {result['author']}")
        print(f"    Collection: {result['collection']}")
        print(f"    Work: {result['work']}")
        print(f"    Source: {result['source']}")
        print(f"    Snippet: {result['snippet']}\n")


if __name__ == "__main__":
    main()
