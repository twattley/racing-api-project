import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder

from src.fetch_requests import RawBettingData
from src.market_trader import MarketTrader


def test_invalidates_bets_seven_runners(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):

    requests_data = pd.DataFrame(
        {
            "race_id": [1, 2],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "PLACE"],
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "requested_odds": [4.0, 2.0],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "minutes_to_race": [20, 20],
            "back_price_1": [4.0, 2.1],
            "back_price_1_depth": [100, 100],
            "back_price_2": [4.1, 2.1],
            "back_price_2_depth": [100, 100],
            "lay_price_1": [4.4, 1.9],
            "lay_price_1_depth": [100, 100],
            "lay_price_2": [4.5, 2.68],
            "lay_price_2_depth": [100, 100],
            "eight_to_seven_runners": [False, True],
            "short_price_removed_runners": [False, False],
            "average_price_matched": [4.4, 2.0],
            "size_matched": [4.0, 2.0],
        }
    )

    selections_data = pd.DataFrame(
        {
            "race_id": [1, 2],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "race_date": [
                pd.Timestamp("2025-01-01 00:00:00"),
                pd.Timestamp("2025-01-01 00:00:00"),
            ],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "WIN"],
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "requested_odds": [3.9, 2.0],
            "valid": [True, True],
            "invalidated_reason": ["None", "None"],
            "invalidated_at": [None, None],
        }
    )
    cashed_out_bets = pd.DataFrame(
        {
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "selection_type": ["BACK", "LAY"],
            "average_price_matched": [3.9, 2.0],
            "size_matched": [4.0, 15.0],
        }
    )

    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(cashed_out_data=cashed_out_bets),
        stake_size=set_stake_size,
    )

    trader.trade_markets(
        requests_data=requests_data,
        betting_data=RawBettingData(
            selections_data=selections_data,
            fully_matched_bets=pd.DataFrame(),
            cashed_out_bets=pd.DataFrame(),
            invalidated_bets=pd.DataFrame(),
            market_state_data=pd.DataFrame(),
            betfair_market_data=pd.DataFrame(),
            current_orders=pd.DataFrame(),
        ),
        now_timestamp=now_timestamp_fixture,
    )

    assert (
        trader.s3_client.stored_data[0]["object_path"]
        == "today/2025_01_01/invalidated_bets.parquet"
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame(
            {
                "race_id": [2],
                "horse_id": [2],
                "horse_name": ["Horse B"],
                "selection_type": ["LAY"],
                "market_type": ["PLACE"],
                "market_id": ["2"],
                "selection_id": [2],
                "requested_odds": [2.0],
                "race_time": [
                    pd.Timestamp("2025-01-01 16:00:00+01:00"),
                ],
                "invalidated_reason": ["Invalid 8 to 7 Place"],
                "time_invalidated": [
                    pd.Timestamp("2025-01-01 13:00:00+00:00", tz="Europe/London"),
                ],
                "average_price_matched": [2.0],
                "size_matched": [15.0],
            }
        ),
        trader.s3_client.stored_data[0]["data"],
    )
    assert (
        trader.s3_client.stored_data[1]["object_path"]
        == "today/2025_01_01/selections_data.parquet"
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame(
            {
                "race_id": [1],
                "race_time": [
                    pd.Timestamp("2025-01-01 15:00:00+01:00"),
                ],
                "race_date": [
                    pd.Timestamp("2025-01-01 00:00:00"),
                ],
                "horse_id": [1],
                "horse_name": ["Horse A"],
                "selection_type": ["BACK"],
                "market_type": ["WIN"],
                "market_id": ["1"],
                "selection_id": [1],
                "requested_odds": [3.9],
                "valid": [True],
                "invalidated_reason": ["None"],
                "invalidated_at": [None],
            }
        ),
        trader.s3_client.stored_data[1]["data"],
    )
    assert trader.betfair_client.cash_out_market_ids == [["2"]]
    assert trader.betfair_client.placed_orders == [
        BetFairOrder(
            size=6.0,
            price=4.0,
            selection_id=1,
            market_id="1",
            side="BACK",
            strategy="mvp",
        )
    ]


