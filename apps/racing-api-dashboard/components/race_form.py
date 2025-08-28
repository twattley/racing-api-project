from dash import html, dcc, callback, Input, Output, State
import pandas as pd

from services.base_service import race_form


def render_race_form(race_id: int):
    # Initial detailed content; callbacks will toggle compact view
    initial_children = _build_detailed_view(race_id)

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
        # Resolve fresh data to ensure callback reuse is simple
        data = race_form(race_id)
        race_details = (
            data.race_details.iloc[0].to_dict() if not data.race_details.empty else {}
        )
        horses = data.horse_race_info.to_dict("records")
        form_rows = data.race_form
        horse_form = form_rows[form_rows["horse_id"] == h_id]

        # --- Historical form in DataTable ---
        # Remove race_date; include comments as a single column; headers hidden.
        # Unify detail keys to match today's row layout for quick comparison
        detail_keys = [
            "course",
            "distance",
            "going",
            "conditions",
            "race_class",
            "hcap_range",
            "age_range",
            "first_place_prize_money",
            "race_type",
            "surface",
        ]

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
        [
            html.Div(
                [
                    html.Button(
                        "Toggle compact",
                        id="race-form-view-toggle",
                        className="btn btn-outline-secondary btn-sm ms-auto",
                        n_clicks=0,
                    )
                ],
                className="d-flex mb-2",
            ),
            dcc.Store(id="race-form-compact-store", data=False),
            dcc.Store(id="race-form-race-id", data=race_id),
            html.Div(initial_children, id="race-form-content"),
        ],
        className="p-3",
    )


def _get_race_data(race_id: int):
    data = race_form(race_id)
    race_details = (
        data.race_details.iloc[0].to_dict() if not data.race_details.empty else {}
    )
    horses = data.horse_race_info.to_dict("records")
    form_rows = data.race_form
    return race_details, horses, form_rows


def _build_detailed_view(race_id: int):
    race_details, horses, form_rows = _get_race_data(race_id)

    def val(x):
        return "" if pd.isna(x) else x

    def horse_block(horse: dict):
        h_id = horse["horse_id"]
        horse_form = form_rows[form_rows["horse_id"] == h_id]

        detail_keys = [
            "course",
            "distance",
            "going",
            "conditions",
            "race_class",
            "hcap_range",
            "age_range",
            "first_place_prize_money",
            "race_type",
            "surface",
        ]
        perf_keys = [
            "position_of_runners",
            "distance_beaten_signed",
            "betfair_win_sp",
            "total_weeks_since_run",
            "headgear",
        ]
        col_count = len(detail_keys)

        def build_hist_rows():
            rows = []
            if horse_form.empty:
                return rows
            for _, r in horse_form.iterrows():
                # Details
                rows.append(
                    html.Tr(
                        [html.Td(val(r.get(k)), className="border p-2 text-center") for k in detail_keys],
                        className="table-light",
                    )
                )
                # Performance padded to match column count
                perf_cells = [
                    html.Td(val(r.get(k)), className="border p-2 text-center") for k in perf_keys
                ]
                if len(perf_cells) < col_count:
                    perf_cells += [html.Td("", className="border p-2")] * (col_count - len(perf_cells))
                rows.append(html.Tr(perf_cells))

                # Comments merged row
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
                                colSpan=col_count,
                                className="border",
                            )
                        ]
                    )
                )
            return rows

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
        summary_vals = [val(horse.get(key)) for (_, key) in summary_fields]
        today_vals = [val(race_details.get(k)) for k in detail_keys]

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

    race_details, horses, _ = _get_race_data(race_id)
    return [html.H3("Race Form", className="mb-3"), *(horse_block(h) for h in horses)]


def _build_compact_view(race_id: int):
    race_details, horses, _ = _get_race_data(race_id)

    rows = []
    for h in horses:
        rows.append(
            html.Tr(
                [
                    html.Td(h.get("horse_name", ""), className="border p-2"),
                    html.Td(h.get("betfair_win_sp", ""), className="border p-2 text-center"),
                ]
            )
        )

    table = html.Table(
        rows,
        className="table table-sm w-100",
        style={"borderCollapse": "collapse"},
    )
    return [html.H3("Race Form (compact)", className="mb-3"), table]


@callback(
    Output("race-form-compact-store", "data"),
    Input("race-form-view-toggle", "n_clicks"),
    State("race-form-compact-store", "data"),
    prevent_initial_call=True,
)
def _toggle_compact(n_clicks, compact):
    return not compact if n_clicks else compact


@callback(
    Output("race-form-content", "children"),
    Input("race-form-compact-store", "data"),
    State("race-form-race-id", "data"),
)
def _render_content(compact, race_id):
    if compact:
        return _build_compact_view(race_id)
    return _build_detailed_view(race_id)