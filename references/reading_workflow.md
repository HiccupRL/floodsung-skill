# 阅读与回答流程

## 1. 明确问题类型

- 原文释义：先定位单一文本，再解释词句。
- 主题综述：先按关键词查多篇，再按材料组归纳。
- 三家比较：分别抽取毛泽东、王阳明、曾国藩材料，再比较问题意识、方法论和局限。
- 写作辅助：先列原典证据，再写现代转化，不要先写观点后补材料。

## 2. 检索命令

```bash
python scripts/retrieve.py "现实问题或比较问题" --require-collections all --top-k 12
python scripts/search.py "实践" "调查" --collection maozedong
python scripts/search.py "知行合一" "良知" --collection wang_yangming
python scripts/search.py "自强" "戒傲" "勤" --collection zeng_guofan
```

Windows / PowerShell 可用 `powershell -ExecutionPolicy Bypass -File references/search_corpus.ps1 ...`；类 Unix 环境可用 `bash references/search_corpus.sh ...`。

现实问题优先使用 `retrieve.py`，因为它会执行“概念映射 + BM25/短语召回 + 三家覆盖约束”。`search.py` 保留给明确关键词或单家材料定位。

## 3. 回答模板

1. 结论先行：一句话回答用户问题。
2. 原文依据：列出 2-5 条来源和短摘录。
3. 语境解释：说明原文在解决什么问题。
4. 跨文本比较：只比较可比维度，避免强行统一。
5. 现代转化：给出可操作启发，并说明局限。
6. 反例与边界：说明何时该判断不成立。

## 4. 引用要求

- 每次引用都标注标题、作者、来源 URL。
- 不确定版本时写明“当前 corpus 版本”。
- 对现代整理本、译注、选编本保持版权谨慎。
