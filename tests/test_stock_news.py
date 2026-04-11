import os
import unittest
from unittest.mock import patch

from src.integrations import general_news
from src.integrations import stock_news


class RetrieveStockNewsTests(unittest.TestCase):
    def test_clean_mode_returns_clean_rows_only(self) -> None:
        clean_rows = [
            {
                "title": "Clean headline",
                "content": "Clean content",
                "publisher": "Reuters",
                "site": "reuters.com",
                "published_at": "2025-04-11T14:00:00+00:00",
            }
        ]

        with patch.object(stock_news, "_fetch_clean_stock_news_rows", return_value=clean_rows):
            rows = stock_news.retrieve_stock_news_for_date(
                ticker="aapl",
                as_of="2025-04-11",
                simulation_mode="clean",
            )

        self.assertEqual(
            [
                {
                    "title": "Clean headline",
                    "content": "Clean content",
                    "publisher": "Reuters",
                    "site": "reuters.com",
                }
            ],
            rows,
        )

    def test_disinformation_replace_prefers_manipulated_rows(self) -> None:
        clean_rows = [
            {
                "title": "Clean headline",
                "content": "Clean content",
                "publisher": "Reuters",
                "site": "reuters.com",
                "published_at": "2025-04-11T14:00:00+00:00",
            }
        ]
        manipulated_rows = [
            {
                "title": "Manipulated headline",
                "content": "Manipulated content",
                "publisher": "Fake Wire",
                "site": "example.com",
                "published_at": "2025-04-11T23:59:59+00:00",
            }
        ]

        with patch.object(stock_news, "_fetch_clean_stock_news_rows", return_value=clean_rows), patch.object(
            stock_news,
            "_fetch_manipulated_stock_news_rows",
            return_value=manipulated_rows,
        ):
            rows = stock_news.retrieve_stock_news_for_date(
                ticker="AAPL",
                as_of="2025-04-11T10:00:00Z",
                simulation_mode="disinformation",
                disinformation_policy="replace",
            )

        self.assertEqual(
            [
                {
                    "title": "Manipulated headline",
                    "content": "Manipulated content",
                    "publisher": "Fake Wire",
                    "site": "example.com",
                }
            ],
            rows,
        )

    def test_disinformation_append_keeps_both_sets(self) -> None:
        clean_rows = [
            {
                "title": "Clean headline",
                "content": "Clean content",
                "publisher": "Reuters",
                "site": "reuters.com",
                "published_at": "2025-04-11T14:00:00+00:00",
            }
        ]
        manipulated_rows = [
            {
                "title": "Manipulated headline",
                "content": "Manipulated content",
                "publisher": "Fake Wire",
                "site": "example.com",
                "published_at": "2025-04-11T23:59:59+00:00",
            }
        ]

        with patch.object(stock_news, "_fetch_clean_stock_news_rows", return_value=clean_rows), patch.object(
            stock_news,
            "_fetch_manipulated_stock_news_rows",
            return_value=manipulated_rows,
        ):
            rows = stock_news.retrieve_stock_news_for_date(
                ticker="AAPL",
                as_of="2025-04-11",
                simulation_mode="manipulated",
                disinformation_policy="append",
            )

        self.assertEqual(
            [
                {
                    "title": "Manipulated headline",
                    "content": "Manipulated content",
                    "publisher": "Fake Wire",
                    "site": "example.com",
                },
                {
                    "title": "Clean headline",
                    "content": "Clean content",
                    "publisher": "Reuters",
                    "site": "reuters.com",
                },
            ],
            rows,
        )

    def test_simulation_mode_uses_environment_aliases(self) -> None:
        with patch.dict(os.environ, {"SIMULATION_MODE": "manipulated"}, clear=True):
            mode = stock_news.resolve_stock_news_simulation_mode()

        self.assertEqual("disinformation", mode)

    def test_disinformation_policy_defaults_to_append(self) -> None:
        policy = stock_news.resolve_stock_news_disinformation_policy()

        self.assertEqual("append", policy)


class GeneralNewsTests(unittest.TestCase):
    def test_general_news_returns_formatted_rows_for_day(self) -> None:
        general_rows = [
            {
                "title": "Macro headline",
                "content": "Macro content",
                "publisher": "Reuters",
                "site": "reuters.com",
                "published_at": "2025-04-11T14:00:00+00:00",
            }
        ]

        with patch.object(general_news, "_fetch_general_news_rows", return_value=general_rows):
            rows = general_news.get_all_general_news_for_date("2025-04-11")

        self.assertEqual(
            [
                {
                    "title": "Macro headline",
                    "content": "Macro content",
                    "publisher": "Reuters",
                    "site": "reuters.com",
                }
            ],
            rows,
        )


if __name__ == "__main__":
    unittest.main()
