import dash
from components.race_form_navigation import render_race_form_navigation

# Register a Today-specific race page that reuses the shared navigation component
# URL pattern mirrors the feedback page but under /today

dash.register_page(__name__, path_template="/today/race/<race_id>", name="Today Race")


def layout(race_id: str | int | None = None, **_: dict):
    # Coerce to int and fail loudly if missing or invalid
    if race_id is None:
        raise ValueError("race_id is required for today race page")
    rid = int(race_id)
    return render_race_form_navigation(rid, base_segment="today")
