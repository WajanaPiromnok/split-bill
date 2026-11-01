import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def install_error_handlers(app: FastAPI) -> None:
    # Registered inside CORS so browser clients can read even unexpected error responses.
    @app.middleware("http")
    async def unexpected_error(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled error for %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected error occurred",
                    }
                },
            )

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        if any(error["loc"] == ("header", "X-User") for error in errors):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "unauthenticated",
                        "message": "A valid X-User header is required",
                    }
                },
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed",
                    "details": [
                        {
                            "field": ".".join(str(part) for part in error["loc"]),
                            "message": error["msg"],
                            "type": error["type"],
                        }
                        for error in errors
                    ],
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": str(exc.detail)}},
            headers=exc.headers,
        )
