#!/usr/bin/env python3
"""Allowlist-based corpus scraper for Mao / Wang Yangming / Zeng Guofan texts.

Run:
  python scripts/scraper.py --config config/sources.yaml --out data/corpus

The script preserves source_url, license_note and risk_note for every item.
It intentionally avoids random repost sites and only fetches configured sources.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse
from urllib import robotparser

import requests
import yaml
from bs4 import BeautifulSoup
from markdownify import markdownify


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sid(*parts: str) -> str:
    h = hashlib.sha1()
    for p in parts:
        h.update(str(p).encode("utf-8", "ignore"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer"]):
        tag.decompose()
    text = markdownify(str(soup), heading_style="ATX", strip=["span"])
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def slug(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|\s]+", "-", s.strip())
    return re.sub(r"-+", "-", s).strip("-._")[:80] or "untitled"


class Client:
    def __init__(self, ua: str, sleep: float, timeout: int, obey_robots: bool):
        self.ua = ua
        self.sleep = sleep
        self.timeout = timeout
        self.obey_robots = obey_robots
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": ua, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"})
        self.robots: dict[str, robotparser.RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        if not self.obey_robots:
            return True
        u = urlparse(url)
        root = f"{u.scheme}://{u.netloc}"
        if root not in self.robots:
            rp = robotparser.RobotFileParser()
            rp.set_url(urljoin(root, "/robots.txt"))
            try:
                rp.read()
            except Exception:
                return False
            self.robots[root] = rp
        return self.robots[root].can_fetch(self.ua, url)

    def get(self, url: str, **params):
        if not self.allowed(url):
            raise RuntimeError(f"robots.txt disallows {url}")
        time.sleep(self.sleep)
        r = self.s.get(url, params=params or None, timeout=self.timeout)
        r.raise_for_status()
        if r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        return r.text


def record(src: dict, title: str, url: str, text: str) -> dict:
    return {
        "id": sid(src.get("id", ""), title, url),
        "group": src.get("group", ""),
        "collection": src.get("collection", "misc"),
        "author": src.get("author", ""),
        "title": title.strip() or "Untitled",
        "source_id": src.get("id", ""),
        "source_type": src.get("type", ""),
        "source_url": url,
        "license_note": src.get("license_note", ""),
        "risk_note": src.get("risk_note", ""),
        "retrieved_at": now(),
        "text": text.strip(),
    }


def title_ok(title: str, src: dict) -> bool:
    kws = src.get("title_include_keywords") or []
    return not kws or any(k in title for k in kws)


def scrape_wikimedia(c: Client, src: dict, max_pages: int) -> list[dict]:
    out, seen = [], set()
    api = src["api_url"]
    for term in src.get("search_terms", []):
        if len(out) >= max_pages:
            break
        data = c.get(api, action="query", list="search", srsearch=term,
                     srlimit=src.get("max_results_per_term", 20), format="json", formatversion=2)
        for hit in data.get("query", {}).get("search", []):
            title = hit.get("title", "").strip()
            if not title or title in seen or not title_ok(title, src) or len(out) >= max_pages:
                continue
            seen.add(title)
            page = c.get(api, action="parse", page=title, prop="text|displaytitle",
                         format="json", formatversion=2, redirects=1).get("parse", {})
            text = clean_html(page.get("text", ""))
            if len(text) < 100:
                continue
            page_title = BeautifulSoup(page.get("displaytitle", title), "lxml").get_text(" ", strip=True) or title
            page_url = "https://zh.wikisource.org/wiki/" + page.get("title", title).replace(" ", "_")
            out.append(record(src, page_title, page_url, text))
            print(f"[wikimedia] {page_title} {len(text)} chars")
    return out


def canon(url: str) -> str:
    return urldefrag(url)[0]


def link_ok(url: str, src: dict) -> bool:
    if src.get("allowed_prefixes") and not any(url.startswith(p) for p in src["allowed_prefixes"]):
        return False
    if any(re.search(p, url) for p in src.get("exclude_url_regex", [])):
        return False
    inc = src.get("include_url_regex", [])
    if url in src.get("index_urls", []):
        return True
    if not inc:
        return True
    if any(re.search(p, url) for p in inc):
        return True
    return False

def scrape_mia(c: Client, src: dict, max_pages: int) -> list[dict]:
    out, seen = [], set()
    q = [canon(u) for u in src.get("index_urls", [])]
    while q and len(out) < max_pages:
        url = q.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            html = c.get(url)
        except Exception as e:
            print(f"[warn] {url}: {e}")
            continue
        soup = BeautifulSoup(html, "lxml")
        
        # In gushiwen, links are often relative like "/guwen/bookv_xxxx.aspx"
        # Let's extract ALL links first
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # urljoin naturally handles both relative and absolute links
            u = canon(urljoin(url, href))
            
            # Follow redirects if possible or clean up the URL to prevent mobile versions from missing out
            u = u.replace("m.gushiwen.cn", "www.gushiwen.cn")
            
            # Print for debug
            if link_ok(u, src):
                if u not in seen and u not in q:
                    q.append(u)
                    
        if url in src.get("index_urls", []):
            continue
        title = (soup.find("h1") or soup.title)
        title_text = title.get_text(" ", strip=True) if title else url
        
        contsons = soup.find_all("div", class_="contson")
        if contsons:
            text = "\n\n".join(clean_html(str(c)) for c in contsons)
        else:
            main = soup.find("main") or soup.find(id="content") or soup.find("body") or soup
            text = clean_html(str(main))
            
        if len(text) < 250 or not title_ok(title_text + text[:500], src):
            continue
        out.append(record(src, title_text, url, text))
        print(f"[mia] {title_text} {len(text)} chars")
    return out


def dump(items: list[dict], out: Path, cfg: dict, source_errors: list[dict] | None = None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    
    # Load existing data to merge instead of overwrite
    existing_items = []
    all_json_path = out / "all.json"
    if all_json_path.exists():
        try:
            with open(all_json_path, 'r', encoding='utf-8') as f:
                existing_items = json.load(f)
        except Exception as e:
            print(f"[warn] Failed to load existing {all_json_path}: {e}")
            
    # Merge items based on id
    merged_items = {it["id"]: it for it in existing_items}
    for it in items:
        merged_items[it["id"]] = it
        
    merged_list = list(merged_items.values())
    
    by = {}
    for it in merged_list:
        by.setdefault(it["collection"], []).append(it)
    (out / "all.json").write_text(json.dumps(merged_list, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, recs in sorted(by.items()):
        (out / f"{slug(name)}.json").write_text(json.dumps(recs, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [f"# {name}\n", f"Total: {len(recs)}\n"]
        for r in recs:
            lines += ["\n---\n", f"## {r['title']}\n", f"- author: {r['author']}",
                      f"- group: {r['group']}", f"- source: {r['source_url']}",
                      f"- license: {r['license_note']}", f"- risk: {r['risk_note']}\n", r["text"], ""]
        (out / f"{slug(name)}.md").write_text("\n".join(lines), encoding="utf-8")
    summary = {"generated_at": now(), "total_items": len(merged_list),
               "counts_by_collection": {k: len(v) for k, v in sorted(by.items())},
               "source_ids": [s.get("id") for s in cfg.get("sources", []) if s.get("enabled", True)],
               "source_errors": source_errors or [],
               "note": "Each item preserves source_url, license_note, and risk_note. Review rights before redistribution."}
    (out.parent / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/sources.yaml", type=Path)
    ap.add_argument("--out", default="data/corpus", type=Path)
    ap.add_argument("--max-pages-per-source", type=int, default=200)
    ap.add_argument("--sleep", type=float, default=None)
    ap.add_argument("--source", action="append")
    args = ap.parse_args()
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    d = cfg.get("defaults", {})
    c = Client(d.get("user_agent", "dao-skill/0.1"),
               args.sleep if args.sleep is not None else float(d.get("sleep_seconds", 0.8)),
               int(d.get("timeout_seconds", 30)), bool(d.get("obey_robots_txt", True)))
    handlers = {"wikimedia_search": scrape_wikimedia, "mia_index": scrape_mia}
    selected = set(args.source or [])
    items = []
    source_errors = []
    for src in cfg.get("sources", []):
        if not src.get("enabled", True) or (selected and src.get("id") not in selected):
            continue
        print(f"\n=== {src['id']} ===")
        try:
            items += handlers[src["type"]](c, src, args.max_pages_per_source)
        except Exception as e:
            error = {"source_id": src.get("id", ""), "error": str(e)}
            source_errors.append(error)
            print(f"[error] {error['source_id']}: {error['error']}")
    uniq = {it["id"]: it for it in items}
    dump(list(uniq.values()), args.out, cfg, source_errors)
    if source_errors:
        print(f"DONE_WITH_ERRORS: {len(uniq)} items -> {args.out}; errors={len(source_errors)}")
    else:
        print(f"DONE: {len(uniq)} items -> {args.out}")


if __name__ == "__main__":
    main()
