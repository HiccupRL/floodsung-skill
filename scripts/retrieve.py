#!/usr/bin/env python3
"""Hybrid Dao-Skill retrieval: concept expansion + BM25 + optional embeddings."""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

from corpus_lib import (
    ALL_CORPUS_FILE,
    BM25,
    COLLECTIONS,
    CONCEPT_GRAPH_FILE,
    configure_utf8_stdio,
    load_corpus,
    make_snippet,
    normalise_for_search,
    read_json,
    tokenize,
)


def load_graph(path: Path = CONCEPT_GRAPH_FILE) -> dict:
    return read_json(path, default={"concepts": [], "question_triggers": {}})


def expand_query(query: str, graph: dict) -> dict:
    norm_query = normalise_for_search(query)
    selected = []
    concept_by_id = {concept["id"]: concept for concept in graph.get("concepts", [])}

    for trigger, concept_ids in graph.get("question_triggers", {}).items():
        if normalise_for_search(trigger) in norm_query:
            for concept_id in concept_ids:
                if concept_id in concept_by_id:
                    selected.append(concept_by_id[concept_id])

    for concept in graph.get("concepts", []):
        aliases = concept.get("aliases", []) + [concept.get("label", "")]
        if any(normalise_for_search(alias) in norm_query for alias in aliases if alias):
            selected.append(concept)

    deduped = []
    seen = set()
    for concept in selected:
        if concept["id"] not in seen:
            seen.add(concept["id"])
            deduped.append(concept)

    terms_by_collection = defaultdict(list)
    general_terms = [query]
    for concept in deduped:
        general_terms.extend(concept.get("aliases", []))
        for collection, terms in concept.get("collections", {}).items():
            terms_by_collection[collection].extend(terms)

    for collection in COLLECTIONS:
        terms_by_collection[collection] = list(dict.fromkeys(general_terms + terms_by_collection[collection]))

    return {
        "concepts": [{"id": concept["id"], "label": concept["label"]} for concept in deduped],
        "terms_by_collection": dict(terms_by_collection),
        "general_terms": list(dict.fromkeys(general_terms)),
    }


def document_text(item: dict) -> str:
    return " ".join([item.get("collection", ""), item.get("author", ""), item.get("work", ""), item.get("title", ""), item.get("text_clean", "")])


def phrase_score(item: dict, terms: list[str]) -> float:
    title = normalise_for_search(f"{item.get('work', '')} {item.get('title', '')}")
    text = normalise_for_search(item.get("text_clean", ""))
    score = 0.0
    for term in terms:
        norm = normalise_for_search(term)
        if not norm:
            continue
        if norm in title:
            score += 8.0
        count = text.count(norm)
        if count:
            score += min(count, 5) * (2.0 if len(norm) >= 3 else 1.0)
    return score


def try_embedding_rerank(query: str, candidates: list[dict]) -> tuple[list[dict], str]:
    if os.environ.get("DAO_SKILL_DISABLE_EMBEDDINGS") == "1":
        return candidates, "disabled"
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return candidates, "unavailable"

    model_name = os.environ.get("DAO_SKILL_EMBED_MODEL", "BAAI/bge-m3")
    cache_dir = os.environ.get("DAO_SKILL_CACHE_DIR")
    try:
        model = SentenceTransformer(model_name, cache_folder=cache_dir)
        query_vec = model.encode([query], normalize_embeddings=True)[0]
        texts = [document_text(item)[:2400] for item in candidates]
        doc_vecs = model.encode(texts, normalize_embeddings=True)
        for item, vec in zip(candidates, doc_vecs):
            item["embedding_score"] = float(query_vec @ vec)
            item["score"] = item["score"] + item["embedding_score"] * 10
        return sorted(candidates, key=lambda item: item["score"], reverse=True), f"sentence-transformers:{model_name}"
    except Exception as exc:
        return candidates, f"failed:{exc.__class__.__name__}"


def retrieve(query: str, top_k: int = 12, require_collections: str = "", corpus_path: Path = ALL_CORPUS_FILE) -> dict:
    items = load_corpus(corpus_path)
    graph = load_graph()
    expanded = expand_query(query, graph)

    docs = [tokenize(document_text(item)) for item in items]
    bm25 = BM25(docs)
    general_tokens = tokenize(" ".join(expanded["general_terms"]))
    scores = bm25.scores(general_tokens)

    candidates = []
    for idx, item in enumerate(items):
        terms = expanded["terms_by_collection"].get(item.get("collection"), expanded["general_terms"])
        score = scores[idx] + phrase_score(item, terms)
        if "fallback" in item.get("source_id", ""):
            score *= 0.65
        if score <= 0:
            continue
        result = {
            "id": item["id"],
            "collection": item["collection"],
            "group": item.get("group", ""),
            "author": item.get("author", ""),
            "work": item.get("work", ""),
            "title": item.get("title", ""),
            "section": item.get("section", ""),
            "source": item.get("source_url", ""),
            "score": score,
            "snippet": make_snippet(item.get("text_clean", ""), terms),
        }
        candidates.append(result)

    candidates.sort(key=lambda item: item["score"], reverse=True)
    reranked_pool, embedding_status = try_embedding_rerank(query, candidates[:80])
    by_id = {item["id"]: item for item in reranked_pool}
    remaining = [by_id.get(item["id"], item) for item in candidates]
    remaining.sort(key=lambda item: item["score"], reverse=True)

    required = []
    if require_collections == "all":
        required = list(COLLECTIONS)
    elif require_collections:
        required = [part.strip() for part in require_collections.split(",") if part.strip()]

    selected = []
    selected_ids = set()
    for collection in required:
        for item in remaining:
            if item["collection"] == collection and item["id"] not in selected_ids:
                selected.append(item)
                selected_ids.add(item["id"])
                break
    for item in remaining:
        if len(selected) >= top_k:
            break
        if item["id"] in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(item["id"])

    return {
        "query": query,
        "concepts": expanded["concepts"],
        "embedding_status": embedding_status,
        "results": selected[:top_k],
        "total_candidates": len(candidates),
    }


def print_text(result: dict) -> None:
    concepts = ", ".join(concept["label"] for concept in result["concepts"]) or "未命中概念图，使用问题文本召回"
    print(f"Query: {result['query']}")
    print(f"Concepts: {concepts}")
    print(f"Embedding: {result['embedding_status']}")
    print(f"Candidates: {result['total_candidates']}")
    print(f"Showing {len(result['results'])} results:\n")
    for index, item in enumerate(result["results"], 1):
        print(f"[{index}] {item['title']}")
        print(f"    Group: {item['group']}")
        print(f"    Author: {item['author']}")
        print(f"    Collection: {item['collection']}")
        print(f"    Work: {item['work']}")
        print(f"    Source: {item['source']}")
        print(f"    Score: {item['score']:.3f}")
        print(f"    Snippet: {item['snippet']}\n")


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Hybrid retrieve Dao-Skill corpus evidence.")
    parser.add_argument("query", help="Question or topic to retrieve evidence for.")
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--require-collections", default="", help="'all' or comma-separated collections.")
    parser.add_argument("--corpus", default=str(ALL_CORPUS_FILE))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = retrieve(args.query, top_k=args.top_k, require_collections=args.require_collections, corpus_path=Path(args.corpus))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)


if __name__ == "__main__":
    main()
