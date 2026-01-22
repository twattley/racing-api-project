# Multi-Exchange Execution Engine - Design Document

## Overview

Extend the trader to place bets across multiple exchanges (Betfair, Matchbook, Betdaq) while tracking liability at the **system level**. The goal is to get the best available prices across all exchanges while maintaining a single view of exposure per selection.

---

## Core Principles

1. **System-level liability** - A £10 target means £10 total across ALL exchanges, not £10 per exchange
2. **Unified market ID** - Single canonical identifier that maps to exchange-specific IDs
3. **Best price routing** - Route orders to whichever exchange has the best price
4. **Exchange-agnostic decisions** - Decision engine works with unified IDs; execution layer handles exchange specifics

---

## Architecture

### Current State

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Decision   │────▶│   Executor   │────▶│   Betfair    │
│    Engine    │     │              │     │    Client    │
└──────────────┘     └──────────────┘     └──────────────┘
```

### Target State

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Decision   │────▶│   Executor   │────▶│ ExchangeRouter   │
│    Engine    │     │              │     │                  │
└──────────────┘     └──────────────┘     │  ┌────────────┐  │
                                          │  │  Betfair   │  │
                                          │  │  Adapter   │  │
                                          │  └────────────┘  │
                                          │  ┌────────────┐  │
                                          │  │ Matchbook  │  │
                                          │  │  Adapter   │  │
                                          │  └────────────┘  │
                                          │  ┌────────────┐  │
                                          │  │  Betdaq    │  │
                                          │  │  Adapter   │  │
                                          │  └────────────┘  │
                                          └──────────────────┘
```

---

## Unified Market ID

### Format

```
{date}_{course}_{time}_{horse_id}_{market_type}
```

### Examples

```
2026-01-22_ascot_1430_12345_WIN
2026-01-22_ascot_1430_12345_PLACE
2026-01-22_kempton_1545_67890_WIN
```

### Why String Format?

- Human-readable for debugging
- Can be parsed to extract components if needed
- Easy to search/filter in logs and database
- Self-documenting in bet_log table

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `date` | Race date (ISO format) | `2026-01-22` |
| `course` | Lowercase course name, hyphenated | `ascot`, `kempton-park` |
| `time` | Race time (HHMM, 24hr) | `1430` |
| `horse_id` | Internal horse ID from database | `12345` |
| `market_type` | WIN or PLACE | `WIN` |

---

## Database Schema Changes

### New Table: `exchange_market_mapping`

Populated by ETL each morning. Maps unified IDs to exchange-specific IDs.

```sql
CREATE TABLE live_betting.exchange_market_mapping (
    id SERIAL PRIMARY KEY,
    unified_market_id VARCHAR(255) NOT NULL,
    exchange VARCHAR(32) NOT NULL,  -- 'BETFAIR', 'MATCHBOOK', 'BETDAQ'
    exchange_market_id VARCHAR(64) NOT NULL,
    exchange_selection_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE (unified_market_id, exchange)
);

-- Index for fast lookups
CREATE INDEX idx_emm_unified ON live_betting.exchange_market_mapping(unified_market_id);
CREATE INDEX idx_emm_exchange ON live_betting.exchange_market_mapping(exchange, exchange_market_id);
```

### Updated Table: `selections`

```sql
ALTER TABLE live_betting.selections 
ADD COLUMN unified_market_id VARCHAR(255);

-- Migrate existing data (one-time)
UPDATE live_betting.selections s
SET unified_market_id = FORMAT(
    '%s_%s_%s_%s_%s',
    TO_CHAR(s.race_date, 'YYYY-MM-DD'),
    LOWER(REPLACE(s.course, ' ', '-')),
    TO_CHAR(s.race_time, 'HH24MI'),
    s.horse_id,
    s.market_type
);
```

### Updated Table: `bet_log`

```sql
ALTER TABLE live_betting.bet_log 
ADD COLUMN exchange VARCHAR(32) DEFAULT 'BETFAIR',
ADD COLUMN unified_market_id VARCHAR(255);

-- Index for aggregation queries
CREATE INDEX idx_bet_log_unified ON live_betting.bet_log(unified_market_id);
```

