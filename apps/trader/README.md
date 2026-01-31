# Trader - Automated Horse Racing Trading System

An automated trading system for placing and managing bets on horse racing markets via the Betfair exchange. The system implements a sophisticated trading loop with multiple strategies, validation rules, and risk management features.

## Overview

The Trader application is designed to execute trading decisions autonomously while maintaining strict separation between decision-making (pure functions) and execution (side effects). This architecture enables comprehensive testing and predictable behaviour.

### Key Features

- **Dual Trading Modes**: Early Bird (passive) and Normal (active) trading strategies
- **Pure Decision Engine**: All trading logic is deterministic and side-effect free
- **Automated Reconciliation**: Continuous synchronisation with Betfair's order state
- **Risk Management**: Multiple validation layers protect against adverse market conditions
- **Liability Tracking**: Separate handling for BACK (stake-based) and LAY (liability-based) bets
- **Network Resilience**: Built-in handling for connectivity issues and service outages

## Architecture

The system follows a clean separation of concerns with distinct modules handling specific responsibilities:

### Core Components

| Module | Purpose |
|--------|---------|
| **Main Loop** | Orchestrates the trading cycle and handles lifecycle management |
| **Decision Engine** | Pure function that transforms selection state into trading actions |
| **Executor** | Handles all side effects: order placement, cancellation, cash-outs |
| **Reconciliation** | Synchronises database state with Betfair's source of truth |
| **Price Service** | Fetches and stores live market prices independently |

### Data Flow

The system operates on a continuous polling cycle (configurable, default 10 seconds) that processes selections through a clear pipeline:

1. **Price Update**: Fetch current market prices from Betfair and store in database
2. **Reconciliation**: Sync any completed or pending orders from Betfair to local state
3. **Selection Fetch**: Load current selection state including prices, positions, and validation flags
4. **Decision**: Pure function determines what actions to take based on current state
5. **Execution**: Execute the decided actions (place orders, cancel orders, cash out, record invalidations)

## Trading Modes

### Early Bird Mode (>2 hours to race)

When a race is more than 2 hours away, the system enters Early Bird mode. Markets are typically thin with low liquidity during this period, so the strategy focuses on passive order placement.

**Strategy:**
- Places multiple orders at prices better than requested (higher for BACK, lower for LAY)
- Orders are scattered across 4 tick offsets from the base price
- Stakes/liabilities are randomly split to avoid pattern detection
- Orders are placed with staggered delays between them
- Orders sit passively until either matched or cancelled at the 2-hour cutoff

**Tick Offsets:**
- BACK bets: 2, 3, 4, 5 ticks above the base price (better odds for the bettor)
- LAY bets: 2, 3, 4, 5 ticks below the base price (lower liability)

**Fire Once Behaviour:**
Early Bird orders are placed once and then left to sit. The system tracks which selections have Early Bird orders via the order's strategy reference and will not place duplicates.

### Normal Trading Mode (≤2 hours to race)

When a race enters the 2-hour window before post time, the system transitions to Normal mode:

1. Any existing Early Bird orders are cancelled
2. Standard order placement logic takes over
3. Orders are placed at current market prices when acceptable
4. Fill-or-Kill execution may be used when race is imminent (<2 minutes)

## Selection State

The decision engine operates on a list of `SelectionState` objects, each representing a single betting opportunity. This state is derived from a database view that combines:

- Original selection details (horse, race, requested odds, stake points)
- Current market prices (live back/lay prices)
- Betting progress (matched amounts, liability, bet count)
- Validation flags (runner status, place terms changes, short price removals)
- Time-based flags (minutes to race, early bird expiry, fill-or-kill eligibility)
- Stake limit status (whether within configured limits)

## Validation & Risk Management

The system implements multiple validation layers to protect against adverse market conditions:

### Runner Removal

If a selection's runner is removed from the market:
- The selection is immediately invalidated
- Any existing position is cashed out
- No further bets are placed

### Place Terms Changes (8→<8 Rule)

For PLACE market bets, if a race starts with 8 runners and drops below 8:
- The place terms change (typically from 3 places to 2)
- PLACE bets are invalidated as the expected value changes significantly
- Existing positions are cashed out
- WIN bets on the same race remain unaffected

### Short Price Removal

If a short-priced runner (odds < 10.0) is removed from the race:
- All selections for that race may be affected
- Depending on configuration, selections can be invalidated
- This protects against dramatic market shifts

### Stake Limits

The system enforces maximum stake and liability limits:
- BACK bets are tracked by total matched stake
- LAY bets are tracked by total liability (stake × (odds - 1))
- Selections at their limit are skipped until the limit increases

### Manual Invalidation & Cash Out

Users can manually void selections through the frontend:
- If the selection has no matched money, it's simply marked invalid
- If there's matched money, a cash-out is triggered
- Early Bird orders are cancelled for voided selections

