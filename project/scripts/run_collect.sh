#!/usr/bin/env bash
set -euo pipefail

# 本地定时采集入口：只执行采集步骤，不调用 LLM。
# 适合每天运行，输出追加到 logs/collect.log。

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

mkdir -p logs

limit="${KB_COLLECT_LIMIT:-20}"
sources="${KB_COLLECT_SOURCES:-github,rss}"

{
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始定时采集：sources=${sources}, limit=${limit}"
  python3 project/pipeline/pipeline.py \
    --sources "$sources" \
    --limit "$limit" \
    --step 1
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 定时采集完成"
  echo
} >> logs/collect.log 2>&1
