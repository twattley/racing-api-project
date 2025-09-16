import hashlib
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import text
from api_helpers.clients.postgres_client import PostgresClient
from api_helpers.clients.betfair_client import BetFairClient
from api_helpers.helpers.logging_config import E, I, W
from api_helpers.helpers.time_utils import convert_col_utc_to_uk, get_uk_time_now


def update_betfair_prices(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
):
    new_data = betfair_client.create_market_data()
    new_data = new_data.assign(
        created_at=datetime.now().replace(microsecond=0, second=0),
        race_date=new_data["race_time"].dt.date,
    )
    win_and_place = pd.merge(
        new_data[new_data["market"] == "WIN"],
        new_data[new_data["market"] == "PLACE"],
        on=[
            "race_time",
            "course",
            "todays_betfair_selection_id",
            "race_date",
        ],
        suffixes=("_win", "_place"),
    )

    win_and_place = win_and_place.rename(
        columns={
            "horse_win": "horse_name",
            "last_traded_price_win": "betfair_win_sp",
            "last_traded_price_place": "betfair_place_sp",
            "status_win": "status",
            "created_at_win": "created_at",
        }
    )
    win_and_place["race_time_string"] = win_and_place["race_time"].dt.strftime(
        "%Y%m%d%H%M"
    )
    # Build a per-row key and hash it; avoid calling .encode on a Series
    key_series = (
        win_and_place["race_time_string"].astype(str).fillna("")
        + win_and_place["course"].astype(str).fillna("")
        + win_and_place["horse_name"].astype(str).fillna("")
        + win_and_place["todays_betfair_selection_id"].astype(str).fillna("")
    )
    win_and_place["unique_id"] = key_series.map(
        lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
    )
    win_and_place = win_and_place.sort_values(by="race_time", ascending=True)

    data = win_and_place.assign(
        runners_unique_id=win_and_place.groupby("market_id_win")[
            "todays_betfair_selection_id"
        ].transform("sum")
    )

    data = data.pipe(convert_col_utc_to_uk, col_name="race_time")

    new_processed_data = (
        data.rename(
            columns={
                "todays_betfair_selection_id": "selection_id",
            }
        )
        .filter(
            items=[
                "race_time",
                "horse_name",
                "race_date",
                "course",
                "status",
                "market_id_win",
                "selection_id",
                "betfair_win_sp",
                "betfair_place_sp",
                "back_price_1_win",
                "back_price_1_depth_win",
                "back_price_2_win",
                "back_price_2_depth_win",
                "lay_price_1_win",
                "lay_price_1_depth_win",
                "lay_price_2_win",
                "lay_price_2_depth_win",
                "market_place",
                "market_id_place",
                "back_price_1_place",
                "back_price_1_depth_place",
                "back_price_2_place",
                "back_price_2_depth_place",
                "lay_price_1_place",
                "lay_price_1_depth_place",
                "lay_price_2_place",
                "lay_price_2_depth_place",
                "created_at",
                "unique_id",
            ]
        )
        .to_dict(orient="records")
    )

    postgres_client.execute_query(
        """
                INSERT INTO live_betting.updated_price_data(
                    race_time,
                    horse_name,
                    race_date,
                    course,
                    status,
                    market_id_win,
                    selection_id,
                    betfair_win_sp,
                    betfair_place_sp,
                    back_price_1_win,
                    back_price_1_depth_win,
                    back_price_2_win,
                    back_price_2_depth_win,
                    lay_price_1_win,
                    lay_price_1_depth_win,
                    lay_price_2_win,
                    lay_price_2_depth_win,
                    market_place,
                    market_id_place,
                    back_price_1_place,
                    back_price_1_depth_place,
                    back_price_2_place,
                    back_price_2_depth_place,
                    lay_price_1_place,
                    lay_price_1_depth_place,
                    lay_price_2_place,
                    lay_price_2_depth_place,
                    created_at,
                    unique_id
                        )
                    VALUES (
                        :race_time,
                        :horse_name,
                        :race_date,
                        :course,
                        :status,
                        :market_id_win,
                        :selection_id,
                        :betfair_win_sp,
                        :betfair_place_sp,
                        :back_price_1_win,
                        :back_price_1_depth_win,
                        :back_price_2_win,
                        :back_price_2_depth_win,
                        :lay_price_1_win,
                        :lay_price_1_depth_win,
                        :lay_price_2_win,
                        :lay_price_2_depth_win,
                        :market_place,
                        :market_id_place,
                        :back_price_1_place,
                        :back_price_1_depth_place,
                        :back_price_2_place,
                        :back_price_2_depth_place,
                        :lay_price_1_place,
                        :lay_price_1_depth_place,
                        :lay_price_2_place,
                        :lay_price_2_depth_place,
                        :created_at,
                        :unique_id
                        )
                        ON CONFLICT (unique_id)
                        DO UPDATE SET
                            status = EXCLUDED.status,
                            betfair_win_sp = EXCLUDED.betfair_win_sp,
                            betfair_place_sp = EXCLUDED.betfair_place_sp,
                            back_price_1_win = EXCLUDED.back_price_1_win,
                            back_price_1_depth_win = EXCLUDED.back_price_1_depth_win,
                            back_price_2_win = EXCLUDED.back_price_2_win,
                            back_price_2_depth_win = EXCLUDED.back_price_2_depth_win,
                            lay_price_1_win = EXCLUDED.lay_price_1_win,
                            lay_price_1_depth_win = EXCLUDED.lay_price_1_depth_win,
                            lay_price_2_win = EXCLUDED.lay_price_2_win,
                            lay_price_2_depth_win = EXCLUDED.lay_price_2_depth_win,
                            market_place = EXCLUDED.market_place,
                            market_id_place = EXCLUDED.market_id_place,
                            back_price_1_place = EXCLUDED.back_price_1_place,
                            back_price_1_depth_place = EXCLUDED.back_price_1_depth_place,
                            back_price_2_place = EXCLUDED.back_price_2_place,
                            back_price_2_depth_place = EXCLUDED.back_price_2_depth_place,
                            lay_price_1_place = EXCLUDED.lay_price_1_place,
                            lay_price_1_depth_place = EXCLUDED.lay_price_1_depth_place,
                            lay_price_2_place = EXCLUDED.lay_price_2_place,
                            lay_price_2_depth_place = EXCLUDED.lay_price_2_depth_place,
                            created_at = EXCLUDED.created_at;
                """,
        new_processed_data,
    )


