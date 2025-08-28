import dash
from dash import dcc, html, callback, Input, Output
from components.race_form import render_race_form
from components.horse_graphs import render_horse_graphs
from components.race_graphs import render_race_graphs

dash.register_page(__name__, path_template="/feedback/race/<race_id>", name="Race Form")


def layout(race_id: str | int | None = None, **_: dict):
    # Robust layout: works even if race_id isn't passed immediately by pages router
    race_id_str = None if race_id is None else str(race_id)

    return html.Div(
        [
            # Global state for this race page (add horse_id, filters later)
            dcc.Store(
                id="race-state",
                storage_type="session",
                data={"race_id": race_id_str, "horse_id": None},
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
                children=render_race_form(race_id_str),
                style={"padding": "16px"},
            ),
        ],
        style={"padding": "16px"},
    )


@callback(
    Output("race-tab-content", "children"),
    Input("race-tabs", "value"),
    Input("race-state", "data"),
    prevent_initial_call=False,
)
def render_race_subview(active_tab: str, state: dict):
    state = state or {}
    race_id = state.get("race_id")
    horse_id = state.get("horse_id")

    tab = {
        "form": render_race_form(race_id),
        "race-graphs": render_race_graphs(race_id),
        "horse-graphs": render_horse_graphs(race_id, horse_id),
        "root-home": dcc.Location(pathname="/", id="root-redirect"),
        "race-times": dcc.Location(
            pathname="/feedback/race-times", id="race-times-redirect"
        ),
    }
    return tab.get(active_tab, html.Div([html.P("Unknown tab.")]))


@callback(
    Output("race-tabs", "value"),
    Input("url", "pathname"),
    prevent_initial_call=False,
    suppress_callback_exceptions=True,
)
def sync_tabs_with_path(pathname: str | None):
    if not pathname:
        return "form"
    if pathname.startswith("/feedback/race/"):
        return "form"
    return dash.no_update