### Updated Table: `betfair_prices` → `exchange_prices`

Rename and extend to support multiple exchanges:

```sql
-- Option A: Single table with exchange column
CREATE TABLE live_betting.exchange_prices (
    id SERIAL PRIMARY KEY,
    exchange VARCHAR(32) NOT NULL,
    unified_market_id VARCHAR(255) NOT NULL,
    exchange_market_id VARCHAR(64) NOT NULL,
    exchange_selection_id VARCHAR(64) NOT NULL,
    back_price DECIMAL(10,2),
    lay_price DECIMAL(10,2),
    back_size DECIMAL(10,2),  -- Available liquidity
    lay_size DECIMAL(10,2),
    status VARCHAR(32),  -- ACTIVE, REMOVED, etc.
    last_updated TIMESTAMP DEFAULT NOW(),
    
    UNIQUE (exchange, unified_market_id)
);

-- Option B: Separate tables per exchange (simpler ETL, more complex queries)
-- live_betting.betfair_prices (existing)
-- live_betting.matchbook_prices (new)
-- live_betting.betdaq_prices (new)
```

**Decision: Option A** - Single table is cleaner for the trader to query best prices.

---

## New View: `v_best_prices`

Provides best available price across all exchanges for each unified market.

```sql
CREATE VIEW live_betting.v_best_prices AS
WITH ranked_back AS (
    SELECT 
        unified_market_id,
        exchange,
        back_price,
        back_size,
        ROW_NUMBER() OVER (
            PARTITION BY unified_market_id 
            ORDER BY back_price DESC, back_size DESC
        ) as rn
    FROM live_betting.exchange_prices
    WHERE back_price IS NOT NULL
      AND status = 'ACTIVE'
),
ranked_lay AS (
    SELECT 
        unified_market_id,
        exchange,
        lay_price,
        lay_size,
        ROW_NUMBER() OVER (
            PARTITION BY unified_market_id 
            ORDER BY lay_price ASC, lay_size DESC
        ) as rn
    FROM live_betting.exchange_prices
    WHERE lay_price IS NOT NULL
      AND status = 'ACTIVE'
)
SELECT 
    COALESCE(b.unified_market_id, l.unified_market_id) as unified_market_id,
    b.exchange as best_back_exchange,
    b.back_price as best_back_price,
    b.back_size as best_back_size,
    l.exchange as best_lay_exchange,
    l.lay_price as best_lay_price,
    l.lay_size as best_lay_size
FROM ranked_back b
FULL OUTER JOIN ranked_lay l 
    ON b.unified_market_id = l.unified_market_id
WHERE b.rn = 1 OR l.rn = 1;
```

---

## Updated View: `v_selection_state`

Add aggregated matched amounts and best prices:

```sql
CREATE OR REPLACE VIEW live_betting.v_selection_state AS
SELECT 
    s.*,
    -- Aggregated matched across all exchanges
    COALESCE(agg.total_matched_size, 0) as total_matched_size,
    COALESCE(agg.total_matched_liability, 0) as total_matched_liability,
    -- Best available prices
    bp.best_back_exchange,
    bp.best_back_price,
    bp.best_back_size,
    bp.best_lay_exchange,
    bp.best_lay_price,
    bp.best_lay_size,
    -- Exchange mapping for order placement
    emm_bf.exchange_market_id as betfair_market_id,
    emm_bf.exchange_selection_id as betfair_selection_id,
    emm_mb.exchange_market_id as matchbook_market_id,
    emm_mb.exchange_selection_id as matchbook_selection_id,
    emm_bd.exchange_market_id as betdaq_market_id,
    emm_bd.exchange_selection_id as betdaq_selection_id
FROM live_betting.selections s
-- Aggregate matched from bet_log
LEFT JOIN (
    SELECT 
        unified_market_id,
        SUM(matched_size) as total_matched_size,
        SUM(matched_liability) as total_matched_liability
    FROM live_betting.bet_log
    GROUP BY unified_market_id
) agg ON s.unified_market_id = agg.unified_market_id
-- Best prices
LEFT JOIN live_betting.v_best_prices bp 
    ON s.unified_market_id = bp.unified_market_id
-- Exchange mappings
LEFT JOIN live_betting.exchange_market_mapping emm_bf 
    ON s.unified_market_id = emm_bf.unified_market_id 
    AND emm_bf.exchange = 'BETFAIR'
LEFT JOIN live_betting.exchange_market_mapping emm_mb 
    ON s.unified_market_id = emm_mb.unified_market_id 
    AND emm_mb.exchange = 'MATCHBOOK'
LEFT JOIN live_betting.exchange_market_mapping emm_bd 
    ON s.unified_market_id = emm_bd.unified_market_id 
    AND emm_bd.exchange = 'BETDAQ'
WHERE s.race_date = CURRENT_DATE
  AND s.race_time > NOW()
  AND s.valid = TRUE;
```

