import unittest
from unittest.mock import patch

from src.integrations.portfolio_logic import build_portfolio_snapshot
from src.integrations.portfolio_runtime import get_portfolio_compliance_summary


class PortfolioRuntimeApiTests(unittest.TestCase):
    def test_current_compliance_summary_uses_current_state(self) -> None:
        snapshot = build_portfolio_snapshot(
            as_of_date="2024-08-01",
            cash=20.0,
            positions=[
                {"ticker": "AAPL", "qty": 2, "close_price": 10.0},
                {"ticker": "MSFT", "qty": 2, "close_price": 15.0},
            ],
        )

        with patch(
            "src.integrations.portfolio_runtime.get_current_portfolio_state",
            return_value=snapshot,
        ):
            summary = get_portfolio_compliance_summary(run_id="run-1")

        self.assertEqual(summary["run_id"], "run-1")
        self.assertEqual(summary["scope"], "current")
        self.assertIn("status", summary)
        self.assertIn("breaches", summary)

    def test_target_compliance_summary_uses_preview_for_proposal(self) -> None:
        snapshot = build_portfolio_snapshot(
            as_of_date="2024-08-01",
            cash=20.0,
            positions=[{"ticker": "AAPL", "qty": 2, "close_price": 10.0}],
        )

        with patch(
            "src.integrations.portfolio_runtime.get_current_portfolio_state",
            return_value=snapshot,
        ), patch(
            "src.integrations.portfolio_runtime.preview_rebalance",
            return_value={
                "as_of": "2024-08-01",
                "ips_status": "fail",
                "ips_breaches": [{"rule": "max_position_weight"}],
                "missing_prices": [],
                "target_cash_weight": 0.1,
                "requested_stock_weight_sum": 0.9,
            },
        ):
            summary = get_portfolio_compliance_summary(
                run_id="run-2",
                target_weights={"AAPL": 0.90, "CASH": 0.10},
            )

        self.assertEqual(summary["run_id"], "run-2")
        self.assertEqual(summary["scope"], "target")
        self.assertEqual(summary["status"], "fail")
        self.assertEqual(summary["breaches"][0]["rule"], "max_position_weight")


if __name__ == "__main__":
    unittest.main()