def test_invalidates_bets_short_priced(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):

    requests_data = pd.DataFrame(
        {
            "race_id": [1, 2],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "PLACE"],
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "requested_odds": [4.0, 2.0],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "minutes_to_race": [20, 20],
            "back_price_1": [4.0, 2.1],
            "back_price_1_depth": [100, 100],
            "back_price_2": [4.1, 2.1],
            "back_price_2_depth": [100, 100],
            "lay_price_1": [4.4, 1.9],
            "lay_price_1_depth": [100, 100],
            "lay_price_2": [4.5, 2.68],
            "lay_price_2_depth": [100, 100],
            "eight_to_seven_runners": [False, False],
            "short_price_removed_runners": [False, True],
            "average_price_matched": [4.4, 2.0],
            "size_matched": [4.0, 2.0],
        }
    )

    selections_data = pd.DataFrame(
        {
            "race_id": [1, 2],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "race_date": [
                pd.Timestamp("2025-01-01 00:00:00"),
                pd.Timestamp("2025-01-01 00:00:00"),
            ],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "WIN"],
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "requested_odds": [3.9, 2.0],
            "valid": [True, True],
            "invalidated_reason": ["None", "None"],
            "invalidated_at": [None, None],
        }
    )
    cashed_out_bets = pd.DataFrame(
        {
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "selection_type": ["BACK", "LAY"],
            "average_price_matched": [3.9, 2.0],
            "size_matched": [4.0, 15.0],
        }
    )

    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(cashed_out_data=cashed_out_bets),
        stake_size=set_stake_size,
    )

    trader.trade_markets(
        requests_data=requests_data,
        betting_data=RawBettingData(
            selections_data=selections_data,
            fully_matched_bets=pd.DataFrame(),
            cashed_out_bets=pd.DataFrame(),
            invalidated_bets=pd.DataFrame(),
            market_state_data=pd.DataFrame(),
            betfair_market_data=pd.DataFrame(),
            current_orders=pd.DataFrame(),
        ),
        now_timestamp=now_timestamp_fixture,
    )

    assert (
        trader.s3_client.stored_data[0]["object_path"]
        == "today/2025_01_01/invalidated_bets.parquet"
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame(
            {
                "race_id": [2],
                "horse_id": [2],
                "horse_name": ["Horse B"],
                "selection_type": ["LAY"],
                "market_type": ["PLACE"],
                "market_id": ["2"],
                "selection_id": [2],
                "requested_odds": [2.0],
                "race_time": [
                    pd.Timestamp("2025-01-01 16:00:00+01:00"),
                ],
                "invalidated_reason": ["Invalid Short Price Removed"],
                "time_invalidated": [
                    pd.Timestamp("2025-01-01 13:00:00+00:00", tz="Europe/London"),
                ],
                "average_price_matched": [2.0],
                "size_matched": [15.0],
            }
        ),
        trader.s3_client.stored_data[0]["data"],
    )
    assert (
        trader.s3_client.stored_data[1]["object_path"]
        == "today/2025_01_01/selections_data.parquet"
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame(
            {
                "race_id": [1],
                "race_time": [
                    pd.Timestamp("2025-01-01 15:00:00+01:00"),
                ],
                "race_date": [
                    pd.Timestamp("2025-01-01 00:00:00"),
                ],
                "horse_id": [1],
                "horse_name": ["Horse A"],
                "selection_type": ["BACK"],
                "market_type": ["WIN"],
                "market_id": ["1"],
                "selection_id": [1],
                "requested_odds": [3.9],
                "valid": [True],
                "invalidated_reason": ["None"],
                "invalidated_at": [None],
            }
        ),
        trader.s3_client.stored_data[1]["data"],
    )
    assert trader.betfair_client.cash_out_market_ids == [["2"]]
    assert trader.betfair_client.placed_orders == [
        BetFairOrder(
            size=6.0,
            price=4.0,
            selection_id=1,
            market_id="1",
            side="BACK",
            strategy="mvp",
        )
    ]


