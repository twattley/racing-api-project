"""
Dash app for reviewing labeled comments with tabs for Gemini and Model predictions.
"""

import json
from pathlib import Path

from dash import Dash, html, dcc, callback, Output, Input, State

# Paths
BASE_DIR = Path(__file__).parent
LABELED_PATH = BASE_DIR / "labeled.jsonl"
PREDICTIONS_PATH = BASE_DIR / "predictions.jsonl"
GOLDSTANDARD_PATH = BASE_DIR / "goldstandard.jsonl"
CHECKPOINT_GEMINI_PATH = BASE_DIR / ".checkpoint-gemini"
CHECKPOINT_PREDICTIONS_PATH = BASE_DIR / ".checkpoint-predictions"


# Data loading functions
def load_jsonl(path: Path) -> list[dict]:
    """Load data from JSONL file."""
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f]


def load_goldstandard() -> dict:
    """Load goldstandard data keyed by formatted_input."""
    if not GOLDSTANDARD_PATH.exists():
        return {}
    with open(GOLDSTANDARD_PATH) as f:
        return {json.loads(line)["formatted_input"]: json.loads(line) for line in f}


def save_goldstandard(data: dict):
    """Save item to goldstandard (upserts by formatted_input)."""
    reviewed = load_goldstandard()
    reviewed[data["formatted_input"]] = data
    with open(GOLDSTANDARD_PATH, "w") as f:
        for item in reviewed.values():
            f.write(json.dumps(item) + "\n")


def load_checkpoint(path: Path) -> int:
    """Load checkpoint position."""
    if path.exists():
        return int(path.read_text().strip())
    return 0


def save_checkpoint(path: Path, idx: int):
    """Save checkpoint position."""
    path.write_text(str(idx))


def parse_formatted_input(formatted_input: str) -> tuple[str, str, str]:
    """Parse formatted input into result, race comment, horse comment."""
    parts = formatted_input.split(" | ")
    result = parts[0] if parts else ""
    race_comment = ""
    horse_comment = ""

    for part in parts[1:]:
        if part.startswith("[RACE]:"):
            race_comment = part[7:].strip()
        elif part.startswith("[HORSE]:"):
            horse_comment = part[8:].strip()

    return result, race_comment, horse_comment