---

## Code Structure

### New Package: `trader/exchanges/`

```
trader/
├── exchanges/
│   ├── __init__.py
│   ├── types.py           # Common data structures
│   ├── client.py          # ExchangeClient protocol
│   ├── router.py          # ExchangeRouter - routes to best price
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── betfair.py     # BetfairAdapter
│   │   ├── matchbook.py   # MatchbookAdapter
│   │   └── betdaq.py      # BetdaqAdapter
│   └── aggregator.py      # Aggregates state across exchanges
```

### `types.py` - Common Data Structures

```python
from dataclasses import dataclass
from enum import Enum
from typing import Literal
from datetime import datetime


class Exchange(Enum):
    BETFAIR = "BETFAIR"
    MATCHBOOK = "MATCHBOOK"
    BETDAQ = "BETDAQ"


@dataclass(frozen=True)
class Order:
    """Exchange-agnostic order."""
    unified_market_id: str
    size: float
    price: float
    side: Literal["BACK", "LAY"]
    strategy: str  # Links to selection unique_id


@dataclass
class OrderResult:
    """Result of placing an order."""
    success: bool
    exchange: Exchange
    message: str
    exchange_bet_id: str | None = None
    size_matched: float = 0.0
    average_price_matched: float | None = None


@dataclass
class CurrentOrder:
    """Exchange-agnostic view of an active/completed order."""
    exchange: Exchange
    exchange_bet_id: str
    unified_market_id: str
    exchange_market_id: str
    exchange_selection_id: str
    side: Literal["BACK", "LAY"]
    execution_status: Literal["EXECUTABLE", "EXECUTION_COMPLETE"]
    placed_date: datetime
    matched_date: datetime | None
    average_price_matched: float
    strategy_ref: str
    size_matched: float
    size_remaining: float
    price: float
    size: float


@dataclass
class ExchangePrice:
    """Price quote from an exchange."""
    exchange: Exchange
    unified_market_id: str
    back_price: float | None
    lay_price: float | None
    back_size: float | None  # Available liquidity
    lay_size: float | None
```

### `client.py` - Protocol Definition

```python
from typing import Protocol
from .types import Order, OrderResult, CurrentOrder, Exchange


class ExchangeClient(Protocol):
    """Protocol that all exchange adapters must implement."""
    
    exchange: Exchange
    
    def place_order(self, order: Order) -> OrderResult:
        """Place an order on this exchange."""
        ...
    
    def get_current_orders(self) -> list[CurrentOrder]:
        """Get all current orders from this exchange."""
        ...
    
    def cancel_order(self, exchange_bet_id: str, exchange_market_id: str) -> bool:
        """Cancel a specific order."""
        ...
    
    def cash_out(self, exchange_market_ids: list[str]) -> None:
        """Cash out positions in specified markets."""
        ...
```

### `router.py` - Best Price Routing

