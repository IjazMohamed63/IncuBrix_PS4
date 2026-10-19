from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from core.errors import ErrorCode, IncuBrixError
from core.logging import get_logger

logger = get_logger("error_handler")


def register_error_handlers(app: FastAPI) -> None:
    """Registers exception handlers to produce standard IncuBrix error JSON format."""

    @app.exception_handler(IncuBrixError)
    async def incubrix_error_handler(request: Request, exc: IncuBrixError) -> JSONResponse:
        logger.warning(
            f"IncuBrixError: {exc.code.value} - {exc.message}",
            extra={"error_code": exc.code.value, "details": exc.details},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(f"RequestValidationError: {str(exc)}")
        # Format field violations
        violations = []
        for err in exc.errors():
            loc = " -> ".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            violations.append(f"{loc}: {msg}")

        # Map to DEST_SPEC_VIOLATION if this is on connector endpoints, else VALIDATION_ERROR
        is_connector = "/connector/v1/" in request.url.path
        code = ErrorCode.DEST_SPEC_VIOLATION if is_connector else ErrorCode.VALIDATION_ERROR

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": code.value,
                    "message": "Validation failed for request payload.",
                    "retryable": False,
                    "details": {"violations": violations},
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled Exception: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An unexpected internal server error occurred.",
                    "retryable": False,
                    "details": {"error_type": type(exc).__name__},
                }
            },
        )
