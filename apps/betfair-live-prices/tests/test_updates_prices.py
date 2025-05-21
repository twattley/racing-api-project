import pandas as pd
from src.prices_service import PricesService

TZ = "Europe/London"
now_date_str = pd.Timestamp.now(tz=TZ).strftime("%Y-%m-%d")


def test_update_price_data_calculates_sum_correctly_when_runner_removed():
    prices_service = PricesService()
    historical_data = pd.DataFrame(
        {
            "race_time": [
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
            ],
            "race_date": [pd.Timestamp(now_date_str).date()] * 8,
            "horse_id": [1, 2, 3, 1, 2, 3, 1, 2],
            "horse_name": [
                "TEST HORSE A",
                "TEST HORSE B",
                "TEST HORSE C",
                "TEST HORSE A",
                "TEST HORSE B",
                "TEST HORSE C",
                "TEST HORSE A",
                "TEST HORSE B",
            ],
            "course": ["TEST COURSE"] * 8,
            "betfair_win_sp": [2.0, 4.0, 5.0, 2.5, 4.0, 5.0, 3.0, 4.0],
            "betfair_place_sp": [1.0, 2.0, 3.0, 1.5, 2.0, 3.0, 1.0, 2.0],
            "created_at": [
                pd.Timestamp(f"{now_date_str} 11:00:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:00:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:00:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:01:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:01:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:01:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:02:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:02:00", tz=TZ),
            ],
            "status": ["ACTIVE"] * 8,
            "market_id_win": ["1", "1", "1", "1", "1", "1", "1", "1"],
            "market_id_place": ["2", "2", "2", "2", "2", "2", "2", "2"],
            "runners_unique_id": [6, 6, 6, 6, 6, 6, 3, 3],
        }
    )
    live_data = pd.DataFrame(
        {
            "race_time": [
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 23:50:00", tz=TZ),
            ],
            "market": ["WIN", "WIN", "PLACE", "PLACE"],
            "race": ["TEST RACE"] * 4,
            "course": ["TEST COURSE"] * 4,
            "horse": ["TEST HORSE A", "TEST HORSE B"] * 2,
            "status": ["ACTIVE"] * 4,
            "todays_bf_unique_id": [1, 2, 1, 2],
            "last_traded_price": [3.0, 6.0, 2.0, 2.0],
            "created_at": [
                pd.Timestamp(f"{now_date_str} 11:03:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:03:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:03:00", tz=TZ),
                pd.Timestamp(f"{now_date_str} 11:03:00", tz=TZ),
            ],
            "market_id": ["1", "1", "2", "2"],
        }
    )

    combined_data, prices_updated = prices_service.update_price_data(
        live_data, historical_data
    )

    expected_prices_updated = pd.DataFrame(
        {
            "horse_id": [1, 2],
            "betfair_win_sp": [3.0, 6.0],
            "market_id_win": ["1", "1"],
            "price_change": [10.0, 8.33],
        }
    )

    pd.testing.assert_frame_equal(
        combined_data[
            ["horse_id", "betfair_win_sp", "market_id_win", "runners_unique_id"]
        ].reset_index(drop=True),
        pd.DataFrame(
            {
                "horse_id": [1, 2, 3, 1, 2, 3, 1, 2, 1, 2],
                "betfair_win_sp": [2.0, 4.0, 5.0, 2.5, 4.0, 5.0, 3.0, 4.0, 3.0, 6.0],
                "market_id_win": ["1", "1", "1", "1", "1", "1", "1", "1", "1", "1"],
                "runners_unique_id": [6, 6, 6, 6, 6, 6, 3, 3, 3, 3],
            },
        ).reset_index(drop=True),
    )

    pd.testing.assert_frame_equal(expected_prices_updated, prices_updated)
