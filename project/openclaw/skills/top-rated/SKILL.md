---
name: top-rated
description: Use when the user asks OpenClaw/Weixin to recommend high-score, best, most valuable, top N, score highest, or worth-reading articles from the local AI knowledge base.
allowed-tools:
  - Read
---

# Top Rated

Use this skill to answer high-score recommendation requests from the local AI knowledge base.

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
2. Infer `top_n` from the user's message, defaulting to 5 and capping at 10.
3. Infer optional filters:
   - category keywords such as framework, RAG, agent, MCP, crawler, automation.
   - score threshold such as "8 分以上", "0.85 以上", or "score >= 9".
4. Build a candidate list from index entries. If score, tags, category, or summary are missing, read the corresponding `{id}.json` file.
5. Deduplicate by `title`, keeping the item with the highest score.
6. Sort by normalized score descending.
7. Return concise Chinese results.

## Score Rules

- Prefer `score` when present. It is a 1-10 score.
- If only `relevance_score` exists, convert it with `score = relevance_score * 10`.
- Default high-score threshold is 8/10 unless the user gives a threshold.
- If a user writes a decimal threshold between 0 and 1, convert it to 1-10 scale.

## Response Format

```text
⭐ 高分推荐 Top N：

1. <title>
   分数：<score>/10
   分类：<category>
   标签：<tags>
   链接：<source_url>
```

If no results match:

```text
没有找到满足条件的高分条目。我按 <filters> 做了过滤，当前阈值是 <threshold>/10。
```

## Guardrails

- Do not use directory scanning, full-text search tools, command execution, or scan directories.
- Do not read every article unless the index lacks required fields for ranking.
- Do not recommend items below the active score threshold.
- Do not invent scores, tags, categories, or links. Say "未知" when missing.
- If matching is fuzzy, say "我按 title/category/tags 做了模糊匹配。"
