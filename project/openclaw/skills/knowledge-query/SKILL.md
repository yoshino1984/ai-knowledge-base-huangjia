---
name: knowledge-query
description: Query the local AI knowledge base from OpenClaw/Weixin. Use when the user asks to search, count, recommend, summarize, or inspect articles in the knowledge base, especially questions like "知识库里有多少 agent 类文章", "推荐高分项目", "查 Dify", or "今天有哪些条目".
allowed-tools:
  - Read
---

# Knowledge Query

You are answering from the local AI knowledge base. Prefer fast index lookup first, then read full article JSON only when details are needed.

## Data Location

Always prefer the absolute project path:

```text
/Users/xiaoyi/project/ai/study/huangjia/ai-knowledge-base/project/knowledge/articles/index.json
/Users/xiaoyi/project/ai/study/huangjia/ai-knowledge-base/project/knowledge/articles/{id}.json
```

Fallback path if the OpenClaw workspace has the `knowledge` symlink:

```text
knowledge/articles/index.json
knowledge/articles/{id}.json
```

## Workflow

1. Read `/Users/xiaoyi/project/ai/study/huangjia/ai-knowledge-base/project/knowledge/articles/index.json`.
2. Filter in memory using the user's question.
3. Read individual `{id}.json` files only when the user asks for summary, source URL, tags, score, or details.
4. Answer in concise Chinese.

Do not use directory scanning, full-text search tools, command execution, or scan every article unless the user explicitly asks for an exhaustive audit. The index is the entry point.

## Index Schema

The current `index.json` entries are slim records:

```json
{
  "id": "2026-05-12-workflow-bytedance-deer-flow",
  "title": "bytedance/deer-flow",
  "category": "AI Agent框架"
}
```

Some older records may also include `score`, `relevance_score`, `tags`, or dates. Treat missing optional fields as unknown.

## Article Schema

Full article files usually include:

```json
{
  "id": "...",
  "title": "...",
  "source": "github",
  "source_url": "https://github.com/...",
  "summary": "...",
  "score": 8,
  "tags": ["智能体", "开源"],
  "analysis": {
    "technical_category": "AI Agent框架",
    "innovation": "...",
    "difficulty": "medium"
  }
}
```

Support both `source_url` and older `url`. Support both `score` (1-10) and older `relevance_score` (0-1).

## Query Rules

- Count by category: match user terms against `category`, `title`, and, if needed, full article `tags` or `analysis.technical_category`.
- Search by keyword: match keyword against `title` first; read full articles only if title/category is insufficient.
- Recommend top items: read candidate full articles and sort by `score`; if only `relevance_score` exists, convert it by `score = relevance_score * 10`.
- Today's items: infer date from `id` prefix like `YYYY-MM-DD-...` or `updated_at`.
- If the index is empty or missing, say the knowledge base is currently empty and ask the user to run the collection pipeline.

## Response Style

For counts:

```text
我在知识库索引里找到 N 篇和「agent」相关的文章。

1. title（category）
2. title（category）
```

For details:

```text
title
- 分数：8/10
- 标签：智能体、开源
- 摘要：...
- 链接：https://...
```

If matching is fuzzy, say so explicitly, for example: "我按 title/category/tags 做了模糊匹配。"
