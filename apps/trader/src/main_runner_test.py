from datetime import datetime
import sys
from random import randint
from time import sleep
import pandas as pd

from api_helpers.helpers.logging_config import I, W
from api_helpers.helpers.time_utils import get_uk_time_now, make_uk_time_aware

from src.fetch_requests import fetch_betting_data
from src.market_trader import MarketTrader
from src.prepare_requests import prepare_request_data
from src.storage.clients import get_betfair_client, get_s3_client

STAKE_SIZE = 10.0

if __name__ == "__main__":
    s3_client = get_s3_client()
    betfair_client = get_betfair_client()

    trader = MarketTrader(
        s3_client=s3_client,
        betfair_client=betfair_client,
        stake_size=STAKE_SIZE,
    )
    for i in range(100):
        now_timestamp = get_uk_time_now()
        betting_data = fetch_betting_data(s3_client, betfair_client)
        requests_data = prepare_request_data(betting_data)
        trader.trade_markets(
            requests_data=requests_data,
            betting_data=betting_data,
            now_timestamp=now_timestamp,
        )
