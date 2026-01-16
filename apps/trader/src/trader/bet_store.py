"""
Bet Store - Handles bet logging with Parquet failover.

This module provides reliable bet storage:
- Writes to Parquet first (local backup)
- Then writes to database
- Syncs any missed DB writes at start of each loop

The Parquet file acts as a write-ahead log to prevent
data loss if database writes fail.
"""

import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder, OrderResult
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.helpers.logging_config import E, I, W

# Parquet file for local bet log backup
BET_LOG_PARQUET = Path(__file__).parent / "data" / "bet_log.parquet"


# ============================================================================
# PARQUET FUNCTIONS
# ============================================================================


def _load_parquet_log() -> pd.DataFrame:
    """Load the local Parquet bet log, or return empty DataFrame if not exists."""
    if BET_LOG_PARQUET.exists():
        return pd.read_parquet(BET_LOG_PARQUET)
    return pd.DataFrame()


def _save_parquet_log(df: pd.DataFrame) -> None:
    """Save DataFrame to local Parquet bet log."""
    BET_LOG_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(BET_LOG_PARQUET, index=False)


# ============================================================================
# PUBLIC API
# ============================================================================


def generate_bet_attempt_id() -> str:
    """Generate a unique ID for a bet attempt."""
    return str(uuid.uuid4())[:16]


def has_bet_in_parquet(selection_unique_id: str) -> bool:
    """
    Check if we already have a bet for this selection in Parquet (today only).

    This is the critical check - even if DB sync fails, we won't
    double-bet because Parquet is our source of truth.
    """
    parquet_log = _load_parquet_log()
    if parquet_log.empty:
        return False

    if "selection_unique_id" not in parquet_log.columns:
        return False

    # Only check today's bets
    today = datetime.now().date()
    if "placed_at" in parquet_log.columns:
        parquet_log["placed_at"] = pd.to_datetime(parquet_log["placed_at"])
        todays_bets = parquet_log[parquet_log["placed_at"].dt.date == today]
    else:
        todays_bets = parquet_log

    return (todays_bets["selection_unique_id"] == selection_unique_id).any()


def sync_parquet_to_db(postgres_client: PostgresClient) -> int:
    """
    Sync any Parquet entries that aren't in the database (today only).

    Call this at the start of each loop to ensure DB has all bet attempts.
    Returns number of rows synced.
    """
    parquet_log = _load_parquet_log()
    if parquet_log.empty:
        return 0

    # Only sync today's entries
    today = datetime.now().date()
    if "placed_at" in parquet_log.columns:
        parquet_log["placed_at"] = pd.to_datetime(parquet_log["placed_at"])
        parquet_log = parquet_log[parquet_log["placed_at"].dt.date == today]
        if parquet_log.empty:
            return 0

    # Get existing bet_attempt_ids from DB (today only)
    try:
        db_log = postgres_client.fetch_data(
            "SELECT bet_attempt_id FROM live_betting.bet_log WHERE bet_attempt_id IS NOT NULL AND placed_at::date = CURRENT_DATE"
        )
        existing_ids = (
            set(db_log["bet_attempt_id"].tolist()) if not db_log.empty else set()
        )
    except Exception as e:
        W(f"Could not fetch existing bet_attempt_ids: {e}")
        existing_ids = set()

    # Find Parquet rows not in DB
    if "bet_attempt_id" not in parquet_log.columns:
        return 0

    missing = parquet_log[~parquet_log["bet_attempt_id"].isin(existing_ids)]

    if missing.empty:
        return 0

    # Insert missing rows
    I(f"Syncing {len(missing)} missing bet log entries from Parquet to DB")
    try:
        db_columns = [
            "bet_attempt_id",
            "selection_unique_id",
            "market_id",
            "selection_id",
            "side",
            "selection_type",
            "requested_price",
            "requested_size",
            "matched_price",
            "matched_size",
            "matched_liability",
            "status",
            "placed_at",
            "expires_at",
        ]
        missing_for_db = missing[[c for c in db_columns if c in missing.columns]]

        postgres_client.store_data(
            data=missing_for_db,
            table="bet_log",
            schema="live_betting",
        )
        return len(missing)
    except Exception as e:
        E(f"Failed to sync Parquet to DB: {e}")
        return 0


