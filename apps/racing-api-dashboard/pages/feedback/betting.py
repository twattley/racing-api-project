import dash

dash.register_page(__name__, path="/feedback/betting", name="Betting Feedback")
from dash import html


def layout():
    return html.Div(
        [
            html.H1("Betting Feedback"),
            html.P("This page will collect feedback on betting."),
        ],
        style={"padding": "32px"},
    )
