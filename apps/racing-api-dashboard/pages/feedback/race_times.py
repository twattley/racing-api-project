import dash
dash.register_page(__name__, path="/feedback/race-times", name="Race Times Feedback")
from dash import html

def layout():
    return html.Div([
        html.H1("Race Times Feedback"),
        html.P("This page will collect feedback on race times."),
    ], style={"padding": "32px"})
