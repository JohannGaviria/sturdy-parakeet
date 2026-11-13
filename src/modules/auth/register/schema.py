from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator


class RegisterRequest(BaseModel):
    """Request payload to register a new user.

    Attributes:
        email (str): User email address. Normalized to lowercase and stripped.
        password (str): User password with a minimum of 12 and a maximum
            of 128 characters.
        full_name (str | None): Optional full name of the user with a minimum of 2
            and a maximum of 120 characters. Stripped of whitespace.
    """

    email: EmailStr = Field(max_length=320, description="User email address.")
    password: SecretStr = Field(
        min_length=12, max_length=128, description="User password (12-128 characters)."
    )
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
        description="Optional full name of the user (2-120 characters).",
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: str) -> str:
        return email.strip().lower()

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, full_name: str | None) -> str | None:
        return full_name.strip() if full_name else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "josefina.gutierrez@example.com",
                "password": "SecurePass123!",
                "full_name": "Josefina Gutierrez",
            }
        }
    }


class RegisterResponse(BaseModel):
    """Response after successfully registering a new user.

    Attributes:
        id (UUID): Unique identifier of the created user.
        email (str): Verified email address of the user.
        full_name (str | None): Full name of the user, can be None if not provided
            during registration.
        email_verified (bool): Indicates whether the email address has been verified.
        created_at (datetime): Timestamp indicating when the account was created.
    """

    id: UUID = Field(description="Unique identifier of the created user.")
    email: EmailStr = Field(description="User email address.")
    full_name: str | None = Field(
        default=None, description="Full name of the user, can be None."
    )
    email_verified: bool = Field(
        description="Indicates whether the email has been verified."
    )
    created_at: datetime = Field(description="Account creation timestamp.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "email": "josefina.gutierrez@example.com",
                "full_name": "Josefina Gutierrez",
                "email_verified": False,
                "created_at": "2025-11-13T09:00:00Z",
            }
        }
    }
