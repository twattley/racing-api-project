import dash
from dash import html, dash_table
from storage.race_times import get_todays_race_times
dash.register_page(__name__, path="/feedback/race-times", name="Race Times Feedback")

def layout():
    df = get_todays_race_times()
    # Show only a subset of columns for demo
    columns = ["race_id", "race_time", "race_title", "course"]
    data = df[columns].to_dict("records") if not df.empty else []
    return html.Div(
        [
            html.H1("Race Times Feedback"),
            html.P("This page will collect feedback on race times."),
            dash_table.DataTable(
                columns=[{"name": c.replace("_", " ").title(), "id": c} for c in columns],
                data=data,
                page_size=10,
                style_table={"overflowX": "auto"},
                style_header={"fontWeight": "600"},
                style_cell={"padding": "0.5rem", "fontSize": "1rem"},
            )
        ],
        style={"padding": "32px"},
    )