def create_review_panel(tab_id: str) -> html.Div:
    """Create a review panel for a tab."""
    return html.Div(
        [
            # Progress
            html.Div(
                [
                    html.Span(id=f"progress-{tab_id}"),
                    dcc.Slider(
                        id=f"slider-{tab_id}",
                        min=0,
                        max=0,
                        step=1,
                        value=0,
                        marks={},
                    ),
                ],
                style={"margin": "20px"},
            ),
            # Main content
            html.Div(
                [
                    # Left: Comment display
                    html.Div(
                        [
                            html.H3("📊 Result"),
                            html.Div(
                                id=f"result-{tab_id}",
                                style={
                                    "fontSize": "18px",
                                    "fontWeight": "bold",
                                    "marginBottom": "15px",
                                },
                            ),
                            html.H3("📋 Race Comment"),
                            html.Div(
                                id=f"race-comment-{tab_id}",
                                style={
                                    "backgroundColor": "#f5f5f5",
                                    "padding": "15px",
                                    "borderRadius": "8px",
                                    "marginBottom": "15px",
                                    "whiteSpace": "pre-wrap",
                                },
                            ),
                            html.H3("🐴 Horse Comment"),
                            html.Div(
                                id=f"horse-comment-{tab_id}",
                                style={
                                    "backgroundColor": "#e8f4e8",
                                    "padding": "15px",
                                    "borderRadius": "8px",
                                    "whiteSpace": "pre-wrap",
                                },
                            ),
                        ],
                        style={"width": "60%", "padding": "20px"},
                    ),
                    # Right: Labels
                    html.Div(
                        [
                            html.H3("🏷️ Labels"),
                            html.Div(
                                [
                                    dcc.Checklist(
                                        id=f"in-form-{tab_id}",
                                        options=[
                                            {"label": " in_form", "value": "in_form"}
                                        ],
                                        value=[],
                                        style={"fontSize": "16px"},
                                    ),
                                    dcc.Checklist(
                                        id=f"out-of-form-{tab_id}",
                                        options=[
                                            {
                                                "label": " out_of_form",
                                                "value": "out_of_form",
                                            }
                                        ],
                                        value=[],
                                        style={"fontSize": "16px"},
                                    ),
                                    dcc.Checklist(
                                        id=f"better-than-show-{tab_id}",
                                        options=[
                                            {
                                                "label": " better_than_show",
                                                "value": "better_than_show",
                                            }
                                        ],
                                        value=[],
                                        style={"fontSize": "16px"},
                                    ),
                                    dcc.Checklist(
                                        id=f"worse-than-show-{tab_id}",
                                        options=[
                                            {
                                                "label": " worse_than_show",
                                                "value": "worse_than_show",
                                            }
                                        ],
                                        value=[],
                                        style={"fontSize": "16px"},
                                    ),
                                ],
                                style={"marginBottom": "20px"},
                            ),
                            html.Label("Race Strength:", style={"fontWeight": "bold"}),
                            dcc.RadioItems(
                                id=f"race-strength-{tab_id}",
                                options=[
                                    {"label": "Strong", "value": "strong"},
                                    {"label": "Average", "value": "average"},
                                    {"label": "Weak", "value": "weak"},
                                    {"label": "No Signal", "value": "no_signal"},
                                ],
                                value="no_signal",
                                style={"marginBottom": "20px"},
                            ),
                            html.Label("Reasoning:", style={"fontWeight": "bold"}),
                            dcc.Textarea(
                                id=f"reasoning-{tab_id}",
                                style={
                                    "width": "100%",
                                    "height": "120px",
                                    "marginBottom": "20px",
                                },
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "⬅️ Prev",
                                        id=f"prev-{tab_id}",
                                        n_clicks=0,
                                        style={"marginRight": "10px"},
                                    ),
                                    html.Button(
                                        "✅ Submit & Next",
                                        id=f"submit-{tab_id}",
                                        n_clicks=0,
                                        style={
                                            "backgroundColor": "#4CAF50",
                                            "color": "white",
                                            "fontWeight": "bold",
                                            "padding": "10px 20px",
                                        },
                                    ),
                                    html.Button(
                                        "➡️ Skip",
                                        id=f"next-{tab_id}",
                                        n_clicks=0,
                                        style={"marginLeft": "10px"},
                                    ),
                                ],
                                style={"textAlign": "center"},
                            ),
                            html.Div(
                                id=f"status-{tab_id}",
                                style={
                                    "marginTop": "15px",
                                    "textAlign": "center",
                                    "color": "green",
                                },
                            ),
                        ],
                        style={
                            "width": "35%",
                            "padding": "20px",
                            "backgroundColor": "#fafafa",
                            "borderRadius": "8px",
                        },
                    ),
                ],
                style={"display": "flex", "gap": "20px"},
            ),
        ]
    )


# Load initial data
gemini_data = load_jsonl(LABELED_PATH)
predictions_data = load_jsonl(PREDICTIONS_PATH)
goldstandard_data = load_goldstandard()

# App
app = Dash(__name__)

app.layout = html.Div(
    [
        html.H1("🏇 Comment Labeler Review", style={"textAlign": "center"}),
        dcc.Tabs(
            id="tabs",
            value="gemini",
            children=[
                dcc.Tab(
                    label=f"📝 Gemini Review ({len(gemini_data)})",
                    value="gemini",
                    children=[create_review_panel("gemini")],
                ),
                dcc.Tab(
                    label=f"🤖 Model Predictions ({len(predictions_data)})",
                    value="predictions",
                    children=[create_review_panel("predictions")],
                ),
            ],
        ),
        # Hidden stores
        dcc.Store(id="goldstandard-store", data=list(goldstandard_data.keys())),
    ],
    style={"maxWidth": "1400px", "margin": "0 auto", "padding": "20px"},
)


