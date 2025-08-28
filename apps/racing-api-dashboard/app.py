from dash import Dash, html, page_container, dcc

app = Dash(
    __name__,
    use_pages=True,
    title="Racing API",
    suppress_callback_exceptions=True,
    external_stylesheets=[
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    ],
)

app.layout = html.Div([dcc.Location(id="url"), page_container], className="container-fluid p-3")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)
