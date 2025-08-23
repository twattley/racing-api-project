import dash

dash.register_page(__name__, path="/")
from dash import html
from styles.navigation_button import navigation_button


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("Today", style={"textAlign": "center"}),
                            navigation_button("Races", "/today/race-times"),
                            navigation_button("Betting", "/today/betting"),
                        ],
                        style={
                            "flex": "1 1 0",
                            "minWidth": "260px",
                            "background": "#f7f7f7",
                            "borderRadius": "1.5rem",
                            "padding": "2rem",
                            "margin": "1rem",
                            "boxShadow": "0 2px 8px #0001",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                        },
                    ),
                    html.Div(
                        [
                            html.H2("Feedback", style={"textAlign": "center"}),
                            navigation_button("Races", "/feedback/race-times"),
                            navigation_button("Betting", "/feedback/betting"),
                        ],
                        style={
                            "flex": "1 1 0",
                            "minWidth": "260px",
                            "background": "#f7f7f7",
                            "borderRadius": "1.5rem",
                            "padding": "2rem",
                            "margin": "1rem",
                            "boxShadow": "0 2px 8px #0001",
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                        },
                    ),
                ],
                style={"display": "flex", "justifyContent": "center", "gap": "2rem"},
            ),
        ],
        style={"padding": "64px"},
    )
