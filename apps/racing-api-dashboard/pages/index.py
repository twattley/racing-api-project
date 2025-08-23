import dash
dash.register_page(__name__, path="/")
from dash import html, dcc

def layout():
    return html.Div([
        html.H1("Racing Dashboard", style={"textAlign": "center", "marginBottom": "2rem"}),
        html.Div([
            html.Div([
                html.H2("Today", style={"textAlign": "center"}),
                dcc.Link(
                    html.Button("Races", style={
                        "width": "200px", "height": "70px", "fontSize": "1.3rem", "margin": "1rem", "borderRadius": "1rem"
                    }),
                    href="/today/race-times"
                ),
                dcc.Link(
                    html.Button("Betting", style={
                        "width": "200px", "height": "70px", "fontSize": "1.3rem", "margin": "1rem", "borderRadius": "1rem"
                    }),
                    href="/today/betting"
                ),
            ], style={
                "flex": "1 1 0", "minWidth": "260px", "background": "#f7f7f7", "borderRadius": "1.5rem", "padding": "2rem", "margin": "1rem", "boxShadow": "0 2px 8px #0001", "display": "flex", "flexDirection": "column", "alignItems": "center"
            }),
            html.Div([
                html.H2("Feedback", style={"textAlign": "center"}),
                dcc.Link(
                    html.Button("Races", style={
                        "width": "200px", "height": "70px", "fontSize": "1.3rem", "margin": "1rem", "borderRadius": "1rem"
                    }),
                    href="/feedback/race-times"
                ),
                dcc.Link(
                    html.Button("Betting", style={
                        "width": "200px", "height": "70px", "fontSize": "1.3rem", "margin": "1rem", "borderRadius": "1rem"
                    }),
                    href="/feedback/betting"
                ),
            ], style={
                "flex": "1 1 0", "minWidth": "260px", "background": "#f7f7f7", "borderRadius": "1.5rem", "padding": "2rem", "margin": "1rem", "boxShadow": "0 2px 8px #0001", "display": "flex", "flexDirection": "column", "alignItems": "center"
            }),
        ], style={"display": "flex", "justifyContent": "center", "gap": "2rem"})
    ], style={"padding": "64px"})
