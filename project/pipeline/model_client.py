"""统一 LLM 客户端。

通过 OpenAI 兼容接口封装 DeepSeek、Qwen、OpenAI 三类模型提供商，
为后续 Pipeline、模型路由和成本统计提供稳定入口。
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Usage:
    """Token 用量统计。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMResponse:
    """统一的 LLM 响应结构。"""

    content: str
    usage: Usage = field(default_factory=Usage)
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage.to_dict(),
        }


PRICING: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 0.00027, "output": 0.00110},
    "deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
    "qwen-plus": {"input": 0.0008, "output": 0.0020},
    "qwen-turbo": {"input": 0.0003, "output": 0.0006},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.0100},
}


PROVIDER_PRICING_CNY: dict[str, dict[str, float]] = {
    "deepseek": {"input": 1.0, "output": 2.0},
    "qwen": {"input": 4.0, "output": 12.0},
    "openai": {"input": 150.0, "output": 600.0},
}


def estimate_cost(model: str, usage: Usage) -> float:
    """按模型名估算单次调用成本，单位 USD。"""

    prices = PRICING.get(model, {"input": 0.001, "output": 0.003})
    return (
        usage.prompt_tokens / 1000 * prices["input"]
        + usage.completion_tokens / 1000 * prices["output"]
    )


class CostTracker:
    """追踪 LLM 调用的 token 消耗和人民币成本。"""

    def __init__(self) -> None:
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []

    def record(
        self,
        usage: Usage | dict[str, int],
        provider: str = "deepseek",
        model: str = "",
    ) -> None:
        """记录一次 API 调用的 token 消耗。"""

        if isinstance(usage, Usage):
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
        else:
            input_tokens = int(usage.get("prompt_tokens", 0) or 0)
            output_tokens = int(usage.get("completion_tokens", 0) or 0)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.call_count += 1
        self.calls.append(
            {
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )

    def estimated_cost(self, provider: str = "deepseek") -> float:
        """估算累计成本，单位为元。"""

        pricing = PROVIDER_PRICING_CNY.get(provider, PROVIDER_PRICING_CNY["deepseek"])
        input_cost = self.total_input_tokens * pricing["input"] / 1_000_000
        output_cost = self.total_output_tokens * pricing["output"] / 1_000_000
        return input_cost + output_cost

    def report(self, provider: str = "deepseek") -> str:
        """生成并打印 Token 消耗报告。"""

        total_tokens = self.total_input_tokens + self.total_output_tokens
        cost = self.estimated_cost(provider)
        lines = [
            "",
            "=" * 40,
            "Token 消耗报告",
            "=" * 40,
            f"调用次数: {self.call_count}",
            f"输入 tokens: {self.total_input_tokens:,}",
            f"输出 tokens: {self.total_output_tokens:,}",
            f"总 tokens: {total_tokens:,}",
            f"估算成本: {cost:.4f} 元",
            f"计价 provider: {provider}",
            "=" * 40,
        ]
        report_text = "\n".join(lines)
        print(report_text)
        return report_text


tracker = CostTracker()


class LLMProvider(ABC):
    """LLM 提供商抽象基类。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        provider_name: str = "deepseek",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.provider_name = provider_name
        self.client = httpx.Client(timeout=60.0)

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """发送聊天请求并返回统一响应。"""

    def close(self) -> None:
        self.client.close()


class OpenAICompatibleProvider(LLMProvider):
    """使用 OpenAI Chat Completions 格式的模型提供商。"""

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage_data = data.get("usage", {})
        usage = Usage(
            prompt_tokens=int(usage_data.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage_data.get("completion_tokens", 0) or 0),
        )
        return LLMResponse(content=content, usage=usage, model=self.model)


PROVIDER_CONFIG: dict[str, dict[str, str]] = {
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "model_env": "DEEPSEEK_MODEL",
        "default_base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
    },
    "qwen": {
        "api_key_env": "QWEN_API_KEY",
        "base_url_env": "QWEN_BASE_URL",
        "model_env": "QWEN_MODEL",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "model_env": "OPENAI_MODEL",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
}


def create_provider(provider_name: str | None = None) -> LLMProvider:
    """根据环境变量或参数创建模型客户端。"""

    name = (provider_name or os.getenv("LLM_PROVIDER", "deepseek")).lower()
    if name not in PROVIDER_CONFIG:
        raise ValueError(f"未知的模型提供商: {name}")

    config = PROVIDER_CONFIG[name]
    api_key = os.getenv(config["api_key_env"], "")
    if not api_key:
        raise RuntimeError(f"缺少 API Key，请设置环境变量: {config['api_key_env']}")

    base_url = os.getenv(config["base_url_env"], config["default_base_url"])
    model = os.getenv(config["model_env"], config["default_model"])
    logger.info("创建 LLM 客户端: provider=%s, model=%s", name, model)
    return OpenAICompatibleProvider(
        api_key=api_key,
        base_url=base_url,
        model=model,
        provider_name=name,
    )


def chat_with_retry(
    provider: LLMProvider,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    max_retries: int = 3,
    backoff_base: float = 2.0,
) -> LLMResponse:
    """带指数退避的聊天调用。"""

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = provider.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            tracker.record(
                response.usage,
                provider=provider.provider_name,
                model=provider.model,
            )
            if attempt > 0:
                logger.info("第 %d 次重试成功", attempt)
            return response
        except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as exc:
            last_error = exc
            if attempt >= max_retries - 1:
                break
            wait_time = backoff_base**attempt
            logger.warning(
                "LLM 调用失败，第 %d/%d 次，%.1fs 后重试: %s",
                attempt + 1,
                max_retries,
                wait_time,
                exc,
            )
            time.sleep(wait_time)

    raise RuntimeError("LLM 调用失败，已达到最大重试次数") from last_error


def quick_chat(
    prompt: str,
    system: str = "你是一个 AI 技术分析助手。",
    provider_name: str | None = None,
) -> str:
    """一句话调用 LLM，返回纯文本。"""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    provider = create_provider(provider_name)
    try:
        response = chat_with_retry(provider, messages)
        cost = estimate_cost(provider.model, response.usage)
        logger.info(
            "Token 用量: %d + %d = %d，估算成本: $%.6f",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            response.usage.total_tokens,
            cost,
        )
        return response.content
    finally:
        provider.close()


def chat(
    prompt: str,
    system: str = "你是一个 AI 技术分析助手。",
    provider: str | None = None,
    max_retries: int = 3,
) -> dict[str, Any]:
    """便捷调用 LLM，返回字典格式。"""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    llm = create_provider(provider)
    try:
        response = chat_with_retry(llm, messages, max_retries=max_retries)
        return response.to_dict()
    finally:
        llm.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        result = quick_chat("用一句话介绍什么是 AI Agent。")
        logger.info("回复: %s", result)
    except Exception as exc:
        logger.error("调用失败: %s", exc)
