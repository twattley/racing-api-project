import pandas as pd
import pytest
from api_helpers.clients.betfair_client import BetFairOrder
from src.fetch_requests import RawBettingData
from src.market_trader import MarketTrader


def test_multiple_runners_multiple_races(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):
    requests_data = pd.DataFrame(
        {
            "race_id": [1, 2, 2],
            "horse_id": [1, 2, 3],
            "horse_name": ["Horse A", "Horse B", "Horse C"],
            "selection_type": ["BACK", "LAY", "BACK"],
            "market_type": ["WIN", "PLACE", "WIN"],
            "market_id": ["1", "2", "2"],
            "selection_id": [1, 2, 3],
            "requested_odds": [4.0, 2.2, 3.5],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "minutes_to_race": [20, 20, 20],
            "back_price_1": [4.0, 2.0, 5.0],
            "back_price_1_depth": [100, 100, 100],
            "back_price_2": [3.9, 1.9, 4.9],
            "back_price_2_depth": [100, 100, 100],
            "lay_price_1": [4.1, 2.1, 5.1],
            "lay_price_1_depth": [100, 100, 100],
            "lay_price_2": [4.2, 2.2, 5.2],
            "lay_price_2_depth": [100, 100, 100],
            "eight_to_seven_runners": [False, False, False],
            "short_price_removed_runners": [False, False, False],
            "average_price_matched": [0.0, 0.0, 0.0],
            "size_matched": [0.0, 0.0, 0.0],
        }
    )

    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(),
        stake_size=set_stake_size,
    )

    trader.trade_markets(
        requests_data=requests_data,
        betting_data=RawBettingData(
            selections_data=pd.DataFrame(),
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
            size=10.0,
            price=4.0,
            selection_id=1,
            market_id="1",
            side="BACK",
            strategy="mvp",
        ),
        BetFairOrder(
            size=13.64,
            price=2.1,
            selection_id=2,
            market_id="2",
            side="LAY",
            strategy="mvp",
        ),
        BetFairOrder(
            size=10.0,
            price=5.0,
            selection_id=3,
            market_id="2",
            side="BACK",
            strategy="mvp",
        ),
    ]


