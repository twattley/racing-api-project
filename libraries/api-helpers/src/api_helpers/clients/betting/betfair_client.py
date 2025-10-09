from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from time import sleep
from typing import Literal

import betfairlightweight
import numpy as np
import pandas as pd
import requests
from api_helpers.helpers.logging_config import D, I
from api_helpers.helpers.time_utils import get_uk_time_now, make_uk_time_aware

from .cash_out import BetFairCashOut


@dataclass(frozen=True)
class BetFairCancelOrders:
    market_ids: list[str]


@dataclass(frozen=True)
class BetFairOrder:
    size: float
    price: float
    selection_id: str
    market_id: str
    side: str
    strategy: str


@dataclass
class OrderResult:
    success: bool
    message: str
    size_matched: float | None = None
    average_price_matched: float | None = None

    def __bool__(self) -> bool:
        """Allow the result to be used in boolean contexts"""
        return self.success


class BetFairClient:
    """
    Betfair client
    """

    MARKET_FILTER = betfairlightweight.filters.market_filter(
        event_type_ids=["7"],
        market_countries=["GB"],
        market_type_codes=["WIN", "PLACE"],
        market_start_time={
            "from": ((datetime.now()) - timedelta(hours=1)).strftime("%Y-%m-%dT%TZ"),
            "to": (datetime.now())
            .replace(hour=23, minute=59, second=0, microsecond=0)
            .strftime("%Y-%m-%dT%TZ"),
        },
    )

    MARKET_PROJECTION = [
        "COMPETITION",
        "EVENT",
        "EVENT_TYPE",
        "MARKET_START_TIME",
        "MARKET_DESCRIPTION",
        "RUNNER_DESCRIPTION",
        "RUNNER_METADATA",
    ]

    PRICE_PROJECTION = betfairlightweight.filters.price_projection(
        price_data=betfairlightweight.filters.price_data(ex_all_offers=True)
    )

    def __init__(self, username: str, password: str, app_key: str, certs_path: str):
        self.username = username
        self.password = password
        self.app_key = app_key
        self.certs_path = certs_path
        self.trading_client: betfairlightweight.APIClient | None = None

    def login(self):
        if self.trading_client is None or self.trading_client.session_expired:
            I("Logging into Betfair...")
            self.trading_client = betfairlightweight.APIClient(
                username=self.username,
                password=self.password,
                app_key=self.app_key,
                certs=self.certs_path,
            )
            self.trading_client.login(session=requests)
            I("Logged into Betfair!")

    def check_session(self):
        if self.trading_client is None or self.trading_client.session_expired:
            I("Betfair session expired")
            self.login()

    def logout(self):
        if self.trading_client is not None:
            self.trading_client.logout()
            I("Logged out of Betfair")

    def fetch_data(self) -> pd.DataFrame:
        self.check_session()
        events = self.trading_client.betting.list_events(filter=self.MARKET_FILTER)
        markets = []
        if events:
            for event in events:
                event_id = event.event.id
                event_name = event.event.name
                market_catalogue_filter = betfairlightweight.filters.market_filter(
                    event_ids=[event_id],
                )

                market_catalogues = self.trading_client.betting.list_market_catalogue(
                    filter=market_catalogue_filter,
                    max_results=100,
                    market_projection=[self.MARKET_PROJECTION],
                )

                for market in market_catalogues:
                    for runner in market.runners:

                        markets.append(
                            {
                                "event_name": event_name,
                                "event_id": event_id,
                                "race_id": self._make_unique_id(
                                    market.market_start_time,
                                    event_id,
                                    tz="Europe/London",
                                ),
                                "course": market.event.venue,
                                "market_name": market.market_name,
                                "market_id": market.market_id,
                                "race_time": make_uk_time_aware(
                                    market.market_start_time
                                ),
                                "market_type": market.description.market_type,
                                "race_type": market.description.race_type,
                                "selection_id": runner.selection_id,
                                "horse_name": runner.runner_name,
                                "number_of_runners": len(market.runners),
                            }
                        )

    def _make_unique_id(race_time, event_id, tz: str | None = None) -> str:
        ts = pd.to_datetime(race_time, errors="coerce")
        if tz is not None and ts is not pd.NaT:
            try:
                ts = ts.tz_localize(tz) if ts.tzinfo is None else ts.tz_convert(tz)
            except Exception:
                pass
        ts_str = "" if ts is pd.NaT else ts.strftime("%Y%m%d%H%M%S")
        key = f"{ts_str}|{'' if event_id is None else str(event_id)}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()
