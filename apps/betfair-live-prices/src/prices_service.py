import pandas as pd


class PricesService:
    def update_price_data(self, combined_data: pd.DataFrame) -> pd.DataFrame:
        filtered_data = self._filter_for_latest_runners(combined_data)
        processed_data = self._process_price_data(filtered_data)
        return processed_data

    def combine_new_market_data(
        self, live_data: pd.DataFrame, historical_data: pd.DataFrame
    ):
        if historical_data.empty:
            historical_data = pd.DataFrame(
                columns=[
                    "race_time",
                    "race_date",
                    "todays_betfair_selection_id",
                    "horse_name",
                    "course",
                    "betfair_win_sp",
                    "betfair_place_sp",
                    "created_at",
                    "status",
                    "market_id_win",
                    "market_id_place",
                ]
            )
        live_data = live_data.assign(
            created_at=pd.Timestamp.now(tz="Europe/London"),
            race_date=live_data["race_time"].dt.date,
        )
        win_and_place = pd.merge(
            live_data[live_data["market"] == "WIN"],
            live_data[live_data["market"] == "PLACE"],
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
        win_and_place = win_and_place.filter(
            items=[
                "race_time",
                "horse_name",
                "race_date",
                "course",
                "status",
                "market_id_win",
                "todays_betfair_selection_id",
                "betfair_win_sp",
                "betfair_place_sp",
                "total_matched_win",
                "back_price_1_win",
                "back_price_1_depth_win",
                "back_price_2_win",
                "back_price_2_depth_win",
                "back_price_3_win",
                "back_price_3_depth_win",
                "back_price_4_win",
                "back_price_4_depth_win",
                "back_price_5_win",
                "back_price_5_depth_win",
                "lay_price_1_win",
                "lay_price_1_depth_win",
                "lay_price_2_win",
                "lay_price_2_depth_win",
                "lay_price_3_win",
                "lay_price_3_depth_win",
                "lay_price_4_win",
                "lay_price_4_depth_win",
                "lay_price_5_win",
                "lay_price_5_depth_win",
                "total_matched_event_win",
                "percent_back_win_book_win",
                "percent_lay_win_book_win",
                "market_place",
                "market_id_place",
                "total_matched_place",
                "back_price_1_place",
                "back_price_1_depth_place",
                "back_price_2_place",
                "back_price_2_depth_place",
                "back_price_3_place",
                "back_price_3_depth_place",
                "back_price_4_place",
                "back_price_4_depth_place",
                "back_price_5_place",
                "back_price_5_depth_place",
                "lay_price_1_place",
                "lay_price_1_depth_place",
                "lay_price_2_place",
                "lay_price_2_depth_place",
                "lay_price_3_place",
                "lay_price_3_depth_place",
                "lay_price_4_place",
                "lay_price_4_depth_place",
                "lay_price_5_place",
                "lay_price_5_depth_place",
                "total_matched_event_place",
                "percent_back_win_book_place",
                "percent_lay_win_book_place",
                "created_at",
            ]
        )
        win_and_place = win_and_place.sort_values(by="race_time", ascending=True)

        data = win_and_place.assign(
            runners_unique_id=win_and_place.groupby("market_id_win")[
                "todays_betfair_selection_id"
            ].transform("sum")
        )

        historical_data = historical_data[
            historical_data["race_date"] == pd.Timestamp.now(tz="Europe/London").date()
        ]
        if historical_data.empty:
            data = data[
                data["race_date"] == pd.Timestamp.now(tz="Europe/London").date()
            ].sort_values(by=["created_at", "race_time"], ascending=True)
        else:
            data = pd.concat([historical_data, data]).sort_values(
                by=["created_at", "race_time"], ascending=True
            )
        data = data.drop_duplicates()

        return data

    def _filter_for_latest_runners(self, data):
        latest_runners = data[data["created_at"] == data["created_at"].max()][
            "todays_betfair_selection_id"
        ].unique()

        return data[data["todays_betfair_selection_id"].isin(latest_runners)]

    def _process_price_data(self, data: pd.DataFrame):
        dfs = []

        for id in data["runners_unique_id"].unique():
            n = data[data["runners_unique_id"] == id].sort_values("created_at")
            earliest_prices = (
                n.groupby("todays_betfair_selection_id")["betfair_win_sp"]
                .first()
                .to_dict()
            )
            latest_prices = (
                n.groupby("todays_betfair_selection_id")["betfair_win_sp"]
                .last()
                .to_dict()
            )
            n = n.assign(
                earliest_price=n["todays_betfair_selection_id"].map(earliest_prices),
                latest_price=n["todays_betfair_selection_id"].map(latest_prices),
            )
            n = n.assign(
                price_change=round(
                    (100 / n["earliest_price"] - 100 / n["latest_price"]),
                    2,
                )
            )

            n = n.sort_values(by="created_at").drop_duplicates(
                subset=["runners_unique_id", "todays_betfair_selection_id"], keep="last"
            )

            dfs.append(n)

        data = pd.concat(dfs)
        data["price_change"] = data.groupby("todays_betfair_selection_id")[
            "price_change"
        ].transform("sum")

        data = data.sort_values("created_at").drop_duplicates(
            subset=["todays_betfair_selection_id"], keep="last"
        )

        return data