@pytest.mark.parametrize(
    "requested_odds, placed_orders",
    [
        (
            [4.0, 2.0, 3.5],
            [
                BetFairOrder(
                    size=10.0,
                    price=4.0,
                    selection_id=1,
                    market_id="1",
                    side="BACK",
                    strategy="mvp",
                ),
                BetFairOrder(
                    size=10.0,
                    price=5.0,
                    selection_id=3,
                    market_id="2",
                    side="BACK",
                    strategy="mvp",
                ),
            ],
        ),
        (
            [4.0, 2.2, 7.0],
            [
                BetFairOrder(
                    size=10.0,
                    price=4.0,
                    selection_id=1,
                    market_id="1",
                    side="BACK",
                    strategy="mvp",
                ),
                BetFairOrder(
                    size=13.64,
                    price=2.1,
                    selection_id=2,
                    market_id="2",
                    side="LAY",
                    strategy="mvp",
                ),
            ],
        ),
    ],
)
def test_odds_not_available(
    get_s3_client,
    get_betfair_client,
    now_timestamp_fixture,
    set_stake_size,
    requested_odds,
    placed_orders,
):
    requests_data = pd.DataFrame(
        {
            "race_id": [1, 2, 2],
            "horse_id": [1, 2, 3],
            "horse_name": ["Horse A", "Horse B", "Horse C"],
            "selection_type": ["BACK", "LAY", "BACK"],
            "market_type": ["WIN", "PLACE", "WIN"],
            "market_id": ["1", "2", "2"],
            "selection_id": [1, 2, 3],
            "requested_odds": requested_odds,
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "minutes_to_race": [20, 20, 20],
            "back_price_1": [4.0, 2.0, 5.0],
            "back_price_1_depth": [100, 100, 100],
            "back_price_2": [3.9, 1.9, 4.9],
            "back_price_2_depth": [100, 100, 100],
            "lay_price_1": [4.1, 2.1, 5.1],
            "lay_price_1_depth": [100, 100, 100],
            "lay_price_2": [4.2, 2.2, 5.2],
            "lay_price_2_depth": [100, 100, 100],
            "eight_to_seven_runners": [False, False, False],
            "short_price_removed_runners": [False, False, False],
            "average_price_matched": [0.0, 0.0, 0.0],
            "size_matched": [0.0, 0.0, 0.0],
        }
    )

    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(),
        stake_size=set_stake_size,
    )

    trader.trade_markets(
        requests_data=requests_data,
        betting_data=RawBettingData(
            selections_data=pd.DataFrame(),
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
    assert trader.betfair_client.placed_orders == placed_orders


@pytest.mark.parametrize(
    "back_market_depth, lay_market_depth, placed_orders",
    [
        (
            [1, 100, 100],
            [100, 100, 100],
            [
                BetFairOrder(
                    size=13.64,
                    price=2.1,
                    selection_id=2,
                    market_id="2",
                    side="LAY",
                    strategy="mvp",
                ),
                BetFairOrder(
                    size=10.0,
                    price=5.0,
                    selection_id=3,
                    market_id="2",
                    side="BACK",
                    strategy="mvp",
                ),
            ],
        ),
        (
            [100, 100, 100],
            [100, 10, 100],
            [
                BetFairOrder(
                    size=10.0,
                    price=4.0,
                    selection_id=1,
                    market_id="1",
                    side="BACK",
                    strategy="mvp",
                ),
                BetFairOrder(
                    size=10.0,
                    price=5.0,
                    selection_id=3,
                    market_id="2",
                    side="BACK",
                    strategy="mvp",
                ),
            ],
        ),
        (
            [100, 100, 1],
            [100, 100, 100],
            [
                BetFairOrder(
                    size=10.0,
                    price=4.0,
                    selection_id=1,
                    market_id="1",
                    side="BACK",
                    strategy="mvp",
                ),
                BetFairOrder(
                    size=13.64,
                    price=2.1,
                    selection_id=2,
                    market_id="2",
                    side="LAY",
                    strategy="mvp",
                ),
            ],
        ),
    ],
)
def test_market_depth_not_available(
    get_s3_client,
    get_betfair_client,
    now_timestamp_fixture,
    set_stake_size,
    back_market_depth,
    lay_market_depth,
    placed_orders,
):
    requests_data = pd.DataFrame(
        {
            "race_id": [1, 2, 2],
            "horse_id": [1, 2, 3],
            "horse_name": ["Horse A", "Horse B", "Horse C"],
            "selection_type": ["BACK", "LAY", "BACK"],
            "market_type": ["WIN", "PLACE", "WIN"],
            "market_id": ["1", "2", "2"],
            "selection_id": [1, 2, 3],
            "requested_odds": [4.0, 2.2, 3.5],
            "race_time": [
                pd.Timestamp("2025-01-01 15:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
                pd.Timestamp("2025-01-01 16:00:00+01:00"),
            ],
            "minutes_to_race": [20, 20, 20],
            "back_price_1": [4.0, 2.0, 5.0],
            "back_price_1_depth": back_market_depth,
            "back_price_2": [3.9, 1.9, 4.9],
            "back_price_2_depth": [100, 100, 100],
            "lay_price_1": [4.1, 2.1, 5.1],
            "lay_price_1_depth": lay_market_depth,
            "lay_price_2": [4.2, 2.2, 5.2],
            "lay_price_2_depth": [100, 100, 100],
            "eight_to_seven_runners": [False, False, False],
            "short_price_removed_runners": [False, False, False],
            "average_price_matched": [0.0, 0.0, 0.0],
            "size_matched": [0.0, 0.0, 0.0],
        }
    )

    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(),
        stake_size=set_stake_size,
    )

    trader.trade_markets(
        requests_data=requests_data,
        betting_data=RawBettingData(
            selections_data=pd.DataFrame(),
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
    assert trader.betfair_client.placed_orders == placed_orders


@pytest.mark.parametrize(
    "selection_type, requested_odds, back_price, lay_price, average_price_matched, size_matched, expected_betfair_order",
    [
        (
            "LAY",  # selection_type,
            2.2,  # requested_odds,
            2.4,  # back_price,
            2.1,  # lay_price,
            2.0,  # average_price_matched,
            5,  # size_matched,
            [
                BetFairOrder(
                    size=9.09,
                    price=2.1,
                    selection_id=2,
                    market_id="2",
                    side="LAY",
                    strategy="mvp",
                )
            ],
        ),
        (
            "LAY",  # selection_type,
            2.1,  # requested_odds,
            2.4,  # back_price,
            2.5,  # lay_price,
            2.0,  # average_price_matched,
            5,  # size_matched,
            [],
        ),
        (
            "BACK",  # selection_type,
            5.0,  # requested_odds,
            4.0,  # back_price,
            5.2,  # lay_price,
            6.0,  # average_price_matched,
            5.0,  # size_matched,
            [
                BetFairOrder(
                    size=5.0,
                    price=4.0,
                    selection_id=2,
                    market_id="2",
                    side="BACK",
                    strategy="mvp",
                )
            ],
        ),
        (
            "BACK",  # selection_type,
            5.0,  # requested_odds,
            3.9,  # back_price,
            5.2,  # lay_price,
            6.0,  # average_price_matched,
            5.0,  # size_matched,
            [],
        ),
    ],
)
def test_adjusted_stake_size(
    get_s3_client,
    get_betfair_client,
    now_timestamp_fixture,
    set_stake_size,
    selection_type,
    requested_odds,
    back_price,
    lay_price,
    average_price_matched,
    size_matched,
    expected_betfair_order,
):
    requests_data = pd.DataFrame(
        {
            "race_id": [2],
            "horse_id": [2],
            "horse_name": ["Horse B"],
            "selection_type": [selection_type],
            "market_type": ["WIN"],
            "market_id": ["2"],
            "selection_id": [2],
            "requested_odds": [requested_odds],
            "race_time": [pd.Timestamp("2025-01-01 16:00:00+01:00")],
            "minutes_to_race": [20],
            "back_price_1": [back_price],
            "back_price_1_depth": [100],
            "back_price_2": [1.9],
            "back_price_2_depth": [100],
            "lay_price_1": [lay_price],
            "lay_price_1_depth": [100],
            "lay_price_2": [2.2],
            "lay_price_2_depth": [100],
            "eight_to_seven_runners": [False],
            "short_price_removed_runners": [False],
            "average_price_matched": [average_price_matched],
            "size_matched": [size_matched],
        }
    )

    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(),
        stake_size=set_stake_size,
    )

    trader.trade_markets(
        requests_data=requests_data,
        betting_data=RawBettingData(
            selections_data=pd.DataFrame(),
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
    assert trader.betfair_client.placed_orders == expected_betfair_order
