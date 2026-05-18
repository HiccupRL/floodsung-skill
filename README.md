# Chinese Thought Corpus (Dao-Skill)

![Dao-Skill cover: ink-wash mountains, bamboo, circle, and seal marks](assets/dao-skill-cover.png)

> 知而不行，是为未知。

`dao-skill` 是一个面向中文思想材料的 Codex Skill。它把毛泽东著作、王阳明心学、曾国藩家书等材料整理成可检索、可引用、可对照阅读的本地语料库。

它的目标很简单：先找到原文，再解释语境，最后给出能落到行动上的判断。

## 材料范围

- **毛泽东著作 / 毛泽东选集**：实践、矛盾、调查研究、群众路线、实事求是。
- **王阳明 / 传习录**：知行合一、致良知、事上磨炼、心性工夫。
- **曾国藩家书及相关材料**：修身、立志、持恒、处事、交友。

## 能做什么

- 按主题检索原文。
- 对比不同思想传统中的相近概念。
- 生成读书笔记、研究备忘录、文章草稿。
- 回答现实问题时，给出“原文依据 + 解释 + 实践建议”。

## 快速检索

```bash
python scripts/retrieve.py "当 AI 能替人生成判断和方案时，知和行的关系如何变化？" --require-collections all --top-k 12
python scripts/search.py "知行合一" "事上磨炼" --collection wang_yangming
python scripts/search.py "实践" "调查研究" --collection maozedong
python scripts/search.py "修身" "有恒" --collection zeng_guofan
```

Windows / PowerShell 可用：

```powershell
powershell -ExecutionPolicy Bypass -File references/search_corpus.ps1 "实践" "调查研究" --collection maozedong
```

类 Unix 环境也可继续使用 `bash references/search_corpus.sh ...`。

## 语料构建

```bash
python scripts/fetch_corpus.py --source all --output data/raw
python scripts/build_corpus.py --input data/raw --output data/corpus
python scripts/validate_corpus.py --fail-on-noise
python scripts/build_indexes.py --corpus data/corpus/all.json
```

当前 curated corpus 生成 531 条：毛泽东 326、王阳明 10、曾国藩 195。raw HTML/缓存不提交，`data/corpus/`、`data/summary.json` 和 `references/*index.md` 可提交。

可选 embedding 重排：

```powershell
$env:DAO_SKILL_EMBED_MODEL="BAAI/bge-m3"
$env:DAO_SKILL_DISABLE_EMBEDDINGS="1"  # 强制只用本地 BM25/概念检索
```

## 目录结构

| 路径 | 作用 |
| --- | --- |
| `SKILL.md` | Skill 入口说明：材料范围、回答原则、引用要求。 |
| `data/corpus/` | 本地语料数据。 |
| `references/` | 来源索引、概念索引、摘录索引、混合检索流程、回答框架、AI/未来映射框架和检索脚本。 |
| `config/sources.yaml` | 语料来源白名单与许可说明。 |
| `scripts/` | 辅助脚本。 |

## 安装与更新

建议安装到 Codex 的 skills 目录：

```bash
SKILL_DIR="/root/.codex/skills/dao-skill"

if [ -d "$SKILL_DIR" ]; then
  cd "$SKILL_DIR" && git pull
else
  mkdir -p "$(dirname "$SKILL_DIR")"
  git clone https://github.com/HiccupRL/Dao-Skill.git "$SKILL_DIR"
fi
```

## 使用示例

- `$dao-skill 如何理解知行合一？`
- `$dao-skill 科研进展不顺时应该怎么调整？`
- `$dao-skill 对比《实践论》和“事上磨炼”的方法论。`

## 合规说明

- 仓库代码采用 MIT 许可证。
- 语料保留来源 URL、作者信息与许可备注。
- 使用语料时请遵守原始来源的版权与使用限制。
- 回答时应区分原文、解释和综合判断，不伪造出处。

## 致谢

感谢 [floodsung-skill](https://github.com/floodsung/floodsung-skill) 对 Skill 组织方式的启发。
