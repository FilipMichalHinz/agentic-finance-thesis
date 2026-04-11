import unittest

from src.baseline_workflow import (
    build_shared_deep_analysis_set,
    fallback_target_weights,
    parse_json_object,
    sanitize_target_weights,
)


class BaselineWorkflowTests(unittest.TestCase):
    def test_build_shared_deep_analysis_set_unions_holdings_and_flags(self) -> None:
        deep_set = build_shared_deep_analysis_set(
            holdings=["MSFT", "AAPL"],
            screening_outputs=[
                [{"ticker": "AAPL", "status": "no_issue"}],
                [{"ticker": "JPM", "status": "flag_for_deep_analysis"}],
                [{"ticker": "MSFT", "status": "flag_for_deep_analysis"}],
            ],
        )

        self.assertEqual(deep_set, ["AAPL", "JPM", "MSFT"])

    def test_parse_json_object_handles_markdown_fence(self) -> None:
        parsed = parse_json_object(
            """```json
            {"summary": "ok", "target_weights": {"AAPL": 0.1, "CASH": 0.9}}
            ```"""
        )
        self.assertEqual(parsed["summary"], "ok")

    def test_sanitize_target_weights_clips_invalid_weights(self) -> None:
        weights = sanitize_target_weights(
            {"AAPL": 0.40, "TSLA": 0.20, "CASH": 0.40},
            allowed_tickers=["AAPL", "JPM"],
        )

        self.assertIn("AAPL", weights)
        self.assertNotIn("TSLA", weights)
        self.assertLessEqual(weights["AAPL"], 0.15)
        self.assertIn("CASH", weights)

    def test_fallback_target_weights_keeps_simple_cash_buffer(self) -> None:
        weights = fallback_target_weights(["AAPL", "MSFT", "JPM"])
        self.assertEqual(set(weights.keys()), {"AAPL", "MSFT", "JPM", "CASH"})
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=3)


if __name__ == "__main__":
    unittest.main()
