#!/usr/bin/env python3
"""Shared corpus utilities for Dao-Skill scripts."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
RAW_DIR = DATA_DIR / "raw"
INDEX_DIR = DATA_DIR / "index"
REFERENCES_DIR = ROOT / "references"
SOURCES_FILE = ROOT / "config" / "sources.yaml"
ALL_CORPUS_FILE = CORPUS_DIR / "all.json"
CONCEPT_GRAPH_FILE = REFERENCES_DIR / "concept_graph.json"

COLLECTIONS = ("maozedong", "wang_yangming", "zeng_guofan")
COLLECTION_LABELS = {
    "maozedong": "毛泽东著作",
    "wang_yangming": "王阳明心学",
    "zeng_guofan": "曾国藩家书",
}

TRAD_TO_SIMP = str.maketrans(
    {
        "\u50b3": "传",
        "\u7fd2": "习",
        "\u9304": "录",
        "\u967d": "阳",
        "\u570b": "国",
        "藩": "藩",
        "\u66f8": "书",
        "\u5284": "札",
        "\u8a13": "训",
        "\u5be6": "实",
        "\u8e10": "践",
        "\u8abf": "调",
        "查": "查",
        "\u773e": "众",
        "\u70ba": "为",
        "\u7232": "为",
        "\u8207": "与",
        "\u7121": "无",
        "\u5f8c": "后",
        "\u5b78": "学",
        "\u554f": "问",
        "\u8ad6": "论",
        "\u6230": "战",
        "\u722d": "争",
        "\u5f37": "强",
        "\u52d9": "务",
        "\u8aa0": "诚",
        "\u7fa9": "义",
        "\u79ae": "礼",
        "\u6a02": "乐",
        "\u8056": "圣",
        "\u8ce2": "贤",
        "\u805e": "闻",
        "\u898b": "见",
        "\u8655": "处",
        "\u9032": "进",
        "\u958b": "开",
        "\u9580": "门",
        "\u502b": "伦",
        "\u9f4a": "齐",
        "\u7bc0": "节",
        "\u9ad4": "体",
        "\u8b8a": "变",
        "\u96aa": "险",
        "\u968e": "阶",
        "\u61c9": "应",
        "\u89c0": "观",
        "\u9ede": "点",
        "\u5c0d": "对",
        "\u932f": "错",
        "\u8aaa": "说",
        "\u6642": "时",
        "\u5c07": "将",
        "\u5c0e": "导",
        "\u8853": "术",
        "\u6b0a": "权",
        "\u6c7a": "决",
        "\u65b7": "断",
        "\u8b49": "证",
        "\u9a57": "验",
        "\u5167": "内",
        "\u908a": "边",
        "\u6182": "忧",
        "\u6b78": "归",
        "\u5fa9": "复",
        "\u96dc": "杂",
        "\u507d": "伪",
        "\u767c": "发",
        "\u5f9e": "从",
        "\u7368": "独",
        "\u7d42": "终",
        "\u5e36": "带",
        "\u8ecd": "军",
        "\u52d9": "务",
        "\u8b93": "让",
        "\u6eff": "满",
        "\u81e8": "临",
        "\u6aa2": "检",
        "索": "索",
    }
)

_OPENCC = None
_OPENCC_READY = False


def to_simplified(value: str | None) -> str:
    global _OPENCC, _OPENCC_READY
    text = value or ""
    if not _OPENCC_READY:
        _OPENCC_READY = True
        try:
            from opencc import OpenCC

            _OPENCC = OpenCC("t2s")
        except Exception:
            _OPENCC = None
    if _OPENCC is not None:
        return _OPENCC.convert(text)
    return text.translate(TRAD_TO_SIMP)

NOISE_TEXT_MARKERS = (
    "全部导航",
    "点击右上角",
    "微信好友",
    "朋友圈",
    "阅读剩余全文",
    "您此时的心情",
    "新闻表情排行",
    "光明网版权所有",
    "正在阅读：",
    "跳至内容",
    "主选单",
    "个人工具",
    "检视历史",
    "隐私政策",
)


def eprint(*args):
    print(*args, file=sys.stderr)


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def read_json(path: Path, default=None):
    if not path.exists():
        return [] if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_sources():
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML is required. Install requirements.txt first.") from exc
    return yaml.safe_load(SOURCES_FILE.read_text(encoding="utf-8"))


def normalise_space(value: str | None) -> str:
    value = value or ""
    value = value.replace("\u3000", " ")
    return re.sub(r"\s+", " ", value).strip()


def normalise_for_search(value: str | None) -> str:
    return to_simplified(normalise_space(value)).lower()


def strip_markup(value: str | None) -> str:
    text = value or ""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return to_simplified(normalise_space(text))


def clean_text(value: str | None) -> str:
    text = strip_markup(value)
    text = re.sub(r"\*\*\*\s*START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*", " ", text, flags=re.I)
    text = re.sub(r"\*\*\*\s*END OF THE PROJECT GUTENBERG EBOOK.*", " ", text, flags=re.I)
    text = re.sub(r"Produced by .*?(?=传习录)", " ", text, flags=re.I)
    text = re.sub(r"Project Gutenberg[^。]*?(?=传习录)", " ", text, flags=re.I)
    text = text.replace("_古文岛_原古诗文网", " ")
    text = text.replace("中文马克思主义文库 -> 毛泽东", " ")
    text = re.sub(r"古文岛 推荐 诗文 名句 古籍 作者 字词 APP 登录.*?您的浏览器不支持 audio 元素。", " ", text)
    text = re.sub(r"播放列表.*?您的浏览器不支持 audio 元素。", " ", text)
    text = re.sub(r"上一章\s+目录\s+下一章\s+完善\s+©.*", " ", text)
    text = re.sub(r"©\s*\d{4}\s+古诗文网.*", " ", text)
    text = re.sub(r"【编者按：.*?】", " ", text)
    text = re.sub(r"毛选[一二三四五六七八九十]+卷删改版：", " ", text)
    text = re.sub(r"^APP\s*\[\s*登录\s*\]\([^)]*\)\s*\d+\s*#\s*\*\*[^*]+\*\*\s*", "", text)
    text = re.sub(r"\s+完善\s*$", "", text)
    text = re.sub(r"\[[编辑校对注释参考资料来源]+\]", "", text)
    text = re.sub(r"取自「https?://[^」]+」", "", text)
    text = re.sub(r"此页面最后编辑于.*", "", text)
    return to_simplified(normalise_space(text))


def sha1_text(*parts: str, length: int = 16) -> str:
    digest = hashlib.sha1()
    for part in parts:
        digest.update((part or "").encode("utf-8", errors="ignore"))
        digest.update(b"\0")
    return digest.hexdigest()[:length]


def checksum(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def compile_patterns(patterns: Iterable[str] | None):
    return [re.compile(pattern) for pattern in patterns or []]


def any_pattern(patterns: Iterable[str] | None, text: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns or [])


def first_match(patterns: Iterable[str] | None, text: str) -> str | None:
    for pattern in patterns or []:
        if re.search(pattern, text):
            return pattern
    return None


def derive_work(collection: str, title: str, source_work: str = "") -> tuple[str, str]:
    title = to_simplified(normalise_space(title))
    source_work = to_simplified(source_work)
    if collection == "wang_yangming":
        if title.startswith("传习录（"):
            return "传习录", "全文备选"
        if title.startswith("传习录/"):
            return "传习录", title.split("/", 1)[1]
        if title == "传习录":
            return "传习录", ""
        return title.split("/", 1)[0], title.split("/", 1)[1] if "/" in title else ""
    if collection == "zeng_guofan":
        for prefix in ("曾文正公家书", "曾文正公书札", "曾文正公家训"):
            if title.startswith(prefix):
                return prefix, title[len(prefix) :].lstrip("/")
        return source_work or "曾文正公全集", title
    if collection == "maozedong":
        return source_work or "中文马克思主义文库·毛泽东", title
    return source_work, ""


def quality_flags(item: dict, source: dict | None = None) -> list[str]:
    flags = []
    title = to_simplified(normalise_space(item.get("title")))
    text = to_simplified(normalise_space(item.get("text_clean") or item.get("text") or item.get("raw_text")))
    combined = f"{title}\n{text}"

    if len(text) < 80:
        flags.append("too_short")
    if title in {"全部导航", "视觉焦点", "最热文章", "相关阅读", "推荐阅读"}:
        flags.append("navigation_title")
    marker_count = sum(1 for marker in NOISE_TEXT_MARKERS if marker in combined)
    if marker_count >= 2:
        flags.append("navigation_text")

    if source:
        title_exclude = source.get("title_exclude_patterns") or []
        title_exclude = list(title_exclude) + [to_simplified(pattern) for pattern in title_exclude]
        if first_match(title_exclude, title):
            flags.append("title_excluded")
        required = source.get("title_required_patterns") or []
        required = list(required) + [to_simplified(pattern) for pattern in required]
        if required and not any_pattern(required, title):
            flags.append("title_required_missing")

    collection = item.get("collection")
    if collection == "wang_yangming" and re.search(
        r"孙子兵法|格言联璧|始计篇|作战篇|军形篇|兵势篇|虚实篇|军争篇|九变篇|行军篇|地形篇|九地篇|火攻篇|用间篇",
        title,
    ):
        flags.append("known_wang_pollution")
    if collection == "zeng_guofan" and re.search(r"西厢记|第[一二三四五六七八九十百零〇]+回|第[一二三四五六七八九十百零〇]+本|折$", title):
        flags.append("known_zeng_pollution")
    if collection == "maozedong" and "全部导航" in combined:
        flags.append("known_mao_navigation")
    return sorted(set(flags))


def load_corpus(path: Path = ALL_CORPUS_FILE) -> list[dict]:
    return read_json(path, default=[])


def cjk_ngrams(text: str, min_n: int = 2, max_n: int = 3) -> list[str]:
    chars = re.findall(r"[\u4e00-\u9fff]", normalise_for_search(text))
    grams = []
    for n in range(min_n, max_n + 1):
        grams.extend("".join(chars[i : i + n]) for i in range(0, max(0, len(chars) - n + 1)))
    return grams


def tokenize(text: str) -> list[str]:
    norm = normalise_for_search(text)
    words = re.findall(r"[a-z0-9_]+", norm)
    cjk = cjk_ngrams(norm)
    return words + cjk


def make_snippet(text: str, terms: Iterable[str], before: int = 120, after: int = 300) -> str:
    raw = clean_text(text)
    raw_norm = normalise_for_search(raw)
    for term in sorted({t for t in terms if t}, key=lambda value: (len(normalise_for_search(value)), value), reverse=True):
        norm = normalise_for_search(term)
        if len(norm) < 2:
            continue
        idx = raw_norm.find(norm)
        if idx >= 0:
            start = max(0, idx - before)
            end = min(len(raw), idx + len(term) + after)
            return f"...{raw[start:end]}..."
    best_idx = -1
    for term in sorted({t for t in terms if t}, key=len, reverse=True):
        idx = raw_norm.find(normalise_for_search(term))
        if idx >= 0 and (best_idx < 0 or idx < best_idx):
            best_idx = idx
    if best_idx < 0:
        return f"...{raw[: before + after]}..."
    start = max(0, best_idx - before)
    end = min(len(raw), best_idx + after)
    return f"...{raw[start:end]}..."


class BM25:
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.doc_freq = Counter()
        self.term_freqs = []
        self.doc_lens = []
        for tokens in documents:
            counts = Counter(tokens)
            self.term_freqs.append(counts)
            self.doc_lens.append(len(tokens))
            self.doc_freq.update(counts.keys())
        self.n_docs = len(documents)
        self.avgdl = sum(self.doc_lens) / self.n_docs if self.n_docs else 0.0

    def idf(self, term: str) -> float:
        df = self.doc_freq.get(term, 0)
        return math.log(1 + ((self.n_docs - df + 0.5) / (df + 0.5)))

    def scores(self, query_tokens: Iterable[str]) -> list[float]:
        query = list(dict.fromkeys(query_tokens))
        scores = [0.0] * self.n_docs
        if not query or not self.n_docs:
            return scores
        for i, counts in enumerate(self.term_freqs):
            dl = self.doc_lens[i] or 1
            denom_const = self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            score = 0.0
            for term in query:
                tf = counts.get(term, 0)
                if not tf:
                    continue
                score += self.idf(term) * ((tf * (self.k1 + 1)) / (tf + denom_const))
            scores[i] = score
        return scores


def group_by_collection(items: Iterable[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for item in items:
        grouped[item.get("collection", "")].append(item)
    return dict(grouped)


MAO_URL_ARTICLES = {
    "193612": "中国革命战争的战略问题",
    "193707": "实践论",
    "193708": "矛盾论",
    "193805b": "论持久战",
    "193805": "抗日游击战争的战略问题",
    "19381012aa": "中国共产党在民族战争中的地位",
    "19410519": "改造我们的学习",
    "19420201": "整顿党的作风",
    "194205": "在延安文艺座谈会上的讲话",
    "19440412": "学习和时局",
    "19450424": "论联合政府",
    "19450424aa": "论联合政府",
    "19560425": "论十大关系",
    "19570227": "关于正确处理人民内部矛盾的问题",
    "19570227AA": "关于正确处理人民内部矛盾的问题（讲话稿）",
}


def mao_article_from_url(source_url: str) -> str:
    for marker, article in sorted(MAO_URL_ARTICLES.items(), key=lambda pair: len(pair[0]), reverse=True):
        if marker in source_url:
            return article
    return ""


def citation_label(item: dict) -> str:
    author = to_simplified(normalise_space(item.get("author")))
    collection = item.get("collection", "")
    work = to_simplified(normalise_space(item.get("work")))
    title = to_simplified(normalise_space(item.get("title")))
    section = to_simplified(normalise_space(item.get("section")))

    if collection == "wang_yangming":
        if title.startswith("传习录/"):
            section = section or title.split("/", 1)[1]
            return f"{author}《传习录》{section}"
        if title.startswith("传习录（"):
            return f"{author}《传习录》全文备选"
        return f"{author}《{title or work}》"

    if collection == "zeng_guofan":
        base = "曾国藩家书" if "家书" in work else work or "曾国藩家书"
        return f"{author}《{base}》{section or title}"

    if collection == "maozedong":
        article = mao_article_from_url(item.get("source_url", ""))
        if article and title and article not in title:
            return f"{author}《{article}》{title}"
        return f"{author}《{title or article or work}》"

    if section:
        return f"{author}《{work or title}》{section}"
    return f"{author}《{title or work}》"
