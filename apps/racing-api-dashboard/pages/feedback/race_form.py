import dash
from dash import html

from components.race_form import race_form


dash.register_page(__name__, path_template="/feedback/race/<race_id>", name="Race Form")

def race_form(race_id=None):
    return html.Div(
        [
            html.H2("Race Form"),
            html.P(f"race_id: {race_id or 'None provided'}"),
            html.P("TODO: Implement race form UI here."),
        ],
        style={"padding": "16px"},
    )

def layout(race_id=None, **_kwargs):
	return html.Div([race_form(race_id=race_id)], style={"padding": "16px"})

