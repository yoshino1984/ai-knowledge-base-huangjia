import json
from pathlib import Path

from project.bot.knowledge_bot import (
    Intent,
    KnowledgeBot,
    KnowledgeSearchEngine,
    PermissionLevel,
    PermissionManager,
    SubscriptionManager,
    format_search_results,
    recognize_intent,
)


def write_article(articles_dir: Path, article: dict) -> None:
    (articles_dir / f"{article['id']}.json").write_text(
        json.dumps(article, ensure_ascii=False),
        encoding="utf-8",
    )


def make_articles(tmp_path: Path) -> Path:
    articles_dir = tmp_path / "articles"
    articles_dir.mkdir()
    articles = [
        {
            "id": "2026-05-14-workflow-agent-framework",
            "title": "agent-framework",
            "source": "github",
            "source_url": "https://github.com/example/agent-framework",
            "summary": "一个面向多智能体协作的框架。",
            "score": 9,
            "tags": ["agent", "framework"],
            "analysis": {"technical_category": "AI Agent框架"},
            "updated_at": "2026-05-14T09:00:00",
        },
        {
            "id": "2026-05-13-workflow-rag-tools",
            "title": "rag-tools",
            "source": "github",
            "source_url": "https://github.com/example/rag-tools",
            "summary": "检索增强生成工具集合。",
            "score": 7,
            "tags": ["RAG", "retrieval"],
            "analysis": {"technical_category": "知识库工具"},
            "updated_at": "2026-05-13T09:00:00",
        },
        {
            "id": "2026-05-14-workflow-browser-agent",
            "title": "browser-agent",
            "source": "github",
            "url": "https://github.com/example/browser-agent",
            "summary": "浏览器自动化智能体。",
            "relevance_score": 0.8,
            "tags": ["browser", "automation"],
            "analysis": {"technical_category": "自动化 Agent"},
            "updated_at": "2026-05-14T10:00:00",
        },
    ]
    for article in articles:
        write_article(articles_dir, article)
    (articles_dir / "index.json").write_text("[]", encoding="utf-8")
    return articles_dir


def test_recognize_intent_prefers_commands_and_extracts_payload() -> None:
    assert recognize_intent("/search MCP") == (Intent.SEARCH, "MCP")
    assert recognize_intent("/today") == (Intent.BROWSE_TODAY, "")
    assert recognize_intent("/top 3") == (Intent.BROWSE_TOP, "3")
    assert recognize_intent("/subscribe agent") == (Intent.SUBSCRIBE, "agent")
    assert recognize_intent("/help") == (Intent.HELP, "")


def test_recognize_intent_supports_natural_language() -> None:
    assert recognize_intent("搜一下 RAG") == (Intent.SEARCH, "RAG")
    assert recognize_intent("今天有什么新内容")[0] == Intent.BROWSE_TODAY
    assert recognize_intent("推荐高分项目")[0] == Intent.BROWSE_TOP
    assert recognize_intent("订阅 agent")[0] == Intent.SUBSCRIBE
    assert recognize_intent("随便聊聊")[0] == Intent.UNKNOWN


def test_search_engine_weights_title_tags_summary_and_category(tmp_path: Path) -> None:
    articles_dir = make_articles(tmp_path)
    engine = KnowledgeSearchEngine(articles_dir)

    results = engine.search(keyword="agent", limit=2)

    assert [item["title"] for item in results] == [
        "agent-framework",
        "browser-agent",
    ]
    assert results[0]["_match_score"] > results[1]["_match_score"]


def test_search_engine_filters_tags_and_dates(tmp_path: Path) -> None:
    articles_dir = make_articles(tmp_path)
    engine = KnowledgeSearchEngine(articles_dir)

    by_tag = engine.search(tags=["RAG"])
    today = engine.search(date_from="2026-05-14")

    assert [item["title"] for item in by_tag] == ["rag-tools"]
    assert {item["title"] for item in today} == {
        "agent-framework",
        "browser-agent",
    }


def test_format_search_results_includes_score_tags_and_url(tmp_path: Path) -> None:
    articles_dir = make_articles(tmp_path)
    engine = KnowledgeSearchEngine(articles_dir)

    text = format_search_results(engine.search(keyword="agent", limit=1), query="agent")

    assert "找到 1 条与「agent」相关的内容" in text
    assert "agent-framework" in text
    assert "9/10" in text
    assert "https://github.com/example/agent-framework" in text


def test_subscription_requires_write_permission(tmp_path: Path) -> None:
    bot = KnowledgeBot(
        knowledge_dir=make_articles(tmp_path),
        data_dir=tmp_path / "bot-data",
        writable_users={"admin"},
    )

    denied = bot.handle_message("reader", "/subscribe agent")
    accepted = bot.handle_message("admin", "/subscribe agent")

    assert "没有订阅权限" in denied
    assert "已订阅" in accepted


def test_bot_handles_help_search_today_and_top(tmp_path: Path) -> None:
    bot = KnowledgeBot(knowledge_dir=make_articles(tmp_path), data_dir=tmp_path / "bot-data")

    assert "/search" in bot.handle_message("reader", "/help")
    assert "agent-framework" in bot.handle_message("reader", "/search agent")
    assert "今日知识库" in bot.handle_message("reader", "/today 2026-05-14")
    assert "Top 2" in bot.handle_message("reader", "/top 2")


def test_managers_persist_subscriptions_and_permissions(tmp_path: Path) -> None:
    manager = SubscriptionManager(tmp_path)
    manager.subscribe("user-1", "agent")

    reloaded = SubscriptionManager(tmp_path)
    permissions = PermissionManager(writable_users={"admin"}, deletable_users={"owner"})

    assert reloaded.list_subscriptions("user-1") == ["agent"]
    assert permissions.has_permission("anyone", PermissionLevel.READ)
    assert permissions.has_permission("admin", PermissionLevel.WRITE)
    assert not permissions.has_permission("admin", PermissionLevel.DELETE)
    assert permissions.has_permission("owner", PermissionLevel.DELETE)
