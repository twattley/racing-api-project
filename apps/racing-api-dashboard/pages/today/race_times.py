import dash
from dash import html
from components.race_times import render_race_times

dash.register_page(__name__, path="/today/race-times", name="Race Times")


def layout():
    return html.Div(
        [
            html.H1("Today's Race Times"),
            render_race_times("today"),
        ],
        style={"padding": "32px"},
    )
