from dash import html

from services.base_service import race_form


def render_race_form(race_id: int):
    # Fail fast behavior relies on callers always providing a valid race_id
    details = race_form(race_id)

    return html.Div(
        [
            html.H3("Race Form"),
            html.P(f"race_id: {race_id}"),
            html.P("TODO: Implement race form UI here."),
        ]
    )