def write_pending_bet(
    bet_attempt_id: str,
    unique_id: str,
    order: BetFairOrder,
    selection_type: str,
    now: datetime,
) -> None:
    """
    Write a pending bet to Parquet before placing.

    Call this BEFORE placing the bet with Betfair.
    """
    row = {
        "bet_attempt_id": bet_attempt_id,
        "selection_unique_id": unique_id,
        "market_id": order.market_id,
        "selection_id": int(order.selection_id),
        "side": order.side,
        "selection_type": selection_type,
        "requested_price": order.price,
        "requested_size": order.size,
        "matched_price": None,
        "matched_size": None,
        "matched_liability": None,
        "status": "PENDING",
        "placed_at": now,
        "expires_at": now + timedelta(minutes=5),
    }

    parquet_log = _load_parquet_log()
    new_row = pd.DataFrame([row])

    if parquet_log.empty:
        updated = new_row
    else:
        updated = pd.concat([parquet_log, new_row], ignore_index=True)

    _save_parquet_log(updated)
    I(f"[{unique_id}] Wrote pending bet {bet_attempt_id} to Parquet")


def _calculate_matched_liability(
    selection_type: str,
    matched_size: float | None,
    matched_price: float | None,
) -> float | None:
    """
    Calculate matched liability from size and price.

    BACK: liability = stake (matched_size)
    LAY: liability = matched_size * (matched_price - 1)
    """
    if matched_size is None or matched_size == 0:
        return None

    if selection_type == "BACK":
        return matched_size
    elif selection_type == "LAY":
        if matched_price is None or matched_price <= 1:
            return None
        return matched_size * (matched_price - 1)
    return None


def update_bet_result(
    bet_attempt_id: str,
    status: str,
    result: OrderResult,
) -> None:
    """
    Update Parquet with the bet result after placing.

    Call this AFTER placing the bet with Betfair.
    """
    parquet_log = _load_parquet_log()
    if parquet_log.empty:
        return

    mask = parquet_log["bet_attempt_id"] == bet_attempt_id
    if mask.any():
        parquet_log.loc[mask, "status"] = status
        parquet_log.loc[mask, "matched_price"] = (
            result.average_price_matched if result.success else None
        )
        parquet_log.loc[mask, "matched_size"] = (
            result.size_matched if result.success else None
        )

        # Calculate matched_liability
        selection_type = parquet_log.loc[mask, "selection_type"].iloc[0]
        matched_liability = _calculate_matched_liability(
            selection_type,
            result.size_matched if result.success else None,
            result.average_price_matched if result.success else None,
        )
        parquet_log.loc[mask, "matched_liability"] = matched_liability

        _save_parquet_log(parquet_log)


def store_bet_to_db(
    bet_attempt_id: str,
    unique_id: str,
    order: BetFairOrder,
    selection_type: str,
    result: OrderResult,
    status: str,
    now: datetime,
    postgres_client: PostgresClient,
) -> None:
    """
    Store the bet in the database.

    Call this AFTER updating Parquet with the result.
    """
    matched_price = result.average_price_matched if result.success else None
    matched_size = result.size_matched if result.success else None
    matched_liability = _calculate_matched_liability(
        selection_type, matched_size, matched_price
    )

    data = pd.DataFrame(
        [
            {
                "bet_attempt_id": bet_attempt_id,
                "selection_unique_id": unique_id,
                "market_id": order.market_id,
                "selection_id": int(order.selection_id),
                "side": order.side,
                "selection_type": selection_type,
                "requested_price": order.price,
                "requested_size": order.size,
                "matched_price": matched_price,
                "matched_size": matched_size,
                "matched_liability": matched_liability,
                "status": status,
                "placed_at": now,
                "expires_at": now + timedelta(minutes=5),
            }
        ]
    )

    postgres_client.store_data(
        data=data,
        table="bet_log",
        schema="live_betting",
    )

    I(
        f"[{unique_id}] Recorded bet: {status} - matched {result.size_matched or 0}/{order.size}"
    )
