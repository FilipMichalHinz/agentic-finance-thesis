"""
Alpaca paper-trading client kept separate from the MAS graph.
Use this to submit trades once a proposal is approved by Risk.
"""

import os
from dataclasses import dataclass
from typing import Optional

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest
except ImportError:  # pragma: no cover - optional dependency
    TradingClient = None  # type: ignore
    OrderSide = None  # type: ignore
    TimeInForce = None  # type: ignore
    MarketOrderRequest = None  # type: ignore


@dataclass
class TradeResult:
    order_id: Optional[str]
    status: str
    message: str


class AlpacaPaperBroker:
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper: bool = True,
    ) -> None:
        api_key = api_key or os.getenv("ALPACA_API_KEY_ID")
        api_secret = api_secret or os.getenv("ALPACA_API_SECRET_KEY")
        if not api_key or not api_secret or not TradingClient:
            self.client = None
        else:
            self.client = TradingClient(api_key, api_secret, paper=paper)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def submit_market_order(self, symbol: str, qty: float, side: str = "buy") -> TradeResult:
        """
        Submit a basic market order. Extend this as strategies mature.
        """
        if not self.enabled:
            return TradeResult(order_id=None, status="disabled", message="Alpaca client not configured")

        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        try:
            req = MarketOrderRequest(
                symbol=symbol.upper(),
                qty=qty,
                side=side_enum,
                time_in_force=TimeInForce.DAY,
            )
            order = self.client.submit_order(req)  # type: ignore[call-arg]
            return TradeResult(order_id=order.id, status=order.status, message="order submitted")
        except Exception as exc:  # pragma: no cover
            return TradeResult(order_id=None, status="error", message=str(exc))

    def get_account_summary(self) -> Optional[dict]:
        if not self.enabled:
            return None
        account = self.client.get_account()  # type: ignore[call-arg]
        return {
            "id": account.id,
            "cash": account.cash,
            "portfolio_value": account.portfolio_value,
            "multiplier": getattr(account, "multiplier", None),
            "status": account.status,
        }
