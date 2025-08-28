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

    def val(x):
        return "" if pd.isna(x) else x

    def horse_block(horse: dict):
        # Per-horse: summary, today's race, historical (custom HTML tables)
        h_id = horse["horse_id"]
        horse_form = form_rows[form_rows["horse_id"] == h_id]

        # --- Historical form in DataTable ---
        # Remove race_date; include comments as a single column; headers hidden.
        # Try to make details 5 columns by appending a filler key if available.
        base_detail_keys = ["course", "distance", "going", "race_class"]
        extra_detail_key = None
        for k in ("surface", "conditions"):
            if k in horse_form.columns:
                extra_detail_key = k
                break
        detail_keys = base_detail_keys + [extra_detail_key]  # extra may be None

        perf_keys = [
            "position_of_runners",
            "distance_beaten_signed",
            "betfair_win_sp",
            "total_weeks_since_run",
            "headgear",
        ]
        # Build historical rows (two data rows + merged comment row per entry)
        def build_hist_rows():
            rows = []
            if horse_form.empty:
                return rows
            for _, r in horse_form.iterrows():
                # Details row
                rows.append(
                    html.Tr(
                        [
                            html.Td(val(r.get(k)) if k else "", className="border p-2")
                            for k in detail_keys
                        ],
                        className="table-light",
                    )
                )
                # Performance row
                rows.append(
                    html.Tr(
                        [
                            html.Td(val(r.get(k)), className="border p-2")
                            for k in perf_keys
                        ]
                    )
                )
                # Merged comments row
                comments = []
                for k in ("tf_comment", "rp_comment", "main_race_comment"):
                    v = r.get(k)
                    if not pd.isna(v) and str(v).strip():
                        comments.append(str(v))
                rows.append(
                    html.Tr(
                        [
                            html.Td(
                                html.Div(
                                    [html.Div(c) for c in comments] or [html.Div("")],
                                    className="fst-italic bg-body-secondary p-2",
                                ),
                                colSpan=max(len(detail_keys), len(perf_keys)),
                                className="border",
                            )
                        ]
                    )
                )
            return rows

        # Build summary and today's tables as compact HTML tables (no labels, values only)
        summary_vals = [val(horse.get(key)) for (_, key) in summary_fields]
        today_vals = [val(race_details.get(key)) for (_, key) in today_fields]

        return html.Div(
            [
                html.H4(horse.get("horse_name", ""), className="mt-4"),
                html.Table(
                    [html.Tr([html.Td(v, className="border p-2 text-center") for v in summary_vals], className="table-light")],
                    className="table table-sm w-100 mb-2",
                    style={"borderCollapse": "collapse"},
                ),
                html.Table(
                    [html.Tr([html.Td(v, className="border p-2 text-center") for v in today_vals], className="table-primary")],
                    className="table table-sm w-100 mb-2",
                    style={"borderCollapse": "collapse"},
                ),
                html.Div(
                    html.Table(
                        build_hist_rows(),
                        className="table table-sm w-100",
                        style={"borderCollapse": "collapse"},
                    ),
                    style={"maxHeight": "16rem", "overflowY": "auto", "marginBottom": "0.75rem", "border": "1px solid #e5e7eb"},
                    className="rounded",
                ),
            ]
        )

    return html.Div(
        [html.H3("Race Form", className="mb-3"), *(horse_block(h) for h in horses)],
        className="p-3",
    )