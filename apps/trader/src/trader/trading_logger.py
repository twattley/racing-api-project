"""
Trading Logger - Enhanced logging for the trader module.

Provides formatted logging for:
- DataFrames (selection state summaries)
- Order details
- Trading decisions
- Performance metrics

Verbosity modes:
- QUIET: Only log when actions are taken (orders, cash-outs, invalidations)
- NORMAL: Log cycle summaries + actions
- VERBOSE: Log everything including individual selections
"""

from datetime import datetime
from typing import Any

import pandas as pd
from api_helpers.helpers.logging_config import D, I, W, E


# ============================================================================
# VERBOSITY CONTROL
# ============================================================================

# Set this to control log verbosity:
# "QUIET"   - Only log when something happens (recommended for production)
# "NORMAL"  - Log cycle summaries
# "VERBOSE" - Log everything (useful for debugging)
LOG_LEVEL = "QUIET"

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


def log_selection_state_summary(df: pd.DataFrame) -> None:
    """Log a summary of the selection state DataFrame."""
    global _cycle_count
    _cycle_count += 1

    if df.empty:
        if _should_log("NORMAL"):
            I("Selection state: No selections for now")
        return

    # In QUIET mode, only log full state periodically
    if LOG_LEVEL == "QUIET" and _cycle_count % FULL_LOG_INTERVAL != 0:
        return

    total = len(df)
    valid = df["valid"].sum() if "valid" in df.columns else total
    has_bet = df["has_bet"].sum() if "has_bet" in df.columns else 0

    I(f"═══════════════════════════════════════════════════════════")
    I(f"SELECTION STATE: {total} total, {valid} valid, {has_bet} with bets")
    I(f"═══════════════════════════════════════════════════════════")

    # Group by time bucket for overview
    if "minutes_to_race" in df.columns:
        df_copy = df.copy()
        df_copy["time_bucket"] = pd.cut(
            df_copy["minutes_to_race"],
            bins=[-float("inf"), 30, 60, 120, 180, float("inf")],
            labels=["<30m", "30-60m", "1-2h", "2-3h", ">3h"],
        )
        time_summary = df_copy.groupby("time_bucket", observed=True).size()
        I(f"By time to race: {time_summary.to_dict()}")

    # Log each selection only in VERBOSE mode
    if _should_log("VERBOSE"):
        for _, row in df.iterrows():
            _log_selection_row(row)


def _log_selection_row(row: pd.Series) -> None:
    """Log a single selection row in a compact format."""
    unique_id = row.get("unique_id", "?")
    horse = row.get("horse_name", "?")[:20]
    sel_type = row.get("selection_type", "?")
    market = row.get("market_type", "?")
    odds = row.get("requested_odds", 0)
    mins = row.get("minutes_to_race", 0)
    valid = "✓" if row.get("valid", False) else "✗"
    has_bet = "💰" if row.get("has_bet", False) else ""

    back_price = row.get("current_back_price", "-")
    lay_price = row.get("current_lay_price", "-")

    D(
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
    fok = "🚀 FOK" if order_with_state.use_fill_or_kill else ""
    stake_ok = "✓" if order_with_state.within_stake_limit else "⚠️ LIMIT"

    I(
        f"  ORDER: {order.side} {order.size:.2f} @ {order.price} "
        f"[{order.market_id}:{order.selection_id}] "
        f"{fok} {stake_ok}"
    )


def log_early_bird_decision(
    selection_id: str,
    horse_name: str,
    is_early_bird: bool,
    reason: str,
) -> None:
    """Log early bird eligibility decision."""
    if is_early_bird:
        I(f"  🐦 EARLY BIRD: {selection_id} ({horse_name}) - {reason}")
    else:
        D(f"  ⏰ NORMAL: {selection_id} ({horse_name}) - {reason}")


def log_early_bird_orders(orders: list) -> None:
    """Log generated early bird orders."""
    if not orders:
        return

    I(f"  🐦 Generated {len(orders)} early bird orders:")
    for order in orders:
        I(f"      {order.description}")


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


def log_execution_summary(summary: dict) -> None:
    """Log execution cycle summary."""
    # Only log if something actually happened
    has_activity = any(v > 0 for k, v in summary.items() if k != "orders_skipped")
    if not has_activity:
        return

    I(f"═══════════════════════════════════════════════════════════")
    I(f"EXECUTION COMPLETE:")
    for key, value in summary.items():
        if value > 0:
            I(f"  {key}: {value}")
    I(f"═══════════════════════════════════════════════════════════")


def log_cycle_start(cycle_num: int) -> None:
    """Log start of a trading cycle."""
    # In QUIET mode, don't log cycle starts (too noisy)
    if LOG_LEVEL == "QUIET":
        return

    now = datetime.now().strftime("%H:%M:%S")
    I(f"")
    I(f"╔═══════════════════════════════════════════════════════════╗")
    I(f"║  TRADING CYCLE {cycle_num} - {now}                        ║")
    I(f"╚═══════════════════════════════════════════════════════════╝")


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
