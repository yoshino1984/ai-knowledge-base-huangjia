"""多渠道发布模块。

把 formatter 生成的内容发布到 OpenClaw/微信等渠道。默认支持 dry-run，
真实发送通过 `openclaw message send` 完成。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable

from project.distribution.formatter import generate_daily_digest


CommandRunner = Callable[[list[str]], Awaitable[tuple[int, str, str]]]


@dataclass
class PublishResult:
    """单次发布结果。"""

    channel: str
    success: bool
    message_id: str | None = None
    error: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BasePublisher(ABC):
    """发布器抽象基类。"""

    channel: str

    @abstractmethod
    async def send_message(self, content: str, target: str | None = None) -> PublishResult:
        """发送一条消息。"""

    async def send_digest(self, digest_content: dict[str, Any]) -> PublishResult:
        """发送每日简报。"""

        content = str(digest_content.get(self.channel) or digest_content.get("weixin") or "")
        return await self.send_message(content=content)


class DryRunPublisher(BasePublisher):
    """Dry-run 发布器：只打印/返回内容，不触达外部渠道。"""

    def __init__(self, channel: str = "weixin") -> None:
        self.channel = channel

    async def send_message(self, content: str, target: str | None = None) -> PublishResult:
        preview = content[:500]
        print(f"[dry-run:{self.channel}] target={target or '-'}\n{preview}")
        return PublishResult(
            channel=self.channel,
            success=True,
            message_id="dry-run",
        )


class OpenClawPublisher(BasePublisher):
    """通过 OpenClaw CLI 发送消息。"""

    def __init__(
        self,
        channel: str = "openclaw-weixin",
        target: str | None = None,
        account: str | None = None,
        runner: CommandRunner | None = None,
    ) -> None:
        self.channel = channel
        self.target = target or os.getenv("OPENCLAW_WEIXIN_TARGET", "")
        self.account = account or os.getenv("OPENCLAW_ACCOUNT", "")
        self.runner = runner or _run_command

    async def send_message(self, content: str, target: str | None = None) -> PublishResult:
        """调用 `openclaw message send` 发送消息。"""

        destination = target or self.target
        if not destination:
            return PublishResult(
                channel=self.channel,
                success=False,
                error="缺少推送目标，请传入 target 或设置 OPENCLAW_WEIXIN_TARGET",
            )

        command = [
            "openclaw",
            "message",
            "send",
            "--channel",
            self.channel,
            "--target",
            destination,
            "--message",
            content,
            "--json",
        ]
        if self.account:
            command.extend(["--account", self.account])

        return_code, stdout, stderr = await self.runner(command)
        if return_code != 0:
            return PublishResult(
                channel=self.channel,
                success=False,
                error=(stderr or stdout or f"openclaw exited with {return_code}").strip(),
            )

        message_id = _extract_message_id(stdout)
        return PublishResult(
            channel=self.channel,
            success=True,
            message_id=message_id or "sent",
        )


async def _run_command(command: list[str]) -> tuple[int, str, str]:
    """异步执行命令并返回 returncode/stdout/stderr。"""

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    return (
        process.returncode,
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
    )


def _extract_message_id(stdout: str) -> str | None:
    """从 OpenClaw JSON 输出中提取消息 id。"""

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None

    for key in ("messageId", "message_id", "id"):
        value = data.get(key)
        if value:
            return str(value)
    result = data.get("result")
    if isinstance(result, dict):
        for key in ("messageId", "message_id", "id"):
            value = result.get(key)
            if value:
                return str(value)
    return None


def _publisher_for(channel: str, dry_run: bool, target: str | None) -> BasePublisher:
    """根据渠道名创建发布器。"""

    if dry_run:
        return DryRunPublisher(channel=channel)
    if channel in {"weixin", "openclaw-weixin"}:
        return OpenClawPublisher(channel="openclaw-weixin", target=target)
    return OpenClawPublisher(channel=channel, target=target)


async def publish_daily_digest(
    knowledge_dir: str = "project/knowledge/articles",
    date: str | None = None,
    channels: list[str] | None = None,
    top_n: int = 5,
    dry_run: bool = False,
    target: str | None = None,
) -> list[PublishResult]:
    """生成每日简报并发布到指定渠道。"""

    enabled_channels = channels or ["weixin"]
    digest = generate_daily_digest(knowledge_dir=knowledge_dir, date=date, top_n=top_n)
    tasks = []
    for channel in enabled_channels:
        publisher = _publisher_for(channel, dry_run=dry_run, target=target)
        tasks.append(publisher.send_digest(digest))
    return list(await asyncio.gather(*tasks))


def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="发布 AI 知识库每日简报")
    parser.add_argument("--knowledge-dir", default="project/knowledge/articles")
    parser.add_argument("--date", default=None)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--channel", action="append", dest="channels")
    parser.add_argument("--target", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


async def _main() -> None:
    """命令行入口。"""

    args = _parse_args()
    results = await publish_daily_digest(
        knowledge_dir=args.knowledge_dir,
        date=args.date,
        channels=args.channels,
        top_n=args.top_n,
        dry_run=args.dry_run,
        target=args.target,
    )
    for result in results:
        status = "OK" if result.success else "FAIL"
        print(f"[{status}] {result.channel}: {result.message_id or result.error}")


if __name__ == "__main__":
    asyncio.run(_main())