```python
from dataclasses import dataclass
from .types import Order, OrderResult, CurrentOrder, Exchange, ExchangePrice
from .client import ExchangeClient


@dataclass
class ExchangeRouter:
    """Routes orders to the exchange with the best price."""
    
    clients: dict[Exchange, ExchangeClient]
    
    def place_order(
        self, 
        order: Order,
        exchange_mapping: dict[Exchange, tuple[str, str]],  # {exchange: (market_id, selection_id)}
        best_exchange: Exchange,
    ) -> OrderResult:
        """
        Place order on the specified exchange.
        
        Args:
            order: The order to place
            exchange_mapping: Mapping of exchange to (market_id, selection_id)
            best_exchange: Which exchange to route to (from v_best_prices)
        """
        client = self.clients.get(best_exchange)
        if not client:
            return OrderResult(
                success=False,
                exchange=best_exchange,
                message=f"No client configured for {best_exchange}",
            )
        
        market_id, selection_id = exchange_mapping[best_exchange]
        # Adapter will translate Order to exchange-specific format
        return client.place_order(order, market_id, selection_id)
    
    def get_all_current_orders(self) -> list[CurrentOrder]:
        """Aggregate current orders from all exchanges."""
        all_orders = []
        for client in self.clients.values():
            try:
                orders = client.get_current_orders()
                all_orders.extend(orders)
            except Exception as e:
                # Log but continue - one exchange being down shouldn't stop others
                pass
        return all_orders
    
    def cancel_order(self, order: CurrentOrder) -> bool:
        """Cancel order on the appropriate exchange."""
        client = self.clients.get(order.exchange)
        if not client:
            return False
        return client.cancel_order(order.exchange_bet_id, order.exchange_market_id)
```

### `adapters/betfair.py` - Betfair Adapter

```python
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder
from ..types import Order, OrderResult, CurrentOrder, Exchange
from ..client import ExchangeClient


class BetfairAdapter:
    """Adapts BetFairClient to ExchangeClient protocol."""
    
    exchange = Exchange.BETFAIR
    
    def __init__(self, betfair_client: BetFairClient):
        self._client = betfair_client
    
    def place_order(
        self, 
        order: Order, 
        market_id: str, 
        selection_id: str,
    ) -> OrderResult:
        """Translate to BetfairOrder and place."""
        bf_order = BetFairOrder(
            size=order.size,
            price=order.price,
            selection_id=selection_id,
            market_id=market_id,
            side=order.side,
            strategy=order.strategy,
        )
        
        result = self._client.place_order(bf_order)
        
        return OrderResult(
            success=result.success,
            exchange=Exchange.BETFAIR,
            message=result.message,
            size_matched=result.size_matched or 0.0,
            average_price_matched=result.average_price_matched,
        )
    
    def get_current_orders(self) -> list[CurrentOrder]:
        """Translate Betfair orders to common format."""
        bf_orders = self._client.get_current_orders()
        
        return [
            CurrentOrder(
                exchange=Exchange.BETFAIR,
                exchange_bet_id=o.bet_id,
                unified_market_id=None,  # Need to look up from mapping
                exchange_market_id=o.market_id,
                exchange_selection_id=str(o.selection_id),
                side=o.side,
                execution_status=o.execution_status,
                placed_date=o.placed_date,
                matched_date=o.matched_date,
                average_price_matched=o.average_price_matched,
                strategy_ref=o.customer_strategy_ref,
                size_matched=o.size_matched,
                size_remaining=o.size_remaining,
                price=o.price,
                size=o.size,
            )
            for o in bf_orders
        ]
    
    def cancel_order(self, exchange_bet_id: str, exchange_market_id: str) -> bool:
        """Cancel via Betfair API."""
        try:
            self._client.trading_client.betting.cancel_orders(
                market_id=exchange_market_id,
                instructions=[{"betId": exchange_bet_id}],
            )
            return True
        except Exception:
            return False
    
    def cash_out(self, exchange_market_ids: list[str]) -> None:
        """Cash out via Betfair."""
        self._client.cash_out_bets(exchange_market_ids)
```

---

## Routing Strategy

### Phase 1: Simple Best Price

Route to whichever exchange has the best price at decision time:

