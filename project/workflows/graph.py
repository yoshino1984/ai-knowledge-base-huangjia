"""LangGraph 7 节点教学版工作流图。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from langgraph.graph import END, StateGraph

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COST_REPORT_PATH = PROJECT_ROOT / "knowledge" / "cost-report.json"
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
from model_client import BudgetExceededError, get_cost_guard

from project.workflows.human_flag import human_flag_node
from project.workflows.nodes import (
    analyze_node,
    collect_node,
    organize_node,
    review_node_test,
    save_node,
)
from project.workflows.planner import planner_node
from project.workflows.reviewer import review_node
from project.workflows.reviser import revise_node
from project.workflows.state import KBState


def route_after_review(state: KBState) -> str:
    """审核后 3 路分支：通过、修正、人工复核。"""

    plan = state.get("plan", {}) or {}
    max_iterations = int(plan.get("max_iterations", 3))
    if state.get("review_passed", False):
        return "organize"
    if state.get("iteration", 0) >= max_iterations:
        return "human_flag"
    return "revise"


def build_graph():
    """构建知识库 7 节点工作流。"""

    graph = StateGraph(KBState)
    graph.add_node("plan", planner_node)
    graph.add_node("collect", collect_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("organize", organize_node)
    if os.getenv("KB_REVIEW_TEST") == "1":
        graph.add_node("review", review_node_test)
    else:
        graph.add_node("review", review_node)
    graph.add_node("revise", revise_node)
    graph.add_node("save", save_node)
    graph.add_node("human_flag", human_flag_node)

    graph.add_edge("plan", "collect")
    graph.add_edge("collect", "analyze")
    graph.add_edge("analyze", "review")
    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "organize": "organize",
            "revise": "revise",
            "human_flag": "human_flag",
        },
    )
    graph.add_edge("revise", "review")
    graph.add_edge("organize", "save")
    graph.add_edge("save", END)
    graph.add_edge("human_flag", END)
    graph.set_entry_point("plan")
    return graph.compile()


app = build_graph()


if __name__ == "__main__":
    print("=" * 60)
    print("AI 知识库 - LangGraph 工作流启动")
    print("=" * 60)
    initial_state: KBState = {
        "plan": {},
        "sources": [],
        "analyses": [],
        "articles": [],
        "review_feedback": "",
        "review_passed": False,
        "iteration": 0,
        "needs_human_review": False,
        "cost_tracker": {},
    }

    try:
        for event in app.stream(initial_state):
            node_name = list(event.keys())[0]
            print(f"\n--- [{node_name}] 完成 ---")
        print("\n" + "=" * 60)
        print("工作流执行完毕")
    except BudgetExceededError as exc:
        print(f"\n[FATAL] 预算熔断触发: {exc}")
    finally:
        guard = get_cost_guard()
        report = guard.get_report()
        print(
            f"\n[CostGuard] 总调用 {report['total_calls']} 次 · "
            f"总成本 ¥{report['total_cost_yuan']}"
        )
        print(f"[CostGuard] 按节点: {report['cost_by_node']}")
        guard.save_report(COST_REPORT_PATH)
        print(f"[CostGuard] 报告已保存: {COST_REPORT_PATH}")
