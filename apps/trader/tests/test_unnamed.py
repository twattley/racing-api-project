from api_helpers.clients.betfair_client import BetFairOrder, OrderResult


class TestS3Client:
    def __init__(self):
        self.stored_data = None

    def store_data(self, data: pd.DataFrame, object_path: str):
        self.stored_data = {"object_path": object_path, "data": data}


class TestBetfairClient:
    def __init__(self):
        self.cash_out_market_ids = []
        self.placed_orders = []

    def cash_out_bets(self, market_ids: list[str]):
        self.cash_out_market_ids.append(list(market_ids))
        return self.cash_out_market_ids

    def place_order(self, betfair_order: BetFairOrder):
        self.placed_orders.append({"betfair_order": betfair_order})
        return OrderResult(success=True, message="Test Bet Placed")
