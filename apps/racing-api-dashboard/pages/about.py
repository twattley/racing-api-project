import dash
dash.register_page(__name__)
from dash import html, dcc

def layout():
    return html.Div([
        html.H1("About"),
        html.P("This is the about page for the Racing Dashboard."),
        dcc.Link("Go back home", href="/"),
    ], style={"padding": "16px"})
