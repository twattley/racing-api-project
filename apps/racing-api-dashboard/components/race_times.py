from typing import Literal

from dash import html, dcc

from services.base_service import todays_race_times


def _format_time(t) -> str:
    """Format a time object as HH:MM, safely handling None."""
    if not t:
        return ""
    try:
        return t.strftime("%H:%M")
    except Exception:
        # Fallback if it's already a string or unexpected type
        s = str(t)
        return s[:5]


def _race_details(r) -> str:
    """Compose the secondary details line for a race card."""
    bits = []
    if r.distance:
        bits.append(str(r.distance))
    if r.number_of_runners:
        bits.append(f"{r.number_of_runners}r")
    if r.race_type:
        bits.append(str(r.race_type))
    if r.race_class:
        bits.append(f"Cl {r.race_class}")
    if getattr(r, "is_hcap", False):
        bits.append("Hcap")
    return " • ".join(bits)


def render_race_times(data_type: Literal["today", "feedback"] = "today"):
    """Render grouped race times for the given data type.

    Layout structure:
    - Container
      - Course section (title)
            - Race card(s): time, title, details
    """

    # Fetch data via service (already typed via Pydantic models)
    response = todays_race_times(data_type)
    courses = response.data if response and response.data else []

    container_children = [html.Div(style={"height": "12px"})]

    for course in courses:
        race_cards = []
        for r in course.races or []:
            card = html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                _format_time(getattr(r, "time_hours", None)),
                                style={
                                    "fontSize": "12px",
                                    "fontWeight": 500,
                                    "color": "#6b7280",
                                    "paddingTop": "2px",
                                    "minWidth": "44px",
                                    "display": "inline-block",
                                },
                            ),
                            html.Span(
                                r.race_title,
                                style={
                                    "fontSize": "15px",
                                    "fontWeight": 600,
                                    "color": "#111827",
                                    "lineHeight": "20px",
                                    "marginLeft": "10px",
                                },
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "flex-start",
                            "gap": "10px",
                            "marginBottom": "4px",
                            "flexWrap": "wrap",
                        },
                    ),
                    html.Div(
                        _race_details(r),
                        style={"fontSize": "18px", "color": "#555"},
                    ),
                ],
                style={
                    "backgroundColor": "#fff",
                    "borderRadius": "10px",
                    "padding": "10px 14px",
                    "marginBottom": "12px",
                    "border": "1px solid #e5e5e5",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.04)",
                    "transition": "opacity 0.2s ease",
                    "cursor": "pointer",
                },
            )

            race_cards.append(
                dcc.Link(
                    card,
                    href=f"/feedback/race/{r.race_id}",
                    style={"textDecoration": "none", "display": "block"},
                    refresh=False,
                )
            )

        container_children.append(
            html.Div(
                [
                    html.H2(
                        course.course,
                        style={
                            "fontSize": "20px",
                            "fontWeight": 600,
                            "color": "#222",
                            "marginBottom": "12px",
                            "letterSpacing": "0.5px",
                        },
                    ),
                    *race_cards,
                ],
                style={"marginBottom": "28px"},
            )
        )

    return html.Div(
        container_children,
        style={
            "padding": "16px",
            "backgroundColor": "#f5f5f5",
            "paddingBottom": "40px",
        },
    )
