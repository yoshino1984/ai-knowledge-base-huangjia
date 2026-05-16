---
name: knowledge-present
description: Use when presenting AI knowledge base articles to the user in OpenClaw/Weixin, especially for daily digests, search results, top recommendations, article details, or knowledge cards.
allowed-tools: []
---

# Knowledge Present

Use this skill to format final answers about AI knowledge base articles. This skill does not fetch data; combine it with a query or recommendation skill when article data is needed.

## Default Style

- Answer in concise Chinese.
- Prefer readable plain text for Weixin.
- Do not use Markdown tables.
- Keep each article card compact.
- Do not invent missing fields. Use `未知` or omit the line.
- Always include the source link when available.

## Knowledge Card

Use this format for article details, recommendations, and daily digest items:

```text
N. <title>
   价值：<one-sentence value>
   分数：<score>/10
   分类：<category>
   标签：<tag1>、<tag2>、<tag3>
   难度：<difficulty>
   链接：<source_url>
```

Field mapping:

- `title`: article title.
- `价值`: prefer `summary`; if too long, compress to one sentence.
- `score`: prefer `score`; if only `relevance_score` exists, convert to 1-10 scale.
- `category`: prefer `category`, then `analysis.technical_category`.
- `tags`: use up to 5 tags.
- `difficulty`: prefer `analysis.difficulty`.
- `source_url`: support both `source_url` and `url`.

## List Formats

For search results:

```text
我找到 N 条相关内容：

1. <title>
   价值：...
   分数：...
   链接：...
```

For top recommendations:

```text
高分推荐 Top N：

1. <title>
   价值：...
   分数：...
   分类：...
   链接：...
```

For daily digest:

```text
今日 AI 知识库更新：

采集：<collected> 条
入库：<saved> 条

值得关注：
1. <title>
   价值：...
   分数：...
   链接：...
```

## Detail Format

When the user asks about one specific article, include a short reason section:

```text
<title>

价值：...
适合：<audience or inferred audience>
难度：<difficulty>
分数：<score>/10
标签：...
链接：...

为什么值得看：
<2-3 short bullets or sentences>
```

## Guardrails

- If the user asks only for a count, do not expand every article.
- If more than 5 items match, show the first page and mention how to ask for more.
- If the answer is going to Weixin, avoid long code blocks and deeply nested bullets.
- If matching is fuzzy, say "我按 title/category/tags 做了模糊匹配。"
