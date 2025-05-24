import json
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware
from starlette_context.middleware import RawContextMiddleware

from .controllers.betting_api import router as BettingAPIRouter
from .controllers.collateral_api import router as CollateralAPIRouter
from .controllers.feedback_api import router as FeedbackAPIRouter
from .controllers.todays_api import router as TodaysAPIRouter
from .middlewares.db_session import DBSessionMiddleware
from .storage.database_session_manager import database_session

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
app.include_router(TodaysAPIRouter, prefix=API_PREFIX_V1)
app.include_router(CollateralAPIRouter, prefix=API_PREFIX_V1)
app.include_router(BettingAPIRouter, prefix=API_PREFIX_V1)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
