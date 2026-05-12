"""HumanFlag Agent：审核循环超限后的人工复核兜底节点。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from project.workflows.state import KBState


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PENDING_DIR = PROJECT_ROOT / "knowledge" / "pending_review"


def human_flag_node(state: KBState) -> dict:
    """保存待人工复核数据，并标记 needs_human_review。"""

    analyses = state.get("analyses", [])
    iteration = state.get("iteration", 0)
    feedback = state.get("review_feedback", "")

    print(f"[HumanFlag] 达到 {iteration} 次审核仍未通过")
    print(f"[HumanFlag] 最后反馈: {feedback[:200]}")

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    file_path = PENDING_DIR / f"pending-{timestamp}.json"
    payload = {
        "timestamp": timestamp,
        "iterations_used": iteration,
        "last_feedback": feedback,
        "analyses": analyses,
    }
    file_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[HumanFlag] 已保存到 {file_path}")
    return {"needs_human_review": True}
