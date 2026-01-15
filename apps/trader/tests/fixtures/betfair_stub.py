"""
Betfair API stub for testing.

Allows configuring responses without hitting the real API.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StubbedOrder:
    """Represents an order we've "placed" in the stub."""

    bet_id: str
    market_id: str
    selection_id: int
    side: str
    requested_price: float
    requested_size: float
    matched_size: float = 0.0
    matched_price: Optional[float] = None
    size_remaining: float = 0.0
    status: str = "EXECUTABLE"  # EXECUTABLE / EXECUTION_COMPLETE


@dataclass
class PlaceOrderResult:
    """Result of placing an order."""

    success: bool
    bet_id: Optional[str] = None
    message: str = ""
    size_matched: float = 0.0
    average_price_matched: Optional[float] = None


@dataclass
class BetfairStub:
    """
    Stub for Betfair API.

    Configure behavior before test, then inspect what was called after.
    """

    # Configuration: how should the stub behave?
    should_match_immediately: bool = False
    match_percentage: float = 0.0  # 0-100, how much gets matched on place
    should_fail_orders: bool = False
    fail_message: str = "API Error"

    # State: what orders exist?
    orders: dict[str, StubbedOrder] = field(default_factory=dict)
    _next_bet_id: int = 1

    # Recording: what was called?
    placed_orders: list[dict] = field(default_factory=list)
    cancelled_orders: list[str] = field(default_factory=list)

    def place_order(
        self,
        market_id: str,
        selection_id: int,
        side: str,
        price: float,
        size: float,
        strategy_ref: str = None,
    ) -> PlaceOrderResult:
        """Place an order. Returns configured result."""

        # Record the call
        self.placed_orders.append(
            {
                "market_id": market_id,
                "selection_id": selection_id,
                "side": side,
                "price": price,
                "size": size,
                "strategy_ref": strategy_ref,
            }
        )

        if self.should_fail_orders:
            return PlaceOrderResult(
                success=False,
                message=self.fail_message,
            )

        # Generate bet ID
        bet_id = f"BET-{self._next_bet_id:06d}"
        self._next_bet_id += 1

        # Calculate matching
        if self.should_match_immediately:
            matched_size = size
            matched_price = price
            status = "EXECUTION_COMPLETE"
            size_remaining = 0.0
        elif self.match_percentage > 0:
            matched_size = size * (self.match_percentage / 100)
            matched_price = price
            status = "EXECUTABLE"
            size_remaining = size - matched_size
        else:
            matched_size = 0.0
            matched_price = None
            status = "EXECUTABLE"
            size_remaining = size

        # Create order
        order = StubbedOrder(
            bet_id=bet_id,
            market_id=market_id,
            selection_id=selection_id,
            side=side,
            requested_price=price,
            requested_size=size,
            matched_size=matched_size,
            matched_price=matched_price,
            size_remaining=size_remaining,
            status=status,
        )
        self.orders[bet_id] = order

        return PlaceOrderResult(
            success=True,
            bet_id=bet_id,
            message="Order placed",
            size_matched=matched_size,
            average_price_matched=matched_price,
        )

    def cancel_order(self, bet_id: str) -> bool:
        """Cancel an order."""
        self.cancelled_orders.append(bet_id)
        if bet_id in self.orders:
            order = self.orders[bet_id]
            order.status = "EXECUTION_COMPLETE"
            order.size_remaining = 0.0
            return True
        return False

    def get_current_orders(self, market_ids: list[str] = None) -> list[StubbedOrder]:
        """Get orders that are still EXECUTABLE."""
        orders = [o for o in self.orders.values() if o.status == "EXECUTABLE"]
        if market_ids:
            orders = [o for o in orders if o.market_id in market_ids]
        return orders

    def simulate_match(self, bet_id: str, size: float = None, price: float = None):
        """Simulate a bet getting matched (for testing)."""
        if bet_id not in self.orders:
            return

        order = self.orders[bet_id]
        match_size = size or order.size_remaining
        match_price = price or order.requested_price

        order.matched_size += match_size
        order.matched_price = match_price  # Simplified - should be weighted avg
        order.size_remaining -= match_size

        if order.size_remaining <= 0:
            order.status = "EXECUTION_COMPLETE"
            order.size_remaining = 0.0

    def simulate_lapse(self, bet_id: str):
        """Simulate a bet lapsing (market closed)."""
        if bet_id not in self.orders:
            return
        order = self.orders[bet_id]
        order.status = "EXECUTION_COMPLETE"
        # size_remaining becomes lapsed

    def reset(self):
        """Reset all state for next test."""
        self.orders.clear()
        self.placed_orders.clear()
        self.cancelled_orders.clear()
        self._next_bet_id = 1
        self.should_match_immediately = False
        self.match_percentage = 0.0
        self.should_fail_orders = False
