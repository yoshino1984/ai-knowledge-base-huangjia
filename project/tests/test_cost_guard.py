"""CostGuard 行为测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from project.tests.cost_guard import BudgetExceededError, CostGuard


class CostGuardTest(unittest.TestCase):
    def test_record_accumulates_tokens_and_cost_by_node(self) -> None:
        guard = CostGuard(budget_yuan=1.0)

        guard.record("analyze", {"prompt_tokens": 2_000, "completion_tokens": 1_000})
        guard.record("review", {"prompt_tokens": 500, "completion_tokens": 250})

        report = guard.get_report()
        self.assertEqual(report["total_calls"], 2)
        self.assertEqual(report["total_prompt_tokens"], 2_500)
        self.assertEqual(report["total_completion_tokens"], 1_250)
        self.assertEqual(report["cost_by_node"]["analyze"], 0.004)
        self.assertEqual(report["cost_by_node"]["review"], 0.001)
        self.assertEqual(report["total_cost_yuan"], 0.005)

    def test_check_warns_when_cost_reaches_alert_threshold(self) -> None:
        guard = CostGuard(budget_yuan=0.01, alert_threshold=0.5)

        guard.record("analyze", {"prompt_tokens": 4_000, "completion_tokens": 1_000})

        result = guard.check()
        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["usage_ratio"], 0.6)

    def test_check_raises_when_budget_is_exceeded(self) -> None:
        guard = CostGuard(budget_yuan=0.001)

        guard.record("analyze", {"prompt_tokens": 1_000, "completion_tokens": 1_000})

        with self.assertRaises(BudgetExceededError):
            guard.check()

    def test_save_report_writes_json_report(self) -> None:
        guard = CostGuard(budget_yuan=1.0)
        guard.record("review", {"prompt_tokens": 100, "completion_tokens": 50})

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "cost-report.json"
            saved_path = guard.save_report(report_path)

        self.assertEqual(saved_path, report_path)


if __name__ == "__main__":
    unittest.main()
