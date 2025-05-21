from api_helpers.clients.betfair_client import BetFairOrder, BetFairCashOut
import pandas as pd


def test_handles_single_matched_lay_bet():
    cash_out_data = pd.DataFrame(
        {
            "market_id": ["1"],
            "selection_id": [1],
            "selection_type": ["LAY"],
            "average_price_matched": [3.35],
            "size_matched": [10.0],
            "market": ["WIN"],
            "status": ["ACTIVE"],
            "back_price_1": [3.25],
            "back_price_1_depth": [10],
            "back_price_2": [3.2],
            "back_price_2_depth": [10],
            "lay_price_1": [3.4],
            "lay_price_1_depth": [10],
            "lay_price_2": [3.45],
            "lay_price_2_depth": [10],
        }
    )

    b = BetFairCashOut()
    bets = b.cash_out(cash_out_data)
    assert bets == [
        BetFairOrder(
            size=10.4,
            price=3.2,
            selection_id="1",
            market_id="1",
            side="BACK",
            strategy="cash_out",
        )
    ]


def test_handles_single_matched_back_bet():
    cash_out_data = pd.DataFrame(
        {
            "market_id": ["1"],
            "selection_id": [1],
            "selection_type": ["BACK"],
            "average_price_matched": [3.4],
            "size_matched": [10.0],
            "market": ["WIN"],
            "status": ["ACTIVE"],
            "back_price_1": [3.25],
            "back_price_1_depth": [10],
            "back_price_2": [3.2],
            "back_price_2_depth": [10],
            "lay_price_1": [3.35],
            "lay_price_1_depth": [10],
            "lay_price_2": [3.3],
            "lay_price_2_depth": [10],
        }
    )

    b = BetFairCashOut()
    bets = b.cash_out(cash_out_data)
    assert bets == [
        BetFairOrder(
            size=10.24,
            price=3.3,
            selection_id="1",
            market_id="1",
            side="LAY",
            strategy="cash_out",
        )
    ]


def test_handles_multiple_back_and_lay_bets():
    cash_out_data = pd.DataFrame(
        {
            "market_id": ["1", "1", "1"],
            "selection_id": [1, 2, 3],
            "selection_type": ["BACK", "BACK", "LAY"],
            "average_price_matched": [5.63, 5.80, 5.4],
            "size_matched": [10.0, 15.0, 3.99],
            "market": ["WIN", "WIN", "WIN"],
            "status": ["ACTIVE", "ACTIVE", "ACTIVE"],
            "back_price_1": [5.6, 6.0, 5.3],
            "back_price_1_depth": [10, 10, 4],
            "back_price_2": [5.5, 5.9, 5.2],
            "back_price_2_depth": [10, 10, 6],
            "lay_price_1": [5.8, 6.4, 5.5],
            "lay_price_1_depth": [1, 12, 10],
            "lay_price_2": [5.9, 6.6, 5.5],
            "lay_price_2_depth": [27, 3, 10],
        }
    )

    b = BetFairCashOut()
    bets = b.cash_out(cash_out_data)
    assert bets == [
        BetFairOrder(
            size=9.54,
            price=5.9,
            selection_id="1",
            market_id="1",
            side="LAY",
            strategy="cash_out",
        ),
        BetFairOrder(
            size=13.51,
            price=6.6,
            selection_id="2",
            market_id="1",
            side="LAY",
            strategy="cash_out",
        ),
        BetFairOrder(
            size=4.11,
            price=5.2,
            selection_id="3",
            market_id="1",
            side="BACK",
            strategy="cash_out",
        ),
    ]


def test_handles_multiple_partially_matched_back_and_lay_bets():
    cash_out_data = pd.DataFrame(
        {
            "market_id": ["1", "1", "1"],
            "selection_id": [1, 1, 2],
            "selection_type": ["BACK", "LAY", "LAY"],
            "average_price_matched": [5.15, 5.21, 6.2],
            "size_matched": [6.13, 2.0, 2.0],
            "market": ["WIN", "WIN", "WIN"],
            "status": ["ACTIVE", "ACTIVE", "ACTIVE"],
            "back_price_1": [5.1, 5.1, 5.9],
            "back_price_1_depth": [14, 14, 5],
            "back_price_2": [4.9, 4.9, 5.8],
            "back_price_2_depth": [2, 2, 4],
            "lay_price_1": [5.5, 5.5, 6.4],
            "lay_price_1_depth": [1, 1, 7],
            "lay_price_2": [5.6, 5.6, 6.6],
            "lay_price_2_depth": [13, 13, 1],
        }
    )

    b = BetFairCashOut()
    bets = b.cash_out(cash_out_data)
    assert bets == [
        BetFairOrder(
            size=3.78,
            price=5.6,
            selection_id="1",
            market_id="1",
            side="LAY",
            strategy="cash_out",
        ),
        BetFairOrder(
            size=2.12,
            price=5.8,
            selection_id="2",
            market_id="1",
            side="BACK",
            strategy="cash_out",
        ),
    ]
