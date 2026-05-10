---
name: tech-summary
description: 当需要对采集到的技术项目、技术文章或 AI 工程内容进行摘要、评分、打标签和趋势分析时使用此技能。
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
---

# 技术摘要分析技能

## 使用场景

在知识库分析阶段，对 `knowledge/raw/` 中的采集结果进行深度分析。

此技能通常由 Analyzer Agent 使用。它描述分析步骤，不代表硬性安全沙箱。

## 执行步骤

### 第 1 步：读取采集数据

读取 `knowledge/raw/` 中最新或指定的采集文件。

输入应包含：

- `title` 或 `name`
- `url`
- `source`
- `description` 或 `summary`
- 热度指标，如 stars、forks、score、comments
- topics、language 等辅助字段

### 第 2 步：补充上下文

必要时使用 WebFetch 读取项目 README、文章正文或项目介绍。

如果外部读取失败，基于已有字段分析，并在结果中避免编造。

### 第 3 步：逐条生成分析

每条内容输出：

- 中文摘要：不超过 80 字，说明它是什么、为什么值得关注。
- 技术亮点：2-3 个，用事实描述。
- 技术类别：如 `agent-framework`、`llm-runtime`、`rag`、`workflow-automation`。
- 创新点：说明具体变化或值得关注的工程价值。
- 使用难度：`low`、`medium`、`high`。
- 标签：3-5 个英文小写标签。
- 评分：1-10 分，并说明理由。

### 第 4 步：趋势发现

处理一批内容后，总结共同主题：

- 是否出现新的工具范式
- 是否集中在 Agent、RAG、MCP、本地模型、工作流等方向
- 哪些内容适合优先进入知识库

### 第 5 步：输出分析结果

输出 JSON，不直接发布到 `knowledge/articles/`。

## 评分标准

- `9-10`：改变格局或高度值得跟进。
- `7-8`：对 AI 工程实践直接有帮助。
- `5-6`：值得了解，但优先级一般。
- `1-4`：相关性弱或质量不足。

约束：

- 一批 15 个项目中，`9-10` 分不超过 2 个，避免评分虚高。
- `score < 6` 的条目应标记为 `review_pending`。

## 输出格式

```json
{
  "title": "Example Project",
  "source_url": "https://github.com/owner/example",
  "summary": "Example Project 是一个用于构建 Agent 工作流的项目，适合快速验证多工具编排。",
  "technical_highlights": [
    "支持多工具编排",
    "提供可扩展工作流接口"
  ],
  "analysis": {
    "technical_category": "agent-framework",
    "innovation": "把 Agent 工作流步骤抽象成可组合节点。",
    "difficulty": "medium",
    "score": 8,
    "reason": "对 Agent 工程实践有直接帮助，但仍需要集成成本。"
  },
  "tags": ["agent", "workflow", "llm"],
  "status": "published"
}
```

## 注意事项

- 不要把热度等同于价值，评分必须结合技术类别、创新点和使用难度。
- 不要编造 README 或正文中不存在的信息。
- 摘要用中文，技术名词保留英文原文。
- 分析结果交给 Organizer 归档。
