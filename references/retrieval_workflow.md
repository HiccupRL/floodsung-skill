# 混合检索流程

目标：把用户问题先映射为概念，再召回原文证据，避免只靠字面关键词。

## 1. 问题解析

先识别问题类型：

- 原文释义：定位单篇或单句。
- 三家比较：强制三家覆盖。
- 现实判断：需要原文证据、类比边界和行动建议。
- AI/未来问题：不得直接搜索“AI”作为原典依据，先映射到传统概念。

## 2. 概念映射

读取 `references/concept_graph.json`。当前核心概念包括：

- 实践验证
- 知行关系
- 治理与权力
- 风险与不确定性
- 修身与自我约束
- 学习与研究方法

现代词只作为触发器。例如“AI 决策”应优先映射到治理、权力、责任、实践检验；“长期不确定性”应优先映射到持久战、阶段判断、有恒、慎。

## 3. 召回顺序

推荐命令：

```bash
python scripts/retrieve.py "问题文本" --require-collections all --top-k 12
```

内部流程：

1. 用概念图扩展三家各自的检索词。
2. 用本地 BM25 和短语匹配召回候选。
3. 对每家保留最低候选覆盖。
4. 若安装了 `sentence-transformers` 且未禁用，则用 `DAO_SKILL_EMBED_MODEL` 做 embedding 重排。
5. 对全文备选源轻微降权，优先使用更精确的卷、篇、书信条目。
6. 输出作者、标题、作品、来源 URL 和片段。

## 4. 可选 embedding

默认无需外部模型即可工作。若本地安装：

```powershell
$env:DAO_SKILL_EMBED_MODEL="BAAI/bge-m3"
python scripts/retrieve.py "问题文本" --require-collections all
```

强制只用本地 BM25/概念检索：

```powershell
$env:DAO_SKILL_DISABLE_EMBEDDINGS="1"
```

模型和缓存应放入 `DAO_SKILL_CACHE_DIR` 或 `data/cache/`，不得提交模型文件。

## 5. 失败处理

- 若某家只召回目录、页眉或明显错归类内容，运行 `python scripts/validate_corpus.py --fail-on-noise`。
- 若某一概念召回薄弱，优先扩展 `references/concept_graph.json`，不要回退到机械关键词堆叠。
- 若 corpus 没有足够材料，回答中说明证据不足。
