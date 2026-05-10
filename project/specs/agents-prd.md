# AI 知识库 · 三 Agent 协作 PRD v1.0

## 总流程

V1 使用串行流程：

```text
collector -> analyzer -> organizer
```

数据通过文件传递，不通过上下文隐式传递。

## Agent 职责

- collector：采集 GitHub/HN/RSS 候选内容，输出 raw JSON。
- analyzer：读取 raw JSON，补充摘要、技术类别、创新点、使用难度、1-10 分评分和标签。
- organizer：读取已分析数据，去重、过滤、归档到 articles 或 review_pending。

## 数据流

```text
project/knowledge/raw/*.json
  -> analyzer enriches raw items
  -> organizer writes project/knowledge/articles/*.json
  -> organizer writes project/knowledge/review_pending/*.json when score < 6
```

## 协作规则

1. collector 成功后，analyzer 才能启动。
2. analyzer 必须看到 `summary`、`analysis`、`tags`、`status` 后，organizer 才能启动。
3. organizer 不访问外部网络，只处理已有分析结果。
4. score 小于 6 的条目进入待复核队列，不直接发布。
5. 任一阶段失败时，下游阶段不得继续执行，必须记录失败原因。

## 失败处理

- collector 无结果：记录空结果和原因，停止 analyzer。
- collector 网络失败：记录错误，不编造数据。
- analyzer 缺字段：标记为 `review_pending` 或停止 organizer。
- organizer 发现重复 URL：跳过重复条目并记录。
- organizer 写入失败：停止流程，保留 raw 文件。

## 验收标准

- 能产出 `project/knowledge/raw/*.json`。
- 能产出带分析字段的 raw 数据。
- 能产出 `project/knowledge/articles/*.json`。
- 能产出 `project/knowledge/review_pending/*.json`。
- 能通过 JSON 解析校验。
- 能在 `project/sub-agent-test-log.md` 记录角色执行和越权情况。
