#!/usr/bin/env bash
set -euo pipefail

# 本地完整流水线入口：采集、分析、整理、保存一次完成。
# 需要配置 LLM API Key，适合低频运行。

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

mkdir -p logs

limit="${KB_PIPELINE_LIMIT:-5}"
sources="${KB_PIPELINE_SOURCES:-github,rss}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始完整流水线：sources=${sources}, limit=${limit}"
  python3 -m project.pipeline.pipeline \
    --sources "$sources" \
    --limit "$limit"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 完整流水线完成"
  echo
} >> logs/pipeline.log 2>&1
