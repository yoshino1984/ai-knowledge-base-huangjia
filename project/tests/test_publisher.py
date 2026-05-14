"""Publisher 模块行为测试。"""

from __future__ import annotations

import unittest

from project.distribution.publisher import (
    DryRunPublisher,
    OpenClawPublisher,
    PublishResult,
    publish_daily_digest,
)


class PublisherTest(unittest.IsolatedAsyncioTestCase):
    async def test_dry_run_publisher_returns_success_without_network(self) -> None:
        publisher = DryRunPublisher(channel="weixin")

        result = await publisher.send_message(content="hello")

        self.assertTrue(result.success)
        self.assertEqual(result.channel, "weixin")
        self.assertEqual(result.message_id, "dry-run")

    async def test_openclaw_publisher_builds_message_send_command(self) -> None:
        captured: list[list[str]] = []

        async def fake_runner(command: list[str]) -> tuple[int, str, str]:
            captured.append(command)
            return 0, '{"ok": true, "messageId": "m-1"}', ""

        publisher = OpenClawPublisher(
            channel="openclaw-weixin",
            target="filehelper",
            runner=fake_runner,
        )

        result = await publisher.send_message(content="hello")

        self.assertTrue(result.success)
        self.assertEqual(result.message_id, "m-1")
        self.assertEqual(captured[0][:4], ["openclaw", "message", "send", "--channel"])
        self.assertIn("openclaw-weixin", captured[0])
        self.assertIn("filehelper", captured[0])
        self.assertIn("hello", captured[0])

    async def test_openclaw_publisher_reports_missing_target(self) -> None:
        publisher = OpenClawPublisher(channel="openclaw-weixin", target="")

        result = await publisher.send_message(content="hello")

        self.assertFalse(result.success)
        self.assertIn("缺少推送目标", result.error or "")

    async def test_publish_daily_digest_supports_dry_run(self) -> None:
        results = await publish_daily_digest(
            knowledge_dir="project/knowledge/articles",
            date="2099-01-01",
            channels=["weixin"],
            dry_run=True,
        )

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], PublishResult)
        self.assertTrue(results[0].success)
        self.assertEqual(results[0].channel, "weixin")


if __name__ == "__main__":
    unittest.main()
