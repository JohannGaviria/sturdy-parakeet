from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.shared.logging.structlog_logger import StructlogLogger
from src.shared.schemas.response_schema import ErrorsResponseSchema

_logger = StructlogLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()

        _logger.warning(
            "Request validation failed.",
            request_method=request.method,
            request_path=request.url.path,
            error_count=len(errors),
            validation_errors=[
                {
                    "location": error["loc"],
                    "message": error["msg"],
                    "type": error["type"],
                }
                for error in errors
            ],
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=jsonable_encoder(
                ErrorsResponseSchema(
                    message="The request contains invalid or missing fields.",
                    code="VALIDATION_ERROR",
                    context={
                        ".".join(str(part) for part in error["loc"][1:])
                        or "request": error["msg"]
                        for error in errors
                    },
                ),
                exclude_none=True,
            ),
        )
