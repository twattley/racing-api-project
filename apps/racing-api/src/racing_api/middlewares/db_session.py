from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..storage.database_session_manager import sessionmanager


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        session = sessionmanager.session()
        request.state.db = session
        try:
            response = await call_next(request)
            return response
        finally:
            await session.close()
