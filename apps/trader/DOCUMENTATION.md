# Trader Application - Comprehensive Documentation

## Overview

The Trader is an **automated betting execution system** that runs throughout the day on a cron job. Its purpose is to automatically execute bets at favorable prices based on selections you make in the morning.

### Workflow Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MORNING (Manual)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. You analyze races and select bets                                       │
│  2. Market state is captured and stored in `live_betting.market_state`      │
│  3. Selections stored in `live_betting.selections`                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THROUGHOUT THE DAY (Automated)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Cron job starts the trader                                              │
│  2. Every 15 seconds (or 2 mins before 10am):                               │
│     a) Fetch live Betfair prices → store in DB                              │
│     b) Check pending selections against current market                      │
│     c) Validate conditions (no market changes that invalidate bet)          │
│     d) Place orders progressively based on time-to-race staking             │
│     e) Track matched amounts, handle cash-outs if needed                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Overview

### File Structure

```
trader/
├── main.py                 # Entry point - main trading loop
├── betfair_live_prices.py  # Fetches & stores live prices from Betfair
├── fetch_requests.py       # Retrieves pending bets & market state from DB
├── prepare_requests.py     # Merges data, calculates validation conditions
├── market_trader.py        # Core trading logic - decides & executes trades
├── utils.py                # Staking config loader & time-based stake helper
└── config/
    └── staking_config.yaml # Time-based staking amounts
```

### Data Flow Diagram

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Betfair API    │     │   PostgreSQL DB  │     │  Staking Config  │
│  (Live Prices)   │     │ (live_betting.*)│     │    (YAML)        │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           main.py                                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ LOOP every 15s (or 2 mins before 10am):                     │    │
│  │                                                              │    │
│  │  1. update_betfair_prices()     ──▶ DB: updated_price_data   │    │
│  │  2. update_live_betting_data()  ──▶ DB: upcoming_bets/       │    │
│  │                                       live_results           │    │
│  │  3. fetch_betting_data()        ◀── DB: market_state,        │    │
│  │                                       selections             │    │
│  │  4. prepare_request_data()      (merge & validate)           │    │
│  │  5. trader.trade_markets()      (decide & execute)           │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 1. Market State Snapshots

When you create a selection in the morning, the system captures the market state at that moment. This becomes the "reference point" for validating whether the bet is still worth placing.

**Tables Involved:**
- `live_betting.market_state` - Stores snapshot of prices/runners when selection made
- `live_betting.selections` - Your actual bet selections

### 2. Bet Validation Conditions

Two critical safety checks before placing any bet:

| Condition | Applies To | Logic | Reason |
|-----------|------------|-------|--------|
| **Short Price Removal** | BACK bets (WIN & PLACE) | If any horse with `back_price < 12` is marked `REMOVED` | Market dynamics change significantly when a fancied horse is withdrawn |
| **8-to-7 Runners** | PLACE bets only | If active runners drop from ≥8 to ≤7 | Place terms change (typically 1-2-3 paid vs 1-2-3-4), fundamentally changing the bet value |

**Code Location:** `prepare_requests.py`
```python
def calculate_eight_to_seven_runners(data: pd.DataFrame) -> pd.DataFrame:
    # Counts ACTIVE runners, flags if original ≥8 but current ≤7

def calculate_short_price_removed_runners(data: pd.DataFrame) -> pd.DataFrame:
    # Checks for any REMOVED horse with back_price < 12
```

### 3. Progressive Time-Based Staking

The system stakes progressively more money as race time approaches - getting better prices early while ensuring full position near the off.

**Configuration:** `config/staking_config.yaml`

```
Time to Race │ BACK Stake │ LAY Liability
─────────────┼────────────┼──────────────
8+ hours     │   £2       │   £5
4 hours      │   £8       │   £16
2 hours      │   £20      │   £35
1 hour       │   £36      │   £55
30 mins      │   £50      │   £75 (max)
```

**Note on LAY bets:** The config specifies **liability** (max loss), not stake. The actual stake is calculated as:
```
Stake = Liability ÷ (Odds - 1)
```

