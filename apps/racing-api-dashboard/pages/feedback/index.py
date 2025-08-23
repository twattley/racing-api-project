import dash

dash.register_page(__name__, path="/feedback", name="Feedback")
from dash import html, dcc


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
            html.H1("Feedback & Insights"),
            html.P("Welcome to the Feedback page. Choose a section below:"),
            html.Div(
                [
                    dcc.Link(
                        html.Button(
                            "Race Times Feedback",
                            style={
                                "width": "220px",
                                "height": "70px",
                                "fontSize": "1.3rem",
                                "margin": "1rem",
                                "borderRadius": "1rem",
                            },
                        ),
                        href="/feedback/race-times",
                    ),
                    dcc.Link(
                        html.Button(
                            "Betting Feedback",
                            style={
                                "width": "220px",
                                "height": "70px",
                                "fontSize": "1.3rem",
                                "margin": "1rem",
                                "borderRadius": "1rem",
                            },
                        ),
                        href="/feedback/betting",
                    ),
                ],
                style={"display": "flex", "justifyContent": "center", "gap": "2rem"},
            ),
        ],
        style={"padding": "32px", "position": "relative"},
    )
