#!/usr/bin/env python3
"""Fetch raw Dao-Skill source texts into data/raw."""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from corpus_lib import RAW_DIR, configure_utf8_stdio, eprint, load_sources, normalise_space, sha1_text, write_json


def session_for(defaults: dict) -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"User-Agent": defaults.get("user_agent", "Dao-Skill/1.0")})
    return sess


def request_text(sess: requests.Session, url: str, timeout: int) -> str:
    response = sess.get(url, timeout=timeout)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding
    return response.text


def soup_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer"]):
        tag.decompose()
    return normalise_space(soup.get_text("\n"))


def soup_title(html: str, fallback: str = "") -> str:
    soup = BeautifulSoup(html, "lxml")
    for selector in ("h1", "h2", "h3", "title"):
        tag = soup.select_one(selector)
        if tag:
            title = normalise_space(tag.get_text(" "))
            if title:
                return re.sub(r"\s*[-|].*$", "", title)
    return fallback


def allowed_url(url: str, source: dict) -> bool:
    if any(re.search(pattern, url) for pattern in source.get("url_exclude_patterns", [])):
        return False
    allow = source.get("url_allowlist", [])
    return not allow or any(re.search(pattern, url) for pattern in allow)


def fetch_mia_index(sess: requests.Session, source: dict, defaults: dict, limit: int | None) -> tuple[list[dict], list[str]]:
    entries: list[dict] = []
    errors: list[str] = []
    seen = set()
    timeout = int(defaults.get("timeout_seconds", 30))
    sleep = float(defaults.get("sleep_seconds", 0.8))

    for index_url in source.get("index_urls", []):
        try:
            html = request_text(sess, index_url, timeout)
        except Exception as exc:
            errors.append(f"{index_url}: {exc}")
            continue
        soup = BeautifulSoup(html, "lxml")
        candidates = []
        for link in soup.find_all("a", href=True):
            href = urljoin(index_url, link["href"])
            if href in seen or not allowed_url(href, source) or href == index_url:
                continue
            seen.add(href)
            label = normalise_space(link.get_text(" "))
            candidates.append((href, label))

        for href, label in candidates:
            if limit and len(entries) >= limit:
                break
            try:
                page_html = request_text(sess, href, timeout)
                title = soup_title(page_html, fallback=label)
                raw_text = soup_text(page_html)
            except Exception as exc:
                errors.append(f"{href}: {exc}")
                continue
            entries.append(
                {
                    "source_id": source["id"],
                    "source_type": source["type"],
                    "group": source["group"],
                    "collection": source["collection"],
                    "author": source["author"],
                    "source_work": source.get("work", ""),
                    "title": title or label or href.rsplit("/", 1)[-1],
                    "source_url": href,
                    "license_note": source.get("license_note", ""),
                    "risk_note": source.get("risk_note", ""),
                    "raw_text": raw_text,
                }
            )
            time.sleep(sleep)
    return entries, errors


def wikisource_api(sess: requests.Session, api_url: str, params: dict, timeout: int) -> dict:
    merged = {"format": "json", "formatversion": "2", **params}
    last_exc = None
    for attempt in range(5):
        try:
            response = sess.get(api_url, params=merged, timeout=timeout)
            if response.status_code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError("request failed after retries, likely rate limited")


def list_wikisource_prefix(sess: requests.Session, api_url: str, prefix: str, timeout: int) -> list[str]:
    titles = [prefix]
    apcontinue = None
    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apnamespace": 0,
            "apprefix": f"{prefix}/",
            "aplimit": "max",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue
        data = wikisource_api(sess, api_url, params, timeout)
        titles.extend(page["title"] for page in data.get("query", {}).get("allpages", []))
        apcontinue = data.get("continue", {}).get("apcontinue")
        if not apcontinue:
            break
    return titles


