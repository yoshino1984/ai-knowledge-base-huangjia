---
name: github-trending
description: 当需要采集 GitHub 热门开源项目，尤其是 AI、LLM、Agent、RAG、MCP 相关项目时使用此技能。
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
---

# GitHub Trending 采集技能

## 使用场景

在知识库采集阶段，从 GitHub 搜索并采集 AI/LLM/Agent 相关热门开源项目。

此技能通常由 Collector Agent 使用。它描述采集步骤，不代表硬性安全沙箱。

## 执行步骤

### 第 1 步：搜索热门仓库

使用 GitHub Search API：

```text
GET https://api.github.com/search/repositories
```

推荐查询条件：

```text
topic:llm pushed:>={7天前日期} stars:>50 fork:false
topic:ai-agent pushed:>={7天前日期} stars:>50 fork:false
topic:rag pushed:>={7天前日期} stars:>50 fork:false
topic:mcp pushed:>={7天前日期} stars:>50 fork:false
topic:artificial-intelligence pushed:>={7天前日期} stars:>50 fork:false
```

排序：

```text
sort=stars&order=desc&per_page=30
```

### 第 2 步：提取仓库信息

提取字段：

- `name`
- `full_name`
- `html_url`
- `description`
- `stargazers_count`
- `forks_count`
- `language`
- `topics`
- `pushed_at`

### 第 3 步：过滤

纳入：

- AI/LLM/Agent/RAG/MCP 相关项目
- AI 工程工具
- 模型运行时、Agent 框架、工作流自动化、知识库相关项目

排除：

- Awesome 列表
- 课程作业
- 个人笔记
- 无真实来源或描述过少的项目

### 第 4 步：去重

按 `full_name` 去重，只保留一条。

### 第 5 步：撰写中文摘要

摘要公式：

```text
项目名 + 做什么 + 为什么值得关注
```

摘要要具体，避免“强大”“优秀”这类空泛词。

### 第 6 步：排序取 Top 15

按 Star 数降序排列，V1 默认取 15 条。

任务要求 Top 10 时，按任务覆盖默认值。

### 第 7 步：输出 JSON

推荐输出路径：

```text
knowledge/raw/github-trending-{YYYY-MM-DD}.json
```

## 输出格式

```json
{
  "source": "github-trending",
  "skill": "github-trending",
  "collected_at": "2026-05-11T10:00:00Z",
  "items": [
    {
      "name": "example",
      "full_name": "owner/example",
      "url": "https://github.com/owner/example",
      "summary": "example 是一个用于构建 AI Agent 工作流的开源项目，值得关注是因为它降低了多工具编排成本。",
      "stars": 1234,
      "forks": 100,
      "language": "Python",
      "topics": ["agent", "llm", "workflow"],
      "updated_at": "2026-05-11T00:00:00Z"
    }
  ]
}
```

## 注意事项

- 未认证 GitHub API 有限流，优先使用 `GITHUB_TOKEN`。
- 不编造不存在的仓库、Star 数或链接。
- 摘要必须是中文，技术术语保留英文原文。
- Skill 只负责定义采集方法；是否写入文件由 Agent/主流程决定。
