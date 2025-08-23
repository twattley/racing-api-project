import dash
dash.register_page(__name__, path="/today", name="Today")
from dash import html

from styles.navigation_button import navigation_button

def layout():
    return html.Div([
        html.H1("Today's Races & Betting"),
        html.P("Welcome to the Today page. Choose a section below:"),
        html.Div([
            navigation_button("Race Times", "/today/race-times"),
            navigation_button("Betting", "/today/betting"),
        ], style={"display": "flex", "justifyContent": "center", "gap": "2rem"})
    ], style={"padding": "32px"})

