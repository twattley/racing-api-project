from __future__ import annotations

# A tiny Dash app to get started
# Concepts (mapping to React):
# - dash.Dash(...) -> App instance (like creating a root).
# - app.layout -> The component tree (analogous to JSX). Use dash.html for HTML tags and dash.dcc for higher-level widgets.
# - @app.callback -> Event wiring. Inputs/States trigger the function; Outputs update component props (like event handlers + setState).

from datetime import datetime
from collections import Counter
from dash import Dash, html, dcc, Output, Input, dash_table
from plotly import graph_objs as go


# note on wrappers: In Dash you assign a single root component to app.layout.
# Using html.Div(...) as the root is conventional (like a root <div> in React),
# but it's not mandatory—you can set any single component as the root.
#
# note on units: 'rem' is a CSS unit relative to the root font-size (usually 16px).
# 1rem ~= 16px by default; 0.5rem ~= 8px. Inline style strings accept standard CSS units.

# Sample static rows for the DataTable (we'll swap this to real API data later)
SAMPLE_RACES = [
    {
        "course": "Ascot",
        "race_time": "14:30",
        "race_title": "Handicap",
        "distance": "1m",
        "going": "Good",
    },
    {
        "course": "York",
        "race_time": "15:10",
        "race_title": "Maiden",
        "distance": "7f",
        "going": "Good to soft",
    },
    {
        "course": "Ascot",
        "race_time": "16:00",
        "race_title": "Listed",
        "distance": "6f",
        "going": "Good",
    },
]

# Simple aggregation for the demo plot
_course_counts = Counter(r["course"] for r in SAMPLE_RACES)
PLOT_FIGURE = go.Figure(
    data=[go.Bar(x=list(_course_counts.keys()), y=list(_course_counts.values()))],
    layout=go.Layout(title="Races by Course", margin=dict(t=40, r=16, b=40, l=48)),
)

app = Dash(__name__, title="Racing Dashboard")

app.layout = html.Div(
    [
        # Two-column split: left (UI + table), right (plot)
        html.Div(
            [
                # LEFT COLUMN
                html.Div(
                    [
                        html.H1("Racing Dashboard", style={"marginBottom": "0.5rem"}),
                        html.P("A tiny Dash app to verify the dashboard setup."),
                        html.Div(
                            [
                                html.Button("Click me", id="btn", n_clicks=0),
                                html.Div(
                                    id="click-output", style={"marginTop": "0.75rem"}
                                ),
                            ],
                            style={"marginTop": "1rem", "marginBottom": "1rem"},
                        ),
                        html.Div(
                            [
                                html.Strong("Clock: "),
                                html.Span(id="clock"),
                                dcc.Interval(
                                    id="clock-tick", interval=60_000, n_intervals=0
                                ),  # 1 min
                            ]
                        ),
                        html.Hr(),
                        html.H2("Sample Races", style={"margin": "1rem 0 0.5rem"}),
                        dash_table.DataTable(
                            id="races-table",
                            columns=[
                                {"name": "Course", "id": "course"},
                                {"name": "Time", "id": "race_time"},
                                {"name": "Title", "id": "race_title"},
                                {"name": "Distance", "id": "distance"},
                                {"name": "Going", "id": "going"},
                            ],
                            data=SAMPLE_RACES,
                            page_size=5,
                            style_table={"overflowX": "auto"},
                            style_header={"fontWeight": "600"},
                            style_cell={
                                "padding": "0.5rem",
                                "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
                                "fontSize": "0.95rem",
                            },
                        ),
                    ],
                    style={
                        "flex": "1 1 50%",
                        "minWidth": 0,
                        "paddingRight": "0.75rem",
                    },
                ),
                # RIGHT COLUMN
                html.Div(
                    [
                        html.H2("Overview", style={"margin": "0 0 0.5rem"}),
                        dcc.Graph(figure=PLOT_FIGURE, config={"displayModeBar": False}),
                    ],
                    style={
                        "flex": "1 1 50%",
                        "minWidth": 0,
                        "paddingLeft": "0.75rem",
                        "borderLeft": "1px solid #e5e7eb",
                    },
                ),
            ],
            style={
                "display": "flex",
                "gap": "1rem",
                "alignItems": "flex-start",
            },
        ),
    ],
    style={
        "fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        "padding": "16px",
        "height": "100vh",
        "boxSizing": "border-box",
    },
)


@app.callback(Output("click-output", "children"), Input("btn", "n_clicks"))
def on_click(n_clicks: int):
    if not n_clicks:
        return "Button not clicked yet."
    return f"Button clicked {n_clicks} time{'s' if n_clicks != 1 else ''}."


@app.callback(Output("clock", "children"), Input("clock-tick", "n_intervals"))
def update_clock(_):
    return datetime.now().strftime("%H:%M:%S")


if __name__ == "__main__":
    # Run the development server
    # Visit http://127.0.0.1:8050 in your browser
    app.run(debug=True, host="0.0.0.0", port=8050)
