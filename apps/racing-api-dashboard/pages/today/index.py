import dash

dash.register_page(__name__, path="/today", name="Today")
from dash import html, dcc

from styles.navigation_button import navigation_button


def layout():
    return html.Div(
        [
            dcc.Link(
                html.Button(
                    "Home",
                    style={
                        "position": "absolute",
                        "top": "24px",
                        "left": "24px",
                        "fontSize": "1.1rem",
                        "borderRadius": "0.7rem",
                        "padding": "0.5rem 1.5rem",
                    },
                ),
                href="/",
            ),
            html.H1("Today's Races & Betting"),
            html.P("Welcome to the Today page. Choose a section below:"),
            html.Div(
                [
                    navigation_button("Race Times", "/today/race-times"),
                    navigation_button("Betting", "/today/betting"),
                ],
                style={"display": "flex", "justifyContent": "center", "gap": "2rem"},
            ),
        ],
        style={"padding": "32px", "position": "relative"},
    )
