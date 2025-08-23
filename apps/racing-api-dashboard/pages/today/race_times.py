import dash

dash.register_page(__name__, path="/today/race-times", name="Race Times")
from dash import html


def layout():
    return html.Div(
        [
            html.H1("Today's Race Times"),
            html.P("This page will show all race times for today."),
        ],
        style={"padding": "32px"},
    )
