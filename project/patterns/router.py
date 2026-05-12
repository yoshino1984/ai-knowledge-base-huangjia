"""Router 模式：基于意图分类的请求路由。"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"

sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from model_client import chat


def github_search_handler(query: str) -> str:
    """GitHub 搜索处理器。"""

    search_query = (
        query.replace("搜索", "")
        .replace("查找", "")
        .replace("github", "")
        .replace("GitHub", "")
        .replace("仓库", "")
        .replace("项目", "")
        .strip()
    )
    if not search_query:
        search_query = "AI Agent"

    encoded_query = urllib.parse.quote(search_query)
    url = (
        "https://api.github.com/search/repositories"
        f"?q={encoded_query}&sort=stars&order=desc&per_page=5"
    )
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return f"GitHub 搜索失败: {exc}"

    lines: list[str] = []
    for repo in data.get("items", [])[:5]:
        description = repo.get("description") or "无描述"
        lines.append(
            f"- {repo['full_name']} | stars={repo['stargazers_count']} | "
            f"{repo['html_url']} | {description}"
        )
    if not lines:
        return "未找到相关 GitHub 仓库。"
    return "GitHub 搜索结果:\n" + "\n".join(lines)


def load_articles() -> list[dict]:
    """读取本地知识库文章。"""

    articles: list[dict] = []
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


def knowledge_query_handler(query: str) -> str:
    """本地知识库查询处理器。"""

    articles = load_articles()
    if not articles:
        return "知识库为空，请先运行采集流水线。"

    query_lower = query.lower()
    matches: list[dict] = []
    for article in articles:
        searchable = " ".join(
            [
                str(article.get("title", "")),
                str(article.get("summary", "")),
                str(article.get("source", "")),
                " ".join(str(tag) for tag in article.get("tags", [])),
            ]
        ).lower()
        if query_lower in searchable or any(
            keyword in searchable for keyword in query_lower.split()
        ):
            matches.append(article)

    if not matches:
        return "未找到匹配的知识条目。"

    lines = []
    for article in matches[:10]:
        score = article.get("score", article.get("analysis", {}).get("score", "?"))
        lines.append(
            f"- {article.get('title', 'Untitled')} "
            f"(id={article.get('id', '-')}, score={score})"
        )
    return f"找到 {len(matches)} 条相关知识:\n" + "\n".join(lines)


def general_chat_handler(query: str) -> str:
    """通用对话处理器。"""

    result = chat(
        query,
        system="你是一个专业的 AI 技术顾问。请用中文简洁、准确地回答。",
    )
    return str(result["content"])


HANDLERS: dict[str, Callable[[str], str]] = {
    "github_search": github_search_handler,
    "knowledge_query": knowledge_query_handler,
    "general_chat": general_chat_handler,
}

KEYWORD_RULES: list[tuple[list[str], str]] = [
    (["github", "仓库", "repo", "repository", "开源项目", "搜索项目"], "github_search"),
    (["知识库", "已收录", "本地", "检索", "查一下", "内容"], "knowledge_query"),
]


def classify_intent(query: str) -> str:
    """先用关键词分类，无法判断时用 LLM 兜底。"""

    query_lower = query.lower()
    for keywords, intent in KEYWORD_RULES:
        if any(keyword in query_lower for keyword in keywords):
            return intent

    prompt = f"""请判断用户查询的意图类别。

查询：{query}

可选类别：
- github_search：想搜索 GitHub 上的项目或仓库
- knowledge_query：想查询本地已有知识库内容
- general_chat：一般性技术问题或闲聊

请只返回类别名称。"""
    try:
        result = chat(
            prompt,
            system="你是意图分类器，只能返回类别名称。",
            max_retries=2,
        )
        intent = str(result["content"]).strip().lower()
    except Exception:
        return "general_chat"
    return intent if intent in HANDLERS else "general_chat"


def route(query: str) -> str:
    """统一入口：分类意图并调用处理器。"""

    intent = classify_intent(query)
    print(f"[Router] 意图: {intent}")
    return HANDLERS[intent](query)


if __name__ == "__main__":
    user_query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "搜索最近的 AI Agent 框架"
    print(f"查询: {user_query}\n")
    print(route(user_query))
