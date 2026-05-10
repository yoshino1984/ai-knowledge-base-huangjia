# Issue 01 - Collector Agent

## 目标

采集 AI/LLM/Agent 相关候选内容，并输出 raw JSON。

## depends_on

- `project/AGENTS.md`
- `project/specs/project-vision.md`
- `project/specs/agents-prd.md`

## 输入

- 数据源配置或任务提示。
- 采集规模：V1 GitHub 15 条、HN 10 条、RSS 10 条；当前测试可使用 GitHub Top 10。

## 输出

- `project/knowledge/raw/{source}-{YYYY-MM-DD}.json`

## schema

参考 `project/specs/schemas/raw_collection.schema.json`。

## acceptance

- [ ] 输出是合法 JSON。
- [ ] 顶层包含 `source`、`collected_at`、`items`。
- [ ] 每条 item 包含 `title`、`url`、`source`、`description` 或 `summary`。
- [ ] 所有 `url` 来自真实来源。
- [ ] 不直接写入 `knowledge/articles/`。
- [ ] 失败时记录原因，不编造数据。

## 权限契约

- 允许：Read、Grep、Glob、WebFetch。
- 禁止：Write、Edit、Bash。
- 落盘由主流程负责，不由 collector 直接执行。
