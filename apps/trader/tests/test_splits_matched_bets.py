import pandas as pd
from api_helpers.clients.betfair_client import BetFairOrder
from src.fetch_requests import RawBettingData
from src.market_trader import MarketTrader


def test_handles_unmatched_bets(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):
    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(),
        stake_size=set_stake_size,
    )

    requests_data = pd.DataFrame(
        {
            "race_id": [1, 2],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "WIN"],
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "requested_odds": [4.0, 2.0],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "minutes_to_race": [20, 20],
            "back_price_1": [4.0, 2.0],
            "back_price_1_depth": [100, 100],
            "back_price_2": [4.1, 2.1],
            "back_price_2_depth": [100, 100],
            "lay_price_1": [4.4, 1.9],
            "lay_price_1_depth": [100, 100],
            "lay_price_2": [4.5, 2.68],
            "lay_price_2_depth": [100, 100],
            "eight_to_seven_runners": [False, False],
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

    assert not trader.s3_client.stored_data
    assert trader.betfair_client.placed_orders == [
        BetFairOrder(
            size=6.0,
            price=4.0,
            selection_id=1,
            market_id="1",
            side="BACK",
            strategy="mvp",
        ),
        BetFairOrder(
            size=14.44,
            price=1.9,
            selection_id=2,
            market_id="2",
            side="LAY",
            strategy="mvp",
        ),
    ]


def test_handles_fully_matched_bets(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):
    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(),
        stake_size=set_stake_size,
    )

    requests_data = pd.DataFrame(
        {
            "race_id": [1, 2],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "WIN"],
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "requested_odds": [4.0, 2.0],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "minutes_to_race": [20, 20],
            "back_price_1": [4.0, 2.0],
            "back_price_1_depth": [100, 100],
            "back_price_2": [4.1, 2.1],
            "back_price_2_depth": [100, 100],
            "lay_price_1": [4.4, 1.9],
            "lay_price_1_depth": [100, 100],
            "lay_price_2": [4.5, 2.68],
            "lay_price_2_depth": [100, 100],
            "eight_to_seven_runners": [False, False],
            "short_price_removed_runners": [False, False],
            "average_price_matched": [4.4, 2.0],
            "size_matched": [10, 15],
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
        columns=[
            "race_time",
            "race_id",
            "horse_id",
            "horse_name",
            "selection_type",
            "market_type",
            "average_price_matched",
            "size_matched",
        ]
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

    assert not trader.betfair_client.placed_orders
    s3_data = trader.s3_client.stored_data[0]
    assert s3_data["object_path"] == "today/2025_01_01/fully_matched_bets.parquet"
    pd.testing.assert_frame_equal(
        pd.DataFrame(
            {
                "race_time": [
                    pd.Timestamp("2025-01-01 15:00:00+01:00"),
                    pd.Timestamp("2025-01-01 16:00:00+01:00"),
                ],
                "race_id": [1, 2],
                "horse_id": [1, 2],
                "horse_name": ["Horse A", "Horse B"],
                "selection_type": ["BACK", "LAY"],
                "market_type": ["WIN", "WIN"],
                "average_price_matched": [4.4, 2.0],
                "size_matched": [10.0, 15.0],
            }
        ),
        s3_data["data"],
    )


def test_ignores_previously_fully_matched_bets(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):
    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(),
        stake_size=set_stake_size,
    )

    requests_data = pd.DataFrame(
        {
            "race_id": [1, 2],
            "horse_id": [1, 2],
            "horse_name": ["Horse A", "Horse B"],
            "selection_type": ["BACK", "LAY"],
            "market_type": ["WIN", "WIN"],
            "market_id": ["1", "2"],
            "selection_id": [1, 2],
            "requested_odds": [4.0, 2.0],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "minutes_to_race": [20, 20],
            "back_price_1": [4.0, 2.0],
            "back_price_1_depth": [100, 100],
            "back_price_2": [4.1, 2.1],
            "back_price_2_depth": [100, 100],
            "lay_price_1": [4.4, 1.9],
            "lay_price_1_depth": [100, 100],
            "lay_price_2": [4.5, 2.68],
            "lay_price_2_depth": [100, 100],
            "eight_to_seven_runners": [False, False],
            "short_price_removed_runners": [False, False],
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

    assert not trader.s3_client.stored_data
    assert not trader.betfair_client.placed_orders
