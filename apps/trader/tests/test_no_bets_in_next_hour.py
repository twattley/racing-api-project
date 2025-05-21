import pandas as pd

from src.fetch_requests import RawBettingData
from src.market_trader import MarketTrader


def test_trade_markets_no_bets_in_next_hour(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):

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
                pd.Timestamp("2025-05-13 15:00:00+01:00"),
                pd.Timestamp("2025-05-13 16:00:00+01:00"),
            ],
            "minutes_to_race": [61, 61],
            "back_price_1": [4.0, 2.0],
            "back_price_1_depth": [100, 100],
            "back_price_2": [4.1, 2.56],
            "back_price_2_depth": [100, 100],
            "lay_price_1": [4.4, 2.66],
            "lay_price_1_depth": [100, 100],
            "lay_price_2": [4.5, 2.68],
            "lay_price_2_depth": [100, 100],
            "eight_to_seven_runners": [False, False],
            "short_price_removed_runners": [False, False],
            "average_price_matched": [4.4, 2.6],
            "size_matched": [4.0, 3.2],
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

    # Assertions: No actions should have been taken
    assert not trader.s3_client.stored_data, "S3 client should have no stored data."
    assert (
        not trader.betfair_client.placed_orders
    ), "Betfair client should have no placed orders."
    assert (
        not trader.betfair_client.cash_out_market_ids
    ), "Betfair client should have no cash out market IDs."


def test_trade_markets_empty_requests_data(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):
    """
    Tests that trade_markets exits early and performs no actions
    if the input requests_data is empty.
    """
    trader = MarketTrader(
        s3_client=get_s3_client(),
        betfair_client=get_betfair_client(),
        stake_size=set_stake_size,
    )

    requests_data = pd.DataFrame(
        [],
        columns=[
            "race_id",
            "horse_id",
            "horse_name",
            "selection_type",
            "market_type",
            "market_id",
            "selection_id",
            "requested_odds",
            "race_time",
            "minutes_to_race",
            "back_price_1",
            "back_price_1_depth",
            "back_price_2",
            "back_price_2_depth",
            "lay_price_1",
            "lay_price_1_depth",
            "lay_price_2",
            "lay_price_2_depth",
            "eight_to_seven_runners",
            "short_price_removed_runners",
            "average_price_matched",
            "size_matched",
        ],
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

    # Assertions: No actions should have been taken
    assert not trader.s3_client.stored_data, "S3 client should have no stored data."
    assert (
        not trader.betfair_client.placed_orders
    ), "Betfair client should have no placed orders."
    assert (
        not trader.betfair_client.cash_out_market_ids
    ), "Betfair client should have no cash out market IDs."
