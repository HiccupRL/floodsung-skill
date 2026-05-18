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
        "傳": "传",
        "習": "习",
        "錄": "录",
        "陽": "阳",
        "國": "国",
        "藩": "藩",
        "書": "书",
        "劄": "札",
        "訓": "训",
        "實": "实",
        "踐": "践",
        "調": "调",
        "查": "查",
        "眾": "众",
        "為": "为",
        "爲": "为",
        "與": "与",
        "無": "无",
        "後": "后",
        "學": "学",
        "問": "问",
        "論": "论",
        "戰": "战",
        "爭": "争",
        "強": "强",
        "務": "务",
        "誠": "诚",
        "義": "义",
        "禮": "礼",
        "樂": "乐",
        "聖": "圣",
        "賢": "贤",
        "聞": "闻",
        "見": "见",
        "處": "处",
        "進": "进",
        "開": "开",
        "門": "门",
        "倫": "伦",
        "齊": "齐",
        "節": "节",
        "體": "体",
        "變": "变",
        "險": "险",
        "階": "阶",
        "應": "应",
        "觀": "观",
        "點": "点",
        "對": "对",
        "錯": "错",
        "說": "说",
        "時": "时",
        "將": "将",
        "導": "导",
        "術": "术",
        "權": "权",
        "決": "决",
        "斷": "断",
        "證": "证",
        "驗": "验",
        "內": "内",
        "邊": "边",
        "憂": "忧",
        "歸": "归",
        "復": "复",
        "雜": "杂",
        "偽": "伪",
        "發": "发",
        "從": "从",
        "獨": "独",
        "終": "终",
        "帶": "带",
        "軍": "军",
        "務": "务",
        "讓": "让",
        "滿": "满",
        "臨": "临",
        "檢": "检",
        "索": "索",
    }
)

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
    "跳至內容",
    "主選單",
    "个人工具",
    "檢視歷史",
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
    return normalise_space(value).translate(TRAD_TO_SIMP).lower()


def strip_markup(value: str | None) -> str:
    text = value or ""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return normalise_space(text)


def clean_text(value: str | None) -> str:
    text = strip_markup(value)
    text = re.sub(r"\*\*\*\s*START OF THE PROJECT GUTENBERG EBOOK.*?\*\*\*", " ", text, flags=re.I)
    text = re.sub(r"\*\*\*\s*END OF THE PROJECT GUTENBERG EBOOK.*", " ", text, flags=re.I)
    text = re.sub(r"Produced by .*?(?=傳習錄|传习录)", " ", text, flags=re.I)
    text = re.sub(r"Project Gutenberg[^。]*?(?=傳習錄|传习录)", " ", text, flags=re.I)
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
    text = re.sub(r"\[[编辑校对注释參考资料來源]+\]", "", text)
    text = re.sub(r"取自「https?://[^」]+」", "", text)
    text = re.sub(r"此頁面最後編輯於.*", "", text)
    return normalise_space(text)


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
    if collection == "wang_yangming":
        if title.startswith("傳習錄（") or title.startswith("传习录（"):
            return "傳習錄", "全文备选"
        if title.startswith("傳習錄/") or title.startswith("传习录/"):
            return "傳習錄", title.split("/", 1)[1]
        if title == "傳習錄" or title == "传习录":
            return "傳習錄", ""
        return title.split("/", 1)[0], title.split("/", 1)[1] if "/" in title else ""
    if collection == "zeng_guofan":
        for prefix in ("曾文正公家書", "曾文正公書劄", "曾文正公家訓"):
            if title.startswith(prefix):
                return prefix, title[len(prefix) :].lstrip("/")
        return source_work or "曾文正公全集", title
    if collection == "maozedong":
        return source_work or "中文马克思主义文库·毛泽东", title
    return source_work, ""


def quality_flags(item: dict, source: dict | None = None) -> list[str]:
    flags = []
    title = normalise_space(item.get("title"))
    text = normalise_space(item.get("text_clean") or item.get("text") or item.get("raw_text"))
    combined = f"{title}\n{text}"

    if len(text) < 80:
        flags.append("too_short")
    if title in {"全部导航", "视觉焦点", "最热文章", "相关阅读", "推荐阅读"}:
        flags.append("navigation_title")
    marker_count = sum(1 for marker in NOISE_TEXT_MARKERS if marker in combined)
    if marker_count >= 2:
        flags.append("navigation_text")

    if source:
        if first_match(source.get("title_exclude_patterns"), title):
            flags.append("title_excluded")
        required = source.get("title_required_patterns") or []
        if required and not any_pattern(required, title):
            flags.append("title_required_missing")

    collection = item.get("collection")
    if collection == "wang_yangming" and re.search(
        r"孙子兵法|孫子兵法|格言联璧|格言聯璧|始计篇|始計篇|作战篇|作戰篇|军形篇|軍形篇|兵势篇|兵勢篇|虚实篇|虛實篇|军争篇|軍爭篇|九变篇|九變篇|行军篇|行軍篇|地形篇|九地篇|火攻篇|用间篇|用間篇",
        title,
    ):
        flags.append("known_wang_pollution")
    if collection == "zeng_guofan" and re.search(r"西厢记|西廂記|第[一二三四五六七八九十百零〇]+回|第[一二三四五六七八九十百零〇]+本|折$", title):
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
