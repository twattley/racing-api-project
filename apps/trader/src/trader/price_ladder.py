"""
Betfair Price Ladder - utility for working with valid Betfair prices.

Betfair only accepts specific price increments:
- 1.01-2.00: 0.01 increments
- 2.00-3.00: 0.02 increments
- 3.00-4.00: 0.05 increments
- 4.00-6.00: 0.10 increments
- 6.00-10.00: 0.20 increments
- 10.00-20.00: 0.50 increments
"""

from decimal import Decimal


def _generate_ladder() -> list[float]:
    """Generate the complete Betfair price ladder up to 20."""
    prices: list[Decimal] = []

    # 1.01-2.00: 0.01 increments
    price = Decimal("1.01")
    while price <= Decimal("2.00"):
        prices.append(price)
        price += Decimal("0.01")

    # 2.02-3.00: 0.02 increments
    price = Decimal("2.02")
    while price <= Decimal("3.00"):
        prices.append(price)
        price += Decimal("0.02")

    # 3.05-4.00: 0.05 increments
    price = Decimal("3.05")
    while price <= Decimal("4.00"):
        prices.append(price)
        price += Decimal("0.05")

    # 4.10-6.00: 0.10 increments
    price = Decimal("4.10")
    while price <= Decimal("6.00"):
        prices.append(price)
        price += Decimal("0.10")

    # 6.20-10.00: 0.20 increments
    price = Decimal("6.20")
    while price <= Decimal("10.00"):
        prices.append(price)
        price += Decimal("0.20")

    # 10.50-20.00: 0.50 increments
    price = Decimal("10.50")
    while price <= Decimal("20.00"):
        prices.append(price)
        price += Decimal("0.50")

    return [float(p) for p in prices]


# The ladder as a module-level constant
LADDER: list[float] = _generate_ladder()


class PriceLadder:
    """
    Wrapper around the Betfair price ladder for price manipulation.
    
    Usage:
        ladder = PriceLadder()
        
        # Move up/down the ladder by ticks
        ladder.ticks_away(3.0, 4)   # 4 ticks above 3.0 → 3.20
        ladder.ticks_away(3.0, -2)  # 2 ticks below 3.0 → 2.96
        
        # Snap to nearest valid price
        ladder.snap(3.03)  # → 3.05 (rounds to nearest)
        ladder.snap_down(3.03)  # → 3.00
        ladder.snap_up(3.03)  # → 3.05
        
        # Check if valid
        ladder.is_valid(3.05)  # → True
        ladder.is_valid(3.03)  # → False
    """

    def __init__(self) -> None:
        self._ladder = LADDER
        self._ladder_set = set(LADDER)

    @property
    def min_price(self) -> float:
        return self._ladder[0]

    @property
    def max_price(self) -> float:
        return self._ladder[-1]

    def is_valid(self, price: float) -> bool:
        """Check if a price is a valid Betfair price."""
        return round(price, 2) in self._ladder_set

    def index_of(self, price: float) -> int | None:
        """Get the index of a price in the ladder, or None if not found."""
        try:
            return self._ladder.index(round(price, 2))
        except ValueError:
            return None

    def snap(self, price: float) -> float:
        """Snap to nearest valid price on the ladder."""
        if price <= self.min_price:
            return self.min_price
        if price >= self.max_price:
            return self.max_price

        # Binary search for closest
        for i, ladder_price in enumerate(self._ladder):
            if ladder_price >= price:
                if i == 0:
                    return ladder_price
                prev_price = self._ladder[i - 1]
                # Return whichever is closer
                if (price - prev_price) <= (ladder_price - price):
                    return prev_price
                return ladder_price
        return self.max_price

    def snap_down(self, price: float) -> float:
        """Snap down to nearest valid price at or below."""
        if price <= self.min_price:
            return self.min_price
        if price >= self.max_price:
            return self.max_price

        for i, ladder_price in enumerate(self._ladder):
            if ladder_price > price:
                return self._ladder[i - 1] if i > 0 else self.min_price
        return self.max_price

    def snap_up(self, price: float) -> float:
        """Snap up to nearest valid price at or above."""
        if price <= self.min_price:
            return self.min_price
        if price >= self.max_price:
            return self.max_price

        for ladder_price in self._ladder:
            if ladder_price >= price:
                return ladder_price
        return self.max_price

    def ticks_away(self, price: float, ticks: int) -> float:
        """
        Get price N ticks away from given price.
        
        Args:
            price: Starting price (will be snapped to valid price)
            ticks: Number of ticks to move (+ve = higher odds, -ve = lower odds)
        
        Returns:
            New price, clamped to ladder bounds
        
        Example:
            ticks_away(3.0, 4)   # → 3.20 (4 ticks up)
            ticks_away(3.0, -2)  # → 2.96 (2 ticks down)
        """
        # Snap to valid price first
        snapped = self.snap(price)
        idx = self.index_of(snapped)
        
        if idx is None:
            return snapped

        new_idx = idx + ticks
        new_idx = max(0, min(new_idx, len(self._ladder) - 1))
        
        return self._ladder[new_idx]

    def ticks_between(self, price1: float, price2: float) -> int:
        """
        Count ticks between two prices.
        
        Returns positive if price2 > price1, negative otherwise.
        """
        idx1 = self.index_of(self.snap(price1))
        idx2 = self.index_of(self.snap(price2))
        
        if idx1 is None or idx2 is None:
            return 0
        
        return idx2 - idx1


# Module-level instance for convenience
ladder = PriceLadder()
