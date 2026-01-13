import asyncio
import hashlib
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
import pandas as pd
from numba import njit
from racing_api.models.race_form_graph import RaceFormGraph, RaceFormGraphResponse
from racing_api.models.void_bet_request import VoidBetRequest

from ..models.horse_race_info import RaceDataResponse, RaceDataRow
from ..models.race_details import RaceDetailsResponse
from ..models.race_form import RaceForm, RaceFormResponse, RaceFormResponseFull
from ..repository.base_repository import BaseRepository


@njit(cache=True)
def _simulate_loop(base_probs, n_sims, n_places):
    """JIT-compiled inner loop - no seed setting per call."""
    n_horses = len(base_probs)
    win_counts = np.zeros(n_horses, dtype=np.int32)
    place_counts = np.zeros(n_horses, dtype=np.int32)

    # Pre-allocate arrays once (reuse in loop)
    ps = np.empty(n_horses, dtype=np.float64)
    indices = np.empty(n_horses, dtype=np.int32)
    cumsum_buf = np.empty(n_horses, dtype=np.float64)

    for _ in range(n_sims):
        # Reset to full field
        ps[:] = base_probs
        for idx in range(n_horses):
            indices[idx] = idx
        n_remaining = n_horses

        K = min(n_places, n_horses)
        for i in range(K):
            # Normalize in-place
            ps_sum = 0.0
            for j in range(n_remaining):
                ps_sum += ps[j]
            if ps_sum > 0:
                for j in range(n_remaining):
                    ps[j] /= ps_sum

            # Cumsum and sample
            cumsum_buf[0] = ps[0]
            for j in range(1, n_remaining):
                cumsum_buf[j] = cumsum_buf[j - 1] + ps[j]

            rand_val = np.random.rand()
            idx = 0
            for j in range(n_remaining):
                if rand_val <= cumsum_buf[j]:
                    idx = j
                    break

            horse_idx = indices[idx]

            # Record win/place
            if i == 0:
                win_counts[horse_idx] += 1
            place_counts[horse_idx] += 1

            # Remove selected horse (shift arrays left)
            for j in range(idx, n_remaining - 1):
                indices[j] = indices[j + 1]
                ps[j] = ps[j + 1]
            n_remaining -= 1

    return win_counts, place_counts


def simulate_place_counts(
    df,
    price_col="betfair_win_sp",
    horse_col="horse_name",
    n_places=3,
    n_sims=10000,
    seed=42,
):
    """Optimized - assumes unique horses in df."""
    horses = df[horse_col].values
    prices = df[price_col].values

    # Compute implied probabilities
    base_probs = 1.0 / prices
    base_probs = base_probs / base_probs.sum()

    np.random.seed(seed)
    win_counts, place_counts = _simulate_loop(base_probs, n_sims, n_places)

    out = (
        pd.DataFrame(
            {
                "horse": horses,
                "win_prob": win_counts / n_sims,
                "place_prob_topN": place_counts / n_sims,
            }
        )
        .sort_values(["place_prob_topN", "win_prob"], ascending=False)
        .reset_index(drop=True)
    )

    out["sim_place_sp"] = 1 / out["place_prob_topN"]
    return out


@dataclass
class BetRequest:
    race_id: Union[int, str]
    horse_id: Union[int, str]
    market: str  # e.g., 'WIN' or 'PLACE'
    selection_id: Union[int, str]
    market_id: str
    stake_points: Optional[float] = 1.0


