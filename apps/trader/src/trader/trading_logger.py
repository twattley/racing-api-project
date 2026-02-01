"""
Trading Logger - Enhanced logging for the trader module.

Provides formatted logging for:
- SelectionState lists (selection state summaries)
- Order details
- Trading decisions
- Performance metrics

Verbosity modes:
- QUIET: Only log when actions are taken (orders, cash-outs, invalidations)
- NORMAL: Log cycle summaries + actions
- VERBOSE: Log everything including individual selections
"""

from trader.executor import ExecutionSummary
from trader.order_cleanup import CleanupSummary

from collections import Counter
from datetime import datetime
from typing import Any

from api_helpers.helpers.logging_config import D, I, W, E

from .models import SelectionState


# ============================================================================
# VERBOSITY CONTROL
# ============================================================================

# Set this to control log verbosity:
# "QUIET"   - Only log when something happens (recommended for production)
# "NORMAL"  - Log cycle summaries
# "VERBOSE" - Log everything (useful for debugging)
LOG_LEVEL = "VERBOSE"

# How often to log full state in QUIET mode (every N cycles)
FULL_LOG_INTERVAL = 40  # ~10 minutes at 15s intervals

_cycle_count = 0


def set_log_level(level: str) -> None:
    """Set the logging verbosity level."""
    global LOG_LEVEL
    if level in ("QUIET", "NORMAL", "VERBOSE"):
        LOG_LEVEL = level


def _should_log(level: str) -> bool:
    """Check if we should log at this level."""
    levels = {"QUIET": 0, "NORMAL": 1, "VERBOSE": 2}
    return levels.get(LOG_LEVEL, 1) >= levels.get(level, 1)


def log_selection_state_summary(selections: list[SelectionState]) -> None:
    """Log a summary of the selection state list."""
    global _cycle_count
    _cycle_count += 1

    if not selections:
        if _should_log("NORMAL"):
            I("Selection state: No selections for now")
        return

    # In QUIET mode, only log full state periodically
    if LOG_LEVEL == "QUIET" and _cycle_count % FULL_LOG_INTERVAL != 0:
        return

    total = len(selections)
    valid = sum(1 for s in selections if s.valid)
    has_bet = sum(1 for s in selections if s.has_bet)

    I(f"═══════════════════════════════════════════════════════════")
    I(f"SELECTION STATE: {total} total, {valid} valid, {has_bet} with bets")
    I(f"═══════════════════════════════════════════════════════════")

    # Group by time bucket for overview
    def get_time_bucket(mins: float) -> str:
        if mins < 30:
            return "<30m"
        elif mins < 60:
            return "30-60m"
        elif mins < 120:
            return "1-2h"
        elif mins < 180:
            return "2-3h"
        else:
            return ">3h"

    time_buckets = Counter(get_time_bucket(s.minutes_to_race) for s in selections)
    I(f"By time to race: {dict(time_buckets)}")

    # Log each selection only in VERBOSE mode
    if _should_log("VERBOSE"):
        for selection in selections:
            _log_selection(selection)


def _log_selection(selection: SelectionState) -> None:
    """Log a single selection in a compact format."""
    unique_id = selection.unique_id
    horse = selection.horse_name[:20]
    sel_type = selection.selection_type.value
    market = selection.market_type.value
    odds = selection.requested_odds
    mins = selection.minutes_to_race
    valid = "✓" if selection.valid else "✗"
    has_bet = "💰" if selection.has_bet else ""

    back_price = selection.current_back_price or "-"
    lay_price = selection.current_lay_price or "-"

    # Use INFO in VERBOSE mode so it shows up
    I(
        f"  {valid} {unique_id[:30]:<30} | {horse:<20} | "
        f"{sel_type} {market} @ {odds} | "
        f"B:{back_price} L:{lay_price} | "
        f"{mins:.0f}m {has_bet}"
    )


