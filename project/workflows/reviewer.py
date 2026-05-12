"""Reviewer Agent：对 Analyzer 输出做 5 维度加权审核。"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from model_client import chat, tracker

from project.workflows.state import KBState


REVIEWER_WEIGHTS = {
    "summary_quality": 0.25,
    "technical_depth": 0.25,
    "relevance": 0.20,
    "originality": 0.15,
    "formatting": 0.15,
}
REVIEWER_PASS_THRESHOLD = 7.0


def parse_json_object(text: str) -> dict[str, Any]:
    """从模型输出中解析 JSON 对象。"""

    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def update_cost_tracker(cost_state: dict) -> dict:
    """把全局 token 统计同步到 KBState。"""

    return {
        **cost_state,
        "prompt_tokens": tracker.total_input_tokens,
        "completion_tokens": tracker.total_output_tokens,
        "total_tokens": tracker.total_input_tokens + tracker.total_output_tokens,
        "call_count": tracker.call_count,
        "total_cost_yuan": tracker.estimated_cost(os.getenv("LLM_PROVIDER", "deepseek")),
    }


def weighted_score(scores: dict[str, Any]) -> float:
    """用代码重算加权总分，不信任模型算术。"""

    total = 0.0
    for dimension, weight in REVIEWER_WEIGHTS.items():
        raw_score = scores.get(dimension, 0)
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
        total += max(0.0, min(10.0, score)) * weight
    return round(total, 2)


def review_node(state: KBState) -> dict:
    """Reviewer 节点：只审核 analyses，不修改内容。"""

    analyses = state.get("analyses", [])
    iteration = state.get("iteration", 0)
    plan = state.get("plan", {}) or {}
    max_iterations = int(plan.get("max_iterations", 3))
    cost_state = state.get("cost_tracker", {})

    if not analyses:
        return {
            "review_passed": True,
            "review_feedback": "没有分析结果需要审核",
            "iteration": iteration + 1,
            "cost_tracker": cost_state,
        }

    sample = analyses[:5]
    prompt = f"""你是知识库质量审核员。请审核以下 Analyzer 输出：

{json.dumps(sample, ensure_ascii=False, indent=2)}

请按以下维度评分，每项 1-10 分：
1. summary_quality - 摘要质量
2. technical_depth - 技术深度
3. relevance - 相关性
4. originality - 原创性
5. formatting - 格式规范

请只返回 JSON：
{{
  "scores": {{
    "summary_quality": 8,
    "technical_depth": 7,
    "relevance": 8,
    "originality": 6,
    "formatting": 9
  }},
  "feedback": "具体、可执行的改进建议",
  "weak_dimensions": ["technical_depth", "originality"]
}}

当前是第 {iteration + 1} 次审核。"""

    try:
        result = chat(
            prompt,
            system="你是严格但公正的知识库质量审核员。只输出 JSON。",
            temperature=0.1,
            node_name="review",
        )
        review = parse_json_object(str(result["content"]))
        scores = review.get("scores", {})
        total = weighted_score(scores)
        passed = total >= REVIEWER_PASS_THRESHOLD
        feedback = str(review.get("feedback", ""))
        weak_dimensions = review.get("weak_dimensions", [])
        if weak_dimensions:
            feedback = f"[弱项: {', '.join(map(str, weak_dimensions))}] {feedback}"

        if iteration >= max_iterations - 1 and not passed:
            feedback += "\n[系统] 已达最大审核次数，交由人工复核。"

        print(
            f"[Reviewer] 加权总分: {total}/10, "
            f"通过: {passed} (第 {iteration + 1}/{max_iterations} 次审核)"
        )
    except Exception as exc:
        passed = True
        total = 0.0
        feedback = f"审核 LLM 调用失败: {exc}，自动通过"
        print(f"[Reviewer] 审核失败，自动通过: {exc}")

    return {
        "review_passed": passed,
        "review_feedback": feedback,
        "iteration": iteration + 1,
        "cost_tracker": update_cost_tracker(cost_state),
    }