class BaseService:
    def __init__(
        self,
        repository: BaseRepository,
    ):
        self.repository = repository

    def clone_with_session(self, session):
        """Create a new service instance bound to a fresh session."""
        repo_cls = type(self.repository)
        return type(self)(repo_cls(session))

    def _calculate_contender_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate value percentages for contenders in the race data.

        Methodology:
        1. Equal probability: 1 / num_contenders
        2. Normalized market probability: (1 / betfair_sp) / sum_of_contender_probs
        3. Adjusted probability: (equal_prob + normalized_market_prob) / 2
        4. Adjusted odds: 1 / adjusted_prob
        5. Value percentage: ((betfair_sp - adjusted_odds) / adjusted_odds) * 100
        """
        # Initialize value columns with None
        data["equal_prob"] = None
        data["normalized_market_prob"] = None
        data["adjusted_prob"] = None
        data["adjusted_odds"] = None
        data["value_percentage"] = None
        # Lay value columns for not-contenders
        data["lay_threshold"] = None
        data["is_value_lay"] = None
        data["lay_value_percentage"] = None

        # Ensure contender_status column exists
        if "contender_status" not in data.columns:
            data["contender_status"] = None
            return data

        # Get contenders with valid SPs
        contenders_mask = (
            (data["contender_status"] == "contender")
            & (data["betfair_win_sp"].notna())
            & (data["betfair_win_sp"] > 0)
        )
        contenders = data[contenders_mask].copy()

        if contenders.empty:
            return data

        num_contenders = len(contenders)
        equal_prob = 1 / num_contenders

        # Calculate sum of contender probabilities for normalization
        contenders["market_prob"] = 1 / contenders["betfair_win_sp"].astype(float)
        sum_contender_probs = contenders["market_prob"].sum()

        # Calculate value for each contender
        for idx in contenders.index:
            sp = float(data.loc[idx, "betfair_win_sp"])
            market_prob = 1 / sp
            normalized_market_prob = market_prob / sum_contender_probs
            adjusted_prob = (equal_prob + normalized_market_prob) / 2
            adjusted_odds = 1 / adjusted_prob
            value_percentage = ((sp - adjusted_odds) / adjusted_odds) * 100

            data.loc[idx, "equal_prob"] = round(equal_prob * 100, 1)
            data.loc[idx, "normalized_market_prob"] = round(
                normalized_market_prob * 100, 1
            )
            data.loc[idx, "adjusted_prob"] = round(adjusted_prob * 100, 1)
            data.loc[idx, "adjusted_odds"] = round(adjusted_odds, 2)
            data.loc[idx, "value_percentage"] = round(value_percentage, 0)

        # Calculate lay values for not-contenders
        # Logic: If 3 contenders, non-contender should be >= 4.0 (3/1)
        # If price < threshold, it's a value lay
        lay_threshold = num_contenders  # e.g., 3 contenders = 4.0 decimal (3/1)

        not_contenders_mask = (
            (data["contender_status"] == "not-contender")
            & (data["betfair_win_sp"].notna())
            & (data["betfair_win_sp"] > 0)
        )

        for idx in data[not_contenders_mask].index:
            sp = float(data.loc[idx, "betfair_win_sp"])
            is_value_lay = sp < lay_threshold

            data.loc[idx, "lay_threshold"] = round(lay_threshold, 2)
            data.loc[idx, "is_value_lay"] = is_value_lay

            if is_value_lay:
                # How much value: ((threshold - price) / price) * 100
                lay_value_pct = ((lay_threshold - sp) / sp) * 100
                data.loc[idx, "lay_value_percentage"] = round(lay_value_pct, 0)

        return data

    async def get_horse_race_info(
        self, race_id: int
    ) -> tuple[RaceDataResponse, list[int]]:
        """Get horse race information by race ID"""
        data = await self.repository.get_horse_race_info(race_id)
        data = self.simulate_place_prices(data)
        data["number_of_runs"] = data["number_of_runs"] - 1
        # Calculate contender values if any contenders are marked
        data = self._calculate_contender_values(data)
        race_info = RaceDataResponse(
            race_id=race_id,
            data=[RaceDataRow(**row.to_dict()) for _, row in data.iterrows()],
        )
        active_runners = data[data["status"] == "ACTIVE"]["horse_id"].tolist()
        return race_info, active_runners

    async def get_race_details(self, race_id: int) -> Optional[RaceDetailsResponse]:
        """Get race details by race ID"""
        data = await self.repository.get_race_details(race_id)
        if data.empty:
            return None
        return RaceDetailsResponse(**data.iloc[0].to_dict())

    async def get_race_form_graph(
        self, race_id: int, active_runners: list[int]
    ) -> RaceFormGraphResponse:
        """Get race form graph data by race ID"""
        data = await self.repository.get_race_form_graph(race_id)
        todays_race_date = data["todays_race_date"].iloc[0]
        data["race_date"] = pd.to_datetime(data["race_date"])

        hist = data[data["race_date"] < data["todays_race_date"]]
        today = data[data["race_date"] == data["todays_race_date"]]

        projected_data_dicts = []
        for horse in data["horse_id"].unique():
            hist_horse_data = hist[hist["horse_id"] == horse]
            horse_name = hist_horse_data["horse_name"].iloc[0]
            if hist_horse_data.empty:
                projected_data = {
                    "unique_id": horse,
                    "race_date": todays_race_date,
                    "horse_name": horse_name,
                    "official_rating": 0,
                    "horse_id": today["horse_id"].iloc[0],
                    "rating": 0,
                    "speed_figure": 0,
                }

            else:
                today_horse_or = today[today["horse_id"] == horse][
                    "official_rating"
                ].iloc[0]

                if pd.isna(today_horse_or):
                    today_horse_or = 0

                projected_data = {
                    "unique_id": hist_horse_data["unique_id"].iloc[0],
                    "race_date": todays_race_date,
                    "horse_name": horse_name,
                    "official_rating": today_horse_or,
                    "horse_id": hist_horse_data["horse_id"].iloc[0],
                    "rating": hist_horse_data["rating"]
                    .fillna(0)
                    .median()
                    .round(0)
                    .astype(int),
                    "speed_figure": hist_horse_data["speed_figure"]
                    .fillna(0)
                    .median()
                    .round(0)
                    .astype(int),
                }
            projected_data_dicts.append(projected_data)
        projected_data = pd.DataFrame(projected_data_dicts)
        data = (
            pd.concat([hist, projected_data], ignore_index=True)
            .drop(columns=["todays_race_date"])
            .sort_values(by=["horse_id", "race_date"])
        )
        active_runners_graph = data[data["horse_id"].isin(active_runners)]

        form_data = [
            RaceFormGraph(**row.to_dict()) for _, row in active_runners_graph.iterrows()
        ]
        return RaceFormGraphResponse(race_id=race_id, data=form_data)

    async def get_race_form(
        self, race_id: int, active_runners: list[int]
    ) -> RaceFormResponse:
        """Get race form data by race ID"""
        data = await self.repository.get_race_form(race_id)
        active_race_form = data[data["horse_id"].isin(active_runners)]

        return RaceFormResponse(
            race_id=race_id,
            data=[RaceForm(**row.to_dict()) for _, row in active_race_form.iterrows()],
        )

    async def get_full_race_data(self, race_id: int) -> Optional[RaceFormResponseFull]:
        from ..storage.database_session_manager import sessionmanager, with_new_session

        sessionmanager.init_db()

        async def run(op):
            return await with_new_session(
                lambda s: self.clone_with_session(s),
                op,
            )

        race_info, active_runners = await self.get_horse_race_info(race_id)

        race_details, race_form, race_form_graph = await asyncio.gather(
            run(lambda svc: svc.get_race_details(race_id)),
            run(lambda svc: svc.get_race_form(race_id, active_runners)),
            run(lambda svc: svc.get_race_form_graph(race_id, active_runners)),
        )

        return RaceFormResponseFull(
            race_form=race_form,
            race_info=race_info,
            race_form_graph=race_form_graph,
            race_details=race_details,
        )

    def _format_todays_races(self, data: pd.DataFrame) -> pd.DataFrame:
        return (
            data.assign(
                race_class=data["race_class"].fillna(0).astype(int).replace(0, None),
                hcap_range=data["hcap_range"].fillna(0).astype(int).replace(0, None),
                betfair_win_sp=data["betfair_win_sp"].round(1),
            )
            .pipe(self._add_all_skip_flags)
            .drop_duplicates(subset=["race_id"])
        )

    def _add_all_skip_flags(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add all skip flag conditions as separate columns, then combine into final skip_flag"""
        races_to_ignore = [
            "shergar",
            "maiden",
            "novice",
            "hurdle",
            "chase",
            "hunter",
            "heritage",
            "bumper",
            "racing league",
            "lady riders",
            "national hunt flat",
            "claiming",
            "claimer",
            "selling",
        ]

        # Determine threshold based on whether the races are today
        race_date_val = pd.to_datetime(data["race_date"].iloc[0]).normalize()
        today_val = pd.Timestamp.today().normalize()
        min_threshold = 3.3 if race_date_val == today_val else 3.0

        # Flag 1: Race title contains ignored words
        data["skip_race_type"] = (
            data["race_title"]
            .str.lower()
            .str.contains("|".join(races_to_ignore), na=False)
        )

        # Flag 2: Minimum SP per race > 4
        min_sp_per_race = data.groupby("race_id")["betfair_win_sp"].min()
        data["skip_min_sp"] = data["race_id"].map(min_sp_per_race > 4)

        # Flag 3: >10 runners AND favorite > 4
        min_sp_per_race = data.groupby("race_id")["betfair_win_sp"].min()
        max_runners_per_race = data.groupby("race_id")["number_of_runners"].max()
        condition = (max_runners_per_race > 10) & (min_sp_per_race > 4)
        data["skip_runners_fav"] = data["race_id"].map(condition)

        # Flag 4: Races with ≤4 runners
        max_runners_per_race = data.groupby("race_id")["number_of_runners"].max()
        data["skip_few_runners"] = data["race_id"].map(max_runners_per_race <= 4)

        # Flag 5: Minimum SP per race ≤ 2.5
        min_sp_per_race = data.groupby("race_id")["betfair_win_sp"].min()
        data["skip_short_price"] = data["race_id"].map(min_sp_per_race <= 2.28)

        # Flag 6: Races where all horses are 2 years old
        max_age_per_race = data.groupby("race_id")["age"].max()
        data["skip_all_two_year_olds"] = data["race_id"].map(max_age_per_race == 2)

        # Flag 7: Races where all horses are 3 years old AND more than 8 runners
        max_age_per_race = data.groupby("race_id")["age"].max()
        max_runners_per_race = data.groupby("race_id")["number_of_runners"].max()
        condition = (max_age_per_race == 3) & (max_runners_per_race > 8)
        data["skip_all_three_year_olds_big_field"] = data["race_id"].map(condition)

        # Flag 8: skip if the favourite (shortest price) is NOT < threshold
        short_prices = []

        for race_id in data["race_id"].unique():
            race = data[data["race_id"] == race_id]
            min_race_price = race["betfair_win_sp"].min()
            if min_race_price > min_threshold:
                short_prices.append(race_id)
            else:
                continue

        data["skip_short_prices"] = data["race_id"].isin(short_prices)
        # Final skip flag: True if ANY of the conditions are True

        data["skip_flag"] = (
            data["skip_race_type"]
            | data["skip_min_sp"]
            | data["skip_runners_fav"]
            | data["skip_few_runners"]
            | data["skip_short_price"]
            | data["skip_all_two_year_olds"]
            | data["skip_all_three_year_olds_big_field"]
            | data["skip_short_prices"]
        )

        data.to_csv("~/Desktop/test.csv")
        return data.drop(
            columns=[
                "skip_race_type",
                "skip_min_sp",
                "skip_runners_fav",
                "skip_few_runners",
                "skip_short_price",
                "skip_all_two_year_olds",
                "skip_all_three_year_olds_big_field",
            ]
        ).drop_duplicates(subset=["race_id"])

    def create_unique_bet_request_id(self, data: BetRequest) -> str:

        parts = (
            str(data.race_id),
            str(data.horse_id),
            str(data.market).upper(),
            str(data.selection_id),
            str(data.market_id),
        )
        canonical = "|".join(parts)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def create_void_bet_request_id(self, data: VoidBetRequest) -> str:

        parts = (
            str(data.market_id),
            str(data.selection_id),
            str(data.horse_name),
            str(data.market_type),
            str(data.selection_type),
            str(data.race_time),
        )
        canonical = "|".join(parts)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def simulate_place_prices(self, data):
        """
        Simulate place prices and add sim_place_sp and diff_proba to original dataframe.

        Args:
            data: DataFrame with columns ['horse_name', 'betfair_win_sp', 'betfair_place_sp']

        Returns:
            Original dataframe with added columns: 'sim_place_sp' and 'diff_proba'
        """

        race_class = data["race_class"].iloc[0]
        # Create a copy to avoid modifying original data
        df_work = data[["horse_name", "betfair_win_sp", "betfair_place_sp"]].copy()

        # Ensure proper data types
        df_work = df_work.astype(
            {"betfair_win_sp": "float", "betfair_place_sp": "float"}
        )

        # Run simulation
        sim_results = simulate_place_counts(
            df_work,
            price_col="betfair_win_sp",
            horse_col="horse_name",
            n_places=self.calculate_num_places(len(df_work), race_class),
            n_sims=10000,
            seed=7,
        )

        # Calculate probabilities and differences
        sim_results["sim_proba"] = (1 / sim_results["sim_place_sp"]).round(4)
        sim_results["place_proba"] = (
            1
            / df_work.set_index("horse_name")
            .loc[sim_results["horse"], "betfair_place_sp"]
            .values
        ).round(4)
        sim_results["diff_proba"] = (
            sim_results["sim_proba"] - sim_results["place_proba"]
        )

        # Merge back to original dataframe
        result = data.merge(
            sim_results[["horse", "sim_place_sp", "diff_proba"]],
            left_on="horse_name",
            right_on="horse",
            how="left",
        ).drop(columns=["horse"])

        result = result.assign(
            sim_place_sp=result["sim_place_sp"].round(1),
            diff_proba=result["diff_proba"].round(2),
        )

        return result

    def calculate_num_places(self, number_of_runners: int, race_class: str) -> int:
        if pd.to_numeric(race_class, errors="coerce") == 1:
            return 3
        if number_of_runners < 8:
            return 2
        if number_of_runners < 16:
            return 3
        return 4
