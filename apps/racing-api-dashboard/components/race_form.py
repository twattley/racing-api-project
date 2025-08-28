from dash import html
import pandas as pd

from services.base_service import race_form


def render_race_form(race_id: int):
    # Fetch once
    data = race_form(race_id)
    race_details = (
        data.race_details.iloc[0].to_dict() if not data.race_details.empty else {}
    )
    horses = data.horse_race_info.to_dict("records")
    form_rows = data.race_form

    # Pretty label maps for summary and today rows
    summary_fields = [
        ("Horse", "horse_name"),
        ("Headgear", "headgear"),
        ("Age", "age"),
        ("OR", "official_rating"),
        ("Wgt (lbs)", "weight_carried_lbs"),
        ("Win SP", "betfair_win_sp"),
        ("Place SP", "betfair_place_sp"),
        ("Win%", "win_percentage"),
        ("Place%", "place_percentage"),
        ("Runs", "number_of_runs"),
    ]
    today_fields = [
        ("Course", "course"),
        ("Dist", "distance"),
        ("Going", "going"),
        ("Cond.", "conditions"),
        ("Class", "race_class"),
        ("Hcap", "hcap_range"),
        ("Age", "age_range"),
        ("1st £", "first_place_prize_money"),
        ("Type", "race_type"),
        ("Surf.", "surface"),
    ]

    def key_value_row(pairs: list[tuple[str, str]], source: dict):
        # Render pairs as compact key: value cells
        return html.Tr(
            [
                html.Td(
                    [
                        html.Span(f"{label}: ", style={"fontWeight": "600"}),
                        html.Span("" if pd.isna(source.get(key, "")) else source.get(key, "")),
                    ]
                )
                for (label, key) in pairs
            ],
            style={"background": "#f8fafc"},
        )

    def horse_block(horse: dict):
        # Per-horse: summary, today's race, DataTable (last 5), comments
        h_id = horse["horse_id"]
        horse_form = form_rows[form_rows["horse_id"] == h_id].head(5)

        # --- Historical form as stacked blocks with merged comment row ---
        hist_details = [
            ("Date", "race_date"),
            ("Course", "course"),
            ("Dist", "distance"),
            ("Going", "going"),
            ("Class", "race_class"),
        ]
        hist_perf = [
            ("Pos", "position_of_runners"),
            ("Beaten", "distance_beaten_signed"),
            ("SP", "betfair_win_sp"),
            ("Weeks", "total_weeks_since_run"),
            ("Headgear", "headgear"),
        ]

        def fmt(v):
            return "" if pd.isna(v) else v

        hist_rows: list = []
        if not horse_form.empty:
            for _, r in horse_form.iterrows():
                # First row: details
                hist_rows.append(
                    html.Tr(
                        [
                            html.Td(
                                [
                                    html.Span(f"{label}: ", style={"fontWeight": 600}),
                                    html.Span(fmt(r.get(key))),
                                ]
                            )
                            for (label, key) in hist_details
                        ],
                        style={"background": "#f9fafb"},
                    )
                )
                # Second row: performance
                hist_rows.append(
                    html.Tr(
                        [
                            html.Td(
                                [
                                    html.Span(f"{label}: ", style={"fontWeight": 600}),
                                    html.Span(fmt(r.get(key))),
                                ]
                            )
                            for (label, key) in hist_perf
                        ]
                    )
                )
                # Third row: merged comments
                comment_bits: list[str] = []
                for k in ("tf_comment", "rp_comment", "main_race_comment"):
                    val = r.get(k)
                    if not pd.isna(val) and str(val).strip():
                        comment_bits.append(str(val))
                hist_rows.append(
                    html.Tr(
                        [
                            html.Td(
                                html.Div(
                                    [html.Div(c) for c in comment_bits] or [html.Div("")],
                                    style={
                                        "fontStyle": "italic",
                                        "background": "#f6fafd",
                                        "padding": "0.5rem",
                                    },
                                ),
                                colSpan=len(hist_details),
                            )
                        ]
                    )
                )

        return html.Div(
            [
                html.H4(horse.get("horse_name", ""), style={"marginTop": "1.5rem"}),
                html.Table(
                    [
                        key_value_row(summary_fields, horse),
                        key_value_row(today_fields, race_details),
                    ],
                    style={
                        "width": "100%",
                        "marginBottom": "0.75rem",
                        "borderCollapse": "collapse",
                        "border": "1px solid #e5e7eb",
                    },
                ),
                html.Table(
                    hist_rows,
                    style={
                        "width": "100%",
                        "borderCollapse": "collapse",
                        "border": "1px solid #e5e7eb",
                        "marginBottom": "0.75rem",
                    },
                ),
            ]
        )

    return html.Div(
        [html.H3("Race Form"), *(horse_block(h) for h in horses)],
        style={"padding": "16px"},
    )