```python
def decide_exchange(selection_state: pd.Series) -> Exchange:
    """Decide which exchange to route to based on best price."""
    side = selection_state["side"]
    
    if side == "BACK":
        # For BACK, want highest price
        return Exchange(selection_state["best_back_exchange"])
    else:
        # For LAY, want lowest price
        return Exchange(selection_state["best_lay_exchange"])
```

### Phase 2: Liquidity-Aware (Future)

When close to race time, prioritise getting filled over price:

```python
def decide_exchange_with_liquidity(
    selection_state: pd.Series,
    remaining_stake: float,
    minutes_to_race: float,
) -> Exchange:
    """
    Decide exchange considering both price and liquidity.
    
    Closer to race time, weight liquidity more heavily.
    """
    if minutes_to_race > 30:
        # Far from race - pure best price
        return decide_exchange(selection_state)
    
    # Close to race - check if best price has enough liquidity
    side = selection_state["side"]
    
    if side == "BACK":
        best_exchange = selection_state["best_back_exchange"]
        best_size = selection_state["best_back_size"]
    else:
        best_exchange = selection_state["best_lay_exchange"]
        best_size = selection_state["best_lay_size"]
    
    if best_size >= remaining_stake:
        return Exchange(best_exchange)
    
    # Best price doesn't have enough liquidity
    # TODO: Could split across exchanges or fall back to second-best
    return Exchange(best_exchange)  # For now, still use best
```

### Phase 3: Order Splitting (Future)

Split large orders across exchanges to access more liquidity:

```python
def plan_order_execution(
    remaining_stake: float,
    prices: dict[Exchange, ExchangePrice],
) -> list[tuple[Exchange, float]]:
    """
    Plan how to split an order across exchanges.
    
    Returns list of (exchange, size) tuples.
    """
    # Sort exchanges by price (best first)
    # Allocate stake to each until filled
    # Return execution plan
    pass  # Future implementation
```

---

## ETL Changes

### Morning Job: Create Exchange Mappings

New ETL step to populate `exchange_market_mapping`:

```python
def create_exchange_mappings(
    race_date: date,
    postgres_client: PostgresClient,
    betfair_client: BetFairClient,
    matchbook_client: MatchbookClient,
    betdaq_client: BetdaqClient,
) -> None:
    """
    Create unified market ID mappings for today's races.
    
    Called each morning after race data is loaded.
    """
    # 1. Get today's races from our database
    races = postgres_client.fetch_data("""
        SELECT DISTINCT 
            race_date, course, race_time, horse_id, horse_name
        FROM races r
        JOIN runners ru ON r.race_id = ru.race_id
        WHERE race_date = CURRENT_DATE
    """)
    
    # 2. For each race, get market IDs from each exchange
    mappings = []
    
    for _, race in races.iterrows():
        unified_id = generate_unified_market_id(race)
        
        # Betfair
        bf_market = betfair_client.find_market(race)
        if bf_market:
            mappings.append({
                "unified_market_id": unified_id,
                "exchange": "BETFAIR",
                "exchange_market_id": bf_market.market_id,
                "exchange_selection_id": bf_market.selection_id,
            })
        
        # Matchbook
        mb_market = matchbook_client.find_market(race)
        if mb_market:
            mappings.append({
                "unified_market_id": unified_id,
                "exchange": "MATCHBOOK",
                "exchange_market_id": mb_market.market_id,
                "exchange_selection_id": mb_market.selection_id,
            })
        
        # Betdaq
        bd_market = betdaq_client.find_market(race)
        if bd_market:
            mappings.append({
                "unified_market_id": unified_id,
                "exchange": "BETDAQ",
                "exchange_market_id": bd_market.market_id,
                "exchange_selection_id": bd_market.selection_id,
            })
    
    # 3. Store mappings
    postgres_client.store_data(
        pd.DataFrame(mappings),
        table="exchange_market_mapping",
        schema="live_betting",
        truncate=True,  # Replace each morning
    )
```

### Price Refresh Job

Extend `fetch_prices` to pull from all exchanges:

