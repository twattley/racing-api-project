from dash import html


def render_race_graphs(race_id: str | int):
    return html.Div(
        [
            html.H3("Race Graphs (All Horses)"),
            html.P(f"race_id: {race_id}"),
            html.P("TODO: Add aggregated race-level charts here."),
        ]
    )