### 4. Order Types Supported

| Type | Market | Logic |
|------|--------|-------|
| **BACK WIN** | Win market | Back horse to win at `requested_odds` or better |
| **BACK PLACE** | Place market | Back horse to place at `requested_odds` or better |
| **LAY WIN** | Win market | Lay horse at `requested_odds` or lower |
| **LAY PLACE** | Place market | Lay horse at `requested_odds` or lower |

### 5. Cash-Out Functionality

When a bet becomes invalid but has already been partially or fully matched, the system automatically triggers a cash-out via Betfair's API.

**Triggers for Cash-Out:**
1. 8-to-7 runners condition met on a PLACE bet
2. Short price horse removed on any bet
3. Both conditions can trigger on fully matched bets

### 6. Contender Value Calculation

The system includes a methodology for calculating value percentages for "contender" selections:

```
1. Equal probability = 1 / num_contenders
2. Normalized market probability = (1/SP) / sum_of_contender_probs
3. Adjusted probability = (equal_prob + normalized_market_prob) / 2
4. Adjusted odds = 1 / adjusted_prob
5. Value % = ((SP - adjusted_odds) / adjusted_odds) × 100
```

This helps identify overlay opportunities among your contender selections.

---

## Database Schema (live_betting)

The full schema is in [live_betting_schema.sql](live_betting_schema.sql).

### Tables

| Table | Purpose |
|-------|---------|
| `selections` | Your bet selections with status tracking |
| `market_state` | Market snapshot when selection was made (prices, runner count) |
| `updated_price_data` | Rolling live price updates from Betfair (refreshed every loop) |
| `upcoming_bets` | Bets pending execution (bet_outcome = 'TO_BE_RUN') |
| `live_results` | Settled bets with P&L after race has run |
| `contender_selections` | Horses marked as 'contender' or 'not-contender' for value calc |
| `market_types` | Lookup table for market name mappings (Betfair/Matchbook/Betdaq) |

### Views

| View | Purpose |
|------|---------|
| `todays_selections` | Today's valid, non-cashed-out selections |
| `updated_price_data_vw` | Future race price data only |

### Table Details

#### `selections` - Your Bet Selections
```sql
CREATE TABLE live_betting.selections (
    unique_id VARCHAR(255),           -- Hash of race_time + course + horse + selection_id
    race_id INTEGER NOT NULL,
    race_time TIMESTAMP NOT NULL,
    race_date DATE NOT NULL,
    horse_id INTEGER NOT NULL,
    horse_name VARCHAR(255) NOT NULL,
    selection_type VARCHAR(50),       -- 'BACK' or 'LAY'
    market_type VARCHAR(50),          -- 'WIN' or 'PLACE'
    market_id VARCHAR(255),           -- Betfair market ID
    selection_id BIGINT,              -- Betfair selection ID
    requested_odds NUMERIC(8,2),      -- Your target price
    stake_points NUMERIC,             -- Multiplier for stake calculation (1.0 = normal)
    valid BOOLEAN,                    -- Still valid to bet?
    invalidated_at TIMESTAMP,         -- When invalidated
    invalidated_reason TEXT,          -- 'Invalid 8 to 7 Place' / 'Invalid Short Price Removed'
    size_matched NUMERIC(15,2),       -- Amount matched so far
    average_price_matched NUMERIC(8,2), -- Weighted average price
    fully_matched BOOLEAN,            -- Has max exposure been reached?
    cashed_out BOOLEAN,               -- Was position cashed out?
    customer_strategy_ref VARCHAR(255), -- Links to Betfair orders
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP DEFAULT NOW()
);
```

