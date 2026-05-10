# Issue 02 - Analyzer Agent

## 目标

读取 raw JSON，为每条候选内容补充摘要、分析维度、标签、状态和评分。

## depends_on

- `project/specs/issues/01-collector.md`
- `project/knowledge/raw/{source}-{YYYY-MM-DD}.json`

## 输入

- collector 产出的 raw JSON。

## 输出

- 带分析字段的 raw JSON，或主流程可继续传递的分析结果。

## schema

输入参考 `project/specs/schemas/raw_collection.schema.json`。
输出参考 `project/specs/schemas/knowledge_article.schema.json` 中的分析字段。

## acceptance

- [ ] 每条候选内容有中文 `summary`。
- [ ] 每条候选内容有 `analysis.technical_category`。
- [ ] 每条候选内容有 `analysis.innovation`。
- [ ] 每条候选内容有 `analysis.difficulty`，取值 `low`、`medium`、`high`。
- [ ] 每条候选内容有 `analysis.score`，范围 1-10。
- [ ] `score < 6` 的条目标记为 `review_pending`。
- [ ] 标签为英文小写，建议 3-5 个。
- [ ] 不直接写入 `knowledge/articles/`。

## 权限契约

- 允许：Read、Grep、Glob、WebFetch。
- 禁止：Write、Edit、Bash。
- 落盘由主流程负责，不由 analyzer 直接执行。
