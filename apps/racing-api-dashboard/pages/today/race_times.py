import dash
from dash import html
from components.race_times import race_times

dash.register_page(__name__, path="/today/race-times", name="Race Times")


def layout():
    return html.Div(
        [
            html.H1("Today's Race Times"),
            race_times("feedback"),
        ],
        style={"padding": "32px"},
    )