def fetch_wikisource_title(sess: requests.Session, api_url: str, title: str, timeout: int) -> dict | None:
    data = wikisource_api(
        sess,
        api_url,
        {
            "action": "query",
            "prop": "extracts|info",
            "explaintext": 1,
            "exsectionformat": "plain",
            "inprop": "url",
            "redirects": 1,
            "titles": title,
            "variant": "zh-hant",
        },
        timeout,
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    page = pages[0]
    return {
        "title": page.get("title", title),
        "source_url": page.get("fullurl") or f"https://zh.wikisource.org/wiki/{title}",
        "raw_text": page.get("extract", ""),
    }


def fetch_wikisource_pages(sess: requests.Session, source: dict, defaults: dict, limit: int | None) -> tuple[list[dict], list[str]]:
    entries: list[dict] = []
    errors: list[str] = []
    timeout = int(defaults.get("timeout_seconds", 30))
    sleep = float(defaults.get("sleep_seconds", 0.8))
    api_url = source["api_url"]

    titles = []
    titles.extend(source.get("page_titles", []))
    for prefix in source.get("page_prefixes", []):
        try:
            prefix_titles = list_wikisource_prefix(sess, api_url, prefix, timeout)
        except Exception as exc:
            errors.append(f"{prefix}: {exc}")
            prefix_titles = [prefix]
        titles.extend(prefix_titles)

    seen = set()
    for title in titles:
        if title in seen:
            continue
        seen.add(title)
        if limit and len(entries) >= limit:
            break
        try:
            page = fetch_wikisource_title(sess, api_url, title, timeout)
        except Exception as exc:
            errors.append(f"{title}: {exc}")
            continue
        if not page:
            errors.append(f"{title}: missing")
            continue
        entries.append(
            {
                "source_id": source["id"],
                "source_type": source["type"],
                "group": source["group"],
                "collection": source["collection"],
                "author": source["author"],
                "source_work": source.get("work", ""),
                "title": page["title"],
                "source_url": page["source_url"],
                "license_note": source.get("license_note", ""),
                "risk_note": source.get("risk_note", ""),
                "raw_text": page["raw_text"],
            }
        )
        time.sleep(sleep)
    return entries, errors


def fetch_plain_text_urls(sess: requests.Session, source: dict, defaults: dict, limit: int | None) -> tuple[list[dict], list[str]]:
    entries: list[dict] = []
    errors: list[str] = []
    timeout = int(defaults.get("timeout_seconds", 30))
    sleep = float(defaults.get("sleep_seconds", 0.8))
    for spec in source.get("text_urls", []):
        if limit and len(entries) >= limit:
            break
        try:
            raw_text = request_text(sess, spec["url"], timeout)
        except Exception as exc:
            errors.append(f"{spec.get('url')}: {exc}")
            continue
        entries.append(
            {
                "source_id": source["id"],
                "source_type": source["type"],
                "group": source["group"],
                "collection": source["collection"],
                "author": source["author"],
                "source_work": source.get("work", ""),
                "title": spec.get("title") or source.get("work", ""),
                "source_url": spec["url"],
                "license_note": source.get("license_note", ""),
                "risk_note": source.get("risk_note", ""),
                "raw_text": raw_text,
            }
        )
        time.sleep(sleep)
    return entries, errors


def main() -> None:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Fetch Dao-Skill source corpus into raw JSON files.")
    parser.add_argument("--source", default="all", help="Source id to fetch, or 'all'.")
    parser.add_argument("--output", default=str(RAW_DIR), help="Raw output directory.")
    parser.add_argument("--limit-per-source", type=int, help="Debug limit per source.")
    args = parser.parse_args()

    config = load_sources()
    defaults = config.get("defaults", {})
    sources = [src for src in config.get("sources", []) if src.get("enabled", True)]
    if args.source != "all":
        sources = [src for src in sources if src["id"] == args.source]
    if not sources:
        raise SystemExit(f"No enabled source matched {args.source!r}")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    sess = session_for(defaults)
    manifest = {"sources": [], "source_errors": []}

    for source in sources:
        eprint(f"Fetching {source['id']}...")
        if source["type"] == "mia_index":
            entries, errors = fetch_mia_index(sess, source, defaults, args.limit_per_source)
        elif source["type"] == "wikisource_pages":
            entries, errors = fetch_wikisource_pages(sess, source, defaults, args.limit_per_source)
        elif source["type"] == "plain_text_urls":
            entries, errors = fetch_plain_text_urls(sess, source, defaults, args.limit_per_source)
        else:
            entries, errors = [], [f"unsupported source type: {source['type']}"]

        for item in entries:
            item["raw_id"] = sha1_text(item["source_id"], item["source_url"], item["raw_text"])
        write_json(output / f"{source['id']}.json", entries)
        manifest["sources"].append({"source_id": source["id"], "items": len(entries), "path": str(output / f"{source['id']}.json")})
        manifest["source_errors"].extend({"source_id": source["id"], "error": error} for error in errors)
        eprint(f"  wrote {len(entries)} entries, {len(errors)} errors")

    write_json(output / "manifest.json", manifest)


if __name__ == "__main__":
    main()
