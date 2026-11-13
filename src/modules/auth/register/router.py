from typing import Any, cast

from fastapi import APIRouter, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from src.modules.auth.register.schema import RegisterRequest, RegisterResponse
from src.shared.schemas.response_schema import (
    ErrorsResponseSchema,
    SuccessResponseSchema,
)

router = APIRouter()


@router.post(
    path="/register",
    summary="Register a new user account.",
    status_code=status.HTTP_201_CREATED,
    responses=cast(
        dict[int | str, dict[str, Any]],
        {
            status.HTTP_201_CREATED: {
                "model": SuccessResponseSchema[RegisterResponse],
                "description": "User account successfully registered.",
            },
            status.HTTP_422_UNPROCESSABLE_CONTENT: {
                "model": ErrorsResponseSchema,
                "description": "Request validation failed due to missing or invalid fields.",
            },
            status.HTTP_500_INTERNAL_SERVER_ERROR: {
                "model": ErrorsResponseSchema,
                "description": "An unexpected internal server error occurred.",
            },
        },
    ),
)
async def register(request: RegisterRequest) -> JSONResponse:
    """Register a new user account.

    Creates a user account using the provided registration information.

    Args:
        request (RegisterRequest): The user registration data.

    Returns:
        JSONResponse: A response containing the registration result.
    """
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(
            SuccessResponseSchema(
                message="User account successfully registered.",
                # data=RegisterResponse()
            )
        ),
    )
