"""LangGraph 状态定义：AI 知识库工作流的共享数据契约。"""

from typing import TypedDict


class KBState(TypedDict):
    """知识库工作流的全局状态。

    数据流向：plan -> sources -> analyses -> review -> articles -> save。
    每个字段都保存结构化报告，避免节点之间传递不可控的长文本上下文。
    """

    plan: dict  # Planner 输出的执行策略，例如采集数量、过滤阈值、最大审核轮次。
    sources: list[dict]  # 采集结果，来自 GitHub API、RSS 等外部数据源。
    analyses: list[dict]  # LLM 分析结果，每条通常包含 summary、tags、score。
    articles: list[dict]  # 整理后的知识条目，已完成过滤、去重和字段标准化。
    review_feedback: str  # 审核反馈，说明需要修改的具体问题。
    review_passed: bool  # 审核是否通过，作为条件边路由依据。
    iteration: int  # 审核循环次数，避免 review -> organize 无限循环。
    needs_human_review: bool  # 是否需要人工复核，由 HumanFlag 节点设置。
    cost_tracker: dict  # Token 和成本统计，例如 prompt_tokens、completion_tokens、total_cost_yuan。
