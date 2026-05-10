# V1 完整流程汇总

## 目标

跑通 V1 的手动闭环：

```text
Memory -> Sub-Agents -> Skills -> Knowledge
```

## 架构四要素

- Memory：`project/AGENTS.md`
- Sub-Agents：
  - `project/.opencode/agents/collector.md`
  - `project/.opencode/agents/analyzer.md`
  - `project/.opencode/agents/organizer.md`
- Skills：
  - `project/.opencode/skills/github-trending/SKILL.md`
  - `project/.opencode/skills/tech-summary/SKILL.md`
- Knowledge：
  - `project/knowledge/raw/`
  - `project/knowledge/articles/`
  - `project/knowledge/review_pending/`

## 本次运行

### 采集

- Agent：Collector
- Skill：github-trending
- 产出：`project/knowledge/raw/github-trending-2026-05-11.json`
- 条目数：10

### 分析

- Agent：Analyzer
- Skill：tech-summary
- 结果：为 10 条内容补充摘要、技术类别、创新点、使用难度、1-10 分评分、标签和状态。

### 整理

- Agent：Organizer
- 发布条目：9
- 待复核条目：1
- 发布目录：`project/knowledge/articles/`
- 待复核目录：`project/knowledge/review_pending/`

## 验证命令

```bash
python3 - <<'PY'
import glob
import json

files = glob.glob('project/knowledge/**/*.json', recursive=True)
for path in files:
    with open(path, encoding='utf-8') as handle:
        json.load(handle)
print(f'validated {len(files)} JSON files')
PY
```

当前验证结果：

```text
validated 13 JSON files
```

## 结论

V1 已经在 `project/` 中完成手动闭环。后续 V2 将把这套流程升级为自动化 pipeline，并引入 JSON 校验、质量评分、定时任务和成本统计。
