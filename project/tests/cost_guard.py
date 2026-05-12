"""CostGuard：多 Agent 预算守卫。

三重保护：成本追踪、预警提醒、预算熔断。
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class CostRecord:
    """单次 LLM 调用的成本记录。"""

    timestamp: float
    node_name: str
    prompt_tokens: int
    completion_tokens: int
    cost_yuan: float
    model: str = ""


class BudgetExceededError(Exception):
    """预算超标时抛出的熔断异常。"""


class CostGuard:
    """成本守卫：记录调用成本，接近预算时预警，超预算时熔断。"""

    def __init__(
        self,
        budget_yuan: float = 1.0,
        alert_threshold: float = 0.8,
        input_price_per_million: float = 1.0,
        output_price_per_million: float = 2.0,
    ) -> None:
        self.budget_yuan = budget_yuan
        self.alert_threshold = alert_threshold
        self.input_price = input_price_per_million
        self.output_price = output_price_per_million
        self.records: list[CostRecord] = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_yuan = 0.0
        self._alert_fired = False

    def record(self, node_name: str, usage: dict, model: str = "") -> CostRecord:
        """记录一次 LLM 调用的 token 用量和估算成本。"""

        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        cost = (
            prompt_tokens * self.input_price
            + completion_tokens * self.output_price
        ) / 1_000_000
        record = CostRecord(
            timestamp=time.time(),
            node_name=node_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_yuan=cost,
            model=model,
        )

        self.records.append(record)
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_cost_yuan += cost
        return record

    def check(self) -> dict[str, Any]:
        """检查预算状态；超预算时抛出 BudgetExceededError。"""

        usage_ratio = self.total_cost_yuan / self.budget_yuan if self.budget_yuan > 0 else 0
        if self.total_cost_yuan >= self.budget_yuan:
            raise BudgetExceededError(
                f"成本已超出预算！当前: ¥{self.total_cost_yuan:.4f}, "
                f"预算: ¥{self.budget_yuan:.2f}"
            )

        if usage_ratio >= self.alert_threshold and not self._alert_fired:
            self._alert_fired = True
            status = "warning"
            message = f"[预警] 成本已达预算的 {usage_ratio:.0%}！"
        else:
            status = "ok"
            message = f"成本正常: ¥{self.total_cost_yuan:.4f} / ¥{self.budget_yuan:.2f}"

        return {
            "status": status,
            "total_cost": round(self.total_cost_yuan, 6),
            "budget": self.budget_yuan,
            "usage_ratio": round(usage_ratio, 4),
            "message": message,
        }

    def get_report(self) -> dict:
        """生成成本报告，并按节点聚合成本。"""

        cost_by_node: dict[str, float] = {}
        for record in self.records:
            cost_by_node[record.node_name] = (
                cost_by_node.get(record.node_name, 0.0) + record.cost_yuan
            )

        return {
            "total_cost_yuan": round(self.total_cost_yuan, 6),
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_calls": len(self.records),
            "budget_yuan": self.budget_yuan,
            "cost_by_node": {
                node_name: round(cost, 6)
                for node_name, cost in cost_by_node.items()
            },
            "records": [asdict(record) for record in self.records],
        }

    def save_report(self, path: str | Path | None = None) -> Path:
        """保存成本报告到 JSON 文件。"""

        report_path = Path(path) if path is not None else Path("cost_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(self.get_report(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return report_path


def _run_self_test() -> None:
    """直接运行本文件时展示课程版三项检查。"""

    print("=== 测试 1：成本追踪 ===")
    guard = CostGuard(budget_yuan=1.0)
    guard.record("collect", {"prompt_tokens": 100, "completion_tokens": 50})
    guard.record("analyze", {"prompt_tokens": 2_000, "completion_tokens": 1_000})
    guard.record("review", {"prompt_tokens": 2_500, "completion_tokens": 800})
    report = guard.get_report()
    print(f"  调用次数: {report['total_calls']}")
    print(f"  总成本: ¥{report['total_cost_yuan']}")
    print(f"  按节点: {report['cost_by_node']}")
    result = guard.check()
    print(f"  预算状态: {result['status']}\n")

    print("=== 测试 2：预算超限 ===")
    guard2 = CostGuard(budget_yuan=0.001)
    guard2.record("analyze", {"prompt_tokens": 100_000, "completion_tokens": 100_000})
    try:
        guard2.check()
        raise AssertionError("应该抛出 BudgetExceededError")
    except BudgetExceededError as exc:
        print(f"  预算超限检测通过: {exc}\n")

    print("=== 测试 3：预警阈值 ===")
    guard3 = CostGuard(budget_yuan=0.01, alert_threshold=0.5)
    guard3.record("analyze", {"prompt_tokens": 5_000, "completion_tokens": 2_000})
    result3 = guard3.check()
    print(f"  预警状态: {result3['status']} - {result3['message']}\n")
    print("所有测试通过！")


if __name__ == "__main__":
    _run_self_test()
