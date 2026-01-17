# Trader - Behavioural Specification

## What is the Trader?

The Trader is an automated betting execution system. You make selections in the morning; it executes them throughout the day at acceptable prices.

---

## Core Behaviours

### 1. Polling Loop

The trader runs continuously, polling every **15 seconds**:

1. Sync any pending bets from local backup to database
2. Refresh live prices from Betfair
3. Fetch current selection state
4. Decide what actions to take
5. Execute orders and cash-outs

The trader exits when the last race of the day has passed.

---

### 2. Placing Bets

**When to place a bet:**

- Selection is valid (not invalidated)
- Selection is not fully matched
- Current price meets the requested threshold:
  - **BACK**: `current_back_price >= requested_odds`
  - **LAY**: `current_lay_price <= requested_odds`
- Remaining stake/liability is > £1

**Partial matching:**

- If a bet is partially matched, the trader places a top-up order for the remaining amount
- For BACK bets: `remaining = target_stake - total_matched`
- For LAY bets: remaining is calculated based on **liability**, not stake

**Price used for orders:**

- Orders are placed at the **current market price**, not the requested price
- The requested price is only used as a threshold (minimum for BACK, maximum for LAY)

---

### 3. LAY Bet Liability

LAY bets work on **liability** (your maximum loss), not stake.

| Term          | Meaning                               |
| ------------- | ------------------------------------- |
| **Stake**     | Amount you're laying (backer's stake) |
| **Liability** | Your max loss = `stake × (odds - 1)`  |

**Example:**

- Target: £20 liability at odds 3.0
- If current odds are 2.5: stake needed = `£20 / (2.5 - 1) = £13.33`
- If partially matched £10 @ 2.5 = £15 liability used
- Remaining liability = £20 - £15 = £5
- Next stake = `£5 / (current_odds - 1)`

---

### 4. Staking Tiers

Stakes increase as race time approaches. This is configured in the database:

| Minutes to Race | Multiplier |
| --------------- | ---------- |
| 120+            | 0.1 (10%)  |
| 60-120          | 0.25 (25%) |
| 30-60           | 0.5 (50%)  |
| < 30            | 1.0 (100%) |

The calculated stake = `max_stake × multiplier × stake_points`

Where:

- `max_stake` comes from `staking_config` table (separate for BACK and LAY)
- `stake_points` is per-selection (default 1.0, can be higher for strong conviction)

---

### 5. Invalidation Rules

A selection becomes **invalid** when market conditions change in ways that fundamentally alter the bet's value.

#### Rule: 8-to-Less-Than-8 Runners (PLACE bets only)

**Trigger:** Original runners = 8, current runners < 8

**Reason:** Place terms change. With 8+ runners, typically 1-2-3-4 pay. With fewer, only 1-2-3 pay. The bet was priced for 4-place terms.

**Action:**

- Mark selection as invalid
- If bet exists → cash out

#### Rule: Runner Removed

**Trigger:** Selection's runner status = `REMOVED`

**Reason:** Horse is a non-runner. Can't bet on it.

**Action:**

- Mark selection as invalid
- If bet exists → cash out

#### Rule: Short Price Removal (TODO)

**Trigger:** Any horse in the race with odds < 12 is removed

**Reason:** When a short-priced horse withdraws, remaining horses' odds compress significantly. The value calculation that led to the selection is no longer valid.

**Action:**

- Mark all selections in that race as invalid
- Cash out any existing bets

---

### 6. Cash Out

Cash out is triggered when:

- A selection with an existing bet becomes invalid
- The trader calls Betfair's cash-out API for the market

This closes out the position at current market prices, locking in a small loss/gain rather than letting an invalidated bet run.

---

### 7. Fully Matched Detection

A selection is **fully matched** when target exposure is reached:

- **BACK:** `total_matched >= calculated_stake`
- **LAY:** `matched_liability >= target_liability`

Once fully matched, no more orders are placed for that selection.

---

### 8. Failover & Duplicate Prevention

To prevent duplicate bets when database writes fail:

1. Before placing a bet, generate a unique `bet_attempt_id`
2. Write to local Parquet file first (write-ahead log)
3. Place the bet with Betfair
4. Update Parquet with result
5. Write to database

On each loop:

- Sync any Parquet entries not yet in database
- Check Parquet before placing to avoid duplicates

Only today's data is checked/synced (older data ignored).

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    MORNING (via Frontend/API)                    │
├─────────────────────────────────────────────────────────────────┤
│  1. Create selection in live_betting.selections                 │
│  2. Capture market snapshot in live_betting.market_state        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TRADER (Automated Loop)                       │
├─────────────────────────────────────────────────────────────────┤
│  1. Fetch live prices → live_betting.betfair_prices         │
│  2. Read v_selection_state view (joins all data)                │
│  3. Decision engine decides: place / cash out / wait            │
│  4. Executor performs actions via Betfair API                   │
│  5. Record bets in live_betting.bet_log                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Tables

| Table                | Purpose                                              |
| -------------------- | ---------------------------------------------------- |
| `selections`         | Your bet selections with validity state              |
| `market_state`       | Snapshot at selection time (original runners, price) |
| `updated_price_data` | Live prices from Betfair (refreshed each loop)       |
| `bet_log`            | Record of every bet placed                           |
| `staking_config`     | Max stake for BACK and LAY                           |
| `staking_tiers`      | Time-based multipliers                               |

---

## Key View

### `v_selection_state`

Single source of truth for the decision engine. Joins:

- `selections` (what you want to bet)
- `market_state` (original conditions)
- `updated_price_data` (current prices)
- `bet_log` (what's been bet so far)
- `staking_config` + `staking_tiers` (calculated stake)

Returns one row per selection with everything needed to decide.

---

## What the Trader Does NOT Do

- **Pick selections** - You do this manually in the morning
- **Analyse form** - That's your job
- **Set prices** - You set the requested_odds with your margin built in
- **Chase prices** - It only bets when price meets your threshold
- **Bet after race time** - Selections filtered to `race_time > now()`
