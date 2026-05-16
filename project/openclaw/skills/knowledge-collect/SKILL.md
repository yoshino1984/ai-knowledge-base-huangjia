---
name: knowledge-collect
description: Use when the user asks OpenClaw/Weixin to collect, refresh, update, or run the AI knowledge base pipeline on the cloud server.
allowed-tools:
  - Bash
  - Read
---

# Knowledge Collect

Use this skill to run one AI knowledge base collection pipeline from OpenClaw.

## Cloud Location

Prefer the cloud deployment path:

```text
/opt/ai-knowledge-base-huangjia
```

The runtime env file should be outside the repo:

```text
/opt/ai-knowledge-base.env
```

Never print or reveal values from the env file.

## Workflow

1. Confirm the user wants to run collection now if the request is ambiguous.
2. Run the command below from the cloud server.
3. Report whether the pipeline started and finished successfully.
4. Summarize only counts, elapsed time, and the log path. Do not paste secrets.

## Command

```bash
cd /opt/ai-knowledge-base-huangjia && \
mkdir -p logs project/knowledge/raw project/knowledge/articles && \
KB_ENV_FILE=/opt/ai-knowledge-base.env docker compose --profile manual run --rm pipeline \
  >> logs/pipeline.log 2>&1
```

## Status Check

For progress or failure inspection, read only the recent log tail:

```bash
cd /opt/ai-knowledge-base-huangjia && tail -n 120 logs/pipeline.log
```

## Expected Result

A successful run should create or update files under:

```text
/opt/ai-knowledge-base-huangjia/project/knowledge/raw
/opt/ai-knowledge-base-huangjia/project/knowledge/articles
```

Typical final log lines include collected/analyzed/organized/saved counts and a token cost report.

## Guardrails

- Do not run more than one collection at the same time.
- Do not run the command repeatedly unless the user explicitly asks.
- Do not edit `/opt/ai-knowledge-base.env`.
- Do not print API keys, tokens, or the full env file.
- If Docker reports permission errors, run:

```bash
cd /opt/ai-knowledge-base-huangjia && \
mkdir -p project/knowledge/raw project/knowledge/articles logs && \
chown -R 10001:10001 project/knowledge logs
```

- If the env file is missing, tell the user to create `/opt/ai-knowledge-base.env` before running collection.
