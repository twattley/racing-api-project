import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .controllers.feedback_api import router as FeedbackAPIRouter
from .controllers.todays_api import router as TodaysAPIRouter
from .controllers.betting_api import router as BettingAPIRouter


API_PREFIX_V2 = "/racing-api/api/v2"

app = FastAPI(
    title="Racing API",
    description="Racing API",
    version="0.1.0",
    openapi_url="/racing-api/openapi.json",
    docs_url="/racing-api/docs",
)

# Frontend dev origins (adjust as needed)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # avoid "*"
    allow_credentials=True,  # or False if you don’t send cookies/auth
    allow_methods=["*"],  # include OPTIONS
    allow_headers=["*"],
)

app.include_router(FeedbackAPIRouter, prefix=API_PREFIX_V2)
app.include_router(TodaysAPIRouter, prefix=API_PREFIX_V2)
app.include_router(BettingAPIRouter, prefix=API_PREFIX_V2)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
