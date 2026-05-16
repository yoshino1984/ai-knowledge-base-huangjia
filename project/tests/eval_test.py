"""Eval 评估测试：验证 AI 知识库分析行为边界。

核心原则：不测精确文本，测试输出长度、关键词、边界输入和 LLM-as-Judge 分数。
"""

from __future__ import annotations

import json
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Any

import pytest

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = PROJECT_ROOT / "project"
sys.path.insert(0, str(PROJECT_DIR / "pipeline"))

if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")

warnings.filterwarnings("ignore", category=pytest.PytestUnknownMarkWarning)

from model_client import chat


EVAL_CASES = [
    {
        "name": "正面案例 - 技术项目分析",
        "input": "LangGraph 是一个基于有向图的多 Agent 工作流编排框架，支持条件分支和循环。",
        "expected": {
            "min_length": 50,
            "max_length": 1000,
            "must_contain_any": ["LangGraph", "工作流", "Agent", "图"],
        },
    },
    {
        "name": "负面案例 - 无关内容",
        "input": "今天天气真好，适合出去散步，顺便买一杯咖啡。",
        "expected": {
            "max_relevance_score": 0.4,
            "min_reason_length": 8,
        },
    },
    {
        "name": "边界案例 - 极短输入",
        "input": "AI",
        "expected": {
            "min_length": 1,
            "no_crash": True,
        },
    },
    {
        "name": "正面案例 - 英文技术内容",
        "input": "OpenAI released models with long context windows and native tool use.",
        "expected": {
            "min_length": 30,
            "must_contain_any": ["OpenAI", "模型", "上下文", "工具"],
        },
    },
]


def _chat_content(prompt: str, system: str, max_retries: int = 2) -> str:
    """调用项目统一 LLM 客户端，并取出 content。"""

    result = chat(prompt, system=system, max_retries=max_retries)
    return str(result.get("content", ""))


def _extract_json_object(text: str) -> dict[str, Any]:
    """从模型输出中解析 JSON 对象。"""

    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def test_eval_cases_structure() -> None:
    """本地验证：EVAL_CASES 至少覆盖正面、负面、边界三类场景。"""

    assert len(EVAL_CASES) >= 3
    names = [case["name"] for case in EVAL_CASES]
    assert any("正面" in name for name in names)
    assert any("负面" in name for name in names)
    assert any("边界" in name for name in names)

    for case in EVAL_CASES:
        assert isinstance(case.get("name"), str) and case["name"]
        assert isinstance(case.get("input"), str)
        assert isinstance(case.get("expected"), dict)


@pytest.mark.slow
def test_eval_positive_technical_content() -> None:
    """正面案例：技术内容应生成有意义的摘要。"""

    case = EVAL_CASES[0]
    result = _chat_content(
        f"请分析以下技术内容，输出 200 字以内中文摘要：\n{case['input']}",
        system="你是技术分析师。",
    )

    expected = case["expected"]
    assert len(result) >= expected["min_length"]
    assert len(result) <= expected["max_length"]
    assert any(keyword in result for keyword in expected["must_contain_any"])


@pytest.mark.slow
def test_eval_negative_irrelevant_content() -> None:
    """负面案例：无关内容应被识别为低相关。"""

    case = EVAL_CASES[1]
    result = _chat_content(
        f"""请判断以下内容是否与 AI 技术相关，并返回严格 JSON：
内容：{case['input']}

返回格式：
{{"relevance_score": 0.0, "reason": "一句话说明"}}""",
        system="你是技术内容筛选器，只返回 JSON。",
    )
    parsed = _extract_json_object(result)

    expected = case["expected"]
    assert float(parsed.get("relevance_score", 1.0)) <= expected["max_relevance_score"]
    reason = str(parsed.get("reason", "")).strip()
    assert len(reason) >= expected["min_reason_length"]


@pytest.mark.slow
def test_eval_boundary_short_input_does_not_crash() -> None:
    """边界案例：极短输入不应导致分析流程崩溃。"""

    case = EVAL_CASES[2]
    result = _chat_content(
        f"请分析：{case['input']}",
        system="你是技术分析师。即使输入很短，也要给出简短判断。",
    )

    assert result is not None
    assert len(result) >= case["expected"]["min_length"]


@pytest.mark.slow
def test_llm_as_judge_scores_analysis_quality() -> None:
    """LLM-as-Judge：用模型评估一段分析是否达到基本质量。"""

    analysis = _chat_content(
        "请分析 LangGraph 框架的核心优势和适用场景，输出 200 字以内。",
        system="你是技术分析师。",
    )
    score_text = _chat_content(
        f"""请对以下技术分析质量打分，范围 1-10。

评分标准：
- 准确性
- 深度
- 实用性

分析内容：
{analysis}

只返回一个数字。""",
        system="你是质量评审，只返回数字。",
    )

    match = re.search(r"\d+", score_text)
    score = int(match.group()) if match else 0
    assert 1 <= score <= 10
    assert score >= 5


if __name__ == "__main__":
    test_eval_cases_structure()
    print("=== 本地验证（不消耗 token）===")
    print(f"[OK] EVAL_CASES 结构验证通过，共 {len(EVAL_CASES)} 个用例")
    for case in EVAL_CASES:
        print(f"  - {case['name']}")
    print("\n运行完整 LLM Eval：")
    print("  LLM_PROVIDER=deepseek pytest project/tests/eval_test.py -m slow -v")