```python
def fetch_all_exchange_prices(
    betfair_client: BetFairClient,
    matchbook_client: MatchbookClient,
    betdaq_client: BetdaqClient,
    postgres_client: PostgresClient,
) -> None:
    """Refresh prices from all exchanges."""
    
    # Get mappings
    mappings = postgres_client.fetch_data(
        "SELECT * FROM live_betting.exchange_market_mapping"
    )
    
    all_prices = []
    
    # Betfair prices
    bf_mappings = mappings[mappings["exchange"] == "BETFAIR"]
    bf_prices = betfair_client.get_prices(bf_mappings["exchange_market_id"].tolist())
    # ... transform and append
    
    # Matchbook prices
    # ... similar
    
    # Betdaq prices
    # ... similar
    
    # Store all
    postgres_client.store_data(
        pd.DataFrame(all_prices),
        table="exchange_prices",
        schema="live_betting",
        truncate=True,
    )
```

---

## Migration Plan

### Phase 1: Foundation (No Breaking Changes)

1. ✅ Create `exchange_market_mapping` table
2. ✅ Add `unified_market_id` column to `selections` (nullable)
3. ✅ Add `exchange` and `unified_market_id` columns to `bet_log` (with defaults)
4. ✅ Create `exchanges/` package structure
5. ✅ Create `BetfairAdapter` that wraps existing client
6. ✅ Create `ExchangeRouter` that initially only has Betfair

**Result**: System works exactly as before, but with new abstractions in place.

### Phase 2: ETL Integration

1. ⬜ Add ETL job to create exchange mappings (Betfair only initially)
2. ⬜ Populate `unified_market_id` in selections from new mappings
3. ⬜ Update `v_selection_state` to include unified IDs
4. ⬜ Update reconciliation to write `unified_market_id` to bet_log

**Result**: Unified market IDs flowing through system, still Betfair-only.

### Phase 3: Multi-Exchange Prices

1. ⬜ Create `exchange_prices` table
2. ⬜ Extend ETL to fetch Matchbook/Betdaq mappings
3. ⬜ Extend price refresh to include all exchanges
4. ⬜ Create `v_best_prices` view

**Result**: Best prices visible from all exchanges.

### Phase 4: Multi-Exchange Execution

1. ⬜ Create `MatchbookAdapter` and `BetdaqAdapter`
2. ⬜ Update executor to use `ExchangeRouter`
3. ⬜ Update reconciliation to handle multiple exchanges
4. ⬜ Update decision engine to use aggregated matched amounts

**Result**: Full multi-exchange execution!

---

## Testing Strategy

### Unit Tests

- `test_types.py` - Data structure creation and validation
- `test_router.py` - Routing logic with mocked adapters
- `test_adapters/test_betfair.py` - Adapter translation logic
- `test_aggregator.py` - Aggregation across exchanges

### Integration Tests

- Test routing to correct exchange based on price
- Test aggregated matched amounts calculation
- Test reconciliation across exchanges
- Test cash-out across exchanges

### Manual Testing

- Place small bets on each exchange
- Verify bet_log correctly records exchange
- Verify aggregated totals are correct
- Test failure scenarios (one exchange down)

---

## Open Questions

1. **Commission handling?** Different exchanges have different commission rates. Should this factor into routing decisions?

2. **Minimum stake differences?** Exchanges have different minimums (Betfair £2, Matchbook £5?). Need to handle cases where remaining stake is below minimum for best-priced exchange.

3. **Cash-out across exchanges?** If we have £5 on Betfair and £5 on Matchbook, and need to cash out, do we cash out both? Or just the one with position?

4. **Rate limiting?** Each exchange has API rate limits. Need to be careful when polling prices from all three.

5. **Credentials management?** Need to securely manage API keys for multiple exchanges.

---

## Appendix: Exchange API Comparison

| Feature | Betfair | Matchbook | Betdaq |
|---------|---------|-----------|--------|
| API Type | betfairlightweight | REST | REST/SOAP |
| Min Stake | £2 | £5 | £2 |
| Commission | 5% | 1.5% | 2-5% |
| Liquidity | High | Medium | Low |
| Rate Limit | 20/sec | 10/sec | ? |
| Cash Out API | Yes | Manual | ? |
