
import dash
from dash import Dash, Output, Input, html, page_container, dcc
from datetime import datetime

app = Dash(__name__, use_pages=True, title="Racing Dashboard")

# Add a simple navigation bar
app.layout = html.Div([
    html.Nav([
        dcc.Link("Home", href="/index", style={"marginRight": "1rem"}),
        dcc.Link("About", href="/about"),
    ], style={"marginBottom": "2rem"}),
    page_container
])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