#### `market_state` - Market Snapshot When Selection Made
```sql
CREATE TABLE live_betting.market_state (
    selection_id INTEGER NOT NULL,
    back_price_win NUMERIC(8,2) NOT NULL,  -- Price at selection time
    race_id INTEGER NOT NULL,
    race_date DATE NOT NULL,
    race_time TIMESTAMP,
    market_id_win VARCHAR(255) NOT NULL,
    market_id_place VARCHAR(255) NOT NULL,
    number_of_runners INTEGER NOT NULL,    -- CRITICAL: Used for 8-to-7 validation
    created_at TIMESTAMP DEFAULT NOW(),
    unique_id VARCHAR(132),
    bet_selection_id INTEGER,
    bet_type CHAR(16),
    market_type VARCHAR(16),
    horse_id INTEGER
);
```

#### `updated_price_data` - Live Betfair Prices
```sql
CREATE TABLE live_betting.updated_price_data (
    race_time TIMESTAMP,
    horse_name VARCHAR(255),
    race_date DATE,
    course VARCHAR(100),
    status VARCHAR(50),                    -- 'ACTIVE' or 'REMOVED'
    market_id_win VARCHAR(32),
    selection_id INTEGER,
    betfair_win_sp NUMERIC(8,2),           -- Last traded price (WIN)
    betfair_place_sp NUMERIC(8,2),         -- Last traded price (PLACE)
    back_price_1_win NUMERIC(8,2),         -- Best back price
    back_price_1_depth_win NUMERIC(15,2),  -- Depth at best back
    back_price_2_win NUMERIC(8,2),         -- Second best back
    lay_price_1_win NUMERIC(8,2),          -- Best lay price
    lay_price_1_depth_win NUMERIC(15,2),   -- Depth at best lay
    -- ... similar for PLACE market
    market_id_place VARCHAR(255),
    created_at TIMESTAMP,
    unique_id VARCHAR(132)
);
```

#### `live_results` / `upcoming_bets` - Bet Tracking
```sql
-- Both tables have same structure
CREATE TABLE live_betting.live_results (
    unique_id VARCHAR(132),
    race_id VARCHAR(132),
    race_time TIMESTAMP,
    race_date DATE,
    horse_id INTEGER,
    horse_name VARCHAR(132),
    selection_type VARCHAR(132),           -- 'BACK' or 'LAY'
    market_type VARCHAR(132),              -- 'WIN' or 'PLACE'
    market_id VARCHAR(132),
    selection_id INTEGER,
    requested_odds NUMERIC(8,2),
    valid BOOLEAN,
    invalidated_at TIMESTAMP,
    invalidated_reason VARCHAR(132),
    size_matched NUMERIC(8,2),
    average_price_matched NUMERIC(8,2),
    cashed_out BOOLEAN,
    fully_matched BOOLEAN,
    customer_strategy_ref VARCHAR(132),
    created_at TIMESTAMP,
    processed_at TIMESTAMP,
    bet_outcome VARCHAR(132),              -- 'TO_BE_RUN', 'WON', 'LOST'
    price_matched NUMERIC(8,2),
    profit NUMERIC(8,2),                   -- P&L after settlement
    commission NUMERIC(8,2),               -- Betfair commission
    side VARCHAR(32)                       -- 'BACK' or 'LAY'
);
```

### Key Relationships

```
selections.unique_id ──────┬──────▶ market_state.unique_id
                           │
                           ├──────▶ upcoming_bets.unique_id
                           │
                           └──────▶ live_results.unique_id

updated_price_data ◀─────────────── Betfair API (refreshed every loop)
      │
      └──── Joined with market_state to detect:
            • Runner status changes (ACTIVE → REMOVED)
            • Short price removals
            • 8-to-7 runner changes
```

---

## Core Classes & Functions

### MarketTrader Class (`market_trader.py`)

The heart of the trading logic.

```python
class MarketTrader:
    def trade_markets(now_timestamp, requests_data)
        # Main orchestration method
        
    def _calculate_trade_positions(requests_data, now_timestamp)
        # Applies all validation, calculates stakes, creates orders
        
    def _mark_invalid_bets(data, now_timestamp)
        # Applies 8-to-7 and short-price-removed rules
        
    def _mark_fully_matched_bets(data, now_timestamp)
        # Checks if max exposure reached
        
    def _set_time_based_stake_size(requests_data)
        # Adds stake_size column based on minutes_to_race
        
    def _set_new_size_and_price(data)
        # Calculates remaining_size and amended_average_price
        
    def _check_odds_available(data)
        # Checks if current price meets requested_odds requirement
        
    def _create_bet_data(data)
        # Creates BetFairOrder objects for eligible bets
        
    def _process_cash_outs(trades)
        # Executes cash-outs for invalidated positions
```

