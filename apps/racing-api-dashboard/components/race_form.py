from dash import html

from services.base_service import race_form


def render_race_form(race_id: str | int):
    d = race_form(race_id)
    print(d)
    return html.Div(
        [
            html.H3("Race Form"),
            html.P(f"race_id: {race_id}"),
            html.P("TODO: Implement race form UI here."),
        ]
    )
