from dash import html


def race_form(race_id=None):
	"""Skeleton race form component. Replace with real UI later."""
	return html.Div(
		[
			html.H2("Race Form"),
			html.P(f"race_id: {race_id or 'None provided'}"),
		],
		style={"padding": "16px"},
	)

