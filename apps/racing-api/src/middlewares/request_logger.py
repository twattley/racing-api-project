from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from datetime import datetime
import json
from fastapi.responses import JSONResponse


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = datetime.now()

        # Log request details
        try:
            # Try to get request body if it exists
            body = await request.body()
            if body:
                body_str = body.decode()
                try:
                    # Try to parse as JSON for prettier logging
                    body_json = json.loads(body_str)
                    body_str = json.dumps(body_json, indent=2)
                except:
                    pass
            else:
                body_str = "No body"
        except:
            body_str = "Could not read body"

        print(f"""
            === Request ===
            Timestamp: {start_time}
            Method: {request.method}
            URL: {request.url}
            Headers: {dict(request.headers)}
            Body: {body_str}
            """)

        try:
            response = await call_next(request)

            # Get response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # Try to decode and format response body
            try:
                body_str = response_body.decode()
                try:
                    # Try to parse as JSON for prettier logging
                    body_json = json.loads(body_str)
                    body_str = json.dumps(body_json, indent=2)
                except:
                    pass
            except:
                body_str = "Could not decode response body"

            process_time = (datetime.now() - start_time).total_seconds()

            print(f"""
                === Response ===
                    Status: {response.status_code}
                    Process Time: {process_time:.2f}s
                    Headers: {dict(response.headers)}
                    Body: {body_str}
                    """)

            # Create new response with the body we read
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        except Exception as e:
            print(f"""
                === Error ===
                Type: {type(e).__name__}
                Message: {str(e)}
                URL: {request.url}
                """)
            raise
