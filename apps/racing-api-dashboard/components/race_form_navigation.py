import dash
from dash import dcc, html, callback, Input, Output

from components.race_form import render_race_form
from components.horse_graphs import render_horse_graphs
from components.race_graphs import render_race_graphs


def render_race_form_navigation(
    race_id: int,
    *,
    base_segment: str = "feedback",
):
    """
    Reusable race navigation + content area.

    Parameters
    - race_id: race identifier (str|int|None)
    - base_segment: top-level URL segment (e.g. "feedback" or "today")
    """
    return html.Div(
        [
            # Config/state stores
            dcc.Store(
                id="race-config",
                storage_type="session",
                data={"base_segment": base_segment},
            ),
            dcc.Store(
                id="race-state",
                storage_type="session",
                data={"race_id": race_id, "horse_id": None},
            ),

            # Top-level navigation between sub-views
            dcc.Tabs(
                id="race-tabs",
                value="form",
                children=[
                    dcc.Tab(label="Home", value="root-home"),
                    dcc.Tab(label="Race Times", value="race-times"),
                    dcc.Tab(label="Form", value="form"),
                    dcc.Tab(label="Race Graphs", value="race-graphs"),
                    dcc.Tab(label="Horse Graphs", value="horse-graphs"),
                ],
            ),

            # Content swaps based on selected tab
            html.Div(
                id="race-tab-content",
                children=render_race_form(race_id),
                style={"padding": "16px"},
            ),
        ],
        style={"padding": "16px"},
    )


@callback(
    Output("race-tab-content", "children"),
    Input("race-tabs", "value"),
    Input("race-state", "data"),
    Input("race-config", "data"),
    prevent_initial_call=False,
)
def render_race_subview(active_tab: str, state: dict | None, config: dict | None):
    if not state or "race_id" not in state or state["race_id"] is None:
        raise ValueError("race_id is required and must be set in race-state store")
    base_segment = (config or {}).get("base_segment", "feedback")
    race_id: int = int(state["race_id"])  # ensure int for downstream services
    horse_id = state.get("horse_id")

    if active_tab == "form":
        return render_race_form(race_id)
    if active_tab == "race-graphs":
        return render_race_graphs(race_id)
    if active_tab == "horse-graphs":
        return render_horse_graphs(race_id, horse_id)
    if active_tab == "race-times":
        # Navigate to the segment-specific race-times page
        return dcc.Location(
            pathname=f"/{base_segment}/race-times", id="race-times-redirect"
        )
    if active_tab == "root-home":
        return dcc.Location(pathname="/", id="root-redirect")
    return html.Div([html.P("Unknown tab.")])


@callback(
    Output("race-tabs", "value"),
    Input("url", "pathname"),
    Input("race-config", "data"),
    prevent_initial_call=False,
    suppress_callback_exceptions=True,
)
def sync_tabs_with_path(pathname: str | None, config: dict | None):
    base_segment = (config or {}).get("base_segment", "feedback")
    if not pathname:
        return "form"
    # If the user is within the race page for this segment, keep the Form tab selected
    if pathname.startswith(f"/{base_segment}/race/"):
        return "form"
    # If navigating to segment-specific race-times, select that tab
    if pathname == f"/{base_segment}/race-times":
        return "race-times"
    return dash.no_update
