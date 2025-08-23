import dash
dash.register_page(__name__, path="/")
from dash import html, dcc

def layout():
    return html.Div([
        html.H1("Racing Dashboard", style={"textAlign": "center", "marginBottom": "2rem"}),
        html.Div([
            dcc.Link(
                html.Button("Today", style={
                    "width": "300px", "height": "100px", "fontSize": "2rem", "margin": "1rem", "borderRadius": "1.5rem"
                }),
                href="/today"
            ),
            dcc.Link(
                html.Button("Feedback", style={
                    "width": "300px", "height": "100px", "fontSize": "2rem", "margin": "1rem", "borderRadius": "1.5rem"
                }),
                href="/feedback"
            ),
        ], style={"display": "flex", "justifyContent": "center", "gap": "2rem"})
    ], style={"padding": "64px"})