### Data Flow Through MarketTrader

```
requests_data (input)
       │
       ▼
_set_time_based_stake_size()    → Adds stake_size column
       │
       ▼
_mark_invalid_bets()            → Sets valid=False for bad conditions
       │
       ▼
_mark_fully_matched_bets()      → Sets fully_matched=True if max exposure
       │
       ▼
_set_new_size_and_price()       → Calculates remaining_size, amended_average_price
       │
       ▼
_check_odds_available()         → Sets available_odds=True/False
       │
       ▼
_create_bet_data()              → Creates BetFairOrder list + cash_out_market_ids
       │
       ▼
_process_orders()               → Places orders with Betfair
       │
       ▼
_process_cash_outs()            → Cash out invalidated positions
       │
       ▼
_store_updated_selections_data() → Persist to database
```

---

## Complexity Issues (Why Refactor?)

### Current Pain Points

1. **Too Much Logic in Python**
   - Validation conditions (8-to-7, short-price-removed) are calculated in pandas
   - Could be SQL views that are always up-to-date

2. **Multiple Data Merges**
   - `fetch_requests.py` merges selections + market_state + betfair_market + current_orders
   - `prepare_requests.py` does more merging and column renaming
   - Hard to trace which columns come from where

3. **State Spread Across Multiple Places**
   - Betfair API state (current_orders)
   - Database state (selections)
   - In-memory state (requests_data DataFrame)
   - Reconciling these is complex

4. **Column Explosion**
   - WIN and PLACE data merged with suffixes (`_win`, `_place`)
   - Then split back into separate dataframes
   - Then concatenated again

5. **Business Logic Buried in Code**
   - The "why" of validation rules requires reading Python
   - Would be clearer as documented SQL views

---

## Refactoring Ideas

### Move to Database Views

Create SQL views that encapsulate validation logic:

```sql
-- Example: v_active_runner_count
-- Count active runners per race from live price data
CREATE VIEW live_betting.v_active_runner_count AS
SELECT 
    race_id,
    market_id_win,
    COUNT(*) FILTER (WHERE status = 'ACTIVE') as active_runners,
    COUNT(*) as total_runners
FROM live_betting.updated_price_data
WHERE race_time > CURRENT_TIMESTAMP
GROUP BY race_id, market_id_win;

-- Example: v_short_price_removals
-- Identify races with removed short-priced horses
CREATE VIEW live_betting.v_short_price_removals AS
SELECT DISTINCT
    race_id,
    market_id_win,
    TRUE as has_short_price_removal
FROM live_betting.updated_price_data
WHERE status = 'REMOVED'
  AND betfair_win_sp < 12
  AND race_time > CURRENT_TIMESTAMP;

-- Example: v_eight_to_seven_races
-- Races where runners dropped from 8+ to 7 or fewer
CREATE VIEW live_betting.v_eight_to_seven_races AS
SELECT 
    ms.race_id,
    ms.market_id_win,
    ms.number_of_runners as original_runners,
    arc.active_runners as current_runners,
    TRUE as eight_to_seven
FROM live_betting.market_state ms
JOIN live_betting.v_active_runner_count arc 
    ON ms.market_id_win = arc.market_id_win
WHERE ms.number_of_runners >= 8
  AND arc.active_runners <= 7;

-- Example: v_valid_pending_bets
-- Only bets that pass ALL validation rules
CREATE VIEW live_betting.v_valid_pending_bets AS
SELECT 
    s.*,
    upd.back_price_1_win,
    upd.lay_price_1_win,
    upd.back_price_1_place,
    upd.lay_price_1_place,
    upd.status,
    COALESCE(spr.has_short_price_removal, FALSE) as short_price_removed,
    COALESCE(etr.eight_to_seven, FALSE) as eight_to_seven_runners,
    -- Invalidation logic
    CASE 
        WHEN spr.has_short_price_removal THEN FALSE
        WHEN etr.eight_to_seven AND s.market_type = 'PLACE' THEN FALSE
        ELSE s.valid
    END as computed_valid,
    CASE 
        WHEN spr.has_short_price_removal THEN 'Invalid Short Price Removed'
        WHEN etr.eight_to_seven AND s.market_type = 'PLACE' THEN 'Invalid 8 to 7 Place'
        ELSE s.invalidated_reason
    END as computed_invalidated_reason
FROM live_betting.selections s
JOIN live_betting.updated_price_data upd 
    ON s.selection_id = upd.selection_id 
    AND s.market_id = upd.market_id_win
LEFT JOIN live_betting.v_short_price_removals spr 
    ON s.race_id = spr.race_id
LEFT JOIN live_betting.v_eight_to_seven_races etr 
    ON s.race_id = etr.race_id
WHERE s.race_date = CURRENT_DATE
  AND s.race_time > CURRENT_TIMESTAMP
  AND s.valid = TRUE;
```

