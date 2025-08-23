import dash
dash.register_page(__name__, path="/today/betting", name="Betting")
from dash import html

def layout():
    return html.Div([
        html.H1("Today's Betting"),
        html.P("This page will show betting information for today."),
    ], style={"padding": "32px"})
