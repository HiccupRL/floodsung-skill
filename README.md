# Dao-Skill

![Dao-Skill cover: ink-wash landscape with field notes, bamboo, letters, concept graph, and scholar desk](assets/dao-skill-cover.png)

`dao-skill` 是一个中文思想原文检索与解释 Skill。核心目标：读原文，正本清源，少讲空话。

所有中文语料与回答输出统一使用简体字；繁体来源在构建 corpus 时转为简体，正文不输出繁体。

材料只围绕三家：

- 毛泽东：实践、调查、矛盾、群众、组织与阶段判断。
- 王阳明：知行合一、致良知、格物、事上磨炼。
- 曾国藩：修身、有恒、勤慎、戒傲惰、用人与处事。

## 回答规则

默认只用三段：

1. **原文依据**：不少于 7 条原文，尽量原原本本引用；出处写“作者《篇名》章节/条目”，不在正文贴网页链接。
2. **现实含义**：紧扣原文解释含义，少用大白话重述，不把后人的概括当原话。
3. **行动建议**：把原文推到当下问题，给出少而准、可执行的判断。

## 检索

```bash
python scripts/retrieve.py "当 AI 能替人生成判断和方案时，知和行的关系如何变化？" --require-collections all --top-k 12
python scripts/search.py 知行合一 良知 --collection wang_yangming --limit 5
python scripts/search.py 实践 调查 --collection maozedong --limit 5
python scripts/search.py 自强 戒傲 勤 --collection zeng_guofan --limit 5
```

Windows / PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File references/search_corpus.ps1 实践 调查 --collection maozedong
```

## 语料维护

```bash
python scripts/fetch_corpus.py --source all --output data/raw
python scripts/build_corpus.py --input data/raw --output data/corpus
python scripts/validate_corpus.py --fail-on-noise
python scripts/build_indexes.py --corpus data/corpus/all.json
```

当前 curated corpus：毛泽东 326 条，王阳明 10 条，曾国藩 195 条。URL 保留在 corpus 中用于追溯和许可核验；回答正文只写篇章出处。

## 主要文件

| 路径 | 作用 |
| --- | --- |
| `SKILL.md` | Skill 的核心规则。 |
| `data/corpus/` | 清洗后的结构化语料。 |
| `references/concept_graph.json` | 概念映射。 |
| `references/answer_framework.md` | 三段式回答规范。 |
| `scripts/retrieve.py` | 概念映射 + BM25/短语召回。 |
| `scripts/search.py` | 兼容关键词检索。 |

## 许可

代码采用 MIT 许可证。语料来自公开来源，保留原始 URL、许可说明和风险备注；使用时应遵守原始来源限制。
