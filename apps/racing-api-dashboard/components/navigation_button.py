from dash import html, dcc


def navigation_button(label: str, href: str) -> dcc.Link:
    return dcc.Link(
        html.Button(
            label,
            style={
                "width": "220px",
                "height": "70px",
                "fontSize": "1.3rem",
                "margin": "1rem",
                "borderRadius": "1rem",
            },
        ),
        href=href,
    )
