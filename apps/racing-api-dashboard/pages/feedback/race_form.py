import dash
from components.race_form_navigation import render_race_form_navigation

dash.register_page(__name__, path_template="/feedback/race/<race_id>", name="Race Form")


def layout(race_id: str | int | None = None, **_: dict):
    # Coerce to int and fail loudly if missing or invalid
    if race_id is None:
        raise ValueError("race_id is required for feedback race page")
    rid = int(race_id)
    return render_race_form_navigation(rid, base_segment="feedback")
