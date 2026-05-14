"""交互式 AI 知识库机器人。

包含意图识别、知识检索、订阅管理和权限控制。当前模块是可测试的
Python 检索内核，后续可以被命令行、OpenClaw 或其他消息入口调用。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any


class Intent(Enum):
    """用户消息意图。"""

    SEARCH = "search"
    BROWSE_TODAY = "browse_today"
    BROWSE_TOP = "browse_top"
    SUBSCRIBE = "subscribe"
    HELP = "help"
    UNKNOWN = "unknown"


class PermissionLevel(IntEnum):
    """权限等级，数值越大权限越高。"""

    READ = 1
    WRITE = 2
    DELETE = 3


COMMAND_MAP = {
    "/search": Intent.SEARCH,
    "/today": Intent.BROWSE_TODAY,
    "/top": Intent.BROWSE_TOP,
    "/subscribe": Intent.SUBSCRIBE,
    "/help": Intent.HELP,
}


def recognize_intent(text: str) -> tuple[Intent, str]:
    """识别用户输入意图。

    Args:
        text: 用户输入文本。

    Returns:
        二元组：意图枚举和参数字符串。
    """

    cleaned = text.strip()
    lowered = cleaned.lower()
    for command, intent in COMMAND_MAP.items():
        if lowered.startswith(command):
            return intent, cleaned[len(command) :].strip()

    if any(word in cleaned for word in ("今天", "今日", "当天")):
        return Intent.BROWSE_TODAY, _extract_after_keywords(cleaned, ("今天", "今日", "当天"))

    if re.search(r"\btop\b", lowered) or any(word in cleaned for word in ("高分", "推荐", "最好")):
        return Intent.BROWSE_TOP, _extract_first_number(cleaned)

    if "订阅" in cleaned:
        return Intent.SUBSCRIBE, _extract_after_keywords(cleaned, ("订阅",))

    if any(word in cleaned for word in ("搜索", "查询", "查找", "找", "搜")):
        return Intent.SEARCH, _extract_after_keywords(cleaned, ("搜索", "查询", "查找", "搜一下", "搜", "找"))

    if lowered in {"help", "?", "？"} or "帮助" in cleaned or "怎么用" in cleaned:
        return Intent.HELP, ""

    return Intent.UNKNOWN, cleaned


def _extract_after_keywords(text: str, keywords: tuple[str, ...]) -> str:
    for keyword in keywords:
        index = text.find(keyword)
        if index >= 0:
            payload = text[index + len(keyword) :].strip(" ：:，,。")
            return payload
    return ""


def _extract_first_number(text: str) -> str:
    match = re.search(r"\d+", text)
    return match.group(0) if match else ""


class KnowledgeSearchEngine:
    """基于本地 JSON 文件的知识库检索引擎。"""

    def __init__(self, knowledge_dir: str | Path = "project/knowledge/articles") -> None:
        self.knowledge_dir = Path(knowledge_dir)

    def search(
        self,
        keyword: str = "",
        tags: list[str] | None = None,
        date_from: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """搜索知识库条目，支持关键词、标签和日期过滤。"""

        normalized_tags = [tag.lower() for tag in tags or []]
        results: list[dict[str, Any]] = []
        for article in self._load_articles():
            if date_from and self._article_date(article) < date_from:
                continue
            if normalized_tags and not self._matches_tags(article, normalized_tags):
                continue

            match_score = self._score_article(article, keyword)
            if keyword and match_score <= 0:
                continue

            enriched = dict(article)
            enriched["_match_score"] = match_score
            results.append(enriched)

        results.sort(
            key=lambda item: (
                item.get("_match_score", 0),
                _article_score(item),
                item.get("updated_at", ""),
                item.get("id", ""),
            ),
            reverse=True,
        )
        return results[: max(limit, 0)]

    def top(self, limit: int = 5) -> list[dict[str, Any]]:
        """按质量分返回 Top 条目。"""

        articles = self._load_articles()
        articles.sort(key=lambda item: (_article_score(item), item.get("updated_at", "")), reverse=True)
        return articles[: max(limit, 0)]

    def today(self, target_date: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """返回指定日期的条目，默认使用今天。"""

        day = target_date or date.today().isoformat()
        results = [article for article in self._load_articles() if self._article_date(article) == day]
        results.sort(key=lambda item: (_article_score(item), item.get("updated_at", "")), reverse=True)
        return results[: max(limit, 0)]

    def _load_articles(self) -> list[dict[str, Any]]:
        if not self.knowledge_dir.exists():
            return []

        articles: list[dict[str, Any]] = []
        for path in sorted(self.knowledge_dir.glob("*.json")):
            if path.name == "index.json":
                continue
            try:
                articles.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return articles

    def _score_article(self, article: dict[str, Any], keyword: str) -> int:
        if not keyword.strip():
            return 1

        terms = _expand_terms(keyword)
        score = 0
        title = str(article.get("title", "")).lower()
        summary = str(article.get("summary", "")).lower()
        category = str(_category(article)).lower()
        tags = [str(tag).lower() for tag in article.get("tags", [])]

        for term in terms:
            if term in title:
                score += 10
            if any(term in tag for tag in tags):
                score += 5
            if term in summary:
                score += 3
            if term in category:
                score += 4
        return score

    def _matches_tags(self, article: dict[str, Any], tags: list[str]) -> bool:
        article_tags = [str(tag).lower() for tag in article.get("tags", [])]
        return any(tag in item for tag in tags for item in article_tags)

    def _article_date(self, article: dict[str, Any]) -> str:
        article_id = str(article.get("id", ""))
        if re.match(r"\d{4}-\d{2}-\d{2}", article_id):
            return article_id[:10]
        updated_at = str(article.get("updated_at", ""))
        if re.match(r"\d{4}-\d{2}-\d{2}", updated_at):
            return updated_at[:10]
        return ""


class SubscriptionManager:
    """用户订阅管理。"""

    def __init__(self, data_dir: str | Path = "project/bot/data") -> None:
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / "subscriptions.json"
        self._subscriptions = self._load()

    def subscribe(self, user_id: str, topic: str) -> None:
        """订阅一个主题。"""

        topic = topic.strip()
        if not topic:
            return
        topics = self._subscriptions.setdefault(user_id, [])
        if topic not in topics:
            topics.append(topic)
            self._save()

    def unsubscribe(self, user_id: str, topic: str) -> None:
        """取消订阅一个主题。"""

        topics = self._subscriptions.get(user_id, [])
        if topic in topics:
            topics.remove(topic)
            self._save()

    def list_subscriptions(self, user_id: str) -> list[str]:
        """列出用户订阅。"""

        return list(self._subscriptions.get(user_id, []))

    def _load(self) -> dict[str, list[str]]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return {str(user): [str(topic) for topic in topics] for user, topics in data.items()}

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._subscriptions, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


@dataclass(frozen=True)
class PermissionManager:
    """三级权限控制。"""

    writable_users: set[str] | None = None
    deletable_users: set[str] | None = None

    def has_permission(self, user_id: str, level: PermissionLevel) -> bool:
        """判断用户是否具备指定权限。"""

        if level == PermissionLevel.READ:
            return True
        if level == PermissionLevel.WRITE:
            return user_id in (self.writable_users or set()) or self.has_permission(user_id, PermissionLevel.DELETE)
        if level == PermissionLevel.DELETE:
            return user_id in (self.deletable_users or set())
        return False


class KnowledgeBot:
    """知识库 Bot 主入口。"""

    def __init__(
        self,
        knowledge_dir: str | Path = "project/knowledge/articles",
        data_dir: str | Path = "project/bot/data",
        writable_users: set[str] | None = None,
        deletable_users: set[str] | None = None,
    ) -> None:
        self.search_engine = KnowledgeSearchEngine(knowledge_dir)
        self.subscription_manager = SubscriptionManager(data_dir)
        self.permission_manager = PermissionManager(writable_users or set(), deletable_users or set())

    def handle_message(self, user_id: str, text: str) -> str:
        """处理用户消息并返回响应文本。"""

        intent, args = recognize_intent(text)
        handlers = {
            Intent.SEARCH: self._handle_search,
            Intent.BROWSE_TODAY: self._handle_today,
            Intent.BROWSE_TOP: self._handle_top,
            Intent.SUBSCRIBE: self._handle_subscribe,
            Intent.HELP: self._handle_help,
            Intent.UNKNOWN: self._handle_unknown,
        }
        return handlers.get(intent, self._handle_unknown)(user_id, args)

    def _handle_search(self, user_id: str, query: str) -> str:
        if not self.permission_manager.has_permission(user_id, PermissionLevel.READ):
            return "你没有读取知识库的权限。"
        if not query:
            return "请提供搜索关键词，例如：/search agent"
        return format_search_results(self.search_engine.search(keyword=query), query=query)

    def _handle_today(self, user_id: str, args: str) -> str:
        if not self.permission_manager.has_permission(user_id, PermissionLevel.READ):
            return "你没有读取知识库的权限。"
        target_date = _extract_date(args) if args else None
        articles = self.search_engine.today(target_date=target_date)
        day = target_date or date.today().isoformat()
        if not articles:
            return f"{day} 今日知识库暂无新增条目。"
        return f"{day} 今日知识库：\n" + _format_article_list(articles)

    def _handle_top(self, user_id: str, args: str) -> str:
        if not self.permission_manager.has_permission(user_id, PermissionLevel.READ):
            return "你没有读取知识库的权限。"
        limit = _parse_limit(args, default=5)
        articles = self.search_engine.top(limit=limit)
        if not articles:
            return "知识库当前没有可推荐条目。"
        return f"Top {limit} 高分知识条目：\n" + _format_article_list(articles)

    def _handle_subscribe(self, user_id: str, topic: str) -> str:
        if not self.permission_manager.has_permission(user_id, PermissionLevel.WRITE):
            return "你没有订阅权限，请联系管理员开通 WRITE 权限。"
        if not topic:
            return "请提供订阅主题，例如：/subscribe agent"
        self.subscription_manager.subscribe(user_id, topic)
        return f"已订阅「{topic}」。"

    def _handle_help(self, user_id: str, args: str) -> str:
        return (
            "可用指令：\n"
            "/search <关键词> - 搜索知识库\n"
            "/today [YYYY-MM-DD] - 查看指定日期条目\n"
            "/top [数量] - 查看高分条目\n"
            "/subscribe <主题> - 订阅主题\n"
            "/help - 查看帮助"
        )

    def _handle_unknown(self, user_id: str, text: str) -> str:
        return "我还没理解你的需求。可以试试 /search agent、/today、/top 3 或 /help。"


def format_search_results(results: list[dict[str, Any]], query: str = "") -> str:
    """格式化搜索结果。"""

    if not results:
        return f"没有找到与「{query}」相关的内容。"

    header = f"找到 {len(results)} 条与「{query}」相关的内容："
    return header + "\n" + _format_article_list(results)


def _format_article_list(articles: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, article in enumerate(articles, start=1):
        tags = article.get("tags", [])
        tag_text = "、".join(str(tag) for tag in tags) if tags else "无"
        url = article.get("source_url") or article.get("url") or "无"
        lines.extend(
            [
                f"{index}. {article.get('title', '未命名条目')}",
                f"   分数：{_article_score(article):g}/10 | 来源：{article.get('source', 'unknown')}",
                f"   分类：{_category(article) or '未知'} | 标签：{tag_text}",
                f"   链接：{url}",
            ]
        )
    return "\n".join(lines)


def _article_score(article: dict[str, Any]) -> float:
    if "score" in article:
        return float(article.get("score") or 0)
    return float(article.get("relevance_score") or 0) * 10


def _category(article: dict[str, Any]) -> str:
    analysis = article.get("analysis") if isinstance(article.get("analysis"), dict) else {}
    return str(article.get("category") or analysis.get("technical_category") or "")


def _expand_terms(keyword: str) -> set[str]:
    terms = {part.lower() for part in re.split(r"\s+", keyword.strip()) if part.strip()}
    synonyms = {
        "agent": {"agent", "智能体", "代理"},
        "智能体": {"agent", "智能体", "代理"},
        "mcp": {"mcp", "模型上下文协议"},
        "rag": {"rag", "检索增强"},
    }
    expanded = set(terms)
    for term in list(terms):
        expanded.update(synonyms.get(term, set()))
    return expanded


def _parse_limit(text: str, default: int) -> int:
    number = _extract_first_number(text)
    if not number:
        return default
    return max(1, min(int(number), 20))


def _extract_date(text: str) -> str | None:
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return match.group(0) if match else None


if __name__ == "__main__":
    bot = KnowledgeBot()
    while True:
        try:
            message = input("你：").strip()
        except EOFError:
            break
        if message.lower() in {"quit", "exit"}:
            break
        print(f"助手：{bot.handle_message('cli-user', message)}")
