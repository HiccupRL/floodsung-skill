---
name: dao-skill
description: |
  面向毛泽东著作、王阳明心学、曾国藩家书三类中文思想材料的检索、引证、比较分析与现实问题推理 skill。适用于原文定位、三家比较、读书笔记、研究备忘录、文章草稿，以及把 AI/未来/组织治理等现代问题映射到三家材料中进行有边界的类比分析。
---

# Dao-Skill

本 skill 的目标不是模仿人格，而是基于可追溯 corpus 做严谨回答：先检索原文，再解释语境，最后给出现实判断。

## 材料边界

- 毛泽东：MIA 中文毛泽东著作入口抓取的 curated corpus，重点用于实践检验、调查研究、矛盾分析、群众路线、持久战与组织问题。
- 王阳明：Wikisource《傳習錄》及明确作者页作品，Project Gutenberg《傳習錄》仅作备选全文来源，重点用于知行合一、致良知、格物、事上磨炼。
- 曾国藩：Wikisource 入口优先；当前可用主体为古诗文网备选家书条目，重点用于有恒、自强、戒傲惰、勤、慎、用人和处事。

不得新增外部 AI 理论文献来冒充本 skill 的原典依据。AI 与未来只作为现代问题场景。

## 必须使用的流程

回答现实问题或比较问题前，先运行混合检索：

```bash
python scripts/retrieve.py "用户问题" --require-collections all --top-k 12
```

若用户只指定某一家，可用兼容搜索：

```bash
python scripts/search.py 实践 调查 --collection maozedong --limit 5
python scripts/search.py 知行合一 良知 --collection wang_yangming --limit 5
python scripts/search.py 自强 戒傲 勤 --collection zeng_guofan --limit 5
```

Windows 可用：

```powershell
powershell -ExecutionPolicy Bypass -File references/search_corpus.ps1 实践 调查 --collection maozedong
```

详细检索规则见 `references/retrieval_workflow.md`。

## 回答结构

除非用户明确要求短答，否则按以下顺序组织：

1. 定义问题：对象、变量、优化目标、约束。
2. 原文依据：三家各至少一条可追溯材料，标注作者、标题、URL。
3. 语境解释：说明原文原本处理的历史或修身问题。
4. 类比/推论：说明迁移到现代问题时迁移了什么结构。
5. 反例/边界：说明何时判断失效。
6. 行动判断：给出可执行建议或下一步验证。

详细模板见 `references/answer_framework.md`。

## AI 与未来问题

遇到 AI、自动化决策、未来不确定性、技术治理、组织智能等问题，先读 `references/ai_future_reasoning.md`。这类回答必须显式区分：

- 原文事实：原典实际说了什么。
- 现代映射：把哪一种结构迁移到 AI 场景。
- 不可迁移处：哪些历史条件、政治语境或修身语境不能直接套用。

不得搜索“AI”本身作为原典依据；应先映射到实践验证、知行关系、治理权力、风险不确定性、有恒自强等概念。

## 引用纪律

- 不伪造原文、作者、标题或 URL。
- 每条引用必须能从 `data/corpus/all.json` 或来源 URL 追溯。
- 不把解释性概括写成作者原话。
- 不把毛泽东、王阳明、曾国藩强行说成同一体系。
- 如果 corpus 证据不足，直接说明不足，并给出应补抓的来源或概念。

## 质量自检

提交回答前检查：

- 是否覆盖用户要求的材料范围；默认三家覆盖。
- 是否有至少一条反例或失效边界。
- 是否给出因果链，而不是堆金句。
- 是否给出可执行判断。
- AI/未来问题是否明确标注“类比/推论”。
