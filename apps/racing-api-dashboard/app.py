
import dash
from dash import Dash, Output, Input, html, page_container, dcc
from datetime import datetime

app = Dash(__name__, use_pages=True, title="Racing Dashboard")

# Only render the current page
app.layout = html.Div([
    page_container
])

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
