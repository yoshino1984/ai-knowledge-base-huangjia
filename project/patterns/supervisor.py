"""Supervisor 模式：Worker 执行，Supervisor 审核，必要时反馈重做。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from model_client import chat


WORKER_SYSTEM = """你是 AI 技术分析师。
请按要求完成分析任务，输出严格 JSON，包含：
- summary: 一段摘要
- key_points: 3-5 个关键点
- recommendation: 具体建议
不要输出 Markdown 代码块。"""

SUPERVISOR_SYSTEM = """你是质量审核专家，请审核分析报告。

评分维度（每项 1-10）：
1. 准确性：信息是否准确无误
2. 深度：分析是否有洞察力
3. 格式：是否符合 JSON 规范，结构是否清晰

请只输出严格 JSON：
{"passed": true/false, "score": 1-10, "feedback": "具体改进建议"}"""


def parse_json_object(text: str) -> dict[str, Any]:
    """从模型输出中提取 JSON 对象。"""

    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


def run_worker(task: str, previous_output: str | None = None, feedback: str = "") -> str:
    """运行 Worker；如果有反馈，则按反馈修正上次输出。"""

    if previous_output is None:
        prompt = task
    else:
        prompt = (
            f"原始任务：{task}\n\n"
            f"上次产出：{previous_output}\n\n"
            f"审核反馈：{feedback}\n\n"
            "请根据反馈改进，保持严格 JSON 格式。"
        )
    result = chat(prompt, system=WORKER_SYSTEM)
    return str(result["content"])


def run_supervisor(worker_output: str) -> dict[str, Any]:
    """运行 Supervisor 审核 Worker 输出。"""

    review_prompt = f"请审核以下分析报告：\n{worker_output}"
    result = chat(review_prompt, system=SUPERVISOR_SYSTEM)
    try:
        review = parse_json_object(str(result["content"]))
    except json.JSONDecodeError:
        return {
            "passed": False,
            "score": 0,
            "feedback": "审核输出不是合法 JSON，请重新生成并确保格式正确。",
        }

    score = int(review.get("score", 0) or 0)
    return {
        "passed": bool(review.get("passed", False)) or score >= 7,
        "score": score,
        "feedback": str(review.get("feedback", "请提升准确性、深度和格式质量。")),
    }


def supervisor(task: str, max_retries: int = 3) -> dict[str, Any]:
    """监督模式入口：最多审核并返工 max_retries 轮。"""

    worker_output: str | None = None
    feedback = ""
    final_score = 0

    for attempt in range(1, max_retries + 1):
        worker_output = run_worker(task, previous_output=worker_output, feedback=feedback)
        review = run_supervisor(worker_output)
        final_score = int(review.get("score", 0) or 0)
        feedback = str(review.get("feedback", "请改进质量。"))
        print(f"第 {attempt} 轮审核: 得分 {final_score}/10")

        if review.get("passed", False):
            return {
                "output": worker_output,
                "attempts": attempt,
                "final_score": final_score,
            }

    return {
        "output": worker_output or "",
        "attempts": max_retries,
        "final_score": final_score,
        "warning": f"达到最大重试次数({max_retries})，可能质量不达标",
    }


if __name__ == "__main__":
    task = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else "请分析 LangGraph 框架的优缺点和适用场景"
    )
    print("=" * 50)
    print("Supervisor 监督模式测试")
    print("=" * 50)
    result = supervisor(task)
    print("\n最终结果:")
    print(f"审核轮次: {result['attempts']}")
    print(f"最终得分: {result['final_score']}/10")
    if result.get("warning"):
        print(f"警告: {result['warning']}")
    print(f"输出预览: {result['output'][:200]}...")
