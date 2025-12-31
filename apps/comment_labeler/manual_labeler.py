"""
Manual Comment Labeler - Interactive Dash dashboard for manual labeling.

Web UI for quickly labeling race comments.
Tracks session speed and saves directly to database.
"""

import time
from dataclasses import dataclass

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd

from api_helpers.clients import get_postgres_client


# Map non-numeric positions to full words (same as Gemini)
POSITION_MAP = {
    "PU": "Pulled Up",
    "F": "Fell",
    "UR": "Unseated Rider",
    "RO": "Ran Out",
    "BD": "Brought Down",
    "RR": "Refused to Race",
    "SU": "Slipped Up",
    "DSQ": "Disqualified",
}


def _ordinal(n: int) -> str:
    """Return ordinal suffix for a number (1st, 2nd, 3rd, etc)."""
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _distance_category(distance_beaten: float | None) -> str:
    """
    Categorize distance beaten into human-readable description.

    0-3L:  involved in finish
    3-5L:  competitive
    5-8L:  fairly beaten
    8L+:   well beaten
    """
    if distance_beaten is None:
        return ""
    
    # Handle non-numeric values (shouldn't happen, but be safe)
    try:
        dist = float(distance_beaten)
    except (ValueError, TypeError):
        return ""
    
    if dist <= 3:
        return "involved in finish"
    elif dist <= 5:
        return "competitive"
    elif dist <= 8:
        return "fairly beaten"
    else:
        return "well beaten"


def format_position(finishing_position, number_of_runners, distance_beaten=None) -> str:
    """
    Format position in the same style as Gemini input.

    Examples:
    - "Won"
    - "3rd of 12, involved in finish"
    - "6th of 14, competitive"
    - "10th of 16, fairly beaten"
    """
    if not finishing_position or not number_of_runners:
        return "Position Unknown"

    pos = str(finishing_position).strip().upper()

    # Handle special positions
    if pos in POSITION_MAP:
        return POSITION_MAP[pos]

    # Handle win
    if pos == "1":
        return "Won"

    # Normal finishing position with ordinal and distance category
    try:
        pos_num = int(finishing_position)
        pos_str = f"{pos_num}{_ordinal(pos_num)} of {number_of_runners}"

        # Add distance category if available
        dist_cat = _distance_category(distance_beaten)
        if dist_cat:
            return f"{pos_str}, {dist_cat}"
        return pos_str
    except (ValueError, TypeError):
        return f"{finishing_position} of {number_of_runners}"


def fetch_unlabeled_comments(db_client, limit: int = 50, min_date: str = "2020-01-01"):
    """Fetch comments that haven't been labeled yet."""
    query = f"""
    SELECT 
        r.unique_id,
        r.finishing_position,
        r.number_of_runners,
        r.total_distance_beaten as distance_beaten,
        r.tf_comment,
        r.rp_comment,
        r.main_race_comment,
        r.horse_name,
        r.race_date
    FROM public.results_data r
    LEFT JOIN public.comment_labels cl ON r.unique_id = cl.unique_id
    WHERE cl.unique_id IS NULL
      AND r.race_date >= '{min_date}'
      AND (r.tf_comment IS NOT NULL OR r.rp_comment IS NOT NULL)
      AND r.number_of_runners IS NOT NULL
      AND r.race_date > '2025-01-01'
      AND r.race_type = 'Flat'
      AND r.race_class >= 2
      AND r.hcap_range IS NOT NULL
    ORDER BY r.race_date DESC
    LIMIT {limit}
    """
    return db_client.fetch_data(query)


def save_label(db_client, unique_id: str, labels: dict):
    """Save a manually labeled comment to database."""
    row = {
        "unique_id": unique_id,
        **labels,
        "rated_by_gemini": False,
        "reasoning": None,  # No reasoning for manual labels
    }

    df = pd.DataFrame([row])
    db_client.store_data(
        data=df,
        table="comment_labels",
        schema="public",
        created_at=True,
    )


