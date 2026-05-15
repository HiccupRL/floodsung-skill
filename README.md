# dao-corpus-skill

一个 Dao skill，面向三类中文思想材料的语料检索、对照阅读、观点归纳与写作辅助：

1. 毛泽东选集 / 毛泽东著作
2. 王阳明心学 / 传习录
3. 曾国藩家书 / 书信材料

仓库采用 `SKILL.md + references/ + data/ + scripts/ + config/` 的组织方式，方便后续继续扩充 corpus、生成索引、在 Claude Code 中按原典回答问题。

## 目录结构

| 路径 | 作用 |
| --- | --- |
| `SKILL.md` | Skill 入口 prompt：触发条件、材料范围、回答原则、反模式 |
| `config/sources.yaml` | 可抓取来源 allowlist、许可说明、版权风险备注 |
| `scripts/scraper.py` | 主抓取脚本：从 Wikisource / Marxists Internet Archive 等公开来源抓取材料 |
| `scripts/build_references.py` | 从语料生成概念索引、来源索引、摘录索引和阅读流程 |
| `scripts/check_repo.py` | 检查仓库是否仍残留旧关键词、JSON 是否有效、关键文件是否存在 |
| `references/` | 自动或半自动生成的阅读索引 |
| `data/corpus/` | 抓取后的结构化语料；已提交一小批 seed corpus 方便先验证功能 |

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 快速验证

仓库已经包含一小批 seed corpus，可先直接测试：

```bash
bash references/search_corpus.sh "知行合一"
bash references/search_corpus.sh "调查"
bash references/search_corpus.sh "立志"
python scripts/build_references.py --data data/corpus --out references
python scripts/check_repo.py
```

## 抓取更多语料

```bash
python scripts/scraper.py \
  --config config/sources.yaml \
  --out data/corpus \
  --max-pages-per-source 200 \
  --sleep 0.8
```

脚本会生成：

- `data/corpus/all.json`
- `data/corpus/<collection>.json`
- `data/corpus/<collection>.md`
- `data/summary.json`

## 生成 references

```bash
python scripts/build_references.py --data data/corpus --out references
```

会生成或更新：

- `references/source_index.md`
- `references/core_concepts.md`
- `references/quote_index.md`
- `references/reading_workflow.md`
- `references/search_corpus.sh`

## 检查仓库

```bash
python scripts/check_repo.py
```

检查项包括：

- 必要文件是否存在
- `data/corpus/*.json` 是否可解析
- 语料条目是否有 `title/source_url/text/license_note`
- 是否残留旧关键词

## 版权与来源说明

本仓库的代码采用 MIT 许可证。抓取到的文本不统一改授权；每条语料保留其来源 URL、来源项目说明与许可备注。

- 古籍与公版材料优先使用开放来源。
- Marxists Internet Archive 自述为非营利公共图书馆，其内容免费，并标注为公共领域、GFDL 或经权利人许可；脚本仍会记录风险说明。
- seed corpus 主要用于功能验证；正式研究或公开分发前，请重新运行抓取脚本并核对具体版本、来源与许可。

## Claude Code 使用方式

```bash
mkdir -p ~/.claude/skills/chinese-thought-corpus
cp SKILL.md ~/.claude/skills/chinese-thought-corpus/
cp -r references ~/.claude/skills/chinese-thought-corpus/
```

之后可以问：

- 基于语料比较《实践论》和王阳明的知行合一。
- 给我做一份曾国藩家书里关于勤俭的主题笔记。
- 从毛泽东、王阳明、曾国藩三类材料里抽取一个关于行动力的方法论。

## 重要限制

这个仓库优先提供可复现的抓取与索引流程，而不是把版权不明的大体量文本直接塞进 Git。运行抓取脚本前，请确认你的使用场景、所在地法律和目标来源许可相容。特别感谢 https://github.com/floodsung/floodsung-skill 提供了详细的参考和启发。