## Bet Sizing

The Bet Sizer module handles the complex mathematics of determining stake amounts:

### BACK Bets
- Simple stake arithmetic
- Remaining stake = Target stake - Already matched
- Price must be ≥ requested odds to place

### LAY Bets
- Liability-based calculations
- Target is expressed as liability, not stake
- Stake = Remaining liability ÷ (Current odds - 1)
- Price must be ≤ requested odds to place

Both types respect minimum stake requirements (configurable) and round down to valid amounts.

## Price Ladder

Betfair uses specific price increments that vary by price range. The Price Ladder module provides:

- Validation of prices against Betfair's accepted increments
- Movement by ticks (discrete price steps)
- Snapping arbitrary prices to valid ladder prices
- Support for the full ladder from 1.01 to 20.00

**Increment Ranges:**
| Price Range | Increment |
|-------------|-----------|
| 1.01 - 2.00 | 0.01 |
| 2.00 - 3.00 | 0.02 |
| 3.00 - 4.00 | 0.05 |
| 4.00 - 6.00 | 0.10 |
| 6.00 - 10.00 | 0.20 |
| 10.00 - 20.00 | 0.50 |

## Reconciliation

The Reconciliation module ensures database state reflects Betfair's reality:

### Tables Maintained
- **bet_log**: One row per selection for completed orders (matched bets)
- **pending_orders**: One row per selection for executable orders (unmatched)

### Process
1. Fetch all current orders from Betfair (filtered to trader orders only)
2. For EXECUTION_COMPLETE orders: Upsert to bet_log, remove from pending_orders
3. For EXECUTABLE orders: Upsert to pending_orders

This runs at the start of every trading cycle, ensuring accurate state before any decisions are made.

## Order Management

### Order Lifecycle
1. **Creation**: Decision engine creates `OrderWithState` objects
2. **Validation**: Checks for existing orders, staleness, stake limits
3. **Placement**: Executor sends to Betfair API
4. **Tracking**: Pending orders tracked in database
5. **Reconciliation**: Completed orders moved to bet_log

### Stale Order Handling

Orders that have been waiting too long are considered stale and cancelled:
- Normal orders: 5 minute timeout
- Early Bird orders: Persist until early bird expiry (race time - 2 hours)
- The system uses `max(early_bird_expiry, placed_date + timeout)` to automatically handle the transition

### Fill-or-Kill

When a race is imminent (configurable, typically <2 minutes):
- Orders are placed with fill-or-kill instruction
- Either the full amount matches immediately, or the order is cancelled
- Prevents partial fills that can't be topped up before the race starts

## Network Resilience

The system includes built-in handling for network issues:

- Pre-flight network connectivity check before each cycle
- Automatic wait and retry for network outages (up to 5 minutes)
- Distinction between network errors and application errors
- Graceful degradation with exponential backoff

## Logging

Configurable verbosity levels:

| Level | Description |
|-------|-------------|
| QUIET | Only logs when actions occur (orders, cash-outs, invalidations) |
| NORMAL | Logs cycle summaries plus actions |
| VERBOSE | Logs everything including individual selections |

In QUIET mode, full state is periodically logged (every N cycles) for monitoring purposes.

## Database Schema

The system relies on several database tables in the `live_betting` schema:

- **selections**: Original selection requests from the model
- **betfair_prices**: Live price updates from Betfair
- **bet_log**: Completed (matched) orders, one row per selection
- **pending_orders**: Active (executable) orders on Betfair
- **v_selection_state**: View combining all data needed for decision-making

## Testing

The codebase includes comprehensive test coverage:

- **Decision Engine Tests**: Pure function testing with various selection states
- **Early Bird Tests**: Strategy-specific tests for scatter order logic
- **Reconciliation Tests**: Database sync and upsert logic
- **Bet Sizer Tests**: BACK and LAY stake calculations
- **Price Ladder Tests**: Tick manipulation and validation
- **Executor Tests**: Order placement and cancellation logic

The pure functional design of the decision engine makes it particularly amenable to exhaustive testing without requiring API mocks.

## Configuration

Key configuration values are defined as module-level constants:

| Setting | Default | Description |
|---------|---------|-------------|
| POLL_INTERVAL_SECONDS | 10 | Time between trading cycles |
| ORDER_TIMEOUT_MINUTES | 5 | How long normal orders wait before being cancelled |
| EARLY_BIRD_BACK_STAKE | £10 | Total stake scattered across early bird BACK orders |
| EARLY_BIRD_LAY_LIABILITY | £15 | Total liability scattered across early bird LAY orders |
| MIN_STAKE_PER_ORDER | £0.50 | Minimum stake for any single order |

## Exit Conditions

The trading loop exits under these conditions:

- Current time exceeds the latest race time for the day
- Network connectivity cannot be restored after 5 minutes
- Unrecoverable application error