def log_decision_summary(
    orders: list,
    cash_outs: list[str],
    invalidations: list[tuple[str, str]],
    cancel_orders: list | None = None,
) -> None:
    """Log a summary of decisions made."""
    cancel_orders = cancel_orders or []
    # In QUIET mode, only log if there's something to do
    has_actions = orders or cash_outs or invalidations or cancel_orders
    if LOG_LEVEL == "QUIET" and not has_actions:
        return

    if not _should_log("NORMAL") and not has_actions:
        return

    I(f"───────────────────────────────────────────────────────────")
    I(
        f"DECISIONS: {len(orders)} orders, {len(cash_outs)} cash-outs, {len(invalidations)} invalidations, {len(cancel_orders)} cancels"
    )
    I(f"───────────────────────────────────────────────────────────")

    # Always log actual orders/actions
    if orders:
        for order in orders:
            _log_order(order)

    if cash_outs:
        I(f"  Cash out markets: {cash_outs}")

    if invalidations:
        for unique_id, reason in invalidations:
            W(f"  INVALID: {unique_id} - {reason}")


def _log_order(order_with_state: Any) -> None:
    """Log a single order."""
    order = order_with_state.order
    stake_ok = "✓" if order_with_state.within_stake_limit else "⚠️ LIMIT"

    I(
        f"  ORDER: {order.side} {order.size:.2f} @ {order.price} "
        f"[{order.market_id}:{order.selection_id}] "
        f"{stake_ok}"
    )


def log_order_placement(
    unique_id: str,
    side: str,
    size: float,
    price: float,
    order_type: str = "NORMAL",
) -> None:
    """Log order placement attempt."""
    I(f"  📤 PLACING [{order_type}]: {unique_id} - {side} {size:.2f} @ {price}")


def log_order_result(
    unique_id: str,
    success: bool,
    message: str = "",
    matched: float = 0,
) -> None:
    """Log order placement result."""
    if success:
        if matched > 0:
            I(f"  ✅ PLACED & MATCHED: {unique_id} - {matched:.2f} matched")
        else:
            I(f"  ✅ PLACED: {unique_id} - waiting for match")
    else:
        E(f"  ❌ FAILED: {unique_id} - {message}")


def log_stale_order(
    unique_id: str,
    placed_date: datetime,
    expires_at: datetime,
) -> None:
    """Log stale order detection."""
    W(
        f"  ⏱️ STALE ORDER: {unique_id} - "
        f"placed {placed_date}, expires {expires_at}, cancelling"
    )


def log_execution_summary(summary: ExecutionSummary) -> None:
    """Log execution cycle summary."""
    # Only log if something actually happened
    if not summary.has_activity:
        return

    I(f"═══════════════════════════════════════════════════════════")
    I(f"EXECUTION COMPLETE:")
    if summary.orders_placed > 0:
        I(f"  orders_placed: {summary.orders_placed}")
    if summary.orders_matched > 0:
        I(f"  orders_matched: {summary.orders_matched}")
    if summary.orders_failed > 0:
        I(f"  orders_failed: {summary.orders_failed}")
    if summary.orders_skipped > 0:
        I(f"  orders_skipped: {summary.orders_skipped}")
    if summary.orders_cancelled > 0:
        I(f"  orders_cancelled: {summary.orders_cancelled}")
    if summary.cash_outs > 0:
        I(f"  cash_outs: {summary.cash_outs}")
    if summary.invalidations > 0:
        I(f"  invalidations: {summary.invalidations}")
    I(f"═══════════════════════════════════════════════════════════")


def log_cleanup_summary(summary: CleanupSummary) -> None:
    """Log order cleanup summary."""
    if not summary.has_activity:
        return

    I(f"🧹 ORDER CLEANUP: {summary.total_cancelled} cancelled")
    if summary.cancelled_stale > 0:
        I(f"  stale: {summary.cancelled_stale}")
    if summary.cancelled_imminent > 0:
        I(f"  imminent: {summary.cancelled_imminent}")


def log_cycle_start(cycle_num: int) -> None:
    """Log start of a trading cycle."""
    # In QUIET mode, don't log cycle starts (too noisy)
    if LOG_LEVEL == "QUIET":
        return

    now = datetime.now().strftime("%H:%M:%S")
    I(f"  TRADING CYCLE {now}")


def log_reconciliation(
    completed: int,
    pending: int,
    cleaned: int,
) -> None:
    """Log reconciliation results."""
    if completed or pending or cleaned:
        I(
            f"  🔄 RECONCILED: {completed} completed, {pending} pending updated, {cleaned} cleaned"
        )
