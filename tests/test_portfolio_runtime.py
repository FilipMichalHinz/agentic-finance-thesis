import unittest

from src.integrations.portfolio_logic import (
    build_portfolio_snapshot,
    build_rebalance_preview,
    summarize_portfolio_compliance,
    summarize_portfolio_risk,
)


class PortfolioRuntimeTests(unittest.TestCase):
    def test_build_portfolio_snapshot_normalizes_weights(self) -> None:
        snapshot = build_portfolio_snapshot(
            as_of_date="2024-08-01",
            cash=20.0,
            positions=[
                {"ticker": "AAPL", "qty": 2, "close_price": 10.0},
                {"ticker": "MSFT", "qty": 1, "close_price": 20.0},
            ],
        )

        self.assertEqual(snapshot["holdings_count"], 2)
        self.assertAlmostEqual(snapshot["gross_market_value"], 40.0)
        self.assertAlmostEqual(snapshot["total_value"], 60.0)
        self.assertAlmostEqual(snapshot["cash_weight"], 20.0 / 60.0)
        self.assertAlmostEqual(snapshot["positions"][0]["weight"], 20.0 / 60.0)

    def test_summarize_portfolio_compliance_detects_breaches(self) -> None:
        snapshot = build_portfolio_snapshot(
            as_of_date="2024-08-01",
            cash=5.0,
            positions=[
                {"ticker": "AAPL", "qty": 1, "close_price": 60.0},
                {"ticker": "TSLA", "qty": 1, "close_price": 35.0},
            ],
        )

        summary = summarize_portfolio_compliance(
            current_state=snapshot,
        )

        self.assertEqual(summary["status"], "fail")
        rules = {breach["rule"] for breach in summary["breaches"]}
        self.assertIn("holdings_count", rules)
        self.assertIn("max_position_weight", rules)
        self.assertIn("universe_membership", rules)

    def test_build_rebalance_preview_generates_action_types(self) -> None:
        current_state = build_portfolio_snapshot(
            as_of_date="2024-08-01",
            cash=20.0,
            positions=[
                {"ticker": "AAPL", "qty": 3, "close_price": 10.0},
                {"ticker": "MSFT", "qty": 2, "close_price": 15.0},
            ],
        )

        preview = build_rebalance_preview(
            current_state=current_state,
            target_weights={
                "AAPL": 0.20,
                "JPM": 0.20,
                "CASH": 0.60,
            },
            reference_prices={
                "AAPL": 10.0,
                "MSFT": 15.0,
                "JPM": 20.0,
            },
            rationale="test",
        )

        actions = {action["ticker"]: action for action in preview["actions"]}

        self.assertEqual(actions["AAPL"]["action_type"], "reduce")
        self.assertEqual(actions["MSFT"]["action_type"], "sell")
        self.assertEqual(actions["JPM"]["action_type"], "buy")
        self.assertAlmostEqual(preview["target_cash_weight"], 0.60)
        self.assertEqual(preview["ips_status"], "fail")

    def test_summarize_portfolio_risk_computes_drawdown_and_volatility(self) -> None:
        total_values = [
            100.0,
            102.0,
            101.0,
            103.0,
            104.0,
            103.0,
            105.0,
            104.0,
            106.0,
            107.0,
            106.0,
            108.0,
            109.0,
            108.0,
            110.0,
            109.0,
            111.0,
            110.0,
            112.0,
            111.0,
            109.0,
        ]
        history = [
            build_portfolio_snapshot(
                as_of_date=f"2024-08-{index + 1:02d}",
                cash=10.0,
                positions=[
                    {
                        "ticker": "AAPL",
                        "qty": 1.0,
                        "close_price": total_value - 10.0,
                    }
                ],
            )
            for index, total_value in enumerate(total_values)
        ]

        summary = summarize_portfolio_risk(
            current_state=history[-1],
            history_snapshots=history,
        )

        self.assertIsNotNone(summary["rolling_20d_vol"])
        self.assertLess(summary["current_drawdown"], 0.0)
        self.assertEqual(summary["holdings_count"], 1)


if __name__ == "__main__":
    unittest.main()