def create_app():
    """Create the Dash application."""
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    # Initialize database client
    db_client = get_postgres_client()

    # Store for session data
    app.layout = dbc.Container(
        [
            dcc.Store(id="comments-store"),
            dcc.Store(id="current-index", data=0),
            dcc.Store(id="session-start-time"),
            dcc.Store(id="labels-saved", data=0),
            dcc.Interval(id="timer-interval", interval=1000, n_intervals=0),
            # Header
            dbc.Row(
                [
                    dbc.Col(
                        html.H1("Manual Comment Labeler", className="text-center my-4"),
                        width=12,
                    )
                ]
            ),
            # Session controls
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "Start New Session",
                                id="start-session-btn",
                                color="success",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Load Comments",
                                id="load-comments-btn",
                                color="primary",
                                className="me-2",
                            ),
                        ],
                        width=6,
                    ),
                    dbc.Col(
                        [
                            html.Div(id="session-stats", className="text-end"),
                        ],
                        width=6,
                    ),
                ]
            ),
            html.Hr(),
            # Comment display
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(id="comment-display", className="mb-4"),
                        ],
                        width=12,
                    )
                ]
            ),
            # Labels
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4("Form Signals"),
                            dbc.Checklist(
                                id="form-signals",
                                options=[
                                    {"label": "In Form", "value": "in_form"},
                                    {"label": "Out of Form", "value": "out_of_form"},
                                ],
                                value=[],
                                inline=False,
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.H4("Performance Signals"),
                            dbc.Checklist(
                                id="performance-signals",
                                options=[
                                    {
                                        "label": "Better Than Show",
                                        "value": "better_than_show",
                                    },
                                    {
                                        "label": "Flattered by Result",
                                        "value": "flattered_by_result",
                                    },
                                ],
                                value=[],
                                inline=False,
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.H4("Attitude Signals"),
                            dbc.Checklist(
                                id="attitude-signals",
                                options=[
                                    {
                                        "label": "Positive Attitude",
                                        "value": "positive_attitude",
                                    },
                                    {
                                        "label": "Negative Attitude",
                                        "value": "negative_attitude",
                                    },
                                ],
                                value=[],
                                inline=False,
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.H4("Future Signals"),
                            dbc.Checklist(
                                id="future-signals",
                                options=[
                                    {
                                        "label": "To Look Out For",
                                        "value": "to_look_out_for",
                                    },
                                    {"label": "To Oppose", "value": "to_oppose"},
                                    {"label": "Improver", "value": "improver"},
                                    {"label": "Exposed", "value": "exposed"},
                                ],
                                value=[],
                                inline=False,
                            ),
                        ],
                        width=3,
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H4("Race Strength", className="mt-3"),
                            dbc.RadioItems(
                                id="race-strength",
                                options=[
                                    {"label": "No Signal", "value": "no_signal"},
                                    {"label": "Strong", "value": "strong"},
                                    {"label": "Average", "value": "average"},
                                    {"label": "Weak", "value": "weak"},
                                ],
                                value="no_signal",
                                inline=True,
                            ),
                        ],
                        width=12,
                    )
                ]
            ),
            html.Hr(),
            # Navigation
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Button(
                                "← Previous",
                                id="prev-btn",
                                color="secondary",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Skip",
                                id="skip-btn",
                                color="warning",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Save & Next →",
                                id="save-next-btn",
                                color="primary",
                                className="me-2",
                            ),
                        ],
                        width=12,
                        className="text-center",
                    )
                ]
            ),
            html.Div(id="save-feedback", className="text-center mt-3"),
        ],
        fluid=True,
    )

    # Callbacks
    @app.callback(
        Output("session-start-time", "data"),
        Output("labels-saved", "data", allow_duplicate=True),
        Input("start-session-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def start_session(n_clicks):
        if n_clicks:
            return time.time(), 0
        return dash.no_update, dash.no_update

    @app.callback(
        Output("comments-store", "data"),
        Output("current-index", "data", allow_duplicate=True),
        Input("load-comments-btn", "n_clicks"),
        State("comments-store", "data"),
        prevent_initial_call=True,
    )
    def load_comments(n_clicks, current_comments):
        if n_clicks:
            comments = fetch_unlabeled_comments(db_client, limit=50)
            return comments.to_dict("records"), 0
        return current_comments, dash.no_update

    @app.callback(
        Output("comment-display", "children"),
        Input("current-index", "data"),
        State("comments-store", "data"),
    )
    def display_comment(index, comments):
        if not comments or index >= len(comments):
            return html.Div(
                "No comments loaded. Click 'Load Comments' to start.",
                className="alert alert-info",
            )

        row = comments[index]
        comment_text = row.get("tf_comment") or row.get("rp_comment") or "No comment"

        # Get distance and convert to float for formatting and categorization
        distance_beaten = row.get("distance_beaten")
        try:
            distance_beaten_float = float(distance_beaten) if distance_beaten is not None else None
        except (ValueError, TypeError):
            distance_beaten_float = None

        # Format position like Gemini input with distance beaten
        position_text = format_position(
            row.get("finishing_position"),
            row.get("number_of_runners"),
            distance_beaten_float,
        )
        
        # Get distance category for badge
        dist_category = _distance_category(distance_beaten_float)
        
        # Color code the competitiveness badge
        if dist_category == "involved in finish":
            badge_color = "success"  # Green
        elif dist_category == "competitive":
            badge_color = "info"  # Blue
        elif dist_category == "fairly beaten":
            badge_color = "warning"  # Yellow
        elif dist_category == "well beaten":
            badge_color = "danger"  # Red
        else:
            badge_color = "secondary"  # Gray for no data
        
        # Build the full formatted input exactly as Gemini sees it
        parts = [position_text]
        if row.get("main_race_comment"):
            parts.append(f"[RACE]: {row.get('main_race_comment')}")
        parts.append(f"[HORSE]: {comment_text}")
        full_input = " | ".join(parts)

        return dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.H5(f"Comment {index + 1} of {len(comments)}", style={"display": "inline-block"}),
                            # Competitiveness badge
                            (
                                dbc.Badge(
                                    dist_category.upper(),
                                    color=badge_color,
                                    className="ms-3",
                                    style={"fontSize": "0.9em"}
                                )
                                if dist_category
                                else None
                            ),
                        ]
                    ),
                    html.P(
                        [
                            html.Strong("Horse: "),
                            row.get("horse_name", "Unknown"),
                            html.Br(),
                            html.Strong("Date: "),
                            str(row.get("race_date", "Unknown")),
                            html.Br(),
                            html.Strong("Distance Beaten: "),
                            f"{distance_beaten_float:.1f}L" if distance_beaten_float is not None else "N/A",
                        ]
                    ),
                    html.Hr(),
                    # Full formatted input as Gemini sees it
                    html.Div(
                        [
                            html.P("Gemini Input:", className="mb-1", style={"fontSize": "0.9em", "color": "#666"}),
                            html.P(
                                full_input,
                                className="mb-3 p-2",
                                style={
                                    "fontSize": "1.0em",
                                    "backgroundColor": "#f8f9fa",
                                    "border": "1px solid #dee2e6",
                                    "borderRadius": "4px",
                                    "fontFamily": "monospace",
                                },
                            ),
                        ]
                    ),
                    html.Hr(),
                    # Position styled like Gemini input
                    html.P(
                        [html.Strong(position_text)],
                        className="mb-2",
                        style={"fontSize": "1.1em", "color": "#0066cc"},
                    ),
                    # Race comment with [RACE] prefix
                    (
                        html.P(
                            [html.Strong("[RACE]: "), row.get("main_race_comment", "")],
                            className="mb-2",
                        )
                        if row.get("main_race_comment")
                        else None
                    ),
                    # Horse comment with [HORSE] prefix
                    html.P([html.Strong("[HORSE]: "), comment_text]),
                ]
            ),
            className="mb-3",
        )

    @app.callback(
        Output("current-index", "data", allow_duplicate=True),
        Output("form-signals", "value"),
        Output("performance-signals", "value"),
        Output("attitude-signals", "value"),
        Output("future-signals", "value"),
        Output("race-strength", "value"),
        Input("prev-btn", "n_clicks"),
        State("current-index", "data"),
        State("comments-store", "data"),
        prevent_initial_call=True,
    )
    def go_previous(n_clicks, index, comments):
        if n_clicks and index > 0:
            return index - 1, [], [], [], [], "no_signal"
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )

    @app.callback(
        Output("current-index", "data", allow_duplicate=True),
        Output("form-signals", "value", allow_duplicate=True),
        Output("performance-signals", "value", allow_duplicate=True),
        Output("attitude-signals", "value", allow_duplicate=True),
        Output("future-signals", "value", allow_duplicate=True),
        Output("race-strength", "value", allow_duplicate=True),
        Input("skip-btn", "n_clicks"),
        State("current-index", "data"),
        State("comments-store", "data"),
        prevent_initial_call=True,
    )
    def skip_comment(n_clicks, index, comments):
        if n_clicks and comments and index < len(comments) - 1:
            return index + 1, [], [], [], [], "no_signal"
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )

    @app.callback(
        Output("current-index", "data", allow_duplicate=True),
        Output("labels-saved", "data", allow_duplicate=True),
        Output("save-feedback", "children"),
        Output("form-signals", "value", allow_duplicate=True),
        Output("performance-signals", "value", allow_duplicate=True),
        Output("attitude-signals", "value", allow_duplicate=True),
        Output("future-signals", "value", allow_duplicate=True),
        Output("race-strength", "value", allow_duplicate=True),
        Input("save-next-btn", "n_clicks"),
        State("current-index", "data"),
        State("comments-store", "data"),
        State("form-signals", "value"),
        State("performance-signals", "value"),
        State("attitude-signals", "value"),
        State("future-signals", "value"),
        State("race-strength", "value"),
        State("labels-saved", "data"),
        prevent_initial_call=True,
    )
    def save_and_next(
        n_clicks,
        index,
        comments,
        form_signals,
        performance_signals,
        attitude_signals,
        future_signals,
        race_strength,
        labels_saved,
    ):
        if not n_clicks or not comments or index >= len(comments):
            return (
                dash.no_update,
                dash.no_update,
                "",
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
            )

        row = comments[index]
        unique_id = row["unique_id"]

        # Build labels dict
        labels = {
            "in_form": "in_form" in form_signals,
            "out_of_form": "out_of_form" in form_signals,
            "better_than_show": "better_than_show" in performance_signals,
            "flattered_by_result": "flattered_by_result" in performance_signals,
            "positive_attitude": "positive_attitude" in attitude_signals,
            "negative_attitude": "negative_attitude" in attitude_signals,
            "to_look_out_for": "to_look_out_for" in future_signals,
            "to_oppose": "to_oppose" in future_signals,
            "improver": "improver" in future_signals,
            "exposed": "exposed" in future_signals,
            "race_strength": race_strength,
        }

        try:
            save_label(db_client, unique_id, labels)
            new_labels_saved = labels_saved + 1
            feedback = dbc.Alert("✅ Saved!", color="success", duration=2000)

            # Move to next
            if index < len(comments) - 1:
                return (
                    index + 1,
                    new_labels_saved,
                    feedback,
                    [],
                    [],
                    [],
                    [],
                    "no_signal",
                )
            else:
                return (
                    index,
                    new_labels_saved,
                    dbc.Alert("All comments labeled!", color="info"),
                    [],
                    [],
                    [],
                    [],
                    "no_signal",
                )
        except Exception as e:
            return (
                dash.no_update,
                dash.no_update,
                dbc.Alert(f"❌ Error: {e}", color="danger"),
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update,
            )

    @app.callback(
        Output("session-stats", "children"),
        Input("timer-interval", "n_intervals"),
        State("session-start-time", "data"),
        State("labels-saved", "data"),
    )
    def update_stats(n_intervals, start_time, labels_saved):
        if not start_time:
            return "Session not started"

        elapsed = time.time() - start_time
        if elapsed < 1:
            return "Session started..."

        lpm = (labels_saved / elapsed) * 60 if elapsed > 0 else 0

        return html.Div(
            [
                html.P(
                    [
                        html.Strong("Time: "),
                        f"{elapsed/60:.1f} min",
                        html.Br(),
                        html.Strong("Labeled: "),
                        str(labels_saved),
                        html.Br(),
                        html.Strong("Rate: "),
                        f"{lpm:.1f}/min",
                    ],
                    className="mb-0",
                )
            ]
        )

    return app


def run_manual_labeling(port: int = 8050):
    """Run the manual labeling Dash dashboard."""
    app = create_app()
    print(f"\n🚀 Starting manual labeler dashboard at http://localhost:{port}")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manual comment labeler dashboard")
    parser.add_argument("--port", type=int, default=8050, help="Dashboard port")

    args = parser.parse_args()

    run_manual_labeling(port=args.port)
