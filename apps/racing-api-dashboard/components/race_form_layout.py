from dash import html, dcc


def race_form_layout(data_type: str):
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
            html.Div(
                [
                    dcc.Link(
                        html.Button(
                            "Race Times",
                            style={
                                "width": "220px",
                                "height": "70px",
                                "fontSize": "1.3rem",
                                "margin": "1rem",
                                "borderRadius": "1rem",
                            },
                        ),
                        href=f"/{data_type}/race-times",
                    ),
                    dcc.Link(
                        html.Button(
                            "Betting",
                            style={
                                "width": "220px",
                                "height": "70px",
                                "fontSize": "1.3rem",
                                "margin": "1rem",
                                "borderRadius": "1rem",
                            },
                        ),
                        href=f"/{data_type}/betting",
                    ),
                ],
                style={"display": "flex", "justifyContent": "center", "gap": "2rem"},
            ),
        ],
        style={"padding": "32px", "position": "relative"},
    )
