"""Formatter 模块行为测试。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from project.distribution.formatter import (
    generate_daily_digest,
    json_to_feishu,
    json_to_markdown,
    json_to_weixin,
)


class FormatterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.article = {
            "id": "2026-05-14-workflow-demo-agent",
            "title": "demo/agent-tool",
            "source": "github",
            "source_url": "https://github.com/demo/agent-tool",
            "summary": "一个用于测试的 AI Agent 工具，支持知识库检索和多渠道分发。",
            "score": 8,
            "tags": ["AI Agent", "知识库", "微信"],
            "analysis": {
                "technical_category": "AI Agent框架",
                "innovation": "用统一格式化层把 JSON 转成不同渠道内容。",
            },
            "updated_at": "2026-05-14T12:00:00+00:00",
        }

    def test_json_to_markdown_contains_core_fields(self) -> None:
        output = json_to_markdown(self.article)

        self.assertIn("## demo/agent-tool", output)
        self.assertIn("github", output)
        self.assertIn("🟢 8/10", output)
        self.assertIn("`AI Agent`", output)
        self.assertIn("https://github.com/demo/agent-tool", output)

    def test_json_to_weixin_is_readable_plain_text(self) -> None:
        output = json_to_weixin(self.article)

        self.assertIn("demo/agent-tool", output)
        self.assertIn("分数：8/10", output)
        self.assertIn("标签：AI Agent、知识库、微信", output)
        self.assertIn("链接：https://github.com/demo/agent-tool", output)

    def test_json_to_feishu_returns_interactive_card(self) -> None:
        card = json_to_feishu(self.article)

        self.assertEqual(card["msg_type"], "interactive")
        self.assertEqual(card["card"]["header"]["template"], "green")
        self.assertIn("demo/agent-tool", card["card"]["header"]["title"]["content"])

    def test_generate_daily_digest_returns_three_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            article_dir = Path(temp_dir)
            article = dict(self.article)
            article["id"] = "2026-05-14-workflow-demo-agent"
            (article_dir / f"{article['id']}.json").write_text(
                json.dumps(article, ensure_ascii=False),
                encoding="utf-8",
            )

            result = generate_daily_digest(article_dir, date="2026-05-14", top_n=3)

        self.assertEqual(set(result), {"markdown", "weixin", "feishu"})
        self.assertIn("2026-05-14 AI 知识简报", result["markdown"])
        self.assertIn("demo/agent-tool", result["weixin"])
        self.assertEqual(result["feishu"]["msg_type"], "interactive")

    def test_generate_daily_digest_handles_empty_day(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = generate_daily_digest(temp_dir, date="2026-05-14")

        self.assertIn("暂无新增知识条目", result["markdown"])
        self.assertIn("暂无新增知识条目", result["weixin"])


if __name__ == "__main__":
    unittest.main()
