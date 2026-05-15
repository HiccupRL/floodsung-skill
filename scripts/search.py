#!/usr/bin/env python3
"""
Smart search tool for Dao-Skill corpus.
Supports multiple keywords and outputs matched context.
"""
import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_FILE = ROOT / "data" / "corpus" / "all.json"

def main():
    parser = argparse.ArgumentParser(description="Smart search for Dao-Skill corpus")
    parser.add_argument("keywords", nargs="+", help="Keywords to search for (supports multiple)")
    parser.add_argument("--mode", choices=["and", "or"], default="or", help="Search mode: 'or' (match any) or 'and' (match all). Default is 'or'.")
    parser.add_argument("--limit", type=int, default=15, help="Max results to show")
    args = parser.parse_args()

    if not CORPUS_FILE.exists():
        print(f"Error: Corpus not found at {CORPUS_FILE}. Please run scraper first.", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading corpus: {e}", file=sys.stderr)
        sys.exit(1)
    
    results = []
    for item in data:
        text = item.get("text", "")
        title = item.get("title", "")
        search_target = title + "\n" + text
        
        match = False
        if args.mode == "and":
            match = all(kw.lower() in search_target.lower() for kw in args.keywords)
        else:
            match = any(kw.lower() in search_target.lower() for kw in args.keywords)
            
        if match:
            # Extract a snippet around the first matched keyword
            snippet = ""
            for kw in args.keywords:
                idx = text.lower().find(kw.lower())
                if idx != -1:
                    start = max(0, idx - 150)
                    end = min(len(text), idx + 350)
                    snippet = text[start:end].replace('\n', ' ')
                    snippet = f"...{snippet}..."
                    break
            
            if not snippet:
                snippet = "Matched in title only."

            results.append({
                "title": title,
                "source": item.get("source_url", "Unknown"),
                "snippet": snippet
            })

    if not results:
        print(f"No results found for keywords: {args.keywords}")
        return

    print(f"Found {len(results)} results (showing top {min(len(results), args.limit)}):\n")
    for i, res in enumerate(results[:args.limit], 1):
        print(f"[{i}] {res['title']}")
        print(f"    Source: {res['source']}")
        print(f"    Snippet: {res['snippet']}\n")

if __name__ == "__main__":
    main()
