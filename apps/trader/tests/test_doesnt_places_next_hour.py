from trader.market_trader import MarketTrader
from .test_helpers import create_test_data


def test_doesnt_place_bets_in_next_hour(
    get_s3_client, get_betfair_client, now_timestamp_fixture, set_stake_size
):
    trader = MarketTrader(
        s3_client=get_s3_client,
        betfair_client=get_betfair_client,
    )

    trader.trade_markets(
        now_timestamp=now_timestamp_fixture,
        stake_size=set_stake_size,
        requests_data=create_test_data({"minutes_to_race": [100, 100, 100]}),
    )

    assert not trader.s3_client.stored_data
    assert not trader.betfair_client.placed_orders
    assert not trader.betfair_client.cash_out_market_ids
