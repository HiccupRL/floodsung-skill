#!/usr/bin/env python3
"""Build lightweight reference indexes from curated corpus."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from corpus_lib import (
    ALL_CORPUS_FILE,
    COLLECTION_LABELS,
    CONCEPT_GRAPH_FILE,
    INDEX_DIR,
    REFERENCES_DIR,
    clean_text,
    configure_utf8_stdio,
    load_corpus,
    make_snippet,
    normalise_for_search,
    read_json,
    write_json,
)


def concept_terms(graph: dict, collection: str, concept: dict) -> list[str]:
    terms = []
    terms.extend(concept.get("aliases", []))
    terms.extend(concept.get("collections", {}).get(collection, []))
    return list(dict.fromkeys(terms))


def score_item(item: dict, terms: list[str]) -> int:
    haystack = normalise_for_search(f"{item.get('title', '')} {item.get('work', '')} {item.get('text_clean', '')}")
    score = 0
    for term in terms:
        norm = normalise_for_search(term)
        if not norm:
            continue
        score += haystack.count(norm)
        if norm in normalise_for_search(item.get("title", "")):
            score += 3
        if norm in normalise_for_search(item.get("work", "")):
            score += 2
    return score


def build_source_index(items: list[dict]) -> str:
    grouped = defaultdict(list)
    for item in items:
        grouped[item["collection"]].append(item)
    lines = ["# 来源索引", "", "按材料组列出当前 curated corpus 条目。", ""]
    for collection, entries in grouped.items():
        lines.extend([f"## {COLLECTION_LABELS.get(collection, collection)} ({len(entries)})", ""])
        for item in sorted(entries, key=lambda x: (x["work"], x["title"])):
            lines.append(f"- [{item['title']}]({item['source_url']}) — {item['author']} · {item['work']} · `{item['source_id']}`")
        lines.append("")
    return "\n".join(lines)


def build_quote_index(items: list[dict]) -> str:
    grouped = defaultdict(list)
    for item in items:
        grouped[item["collection"]].append(item)
    lines = ["# 代表性短摘录索引", "", "短摘录用于定位原文；正式引用前回到 source_url 核对上下文。", ""]
    for collection, entries in grouped.items():
        lines.extend([f"## {COLLECTION_LABELS.get(collection, collection)}", ""])
        for item in sorted(entries, key=lambda x: (x["work"], x["title"]))[:120]:
            excerpt = clean_text(item.get("text_clean", ""))[:320]
            lines.extend(
                [
                    f"### {item['title']}",
                    f"- author: {item['author']}",
                    f"- work: {item['work']}",
                    f"- source: {item['source_url']}",
                    f"- excerpt: {excerpt}...",
                    "",
                ]
            )
    return "\n".join(lines)


def build_core_concepts(items: list[dict], graph: dict) -> str:
    lines = ["# 核心概念索引", "", "由 concept graph 和 corpus 自动生成；只作阅读入口，不替代原文判断。", ""]
    for concept in graph.get("concepts", []):
        lines.extend([f"## {concept['label']}", ""])
        for collection in ("maozedong", "wang_yangming", "zeng_guofan"):
            terms = concept_terms(graph, collection, concept)
            ranked = []
            for item in items:
                if item["collection"] != collection:
                    continue
                score = score_item(item, terms)
                if score > 0:
                    ranked.append((score, item))
            ranked.sort(key=lambda pair: pair[0], reverse=True)
            if not ranked:
                continue
            lines.append(f"### {COLLECTION_LABELS.get(collection, collection)}")
            for score, item in ranked[:5]:
                snippet = make_snippet(item.get("text_clean", ""), terms)
                lines.append(f"- [{item['title']}]({item['source_url']}) — score {score}：{snippet}")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Build Dao-Skill reference indexes.")
    parser.add_argument("--corpus", default=str(ALL_CORPUS_FILE))
    args = parser.parse_args()

    items = load_corpus(Path(args.corpus))
    graph = read_json(CONCEPT_GRAPH_FILE, default={"concepts": []})
    REFERENCES_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    (REFERENCES_DIR / "source_index.md").write_text(build_source_index(items), encoding="utf-8")
    (REFERENCES_DIR / "quote_index.md").write_text(build_quote_index(items), encoding="utf-8")
    (REFERENCES_DIR / "core_concepts.md").write_text(build_core_concepts(items, graph), encoding="utf-8")
    write_json(
        INDEX_DIR / "manifest.json",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "corpus": str(Path(args.corpus)),
            "items": len(items),
            "concepts": len(graph.get("concepts", [])),
            "embedding_index": "not_built; retrieve.py computes optional embeddings at query time when sentence-transformers is available",
        },
    )


if __name__ == "__main__":
    main()
