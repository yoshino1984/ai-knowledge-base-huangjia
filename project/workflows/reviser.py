"""Reviser Agent：根据 Reviewer 反馈定向修改 analyses。"""

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


def parse_json_array(text: str) -> list[dict[str, Any]]:
    """从模型输出中解析 JSON 数组。"""

    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("Reviser 输出不是 JSON 数组")
    return [item for item in data if isinstance(item, dict)]


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


def revise_node(state: KBState) -> dict:
    """Reviser 节点：只修改 analyses，不做质量评估。"""

    analyses = state.get("analyses", [])
    feedback = state.get("review_feedback", "")
    iteration = state.get("iteration", 0)
    cost_state = state.get("cost_tracker", {})

    if not analyses or not feedback:
        print("[Reviser] 无可修改内容，跳过")
        return {}

    prompt = f"""你是知识库编辑。请根据审核反馈定向修改以下分析结果。

审核反馈：
{feedback}

当前分析结果：
{json.dumps(analyses, ensure_ascii=False, indent=2)}

修改要求：
- 重点改进反馈指出的弱项
- 保留已经不错的字段
- 保持相同字段结构
- 只返回修改后的 JSON 数组，不要输出 Markdown"""

    try:
        result = chat(
            prompt,
            system="你是经验丰富的知识库编辑。根据反馈定向修改，不要过度发散。",
            temperature=0.4,
            node_name="revise",
        )
        improved = parse_json_array(str(result["content"]))
        if improved:
            print(f"[Reviser] 定向修改 {len(improved)} 条 analyses (迭代 {iteration})")
            return {
                "analyses": improved,
                "cost_tracker": update_cost_tracker(cost_state),
            }
    except Exception as exc:
        print(f"[Reviser] 修改失败: {exc}")

    return {"cost_tracker": update_cost_tracker(cost_state)}