def update_live_betting_data(
    betfair_client: BetFairClient,
    postgres_client: PostgresClient,
):
    """Fetch live betting selections from the database and Betfair."""
    start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    selections = postgres_client.fetch_data(
        text("SELECT * FROM live_betting.selections WHERE race_date = CURRENT_DATE;")
    )
    past_orders = betfair_client.get_past_orders_by_date_range(start, end)
    current_orders = betfair_client.get_current_orders()

    if selections.empty:
        return pd.DataFrame(), pd.DataFrame()
    selections = selections[selections["valid"] == True].copy()
    if selections.empty:
        return pd.DataFrame(), pd.DataFrame()

    to_run_df = pd.DataFrame()
    if not current_orders.empty:
        co = current_orders[
            current_orders["execution_status"] == "EXECUTION_COMPLETE"
        ].copy()
        if not co.empty:
            co = (
                co.groupby(
                    ["market_id", "selection_id", "selection_type"], as_index=False
                )
                .agg({"size_matched": "sum", "average_price_matched": "mean"})
                .round(2)
            )
            co = co.assign(
                bet_outcome="TO_BE_RUN",
                profit=np.where(
                    co["selection_type"].str.upper() == "BACK",
                    -co["size_matched"],
                    -co["size_matched"] * (co["average_price_matched"] - 1),
                ),
                commission=0,
                price_matched=co["average_price_matched"],
                side=co["selection_type"].str.upper(),
            )
            # Merge only rows that have current orders (inner join)
            to_run_df = (
                selections.merge(
                    co[
                        [
                            "market_id",
                            "selection_id",
                            "bet_outcome",
                            "price_matched",
                            "profit",
                            "commission",
                            "side",
                            "size_matched",
                            "average_price_matched",
                        ]
                    ],
                    on=["market_id", "selection_id"],
                    how="inner",
                )
                .drop_duplicates(subset=["selection_id", "market_id", "horse_id"])
                .reset_index(drop=True)
            )
            if not to_run_df.empty and "size_matched_x" in to_run_df.columns:
                to_run_df = to_run_df.drop(
                    columns=["size_matched_x", "average_price_matched_x"]
                ).rename(
                    columns={
                        "size_matched_y": "size_matched",
                        "average_price_matched_y": "average_price_matched",
                    }
                )

    ran_df = pd.DataFrame()
    if not past_orders.empty:
        po = past_orders.copy()
        # Sum PnL at (event, market, selection) level
        po["grouped_pnl"] = po.groupby(["event_id", "market_id", "selection_id"])[
            "profit"
        ].transform("sum")
        po_pruned = (
            po[
                [
                    "bet_outcome",
                    "event_id",
                    "market_id",
                    "price_matched",
                    "grouped_pnl",
                    "commission",
                    "selection_id",
                    "side",
                ]
            ]
            .drop_duplicates(subset=["selection_id", "market_id"])
            .rename(columns={"grouped_pnl": "profit"})
        )
        ran_df = (
            selections.merge(
                po_pruned,
                on=["selection_id", "market_id"],
                how="inner",
            )
            .drop_duplicates(subset=["selection_id", "market_id", "horse_id"])
            .reset_index(drop=True)
        )

        if not ran_df.empty and "size_matched_x" in ran_df.columns:
            ran_df = ran_df.drop(
                columns=["size_matched_x", "average_price_matched_x"]
            ).rename(
                columns={
                    "size_matched_y": "size_matched",
                    "average_price_matched_y": "average_price_matched",
                }
            )

    if not pd.api.types.is_datetime64_any_dtype(selections["race_time"]):
        selections.loc[:, "race_time"] = pd.to_datetime(
            selections["race_time"], errors="coerce"
        )

    now = datetime.now()
    future_sel = selections[selections["race_time"] >= now].copy()

    # Exclude selections that already have a 'ran' record
    if not ran_df.empty and not future_sel.empty:
        ran_keys = ran_df[["market_id", "selection_id"]].drop_duplicates()
        future_sel = future_sel.merge(
            ran_keys,
            on=["market_id", "selection_id"],
            how="left",
            indicator=True,
        )
        future_sel = future_sel[future_sel["_merge"] == "left_only"].drop(
            columns=["_merge"]
        )

    # Exclude selections that already appear in to_run from current orders
    if not to_run_df.empty and not future_sel.empty:
        to_run_keys = to_run_df[["market_id", "selection_id"]].drop_duplicates()
        future_sel = future_sel.merge(
            to_run_keys,
            on=["market_id", "selection_id"],
            how="left",
            indicator=True,
        )
        future_sel = future_sel[future_sel["_merge"] == "left_only"].drop(
            columns=["_merge"]
        )

    # Append placeholders for remaining future selections
    if not future_sel.empty:
        future_sel = future_sel.assign(
            bet_outcome="TO_BE_RUN",
            profit=0.0,
            commission=0.0,
            price_matched=None,
            side=future_sel["selection_type"].str.upper(),
        )
        to_run_df = (
            pd.concat([to_run_df, future_sel], ignore_index=True)
            .drop_duplicates(subset=["selection_id", "market_id", "horse_id"])
            .reset_index(drop=True)
        )

    ran_data = ran_df.to_dict(orient="records")
    to_run_data = to_run_df.to_dict(orient="records")

    postgres_client.execute_query(
        """
        INSERT INTO live_betting.upcoming_bets(
                unique_id, 
                race_id, 
                race_time, 
                race_date, 
                horse_id, 
                horse_name, 
                selection_type, 
                market_type, 
                market_id, 
                selection_id, 
                requested_odds, 
                valid, 
                invalidated_at, 
                invalidated_reason, 
                size_matched, 
                average_price_matched, 
                cashed_out, 
                fully_matched, 
                customer_strategy_ref, 
                created_at, 
                processed_at, 
                bet_outcome, 
                event_id, 
                price_matched, 
                profit, 
                commission, 
                side
            )
            VALUES (                
                :unique_id, 
                :race_id, 
                :race_time, 
                :race_date, 
                :horse_id, 
                :horse_name, 
                :selection_type, 
                :market_type, 
                :market_id, 
                :selection_id, 
                :requested_odds, 
                :valid, 
                :invalidated_at, 
                :invalidated_reason, 
                :size_matched, 
                :average_price_matched, 
                :cashed_out, 
                :fully_matched, 
                :customer_strategy_ref, 
                :created_at, 
                :processed_at, 
                :bet_outcome, 
                :event_id, 
                :price_matched, 
                :profit, 
                :commission, 
                :side
            )
                ON CONFLICT (unique_id)
                DO UPDATE SET
                    selection_type = EXCLUDED.selection_type, 
                    requested_odds = EXCLUDED.requested_odds, 
                    valid = EXCLUDED.valid, 
                    invalidated_at = EXCLUDED.invalidated_at, 
                    invalidated_reason = EXCLUDED.invalidated_reason, 
                    size_matched = EXCLUDED.size_matched, 
                    average_price_matched = EXCLUDED.average_price_matched, 
                    cashed_out = EXCLUDED.cashed_out, 
                    fully_matched = EXCLUDED.fully_matched, 
                    customer_strategy_ref = EXCLUDED.customer_strategy_ref, 
                    created_at = EXCLUDED.created_at, 
                    processed_at = EXCLUDED.processed_at, 
                    bet_outcome = EXCLUDED.bet_outcome, 
                    price_matched = EXCLUDED.price_matched, 
                    profit = EXCLUDED.profit, 
                    commission = EXCLUDED.commission, 
                    side = EXCLUDED.side
                """,
        to_run_data,
    )

    postgres_client.execute_query(
        """
        INSERT INTO live_betting.live_results(
                unique_id, 
                race_id, 
                race_time, 
                race_date, 
                horse_id, 
                horse_name, 
                selection_type, 
                market_type, 
                market_id, 
                selection_id, 
                requested_odds, 
                valid, 
                invalidated_at, 
                invalidated_reason, 
                size_matched, 
                average_price_matched, 
                cashed_out, 
                fully_matched, 
                customer_strategy_ref, 
                created_at, 
                processed_at, 
                bet_outcome, 
                event_id, 
                price_matched, 
                profit, 
                commission, 
                side
            )
            VALUES (                
                :unique_id, 
                :race_id, 
                :race_time, 
                :race_date, 
                :horse_id, 
                :horse_name, 
                :selection_type, 
                :market_type, 
                :market_id, 
                :selection_id, 
                :requested_odds, 
                :valid, 
                :invalidated_at, 
                :invalidated_reason, 
                :size_matched, 
                :average_price_matched, 
                :cashed_out, 
                :fully_matched, 
                :customer_strategy_ref, 
                :created_at, 
                :processed_at, 
                :bet_outcome, 
                :event_id, 
                :price_matched, 
                :profit, 
                :commission, 
                :side
            )
                ON CONFLICT (unique_id)
                DO UPDATE SET
                    selection_type = EXCLUDED.selection_type, 
                    requested_odds = EXCLUDED.requested_odds, 
                    valid = EXCLUDED.valid, 
                    invalidated_at = EXCLUDED.invalidated_at, 
                    invalidated_reason = EXCLUDED.invalidated_reason, 
                    size_matched = EXCLUDED.size_matched, 
                    average_price_matched = EXCLUDED.average_price_matched, 
                    cashed_out = EXCLUDED.cashed_out, 
                    fully_matched = EXCLUDED.fully_matched, 
                    customer_strategy_ref = EXCLUDED.customer_strategy_ref, 
                    created_at = EXCLUDED.created_at, 
                    processed_at = EXCLUDED.processed_at, 
                    bet_outcome = EXCLUDED.bet_outcome, 
                    price_matched = EXCLUDED.price_matched, 
                    profit = EXCLUDED.profit, 
                    commission = EXCLUDED.commission, 
                    side = EXCLUDED.side
                """,
        ran_data,
    )
