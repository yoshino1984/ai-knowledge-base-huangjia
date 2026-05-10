# Issue 03 - Organizer Agent

## 目标

读取分析后的数据，去重、过滤并归档成标准知识条目。

## depends_on

- `project/specs/issues/02-analyzer.md`
- 已分析的 raw JSON 或分析结果。

## 输入

- 带 `summary`、`analysis`、`tags`、`status` 的候选条目。

## 输出

- `project/knowledge/articles/*.json`
- `project/knowledge/articles/index.json`
- `project/knowledge/review_pending/*.json`
- `project/knowledge/review_pending/index.json`

## schema

参考 `project/specs/schemas/knowledge_article.schema.json`。

## acceptance

- [ ] 发布条目符合知识条目 JSON schema。
- [ ] `score >= 6` 的条目可进入 `articles/`。
- [ ] `score < 6` 的条目进入 `review_pending/`。
- [ ] 按 `source_url` 去重。
- [ ] 文件命名稳定：`{YYYY-MM-DD}-{source}-{slug}.json`。
- [ ] `index.json` 与实际条目文件一致。
- [ ] 不访问外部网络。

## 权限契约

- 允许：Read、Grep、Glob、Write、Edit。
- 禁止：WebFetch、Bash。
- organizer 是唯一允许写入知识条目的角色。
