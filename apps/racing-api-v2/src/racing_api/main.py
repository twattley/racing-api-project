import uvicorn

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette_context.middleware import RawContextMiddleware

from .controllers.feedback import router as FeedbackAPIRouter
from .middlewares.db_session import DBSessionMiddleware

API_PREFIX_V1 = "/racing-api/api/v1"


app = FastAPI(
    title="Racing API",
    description="Racing API",
    version="0.1.0",
    openapi_url="/racing-api/openapi.json",
    docs_url="/racing-api/docs",
)

app.add_middleware(RawContextMiddleware)
app.add_middleware(DBSessionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
    ],
    allow_headers=["*"],
)

app.include_router(FeedbackAPIRouter, prefix=API_PREFIX_V1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
