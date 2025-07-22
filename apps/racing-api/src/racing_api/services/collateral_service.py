import numpy as np
import pandas as pd
from fastapi import Depends

from ..repository.collateral_repository import (
    CollateralRepository,
    get_collateral_repository,
)
from .base_service import BaseService
from .transformation_service import TransformationService


class CollateralService(BaseService):
    def __init__(
        self,
        collateral_repository: CollateralRepository,
        transformation_service: TransformationService,
    ):
        self.collateral_repository = collateral_repository
        self.transformation_service = transformation_service

    async def get_collateral_form_by_id(
        self, race_date: str, race_id: int, todays_race_date: str, horse_id: int
    ):
        data = await self.collateral_repository.get_collateral_form_by_id(
            race_date, race_id, todays_race_date
        )
        collateral_form_data = self._create_collateral_form_data(data, horse_id)
        transformed_data = self.transformation_service.transform_collateral_form_data(
            collateral_form_data
        )
        transformed_data = transformed_data.sort_values(
            by=["distance_difference", "horse_id"], ascending=[True, False]
        ).reset_index(drop=True)

        horse_collateral_data = []
        all_valid_ratings = []
        number_of_runs = []
        all_important_results = []

        transformed_data["total_distance_beaten_float"] = pd.to_numeric(
            transformed_data["total_distance_beaten"], errors="coerce"
        )
        for horse in transformed_data["horse_name"].unique():
            horse_data = transformed_data[transformed_data["horse_name"] == horse]
            race_form = horse_data[horse_data["collateral_form_type"] == "race_form"]
            collateral = horse_data[horse_data["collateral_form_type"] == "collateral"]

            if collateral.empty:
                continue

            valid_ratings = collateral[collateral["rating"] > 30]["rating"]
            all_valid_ratings.extend(valid_ratings)
            number_of_runs.extend(collateral["rating"])

            important_results = (
                (collateral["finishing_position"].isin(["1", "2"]))
                | (collateral["total_distance_beaten_float"].astype(float) < 2)
                | (
                    (collateral["finishing_position"].isin(["1", "2", "3"]))
                    & (collateral["number_of_runners"].astype(int) >= 12)
                )
                | (
                    (collateral["finishing_position"].isin(["1", "2", "3", "4"]))
                    & (collateral["number_of_runners"].astype(int) >= 16)
                )
            )

            all_important_results.append(important_results)
            horse_data = {
                "horse_id": race_form["horse_id"].iloc[0],
                "horse_name": race_form["horse_name"].iloc[0],
                "distance_difference": race_form["distance_difference"].iloc[0],
                "weight_difference": race_form["weight_difference"].iloc[0],
                "current_official_rating": race_form["current_official_rating"].iloc[0],
                "collateral_form_data": [],
            }

            for _, row in collateral.iterrows():
                collateral_form = {
                    "official_rating": row["official_rating"],
                    "finishing_position": row["finishing_position"],
                    "total_distance_beaten": row["total_distance_beaten"],
                    "betfair_win_sp": row["betfair_win_sp"],
                    "rating": row["rating"],
                    "speed_figure": row["speed_figure"],
                    "horse_id": row["horse_id"],
                    "unique_id": row["unique_id"],
                    "race_id": row["race_id"],
                    "race_time": row["race_time"],
                    "race_date": row["race_date"],
                    "race_type": row["race_type"],
                    "race_class": row["race_class"],
                    "distance": row["distance"],
                    "conditions": row["conditions"],
                    "going": row["going"],
                    "number_of_runners": row["number_of_runners"],
                    "surface": row["surface"],
                    "main_race_comment": row["main_race_comment"],
                    "tf_comment": row["tf_comment"],
                    "tfr_view": row["tfr_view"],
                }
                horse_data["collateral_form_data"].append(collateral_form)

            horse_collateral_data.append(horse_data)

        important_result_count = np.sum(
            [results.sum() for results in all_important_results]
        )

        average_rating = (
            round(pd.Series(all_valid_ratings).mean()) if all_valid_ratings else 0
        )
        valid_performance_count = len(number_of_runs)

        response = {
            "average_collateral_rating": average_rating,
            "valid_collateral_performance_count": valid_performance_count,
            "important_result_count": int(important_result_count),
            "horse_collateral_data": horse_collateral_data,
        }
        return self.sanitize_nan(response)

    def _create_todays_collateral_official_rating(
        self, race_form: pd.DataFrame, collateral_form: pd.DataFrame
    ) -> pd.DataFrame:

        official_ratings = []

        race_form["official_rating"] = (
            race_form["official_rating"].fillna(0).astype(int)
        )
        for horse_id in race_form["horse_id"].unique():
            collateral_max_or = collateral_form[collateral_form["horse_id"] == horse_id]
            if collateral_max_or.empty:
                max_or = race_form[race_form["horse_id"] == horse_id][
                    "official_rating"
                ].iloc[0]
                official_ratings.append({"horse_id": horse_id, "current_or": max_or})
            else:
                collateral_form["official_rating"] = (
                    collateral_form["official_rating"].fillna(0).astype(int)
                )
                sorted_collateral = collateral_form[
                    collateral_form["horse_id"] == horse_id
                ].sort_values(by="race_time", ascending=False)
                max_or = sorted_collateral["official_rating"].iloc[
                    0
                ]  # Now first row is most recent
                official_ratings.append({"horse_id": horse_id, "current_or": max_or})

        return pd.DataFrame(official_ratings)

    def _create_collateral_form_data(
        self, data: pd.DataFrame, horse_id: int
    ) -> pd.DataFrame:

        # Split data by type
        race_form = data[data["collateral_form_type"] == "race_form"].copy()
        collateral_form = data[data["collateral_form_type"] == "collateral"].copy()

        # Convert distance to numeric for calculations
        race_form["float_distance_beaten"] = pd.to_numeric(
            race_form["total_distance_beaten"], errors="coerce"
        ).fillna(999)

        # Get reference values for the target horse
        target_horse = race_form[race_form["horse_id"] == horse_id].iloc[0]
        distance_beaten = target_horse["float_distance_beaten"]
        weight_carried = target_horse["weight_carried_lbs"]

        # Calculate differences for race_form
        race_form["distance_difference"] = (
            race_form["float_distance_beaten"] - distance_beaten
        )
        race_form["weight_difference"] = (
            race_form["weight_carried_lbs"] - weight_carried
        )

        # Apply differences to collateral_form using merge
        diff_data = race_form[["horse_id", "distance_difference", "weight_difference"]]
        collateral_form = collateral_form.merge(diff_data, on="horse_id", how="left")

        official_ratings = self._create_todays_collateral_official_rating(
            race_form, collateral_form
        )

        # Clean up and combine
        race_form = race_form.drop(columns=["float_distance_beaten"])
        combined = pd.concat([collateral_form, race_form], ignore_index=True)

        combined = combined.merge(official_ratings, on="horse_id", how="left").rename(
            columns={"current_or": "current_official_rating"}
        )

        return combined[combined["horse_id"] != horse_id].sort_values(
            by=["horse_id", "race_date"]
        )


def get_collateral_service(
    collateral_repository: CollateralRepository = Depends(get_collateral_repository),
):
    transformation_service = TransformationService()
    return CollateralService(collateral_repository, transformation_service)
