"""LangGraph 5 节点教学版工作流图。"""

from __future__ import annotations

import os

from langgraph.graph import END, StateGraph

from project.workflows.nodes import (
    analyze_node,
    collect_node,
    organize_node,
    review_node_test,
    save_node,
)
from project.workflows.reviewer import review_node
from project.workflows.state import KBState


def should_continue(state: KBState) -> str:
    """审核通过进入 save，未通过回到 organize。"""

    if state.get("review_passed", False):
        return "save"
    return "organize"


def build_graph():
    """构建知识库 5 节点工作流。"""

    graph = StateGraph(KBState)
    graph.add_node("collect", collect_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("organize", organize_node)
    if os.getenv("KB_REVIEW_TEST") == "1":
        graph.add_node("review", review_node_test)
    else:
        graph.add_node("review", review_node)
    graph.add_node("save", save_node)

    graph.add_edge("collect", "analyze")
    graph.add_edge("analyze", "organize")
    graph.add_edge("organize", "review")
    graph.add_conditional_edges(
        "review",
        should_continue,
        {"save": "save", "organize": "organize"},
    )
    graph.add_edge("save", END)
    graph.set_entry_point("collect")
    return graph.compile()


app = build_graph()


if __name__ == "__main__":
    print("=" * 60)
    print("AI 知识库 - LangGraph 工作流启动")
    print("=" * 60)
    initial_state: KBState = {
        "sources": [],
        "analyses": [],
        "articles": [],
        "review_feedback": "",
        "review_passed": False,
        "iteration": 0,
        "cost_tracker": {},
    }

    for event in app.stream(initial_state):
        node_name = list(event.keys())[0]
        print(f"\n--- [{node_name}] 完成 ---")

    print("\n" + "=" * 60)
    print("工作流执行完毕")
