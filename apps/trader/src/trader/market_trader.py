from dataclasses import dataclass

import numpy as np
import pandas as pd
from api_helpers.clients import BetFairClient, PostgresClient
from api_helpers.clients.betfair_client import BetFairClient, BetFairOrder, OrderResult
from api_helpers.helpers.logging_config import D, E, I, W

from .utils import get_time_based_stake

SELECTION_COLS = [
    "unique_id",
    "race_id",
    "race_time",
    "race_date",
    "horse_id",
    "horse_name",
    "selection_type",
    "market_type",
    "market_id",
    "selection_id",
    "requested_odds",
    "stake_points",
    "valid",
    "invalidated_at",
    "invalidated_reason",
    "size_matched",
    "average_price_matched",
    "cashed_out",
    "fully_matched",
    "customer_strategy_ref",
    "processed_at",
]


class MaxStakeSizeExceededError(Exception):
    """Exception raised when the maximum stake size is exceeded."""

    def __init__(self, message="Maximum stake size exceeded."):
        self.message = message
        super().__init__(self.message)


@dataclass
class TradeRequest:
    valid_bets: bool
    info: str
    selections_data: pd.DataFrame | None = None
    orders: list[BetFairOrder] | None = None
    cash_out_market_ids: list[str] | None = None


class MarketTrader:
    def __init__(
        self,
        postgres_client: PostgresClient,
        betfair_client: BetFairClient,
        staking_config: dict,
    ):
        self.postgres_client = postgres_client
        self.betfair_client = betfair_client
        self.staking_config = staking_config

    def trade_markets(
        self,
        now_timestamp: pd.Timestamp,
        requests_data: pd.DataFrame,
    ) -> None:
        I(f"Starting trade_markets with timestamp: {now_timestamp}")
        I(f"Input requests_data shape: {requests_data.shape}")

        trades: TradeRequest = self._calculate_trade_positions(
            requests_data=requests_data,
            now_timestamp=now_timestamp,
        )

        if trades.cash_out_market_ids:
            trades.selections_data = self._process_cash_outs(trades)

        bets = self._process_orders(trades.orders)
        updated_selections_data = self._update_selections_with_new_bets(
            trades.selections_data, bets, now_timestamp
        )
        self._store_updated_selections_data(updated_selections_data)

        I("trade_markets completed")

    def _process_orders(self, orders: list[BetFairOrder] | None) -> list[dict]:
        """Process all betting orders and return bet results"""
        bets = []

        if not orders:
            I("No orders to process")
            return bets

        I(f"Processing {len(orders)} orders")
        for i, order in enumerate(orders, 1):
            I(f"Placing order {i}/{len(orders)}: {order}")
            result: OrderResult = self.betfair_client.place_order(order)

            if result.success:
                I(f"Order {i} placed successfully: {order}")
                bets.append(
                    {
                        "unique_id": order.strategy,
                        "size_matched": result.size_matched,
                        "average_price_matched": result.average_price_matched,
                    }
                )
            else:
                W(f"Failed to place order {i}: {order}, Error: {result.message}")

        return bets

    def _update_selections_with_new_bets(
        self,
        selections_data: pd.DataFrame,
        bets: list[dict],
        now_timestamp: pd.Timestamp,
    ) -> pd.DataFrame:
        """Update selections data with bet results"""
        if not bets:
            I("No bets to store, selections data will not be updated")
            return selections_data

        I(f"Storing {len(bets)} bet results")
        bets_df = pd.DataFrame(bets)
        updated_selections = (
            selections_data.merge(
                bets_df, on="unique_id", how="left", suffixes=("_old", "_new")
            )
            .drop(columns=["size_matched_old", "average_price_matched_old"])
            .rename(
                columns={
                    "size_matched_new": "size_matched_betfair",
                    "average_price_matched_new": "average_price_matched",
                }
            )
            .pipe(self._mark_fully_matched_bets, now_timestamp)
        )

        I("Bet results stored successfully")
        return updated_selections

    def _store_updated_selections_data(
        self, updated_selections_data: pd.DataFrame | None
    ) -> None:
        """Store updated selections data to database"""
        if updated_selections_data is not None:
            I(f"Selections data shape: {updated_selections_data[SELECTION_COLS].shape}")

            # Convert data to dictionary and handle NaT values
            data_dict = updated_selections_data[SELECTION_COLS].to_dict(
                orient="records"
            )

            # Replace NaT values with None for database compatibility
            for record in data_dict:
                for key, value in record.items():
                    if pd.isna(value) and key in [
                        "invalidated_at",
                        "processed_at",
                        "race_time",
                        "race_date",
                    ]:
                        record[key] = None
                    elif pd.isna(value) and isinstance(value, (int, float)):
                        record[key] = None

            self.postgres_client.execute_query(
                """
                INSERT INTO live_betting.selections(
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
                            stake_points, 
                            valid, 
                            invalidated_at, 
                            invalidated_reason, 
                            size_matched, 
                            average_price_matched, 
                            cashed_out, 
                            fully_matched, 
                            customer_strategy_ref, 
                            created_at, 
                            processed_at
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
                            :stake_points,
                            :valid, 
                            :invalidated_at, 
                            :invalidated_reason, 
                            :size_matched, 
                            :average_price_matched, 
                            :cashed_out, 
                            :fully_matched, 
                            :customer_strategy_ref, 
                            NOW(), 
                            NOW()
                        )
                        ON CONFLICT (unique_id)
                        DO UPDATE SET
                            race_id = EXCLUDED.race_id,
                            race_time = EXCLUDED.race_time,
                            race_date = EXCLUDED.race_date,
                            horse_id = EXCLUDED.horse_id,
                            horse_name = EXCLUDED.horse_name,
                            selection_type = EXCLUDED.selection_type,
                            market_type = EXCLUDED.market_type,
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
                            processed_at = EXCLUDED.processed_at;
                """,
                data_dict,
            )
            I("Selections data stored successfully")

    def _set_time_based_stake_size(self, requests_data: pd.DataFrame) -> pd.DataFrame:
        """Add time-based stake sizes to each row based on minutes_to_race"""

        def get_stake_for_minutes(row) -> float:

            minutes_to_race = row["minutes_to_race"]
            selection_type = row["selection_type"]

            # if selection_type == 'LAY' and
            if row.get("selection_type") == "LAY" and row.get("requested_odds") <= 2.5:
                # For LAY bets with low odds, use max lay stake size
                return (
                    self.staking_config["max_lay_staking_size"]
                    * row.get("stake_points")
                ) / (row.get("requested_odds") - 1)
            if (
                row.get("selection_type") == "BACK"
                and row.get("market_type") == "WIN"
                and row.get("requested_odds") >= 10.0
            ):
                # For BACK bets with high odds, use max back stake size
                return self.staking_config["max_back_staking_size"] * row.get(
                    "stake_points"
                )
            if (
                row.get("selection_type") == "BACK"
                and row.get("market_type") == "PLACE"
                and row.get("requested_odds") >= 4.0
            ):
                # For BACK bets with high odds, use max back stake size
                return self.staking_config["max_back_staking_size"] * row.get(
                    "stake_points"
                )

            if minutes_to_race < 30:
                if selection_type == "LAY":
                    # For LAY bets within 30 minutes, use max lay stake size
                    return (
                        self.staking_config["max_lay_staking_size"]
                        * row.get("stake_points")
                    ) / (row.get("requested_odds") - 1)
                else:
                    return self.staking_config["max_back_staking_size"] * row.get(
                        "stake_points"
                    )

            if selection_type == "LAY":
                # For LAY bets, get the liability and convert to stake
                liability = get_time_based_stake(
                    minutes_to_race, self.staking_config["time_based_lay_staking_size"]
                )
                if liability is None:
                    liability = self.staking_config["max_lay_staking_size"] * row.get(
                        "stake_points"
                    )
                # Get the LAY odds for this row
                lay_odds = row.get("lay_price_1", 2.0)  # Default to 2.0 if missing
                if pd.isna(lay_odds) or lay_odds <= 1.0:
                    lay_odds = 2.0  # Safety fallback

                # Convert liability to stake: Stake = Liability ÷ (Odds - 1)
                stake = (liability * row.get("stake_points")) / (lay_odds - 1)

                return int(round(stake, 0))

            else:
                # For BACK bets or unknown types, use back staking
                stake = get_time_based_stake(
                    minutes_to_race, self.staking_config["time_based_back_staking_size"]
                )
                return (
                    stake
                    if stake is not None
                    else self.staking_config["max_back_staking_size"]
                    * row.get("stake_points")
                )  # Default fallback stake

        # Add stake_size column to the DataFrame
        requests_data = requests_data.copy()
        requests_data["stake_size"] = requests_data.apply(get_stake_for_minutes, axis=1)

        return requests_data

    def _calculate_trade_positions(
        self,
        requests_data: pd.DataFrame,
        now_timestamp: pd.Timestamp,
    ) -> TradeRequest:
        I(f"Calculating trade positions for {len(requests_data)} requests")

        requests_data = self._set_time_based_stake_size(requests_data=requests_data)
        requests_data = self._mark_invalid_bets(requests_data, now_timestamp)
        requests_data = self._mark_fully_matched_bets(requests_data, now_timestamp)
        requests_data = self._set_new_size_and_price(requests_data)
        requests_data = self._check_odds_available(requests_data)

        orders, cash_out_market_ids = self._create_bet_data(requests_data)
        selections_data = self._update_selections_data(requests_data)

        I(
            f"Trade calculation complete - Orders: {len(orders) if orders else 0}, Cash outs: {len(cash_out_market_ids) if cash_out_market_ids else 0}"
        )

        return TradeRequest(
            valid_bets=True,
            info="Bets requested!",
            selections_data=selections_data,
            orders=orders,
            cash_out_market_ids=cash_out_market_ids,
        )

    def _check_stake_size_exceeded(
        self, data: pd.DataFrame, stake_size: int
    ) -> pd.DataFrame:
        I(f"Checking stake size limits against {stake_size}")

        # For LAY bets, we need to check against the liability limit, not stake limit
        # If stake_size column exists, use it; otherwise, use time-based calculation
        if "stake_size" in data.columns:
            # Use the row-specific stake_size (already converted from liability for LAY bets)
            data = data.assign(
                stake_exceeded=np.select(
                    [
                        (data["selection_type"] == "BACK"),
                        (data["selection_type"] == "LAY"),
                    ],
                    [
                        (data["size_matched_betfair"] > data["stake_size"]),
                        # For LAY: check if matched liability exceeds target liability
                        # Matched liability = size_matched_betfair * (average_price - 1)
                        # Target liability = stake_size * (current_odds - 1)
                        # Use lay_price_1 if available, otherwise use average_price
                        (
                            data["size_matched_betfair"]
                            * (
                                data.get(
                                    "average_price_matched_betfair",
                                    data.get("lay_price_1", 2.0),
                                )
                                - 1
                            )
                        )
                        > (
                            data["stake_size"]
                            * (
                                data.get(
                                    "lay_price_1",
                                    data.get("average_price_matched_betfair", 2.0),
                                )
                                - 1
                            )
                        ),
                    ],
                    default=False,
                )
            )
        else:
            # Fallback to old method if no stake_size column
            data = data.assign(
                stake_exceeded=np.select(
                    [
                        (data["selection_type"] == "BACK"),
                        (data["selection_type"] == "LAY"),
                    ],
                    [
                        (data["size_matched_betfair"] > stake_size),
                        (data["size_matched_betfair"] > stake_size * 1.5),
                    ],
                    default=False,
                )
            )

        exceeded = data[data["stake_exceeded"] == True]
        if not exceeded.empty:
            W(f"Found {len(exceeded)} bets exceeding stake limits")
            for _, row in exceeded.iterrows():
                W(
                    f"Stake exceeded - {row['selection_type']}: {row['size_matched_betfair']} > limit"
                )

        return exceeded

    def _update_selections_data(self, data: pd.DataFrame) -> pd.DataFrame:
        I("Updating selections data with final values")
        data = data.assign(
            average_price_matched=data["average_price_matched_selections"]
            .astype(float)
            .fillna(data["average_price_matched_betfair"].astype(float))
            .round(2),
            size_matched=data["size_matched_betfair"].round(2),
            customer_strategy_ref=data["customer_strategy_ref_selections"]
            .fillna(data["customer_strategy_ref_betfair"])
            .round(2),
        )
        I(f"Updated selections data shape: {data.shape}")
        return data

    def _mark_invalid_bets(
        self, data: pd.DataFrame, now_timestamp: pd.Timestamp
    ) -> pd.DataFrame:
        I("Marking invalid bets")
        initial_valid_count = (
            data["valid"].sum() if "valid" in data.columns else len(data)
        )

        conditions = [
            (data["eight_to_seven_runners"] == True) & (data["market_type"] == "PLACE"),
            (data["short_price_removed_runners"] == True),
        ]

        condition_names = [
            "Invalid 8 to 7 Place",
            "Invalid Short Price Removed",
        ]

        for i, (condition, name) in enumerate(zip(conditions, condition_names)):
            count = condition.sum()
            if count > 0:
                I(f"Found {count} bets to invalidate due to: {name}")

        result = data.assign(
            valid=np.select(
                conditions,
                [False, False],
                default=data["valid"],
            ),
            invalidated_reason=np.select(
                conditions,
                condition_names,
                default=data["invalidated_reason"],
            ),
            invalidated_at=np.select(
                conditions,
                [now_timestamp] * 2,
                default=data["invalidated_at"],
            ),
            processed_at=now_timestamp,
            cash_out=np.select(
                conditions,
                [True, True],
                default=False,
            ),
        )

        final_valid_count = result["valid"].sum()
        invalidated_count = initial_valid_count - final_valid_count
        if invalidated_count > 0:
            I(f"Invalidated {invalidated_count} bets")

        return result

    def _extract_invalidated_fully_matched_bets(
        self, data: pd.DataFrame, market_ids: list[str]
    ) -> pd.DataFrame:
        result = data[(data["market_id"].isin(market_ids))]
        I(
            f"Extracted {len(result)} invalidated fully matched bets from {len(market_ids)} markets"
        )
        return result

    def _get_invalidated_fully_matched_bets_market_ids(
        self, data: pd.DataFrame
    ) -> list[str]:
        market_ids = (
            data[(data["valid"] == False) & (data["fully_matched"] == True)][
                "market_id"
            ]
            .unique()
            .tolist()
        )
        I(f"Found {len(market_ids)} market IDs with invalidated fully matched bets")
        return market_ids

    def _mark_fully_matched_bets(
        self,
        data: pd.DataFrame,
        now_timestamp: pd.Timestamp,
    ) -> pd.DataFrame:
        I(f"Marking fully matched bets")

        conditions = [
            (data["selection_type"] == "BACK"),
            (data["selection_type"] == "LAY"),
        ]

        data["size_matched"] = data[
            ["size_matched_selections", "size_matched_betfair"]
        ].max(axis=1)

        data = data.assign(
            max_exposure=np.select(
                conditions,
                [
                    self.staking_config["max_back_staking_size"] * data["stake_points"],
                    self.staking_config["max_lay_staking_size"] * data["stake_points"],
                ],
                default=float("inf"),
            ),
            bet_exposure=np.select(
                conditions,
                [
                    data["size_matched"],
                    data["size_matched"] * (data["average_price_matched_betfair"] - 1),
                ],
            ),
        )
        data = data.assign(
            fully_matched=np.where(
                (data["max_exposure"] - data["bet_exposure"]) < 1, True, False
            ),
            processed_at=now_timestamp,
        )
        # .drop(columns=["bet_exposure", "max_exposure"])
        return data

    def _set_new_size_and_price(self, data: pd.DataFrame) -> pd.DataFrame:
        I("Setting new size and price calculations using column-based stake sizes")

        conditions = [
            (data["selection_type"] == "BACK") & (data["size_matched_betfair"] > 0),
            (data["selection_type"] == "LAY") & (data["size_matched_betfair"] > 0),
            (data["selection_type"] == "BACK") & (data["size_matched_betfair"] == 0),
            (data["selection_type"] == "LAY") & (data["size_matched_betfair"] == 0),
        ]

        condition_names = [
            "BACK with existing match",
            "LAY with existing match",
            "BACK new bet",
            "LAY new bet",
        ]

        for condition, name in zip(conditions, condition_names):
            count = condition.sum()
            if count > 0:
                I(f"Processing {count} bets for: {name}")

        data = data.assign(
            remaining_size=np.select(
                conditions,
                [
                    data["stake_size"] - data["size_matched_betfair"],
                    (
                        (data["stake_size"] * (data["lay_price_1"] - 1))
                        - (data["average_price_matched_betfair"] - 1)
                        * data["size_matched_betfair"]
                    )
                    / (data["lay_price_1"] - 1),
                    data["stake_size"],
                    data["stake_size"],
                ],
            ),
            amended_average_price=np.select(
                conditions,
                [
                    (
                        (
                            (
                                data["average_price_matched_betfair"]
                                * data["size_matched_betfair"]
                            )
                            + (
                                data["back_price_1"]
                                * (data["stake_size"] - data["size_matched_betfair"])
                            )
                        )
                        / data["stake_size"]
                    ),
                    (
                        # For LAY bets with existing match, calculate weighted average price
                        # Total liability = stake_size * (lay_odds - 1)
                        # New stake needed for remaining liability
                        (data["stake_size"] * (data["lay_price_1"] - 1))
                        / (
                            (
                                (
                                    (data["stake_size"] * (data["lay_price_1"] - 1))
                                    - (data["average_price_matched_betfair"] - 1)
                                    * data["size_matched_betfair"]
                                )
                                / (data["lay_price_1"] - 1)
                            )
                            + data["size_matched_betfair"]
                        )
                        + 1
                    ).round(2),
                    data["back_price_1"],
                    data["lay_price_1"],
                ],
            ),
        )
        data = data.assign(
            remaining_size=data["remaining_size"].round(2),
            amended_average_price=data["amended_average_price"].round(2),
        )

        I(
            f"Remaining size range: {data['remaining_size'].min():.2f} - {data['remaining_size'].max():.2f}"
        )
        I(
            f"Average price range: {data['amended_average_price'].min():.2f} - {data['amended_average_price'].max():.2f}"
        )

        return data

    def _check_odds_available(self, data: pd.DataFrame) -> pd.DataFrame:
        I("Checking odds availability")

        back_condition = (data["selection_type"] == "BACK") & (
            data["amended_average_price"] >= data["requested_odds"]
        )

        lay_condition = (data["selection_type"] == "LAY") & (
            data["amended_average_price"] <= data["requested_odds"]
        )

        back_available = back_condition.sum()
        lay_available = lay_condition.sum()

        I(f"Odds availability - BACK: {back_available}, LAY: {lay_available}")

        result = data.assign(
            available_odds=np.select(
                [back_condition, lay_condition],
                [True, True],
                default=False,
            )
        )

        total_available = result["available_odds"].sum()
        I(f"Total bets with available odds: {total_available}")

        return result

    def _create_bet_data(
        self, data: pd.DataFrame
    ) -> tuple[list[BetFairOrder], list[str]]:
        I("Creating bet data and orders")

        cash_out_market_ids = (
            data[data["cash_out"] == True]["market_id"].unique().tolist()
        )
        I(f"Cash out market IDs: {len(cash_out_market_ids)}")

        fully_matched_cash_out_market_ids = (
            data[(data["valid"] == False) & (data["fully_matched"] == True)][
                "market_id"
            ]
            .unique()
            .tolist()
        )
        I(
            f"Fully matched cash out market IDs: {len(fully_matched_cash_out_market_ids)}"
        )

        bets = data[
            (data["valid"] == True)
            & (data["available_odds"] == True)
            & (data["cash_out"] == False)
            & (data["remaining_size"] > 1)
            & (data["fully_matched"] == False)
        ]

        I(f"Eligible bets for orders: {len(bets)}")

        orders = []

        bets = bets.assign(
            remaining_size=lambda x: x["remaining_size"].round(2),
        ).drop_duplicates(subset=["unique_id"])

        bets = bets.merge(
            pd.DataFrame(
                {
                    "selection_type": ["BACK", "LAY"],
                    "max_stake": [
                        self.staking_config["max_back_staking_size"],
                        self.staking_config["max_lay_staking_size"],
                    ],
                }
            ),
            on="selection_type",
            how="left",
            indicator=True,
        )

        bets["max_stake"] = bets["max_stake"] * bets["stake_points"]

        bets = bets.assign(
            within_stake_limit=lambda x: x["remaining_size"] <= x["max_stake"]
        )
        exceeded_stakes = bets[bets["within_stake_limit"] == False]
        if not exceeded_stakes.empty:
            for _, row in exceeded_stakes.iterrows():
                E(
                    f"Stake size exceeded for {row['selection_type']} bet: {row['remaining_size']} > {row['max_stake']}"
                )

        within_limit_bets = bets[bets["within_stake_limit"] == True].drop(
            columns=["max_stake", "_merge", "within_stake_limit"]
        )
        I(f"Bets within stake limits: {len(within_limit_bets)}")

        for i in within_limit_bets.itertuples():
            if i.selection_type == "BACK":
                bet_size = round(min(i.remaining_size, i.back_price_1_depth), 2)
                order = BetFairOrder(
                    size=bet_size,
                    price=i.back_price_1,
                    market_id=i.market_id,
                    selection_id=i.selection_id,
                    side=i.selection_type,
                    strategy=i.unique_id,
                )
                orders.append(order)
                I(
                    f"Created BACK order: size={i.remaining_size}, price={i.back_price_1}"
                )
            elif i.selection_type == "LAY":
                bet_size = round(min(i.remaining_size, i.lay_price_1_depth), 2)
                order = BetFairOrder(
                    size=bet_size,
                    price=i.lay_price_1,
                    market_id=i.market_id,
                    selection_id=i.selection_id,
                    side=i.selection_type,
                    strategy=i.unique_id,
                )
                orders.append(order)
                I(f"Created LAY order: size={i.remaining_size}, price={i.lay_price_1}")
            else:
                E(f"Invalid selection type: {i.selection_type}")
                raise ValueError(f"Invalid selection type: {i.selection_type}")

        combined_cash_out_ids = list(
            set(cash_out_market_ids + fully_matched_cash_out_market_ids)
        )
        I(
            f"Total orders created: {len(orders)}, Total cash out markets: {len(combined_cash_out_ids)}"
        )

        return orders, combined_cash_out_ids

    def _process_cash_outs(self, trades: TradeRequest) -> pd.DataFrame:
        """Process cash out operations and update selections data"""
        I(
            f"Processing {len(trades.cash_out_market_ids)} cash out market IDs: {trades.cash_out_market_ids}"
        )

        self.betfair_client.cash_out_bets(trades.cash_out_market_ids)

        # Create cash out update data
        cash_out_mask = trades.selections_data["market_id"].isin(
            trades.cash_out_market_ids
        )
        cash_out_updates = trades.selections_data[cash_out_mask].assign(
            cash_out_placed=True, cashed_out_invalid=False
        )[["market_id", "selection_id", "cash_out_placed", "cashed_out_invalid"]]

        I(f"Cash out data shape: {cash_out_updates.shape}")

        # Merge and update selections data
        updated_selections = (
            trades.selections_data.merge(
                cash_out_updates, on=["market_id", "selection_id"], how="left"
            )
            .assign(
                cashed_out=lambda x: x["cash_out_placed"].fillna(x["cashed_out"]),
                valid=lambda x: x["cashed_out_invalid"].fillna(x["valid"]),
            )
            .drop(columns=["cash_out_placed", "cashed_out_invalid"])
        )

        I("Cash out data merged successfully")
        return updated_selections