# Initialize sliders on load
@callback(
    [
        Output("slider-gemini", "max"),
        Output("slider-gemini", "marks"),
        Output("slider-gemini", "value"),
        Output("slider-predictions", "max"),
        Output("slider-predictions", "marks"),
        Output("slider-predictions", "value"),
    ],
    [Input("tabs", "value")],
)
def init_sliders(_):
    """Initialize slider ranges on app load."""
    gemini_max = max(0, len(gemini_data) - 1)
    gemini_marks = {
        i: str(i + 1)
        for i in range(0, len(gemini_data), max(1, len(gemini_data) // 10))
    }
    gemini_pos = load_checkpoint(CHECKPOINT_GEMINI_PATH)

    pred_max = max(0, len(predictions_data) - 1)
    pred_marks = {
        i: str(i + 1)
        for i in range(0, len(predictions_data), max(1, len(predictions_data) // 10))
    }
    pred_pos = load_checkpoint(CHECKPOINT_PREDICTIONS_PATH)

    return gemini_max, gemini_marks, gemini_pos, pred_max, pred_marks, pred_pos


# Gemini tab callbacks
@callback(
    [
        Output("result-gemini", "children"),
        Output("race-comment-gemini", "children"),
        Output("horse-comment-gemini", "children"),
        Output("in-form-gemini", "value"),
        Output("out-of-form-gemini", "value"),
        Output("better-than-show-gemini", "value"),
        Output("worse-than-show-gemini", "value"),
        Output("race-strength-gemini", "value"),
        Output("reasoning-gemini", "value"),
        Output("progress-gemini", "children"),
    ],
    [Input("slider-gemini", "value")],
)
def update_gemini_display(idx):
    """Update Gemini tab display."""
    if not gemini_data or idx >= len(gemini_data):
        return "", "", "", [], [], [], [], "no_signal", "", "No data"

    item = gemini_data[idx]

    # Check goldstandard for existing values
    gs = load_goldstandard()
    if item["formatted_input"] in gs:
        item = gs[item["formatted_input"]]

    result, race_comment, horse_comment = parse_formatted_input(item["formatted_input"])

    in_form = ["in_form"] if item.get("in_form") else []
    out_of_form = ["out_of_form"] if item.get("out_of_form") else []
    better = ["better_than_show"] if item.get("better_than_show") else []
    worse = ["worse_than_show"] if item.get("worse_than_show") else []

    progress = f"Goldstandard: {len(gs)}/{len(gemini_data)} | Current: #{idx + 1}"

    return (
        result,
        race_comment,
        horse_comment,
        in_form,
        out_of_form,
        better,
        worse,
        item.get("race_strength", "no_signal"),
        item.get("reasoning", ""),
        progress,
    )


@callback(
    [
        Output("slider-gemini", "value", allow_duplicate=True),
        Output("status-gemini", "children"),
    ],
    [
        Input("submit-gemini", "n_clicks"),
        Input("prev-gemini", "n_clicks"),
        Input("next-gemini", "n_clicks"),
    ],
    [
        State("slider-gemini", "value"),
        State("in-form-gemini", "value"),
        State("out-of-form-gemini", "value"),
        State("better-than-show-gemini", "value"),
        State("worse-than-show-gemini", "value"),
        State("race-strength-gemini", "value"),
        State("reasoning-gemini", "value"),
    ],
    prevent_initial_call=True,
)
def handle_gemini_buttons(
    submit_clicks,
    prev_clicks,
    next_clicks,
    idx,
    in_form,
    out_of_form,
    better,
    worse,
    race_strength,
    reasoning,
):
    """Handle Gemini tab button clicks."""
    from dash import ctx

    if not gemini_data:
        return 0, ""

    triggered = ctx.triggered_id

    if triggered == "prev-gemini":
        new_idx = max(0, idx - 1)
        save_checkpoint(CHECKPOINT_GEMINI_PATH, new_idx)
        return new_idx, ""

    elif triggered == "next-gemini":
        new_idx = min(len(gemini_data) - 1, idx + 1)
        save_checkpoint(CHECKPOINT_GEMINI_PATH, new_idx)
        return new_idx, ""

    elif triggered == "submit-gemini":
        item = gemini_data[idx].copy()
        item["in_form"] = "in_form" in in_form
        item["out_of_form"] = "out_of_form" in out_of_form
        item["better_than_show"] = "better_than_show" in better
        item["worse_than_show"] = "worse_than_show" in worse
        item["race_strength"] = race_strength
        item["reasoning"] = reasoning

        save_goldstandard(item)

        new_idx = min(len(gemini_data) - 1, idx + 1)
        save_checkpoint(CHECKPOINT_GEMINI_PATH, new_idx)
        return new_idx, f"✅ Saved #{idx + 1}!"

    return idx, ""


# Predictions tab callbacks
@callback(
    [
        Output("result-predictions", "children"),
        Output("race-comment-predictions", "children"),
        Output("horse-comment-predictions", "children"),
        Output("in-form-predictions", "value"),
        Output("out-of-form-predictions", "value"),
        Output("better-than-show-predictions", "value"),
        Output("worse-than-show-predictions", "value"),
        Output("race-strength-predictions", "value"),
        Output("reasoning-predictions", "value"),
        Output("progress-predictions", "children"),
    ],
    [Input("slider-predictions", "value")],
)
def update_predictions_display(idx):
    """Update Predictions tab display."""
    if not predictions_data or idx >= len(predictions_data):
        return "", "", "", [], [], [], [], "no_signal", "", "No predictions - run: python -m apps.comment_labeler.cli predict"

    item = predictions_data[idx]

    # Check goldstandard for existing values
    gs = load_goldstandard()
    if item["formatted_input"] in gs:
        item = gs[item["formatted_input"]]

    result, race_comment, horse_comment = parse_formatted_input(item["formatted_input"])

    in_form = ["in_form"] if item.get("in_form") else []
    out_of_form = ["out_of_form"] if item.get("out_of_form") else []
    better = ["better_than_show"] if item.get("better_than_show") else []
    worse = ["worse_than_show"] if item.get("worse_than_show") else []

    progress = f"Predictions: {len(predictions_data)} | Current: #{idx + 1}"

    return (
        result,
        race_comment,
        horse_comment,
        in_form,
        out_of_form,
        better,
        worse,
        item.get("race_strength", "no_signal"),
        item.get("reasoning", ""),
        progress,
    )


@callback(
    [
        Output("slider-predictions", "value", allow_duplicate=True),
        Output("status-predictions", "children"),
    ],
    [
        Input("submit-predictions", "n_clicks"),
        Input("prev-predictions", "n_clicks"),
        Input("next-predictions", "n_clicks"),
    ],
    [
        State("slider-predictions", "value"),
        State("in-form-predictions", "value"),
        State("out-of-form-predictions", "value"),
        State("better-than-show-predictions", "value"),
        State("worse-than-show-predictions", "value"),
        State("race-strength-predictions", "value"),
        State("reasoning-predictions", "value"),
    ],
    prevent_initial_call=True,
)
def handle_predictions_buttons(
    submit_clicks,
    prev_clicks,
    next_clicks,
    idx,
    in_form,
    out_of_form,
    better,
    worse,
    race_strength,
    reasoning,
):
    """Handle Predictions tab button clicks."""
    from dash import ctx

    if not predictions_data:
        return 0, ""

    triggered = ctx.triggered_id

    if triggered == "prev-predictions":
        new_idx = max(0, idx - 1)
        save_checkpoint(CHECKPOINT_PREDICTIONS_PATH, new_idx)
        return new_idx, ""

    elif triggered == "next-predictions":
        new_idx = min(len(predictions_data) - 1, idx + 1)
        save_checkpoint(CHECKPOINT_PREDICTIONS_PATH, new_idx)
        return new_idx, ""

    elif triggered == "submit-predictions":
        item = predictions_data[idx].copy()
        item["in_form"] = "in_form" in in_form
        item["out_of_form"] = "out_of_form" in out_of_form
        item["better_than_show"] = "better_than_show" in better
        item["worse_than_show"] = "worse_than_show" in worse
        item["race_strength"] = race_strength
        item["reasoning"] = reasoning

        save_goldstandard(item)

        new_idx = min(len(predictions_data) - 1, idx + 1)
        save_checkpoint(CHECKPOINT_PREDICTIONS_PATH, new_idx)
        return new_idx, f"✅ Saved #{idx + 1}!"

    return idx, ""


if __name__ == "__main__":
    gemini_pos = load_checkpoint(CHECKPOINT_GEMINI_PATH)
    pred_pos = load_checkpoint(CHECKPOINT_PREDICTIONS_PATH)

    print(f"\n📊 Gemini: {len(gemini_data)} examples (position {gemini_pos + 1})")
    print(f"🤖 Predictions: {len(predictions_data)} examples (position {pred_pos + 1})")
    print(f"✅ Goldstandard: {len(goldstandard_data)} total")
    print(f"\n🚀 Starting dashboard at http://127.0.0.1:8050\n")
    app.run(debug=True)
