#!/usr/bin/env python3
"""本地知识库 MCP Server。

通过 JSON-RPC 2.0 over stdio 暴露 3 个工具：
search_articles、get_article、knowledge_stats。
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"


def load_articles() -> list[dict[str, Any]]:
    """读取知识库文章 JSON。"""

    articles: list[dict[str, Any]] = []
    if not ARTICLES_DIR.exists():
        return articles

    for article_file in sorted(ARTICLES_DIR.glob("*.json")):
        if article_file.name == "index.json":
            continue
        try:
            article = json.loads(article_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(article, dict):
            articles.append(article)
    return articles


def article_preview(article: dict[str, Any]) -> dict[str, Any]:
    """返回适合搜索列表展示的文章摘要。"""

    return {
        "id": article.get("id", ""),
        "title": article.get("title", ""),
        "source": article.get("source", ""),
        "source_url": article.get("source_url", ""),
        "score": article.get("score", article.get("analysis", {}).get("score", 0)),
        "tags": article.get("tags", []),
        "summary": article.get("summary", ""),
    }


def search_articles(keyword: str, limit: int = 5) -> list[dict[str, Any]]:
    """按关键词搜索标题、摘要和标签。"""

    keyword_lower = keyword.lower().strip()
    if not keyword_lower:
        return []

    matched: list[dict[str, Any]] = []
    for article in load_articles():
        searchable = " ".join(
            [
                str(article.get("title", "")),
                str(article.get("summary", "")),
                " ".join(str(tag) for tag in article.get("tags", [])),
            ]
        ).lower()
        if keyword_lower in searchable:
            matched.append(article_preview(article))

    return matched[: max(1, min(limit, 20))]


def get_article(article_id: str) -> dict[str, Any]:
    """按文章 ID 返回完整内容。"""

    for article in load_articles():
        if article.get("id") == article_id:
            return article
    raise ValueError(f"未找到文章: {article_id}")


def knowledge_stats() -> dict[str, Any]:
    """返回知识库统计信息。"""

    articles = load_articles()
    source_counter: Counter[str] = Counter()
    tag_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()

    for article in articles:
        source_counter[str(article.get("source", "unknown"))] += 1
        status_counter[str(article.get("status", "unknown"))] += 1
        for tag in article.get("tags", []):
            tag_counter[str(tag)] += 1

    return {
        "article_count": len(articles),
        "sources": dict(source_counter.most_common()),
        "statuses": dict(status_counter.most_common()),
        "top_tags": dict(tag_counter.most_common(10)),
    }


TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_articles",
        "description": "按关键词搜索本地知识库文章的标题、摘要和标签。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "搜索关键词"},
                "limit": {
                    "type": "integer",
                    "description": "最多返回数量",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "get_article",
        "description": "按文章 ID 获取本地知识库文章完整 JSON 内容。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "article_id": {"type": "string", "description": "文章 ID"},
            },
            "required": ["article_id"],
        },
    },
    {
        "name": "knowledge_stats",
        "description": "统计本地知识库文章总数、来源分布、状态分布和热门标签。",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def text_result(data: Any) -> dict[str, Any]:
    """把 Python 数据包装成 MCP 工具文本结果。"""

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(data, ensure_ascii=False, indent=2),
            }
        ]
    }


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    """处理 MCP/JSON-RPC 请求。"""

    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    if request_id is None:
        return None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "ai-knowledge-base",
                    "version": "0.1.0",
                },
            }
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            if tool_name == "search_articles":
                result = text_result(
                    search_articles(
                        keyword=str(arguments.get("keyword", "")),
                        limit=int(arguments.get("limit", 5)),
                    )
                )
            elif tool_name == "get_article":
                result = text_result(get_article(str(arguments.get("article_id", ""))))
            elif tool_name == "knowledge_stats":
                result = text_result(knowledge_stats())
            else:
                raise ValueError(f"未知工具: {tool_name}")
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"未知方法: {method}"},
            }

        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(exc)},
        }


def main() -> None:
    """从 stdin 逐行读取 JSON-RPC 请求并写回 stdout。"""

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
        except json.JSONDecodeError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
