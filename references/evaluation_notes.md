# 五轮迭代记录

本记录用于说明本次增强的验证路径，不替代自动测试。

## 第 1 轮：语料重建

- 远端 `origin/main` 已同步，结果为 already up to date。
- 重新抓取 raw：MIA 毛泽东、Wikisource 王阳明、Project Gutenberg《傳習錄》备选、古诗文网曾国藩家书备选。
- 重建 curated corpus：总计 531 条，毛泽东 326、王阳明 10、曾国藩 195。
- `python scripts/validate_corpus.py --fail-on-noise` 通过。

## 第 2 轮：污染清洗

- 过滤毛泽东“全部导航”等页面噪声。
- 过滤王阳明《孙子兵法》《格言联璧》等错归类项。
- 过滤曾国藩小说回目、西厢记类污染。
- 清理 Project Gutenberg 页眉、古诗文网页头页脚、MIA 编者按干扰。

## 第 3 轮：检索升级

- 新增 `references/concept_graph.json`。
- 新增 `scripts/retrieve.py`：概念映射、BM25/短语召回、三家覆盖、可选 embedding 重排。
- `scripts/search.py` 保留兼容入口，并支持 `--collection`、`--hybrid`、UTF-8 输出。
- `references/search_corpus.ps1` 在 PowerShell 下可用。

## 第 4 轮：AI/未来压力题

已运行：

```bash
python scripts/retrieve.py "当 AI 能替人生成判断和方案时，知和行的关系如何变化？" --require-collections all --top-k 12
python scripts/retrieve.py "AI 决策会提升治理能力还是形成技术官僚主义？" --require-collections all --top-k 12
python scripts/retrieve.py "通用 AI 长期不确定性下应追求速度、控风险还是等待？" --require-collections all --top-k 12
```

三题均能覆盖毛泽东、王阳明、曾国藩，并输出作者、标题、URL、片段。当前 embedding 未安装，结果来自本地混合检索。

## 第 5 轮：Skill 逻辑回改

- `SKILL.md` 精简为入口规则。
- 新增 `references/retrieval_workflow.md` 和 `references/answer_framework.md`。
- 更新 `references/ai_future_reasoning.md`，明确 AI/未来问题只作类比/推论。
- `README.md` 更新语料构建、检索、验证和可选 embedding 环境变量。

## 剩余边界

- 曾国藩高质量全集级 Wikisource 子页不足，当前主力为古诗文网备选家书条目，已在 source risk note 中标注。
- 王阳明 Wikisource 有若干页面缺失或 rate limit，本次以《傳習錄》三卷和若干明确作品为主，Project Gutenberg 作为全文备选。
- 若要进一步提高语义重排质量，可本地安装 `sentence-transformers` 并设置 `DAO_SKILL_EMBED_MODEL=BAAI/bge-m3`。
