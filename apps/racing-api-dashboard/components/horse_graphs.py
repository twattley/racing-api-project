from dash import html


def render_horse_graphs(race_id: str | int, horse_id: str | int | None):
    return html.Div(
        [
            html.H3("Horse Graphs (Individual)"),
            html.P(f"race_id: {race_id}"),
            html.P(
                f"horse_id: {horse_id if horse_id is not None else '— (select later)'}"
            ),
            html.P("TODO: Add per-horse charts and controls here."),
        ]
    )
