from contextlib import asynccontextmanager

import uvicorn
from api_helpers.clients import get_postgres_client
from fastapi import FastAPI
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware
from starlette_context.middleware import RawContextMiddleware

from .controllers.betting_api import router as BettingAPIRouter
from .controllers.collateral_api import router as CollateralAPIRouter
from .controllers.feedback_api import router as FeedbackAPIRouter
from .controllers.todays_api import router as TodaysAPIRouter
from .controllers.etl_status_api import router as ETLStatusAPIRouter
from .middlewares.db_session import DBSessionMiddleware
from .storage.database_session_manager import database_session

API_PREFIX_V1 = "/racing-api/api/v1"


async def get_betting_session_id():
    session = None
    postgres_client = get_postgres_client()
    try:
        session_generator = database_session()
        session = await session_generator.__anext__()

        # Get the current max session_id
        result = await session.execute(
            text(
                "SELECT MAX(session_id) as session_id FROM api.betting_selections_info"
            )
        )
        row = result.first()
        current_session_id = row.session_id if row else 0

        # Calculate next session ID
        next_session_id = (current_session_id or 0) + 1

        # Create or update the betting session record in database
        postgres_client.execute_query(
            f"""
            INSERT INTO api.betting_session (session_id, created_at, is_active) 
            VALUES ({next_session_id}, NOW(), true) 
            ON CONFLICT (session_id) 
            DO UPDATE SET updated_at = NOW(), is_active = true
            """
        )

        # Deactivate previous sessions
        if current_session_id:
            postgres_client.execute_query(
                f"UPDATE api.betting_session SET is_active = false WHERE session_id < {next_session_id}"
            )

    except Exception as e:
        print(f"Error updating betting session ID: {str(e)}")
        raise
    finally:
        if session:
            await session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_betting_session_id()
    yield


app = FastAPI(
    title="Racing API",
    description="Racing API",
    version="0.1.0",
    openapi_url="/racing-api/openapi.json",
    docs_url="/racing-api/docs",
    lifespan=lifespan,
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
app.include_router(ETLStatusAPIRouter, prefix=API_PREFIX_V1)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