def test_cashes_out_fully_matched_bets(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):

    requests_data = pd.DataFrame(
        {
            "race_id": [1, 2],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "PLACE"],
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "requested_odds": [4.0, 2.0],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "minutes_to_race": [20, 20],
            "back_price_1": [4.0, 2.1],
            "back_price_1_depth": [100, 100],
            "back_price_2": [4.1, 2.1],
            "back_price_2_depth": [100, 100],
            "lay_price_1": [4.4, 1.9],
            "lay_price_1_depth": [100, 100],
            "lay_price_2": [4.5, 2.68],
            "lay_price_2_depth": [100, 100],
            "eight_to_seven_runners": [False, True],
            "short_price_removed_runners": [True, False],
            "average_price_matched": [4.4, 2.0],
            "size_matched": [10.0, 15.0],
        }
    )

    selections_data = pd.DataFrame(
        {
            "race_id": [1, 2],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "race_date": [
                pd.Timestamp("2025-01-01 00:00:00"),
                pd.Timestamp("2025-01-01 00:00:00"),
            ],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "WIN"],
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "requested_odds": [3.9, 2.0],
            "valid": [True, True],
            "invalidated_reason": ["None", "None"],
            "invalidated_at": [None, None],
        }
    )
    fully_matched_bets = pd.DataFrame(
        {
            "race_id": [1, 2],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "WIN"],
            "average_price_matched": [3.9, 2.0],
            "size_matched": [10.0, 15.0],
        }
    )
    cashed_out_bets = pd.DataFrame(
        {
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "selection_type": ["BACK", "LAY"],
            "average_price_matched": [5.0, 3.0],
            "size_matched": [10.0, 15.0],
        }
    )

    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(cashed_out_data=cashed_out_bets),
        stake_size=set_stake_size,
    )

    trader.trade_markets(
        requests_data=requests_data,
        betting_data=RawBettingData(
            selections_data=selections_data,
            fully_matched_bets=fully_matched_bets,
            cashed_out_bets=pd.DataFrame(),
            invalidated_bets=pd.DataFrame(),
            market_state_data=pd.DataFrame(),
            betfair_market_data=pd.DataFrame(),
            current_orders=pd.DataFrame(),
        ),
        now_timestamp=now_timestamp_fixture,
    )

    assert (
        trader.s3_client.stored_data[0]["object_path"]
        == "today/2025_01_01/invalidated_bets.parquet"
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame(
            {
                "race_id": [1, 2],
                "horse_id": [1, 2],
                "horse_name": ["Horse A", "Horse B"],
                "selection_type": ["BACK", "LAY"],
                "market_type": ["WIN", "PLACE"],
                "market_id": ["1", "2"],
                "selection_id": [1, 2],
                "requested_odds": [4.0, 2.0],
                "race_time": [
                    pd.Timestamp("2025-01-01 15:00:00+01:00"),
                    pd.Timestamp("2025-01-01 16:00:00+01:00"),
                ],
                "invalidated_reason": [
                    "Invalid Short Price Removed",
                    "Invalid 8 to 7 Place",
                ],
                "time_invalidated": [
                    pd.Timestamp("2025-01-01 13:00:00+00:00", tz="Europe/London"),
                    pd.Timestamp("2025-01-01 13:00:00+00:00", tz="Europe/London"),
                ],
                "average_price_matched": [5.0, 3.0],
                "size_matched": [10.0, 15.0],
            }
        ),
        trader.s3_client.stored_data[0]["data"],
    )
    assert (
        trader.s3_client.stored_data[1]["object_path"]
        == "today/2025_01_01/selections_data.parquet"
    )

    assert trader.s3_client.stored_data[1]["data"].empty

    print(trader.betfair_client.cash_out_market_ids)

    assert trader.betfair_client.cash_out_market_ids == [["1", "2"]]
    assert trader.betfair_client.placed_orders == []
