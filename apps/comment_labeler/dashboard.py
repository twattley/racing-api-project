"""
Simple Dash app for reviewing Gemini-labeled comments.
"""

import json
from pathlib import Path

from dash import Dash, html, dcc, callback, Output, Input, State

# Paths
BASE_DIR = Path(__file__).parent
LABELED_PATH = BASE_DIR / "labeled.jsonl"
GOLDSTANDARD_PATH = BASE_DIR / "goldstandard.jsonl"
CHECKPOINT_PATH = BASE_DIR / ".checkpoint"


def load_data():
    """Load labeled data."""
    if not LABELED_PATH.exists():
        return []
    with open(LABELED_PATH) as f:
        return [json.loads(line) for line in f]


def load_goldstandard():
    """Load in goldstandard data."""
    if not GOLDSTANDARD_PATH.exists():
        return {}
    with open(GOLDSTANDARD_PATH) as f:
        return {json.loads(line)["formatted_input"]: json.loads(line) for line in f}


def save_goldstandard(data: dict):
    """Save reviewed item."""
    reviewed = load_goldstandard()
    reviewed[data["formatted_input"]] = data
    with open(GOLDSTANDARD_PATH, "w") as f:
        for item in reviewed.values():
            f.write(json.dumps(item) + "\n")


def load_checkpoint():
    """Load last position from checkpoint file."""
    if CHECKPOINT_PATH.exists():
        return int(CHECKPOINT_PATH.read_text().strip())
    return 0


def save_checkpoint(idx: int):
    """Save current position to checkpoint file."""
    CHECKPOINT_PATH.write_text(str(idx))


# Load initial data
all_data = load_data()
goldstandard_data = load_goldstandard()
start_position = load_checkpoint()

# App
app = Dash(__name__)

app.layout = html.Div(
    [
        html.H1("🏇 Comment Labeler Review", style={"textAlign": "center"}),
        # Progress bar
        html.Div(
            [
                html.Span(id="progress-text"),
                dcc.Slider(
                    id="item-slider",
                    min=0,
                    max=len(all_data) - 1,
                    step=1,
                    value=start_position,
                    marks={
                        i: str(i + 1)
                        for i in range(0, len(all_data), max(1, len(all_data) // 10))
                    },
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
                            id="result-display",
                            style={
                                "fontSize": "18px",
                                "fontWeight": "bold",
                                "marginBottom": "15px",
                            },
                        ),
                        html.H3("📋 Race Comment"),
                        html.Div(
                            id="race-comment",
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
                            id="horse-comment",
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
                                    id="in-form",
                                    options=[{"label": " in_form", "value": "in_form"}],
                                    value=[],
                                    style={"fontSize": "16px"},
                                ),
                                dcc.Checklist(
                                    id="out-of-form",
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
                                    id="better-than-show",
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
                                    id="worse-than-show",
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
                            id="race-strength",
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
                            id="reasoning",
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
                                    id="prev-btn",
                                    n_clicks=0,
                                    style={"marginRight": "10px"},
                                ),
                                html.Button(
                                    "✅ Submit & Next",
                                    id="submit-btn",
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
                                    id="next-btn",
                                    n_clicks=0,
                                    style={"marginLeft": "10px"},
                                ),
                            ],
                            style={"textAlign": "center"},
                        ),
                        html.Div(
                            id="status-message",
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
        # Hidden store for current index
        dcc.Store(id="current-index", data=0),
    ],
    style={"maxWidth": "1400px", "margin": "0 auto", "padding": "20px"},
)


@callback(
    [
        Output("result-display", "children"),
        Output("race-comment", "children"),
        Output("horse-comment", "children"),
        Output("in-form", "value"),
        Output("out-of-form", "value"),
        Output("better-than-show", "value"),
        Output("worse-than-show", "value"),
        Output("race-strength", "value"),
        Output("reasoning", "value"),
        Output("progress-text", "children"),
    ],
    [Input("item-slider", "value")],
)
def update_display(idx):
    """Update display when slider changes."""
    if not all_data or idx >= len(all_data):
        return "", "", "", [], [], [], [], "no_signal", "", "No data"

    item = all_data[idx]

    # Check if in goldstandard - use those values
    if item["formatted_input"] in goldstandard_data:
        item = goldstandard_data[item["formatted_input"]]

    # Parse formatted_input
    parts = item["formatted_input"].split(" | ")
    result = parts[0] if parts else ""
    race_comment = ""
    horse_comment = ""

    for part in parts[1:]:
        if part.startswith("[RACE]:"):
            race_comment = part[7:].strip()
        elif part.startswith("[HORSE]:"):
            horse_comment = part[8:].strip()

    # Get label values
    in_form = ["in_form"] if item.get("in_form") else []
    out_of_form = ["out_of_form"] if item.get("out_of_form") else []
    better = ["better_than_show"] if item.get("better_than_show") else []
    worse = ["worse_than_show"] if item.get("worse_than_show") else []

    # Progress
    reviewed_count = len(goldstandard_data)
    progress = f"Goldstandard: {reviewed_count}/{len(all_data)} | Current: #{idx + 1}"

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
        Output("item-slider", "value"),
        Output("status-message", "children"),
        Output("current-index", "data"),
    ],
    [
        Input("submit-btn", "n_clicks"),
        Input("prev-btn", "n_clicks"),
        Input("next-btn", "n_clicks"),
    ],
    [
        State("item-slider", "value"),
        State("in-form", "value"),
        State("out-of-form", "value"),
        State("better-than-show", "value"),
        State("worse-than-show", "value"),
        State("race-strength", "value"),
        State("reasoning", "value"),
        State("current-index", "data"),
    ],
    prevent_initial_call=True,
)
def handle_buttons(
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
    stored_idx,
):
    """Handle button clicks."""
    from dash import ctx

    if not all_data:
        return 0, "", 0

    triggered = ctx.triggered_id

    if triggered == "prev-btn":
        new_idx = max(0, idx - 1)
        save_checkpoint(new_idx)
        return new_idx, "", new_idx

    elif triggered == "next-btn":
        new_idx = min(len(all_data) - 1, idx + 1)
        save_checkpoint(new_idx)
        return new_idx, "", new_idx

    elif triggered == "submit-btn":
        # Save current item
        item = all_data[idx].copy()
        item["in_form"] = "in_form" in in_form
        item["out_of_form"] = "out_of_form" in out_of_form
        item["better_than_show"] = "better_than_show" in better
        item["worse_than_show"] = "worse_than_show" in worse
        item["race_strength"] = race_strength
        item["reasoning"] = reasoning

        save_goldstandard(item)

        # Reload reviewed data
        global goldstandard_data
        goldstandard_data = load_goldstandard()

        # Move to next
        new_idx = min(len(all_data) - 1, idx + 1)
        save_checkpoint(new_idx)
        return new_idx, f"✅ Saved #{idx + 1}!", new_idx

    return idx, "", idx


if __name__ == "__main__":
    checkpoint_pos = load_checkpoint()
    print(f"\n📊 Loaded {len(all_data)} examples from {LABELED_PATH}")
    print(f"✅ {len(goldstandard_data)} in goldstandard in {GOLDSTANDARD_PATH}")
    print(f"📍 Resuming from position {checkpoint_pos + 1}")
    print(f"\n🚀 Starting dashboard at http://127.0.0.1:8050\n")
    app.run(debug=True)