**Benefits:**
- SQL is declarative - easier to verify correctness
- Single source of truth
- Can query views directly for debugging
- Python just consumes the result

### Simplify Data Flow

```
Current:
  fetch_requests → prepare_requests → market_trader → betfair

Proposed:
  DB View (v_tradeable_selections) → market_trader → betfair
```

### Separate Concerns

| Layer | Responsibility |
|-------|---------------|
| **Database** | Validation logic, state management |
| **Python** | Orchestration, API calls, staking calculations |
| **Betfair Client** | Order placement, cash-outs |

### Proposed Simplified Python Flow

```python
# Simplified fetch_requests.py
def fetch_tradeable_selections(postgres_client):
    """Just fetch from the view - all validation done in SQL"""
    return postgres_client.fetch_data("""
        SELECT * FROM live_betting.v_valid_pending_bets
        WHERE computed_valid = TRUE
    """)

# Simplified market_trader.py  
def trade_markets(self, selections):
    # Much simpler - just:
    # 1. Calculate time-based stakes
    # 2. Check if price meets requested_odds
    # 3. Create orders
    # 4. Place orders
    # No more validation logic in Python!
    pass
```

---

## Testing

Tests are in `tests/` with pytest fixtures:

- `test_invalidates_bets.py` - Tests validation conditions
- `test_bets_existing_position.py` - Tests with prior matched amounts
- `test_bets_no_existing_position.py` - Tests fresh bets
- `test_bet_success.py` - Happy path tests

Mock clients (`TestPostgresClient`, `TestBetfairClient`) allow unit testing without real APIs.

---

## Configuration

### Environment

- Runs on cron job starting at a configured time
- Sleeps 2 minutes between iterations before 10am
- Sleeps 15 seconds between iterations after 10am
- Exits after max race time for the day

### Staking Config

Edit `config/staking_config.yaml` to adjust:
- `time_based_back_staking_size` - BACK stakes by time bracket
- `time_based_lay_staking_size` - LAY liability by time bracket
- `max_back_staking_size` - Maximum BACK stake (default £50)
- `max_lay_staking_size` - Maximum LAY liability (default £75)

### Stake Points

Each selection can have a `stake_points` multiplier:
- `stake_points = 1.0` → Normal stake
- `stake_points = 2.0` → Double stake
- `stake_points = 0.5` → Half stake

---

## Next Steps for Refactor

1. **Export live_betting schema** (use `backup_live_betting_schema.sh`)
2. **Design SQL views** for validation logic
3. **Simplify `prepare_requests.py`** to just consume views
4. **Reduce column manipulation** in Python
5. **Add better logging/observability**
6. **Consider event-driven architecture** vs polling loop
