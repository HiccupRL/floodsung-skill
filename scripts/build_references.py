#!/usr/bin/env python3
"""Build reference files from data/corpus/all.json."""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

THEMES: dict[str, list[str]] = {
    "实践与行动": ["实践", "實踐", "行动", "行", "事上磨炼", "知行合一", "调查", "研究"],
    "矛盾与变局": ["矛盾", "主要矛盾", "斗争", "变化", "變化", "形势", "形勢"],
    "心性与良知": ["心即理", "良知", "致良知", "天理", "私欲", "慎独", "存养", "省察"],
    "修身与家训": ["修身", "立志", "勤", "俭", "儉", "家", "读书", "讀書", "戒", "恒"],
    "组织与治事": ["组织", "組織", "群众", "群眾", "路线", "干部", "治军", "用人", "居官"],
    "战略与长期主义": ["持久", "战略", "戰略", "统一战线", "統一戰線", "大局", "谋", "謀"],
}


def load_items(data_dir: Path) -> list[dict[str, Any]]:
    path = data_dir / "all.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def excerpt(text: str, max_len: int = 260) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] + ("…" if len(text) > max_len else "")


def find_windows(text: str, keywords: list[str], max_windows: int = 3) -> list[str]:
    windows: list[str] = []
    for kw in keywords:
        for m in re.finditer(re.escape(kw), text):
            start = max(0, m.start() - 90)
            end = min(len(text), m.end() + 160)
            w = excerpt(text[start:end])
            if w and w not in windows:
                windows.append(w)
            if len(windows) >= max_windows:
                return windows
    return windows


def write_source_index(items: list[dict[str, Any]], out_dir: Path) -> None:
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_group[item.get("group") or item.get("collection") or "未分组"].append(item)
    lines = ["# 来源索引\n", "按材料组列出当前 corpus 条目。每条保留来源 URL 与许可备注。\n"]
    if not items:
        lines.append("\n当前 `data/corpus/all.json` 不存在或为空。请先运行 `scripts/scraper.py`。\n")
    for group, records in sorted(by_group.items()):
        lines.append(f"\n## {group} ({len(records)})\n")
        for item in sorted(records, key=lambda x: x.get("title", "")):
            lines.append(f"- [{item.get('title','Untitled')}]({item.get('source_url','')}) — {item.get('author','')} · `{item.get('source_id','')}`")
    (out_dir / "source_index.md").write_text("\n".join(lines), encoding="utf-8")


def write_core_concepts(items: list[dict[str, Any]], out_dir: Path) -> None:
    lines = ["# 核心概念索引\n", "由脚本按关键词从 corpus 中抽取。只作阅读入口，不替代原文判断。\n"]
    if not items:
        lines.append("\n当前没有语料。运行抓取脚本后重新生成本文件。\n")
    for theme, keywords in THEMES.items():
        hits: list[tuple[str, str, str, str]] = []
        for item in items:
            text = item.get("text", "")
            haystack = item.get("title", "") + "\n" + text
            if any(kw in haystack for kw in keywords):
                win = find_windows(text, keywords, max_windows=1)
                hits.append((item.get("title", ""), item.get("source_url", ""), item.get("group", ""), win[0] if win else ""))
        lines.append(f"\n## {theme} ({len(hits)})\n")
        for title, url, group, win in hits[:30]:
            lines.append(f"- **{group}** [{title}]({url})")
            if win:
                lines.append(f"  - 摘录：{win}")
    (out_dir / "core_concepts.md").write_text("\n".join(lines), encoding="utf-8")


def write_quote_index(items: list[dict[str, Any]], out_dir: Path) -> None:
    lines = ["# 代表性短摘录索引\n", "短摘录用于定位原文；正式引用前请回到 source_url 核对上下文。\n"]
    if not items:
        lines.append("\n当前没有语料。\n")
    for item in items[:200]:
        text = item.get("text", "")
        paras = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) >= 40]
        q = excerpt(paras[0] if paras else text, 220)
        if not q:
            continue
        lines.append(f"\n## {item.get('title', 'Untitled')}\n")
        lines.append(f"- group: {item.get('group', '')}")
        lines.append(f"- source: {item.get('source_url', '')}")
        lines.append(f"- excerpt: {q}")
    (out_dir / "quote_index.md").write_text("\n".join(lines), encoding="utf-8")


def write_reading_workflow(out_dir: Path) -> None:
    content = """# 阅读与回答流程

## 1. 明确问题类型

- 原文释义：先定位单一文本，再解释词句。
- 主题综述：先按关键词查多篇，再按材料组归纳。
- 三家比较：分别抽取毛泽东、王阳明、曾国藩材料，再比较问题意识、方法论和局限。
- 写作辅助：先列原典证据，再写现代转化，不要先写观点后补材料。

## 2. 检索命令

```bash
bash references/search_corpus.sh "实践"
bash references/search_corpus.sh "知行合一"
bash references/search_corpus.sh "勤俭"
```

## 3. 回答模板

1. 结论先行：一句话回答用户问题。
2. 原文依据：列出 2-5 条来源和短摘录。
3. 语境解释：说明原文在解决什么问题。
4. 跨文本比较：只比较可比维度，避免强行统一。
5. 现代转化：给出可操作启发，并说明局限。

## 4. 引用要求

- 每次引用都标注标题、作者、来源 URL。
- 不确定版本时写明“当前 corpus 版本”。
- 对现代整理本、译注、选编本保持版权谨慎。
"""
    (out_dir / "reading_workflow.md").write_text(content, encoding="utf-8")


def write_search_helper(out_dir: Path) -> None:
    script = """#!/usr/bin/env bash
# Search generated corpus markdown. Usage: bash references/search_corpus.sh "关键词"
set -euo pipefail
KEYWORD="${1:?need keyword}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if ! compgen -G "data/corpus/*.md" > /dev/null; then
  echo "No corpus markdown found. Run: python scripts/scraper.py --config config/sources.yaml --out data/corpus" >&2
  exit 1
fi
grep -Rni --color=never "$KEYWORD" data/corpus/*.md | head -120 || true
"""
    p = out_dir / "search_corpus.sh"
    p.write_text(script, encoding="utf-8")
    p.chmod(0o755)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/corpus", type=Path)
    ap.add_argument("--out", default="references", type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    items = load_items(args.data)
    write_source_index(items, args.out)
    write_core_concepts(items, args.out)
    write_quote_index(items, args.out)
    write_reading_workflow(args.out)
    write_search_helper(args.out)
    print(f"wrote references to {args.out} from {len(items)} corpus items")


if __name__ == "__main__":
    main()
