import dash
from dash import html
from components.race_times import race_times

dash.register_page(__name__, path="/feedback/race-times", name="Race Times Feedback")


def layout():
    return html.Div(
        [
            html.H1("Race Times Feedback"),
            race_times("feedback"),
        ],
        style={"padding": "32px"},
    )
