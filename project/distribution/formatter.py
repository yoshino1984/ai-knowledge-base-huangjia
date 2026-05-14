"""多渠道内容格式化模块。

把知识库 JSON 条目转换为 Markdown、微信文本和飞书卡片。
formatter 只负责格式化，不发送网络请求。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _score(article: dict[str, Any]) -> float:
    """兼容 score(1-10) 和 relevance_score(0-1) 两种评分字段。"""

    if "score" in article:
        return float(article.get("score") or 0)
    return float(article.get("relevance_score") or 0) * 10


def _score_color(score: float) -> str:
    """根据 1-10 分数返回状态颜色。"""

    if score >= 8:
        return "🟢"
    if score >= 6:
        return "🟡"
    return "🔴"


def _feishu_template(score: float) -> str:
    """根据分数选择飞书卡片颜色。"""

    if score >= 8:
        return "green"
    if score >= 6:
        return "yellow"
    return "red"


def _date(article: dict[str, Any]) -> str:
    """从文章字段中取日期。"""

    value = article.get("updated_at") or article.get("collected_at") or article.get("id", "")
    return str(value)[:10] if value else "未知"


def _url(article: dict[str, Any]) -> str:
    """兼容 source_url 和旧版 url 字段。"""

    return str(article.get("source_url") or article.get("url") or "")


def _tags(article: dict[str, Any]) -> list[str]:
    """取标签列表。"""

    tags = article.get("tags", [])
    return [str(tag) for tag in tags] if isinstance(tags, list) else []


def json_to_markdown(article: dict[str, Any]) -> str:
    """将单篇文章 JSON 转换为 Markdown。"""

    score = _score(article)
    tags = _tags(article)
    tags_text = ", ".join(f"`{tag}`" for tag in tags) or "无"
    url = _url(article) or "#"

    return (
        f"## {article.get('title', '未命名条目')}\n\n"
        f"- **来源**：{article.get('source', '未知')}\n"
        f"- **日期**：{_date(article)}\n"
        f"- **相关性**：{_score_color(score)} {score:g}/10\n"
        f"- **标签**：{tags_text}\n\n"
        f"{article.get('summary', '暂无摘要')}\n\n"
        f"🔗 [原文链接]({url})\n"
    )


def json_to_weixin(article: dict[str, Any]) -> str:
    """将单篇文章 JSON 转换为适合微信阅读的纯文本。"""

    score = _score(article)
    tags_text = "、".join(_tags(article)) or "无"
    url = _url(article) or "暂无"
    insight = ""
    analysis = article.get("analysis", {})
    if isinstance(analysis, dict) and analysis.get("innovation"):
        insight = f"\n洞察：{analysis['innovation']}"

    return (
        f"📌 {article.get('title', '未命名条目')}\n"
        f"分数：{score:g}/10\n"
        f"来源：{article.get('source', '未知')}\n"
        f"标签：{tags_text}\n\n"
        f"{article.get('summary', '暂无摘要')}"
        f"{insight}\n\n"
        f"链接：{url}"
    )


def json_to_feishu(article: dict[str, Any]) -> dict[str, Any]:
    """将单篇文章 JSON 转换为飞书 interactive 卡片。"""

    score = _score(article)
    tags_text = "、".join(_tags(article)) or "无"
    url = _url(article)
    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**分数**：{score:g}/10\n"
                    f"**来源**：{article.get('source', '未知')}\n"
                    f"**标签**：{tags_text}\n\n"
                    f"{article.get('summary', '暂无摘要')}"
                ),
            },
        }
    ]
    if url:
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看原文"},
                        "url": url,
                        "type": "primary",
                    }
                ],
            }
        )

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": _feishu_template(score),
                "title": {
                    "tag": "plain_text",
                    "content": str(article.get("title", "未命名条目")),
                },
            },
            "elements": elements,
        },
    }


def _load_articles(knowledge_dir: str | Path, date: str) -> list[dict[str, Any]]:
    """加载指定日期的文章 JSON。"""

    path = Path(knowledge_dir)
    articles: list[dict[str, Any]] = []
    for file_path in sorted(path.glob(f"{date}-*.json")):
        if file_path.name == "index.json":
            continue
        try:
            articles.append(json.loads(file_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return articles


def generate_daily_digest(
    knowledge_dir: str | Path = "project/knowledge/articles",
    date: str | None = None,
    top_n: int = 5,
) -> dict[str, Any]:
    """生成每日简报，返回 Markdown、微信文本和飞书卡片。"""

    target_date = date or datetime.now().strftime("%Y-%m-%d")
    articles = _load_articles(knowledge_dir, target_date)
    articles.sort(key=_score, reverse=True)
    top_articles = articles[:top_n]

    if not top_articles:
        empty = f"📭 {target_date} 暂无新增知识条目"
        return {
            "markdown": empty,
            "weixin": empty,
            "feishu": {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "template": "grey",
                        "title": {"tag": "plain_text", "content": "AI 知识简报"},
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {"tag": "plain_text", "content": empty},
                        }
                    ],
                },
            },
        }

    markdown_items = "\n\n".join(json_to_markdown(article) for article in top_articles)
    weixin_items = "\n\n---\n\n".join(json_to_weixin(article) for article in top_articles)
    feishu_elements = []
    for article in top_articles:
        feishu_elements.extend(json_to_feishu(article)["card"]["elements"])

    return {
        "markdown": f"# {target_date} AI 知识简报\n\n{markdown_items}",
        "weixin": f"{target_date} AI 知识简报\n\n{weixin_items}",
        "feishu": {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "template": "blue",
                    "title": {
                        "tag": "plain_text",
                        "content": f"{target_date} AI 知识简报",
                    },
                },
                "elements": feishu_elements,
            },
        },
    }


if __name__ == "__main__":
    digest = generate_daily_digest()
    print(digest["markdown"])
