from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.database.base_model import BaseModel


class UserModel(BaseModel):
    """Application user stored in the users table.

    Attributes:
        id (UUID): Unique identifier for the user.
        email (str): Unique email address used for authentication.
        full_name (str | None): Display name of the user.
        password_hash (str): Hashed password for authentication.
        email_verified (bool): Whether the email address has been verified.
        email_verified_at (datetime | None): Timestamp when the email was verified.
        last_login_at (datetime | None): Timestamp of the most recent login.
        created_at (datetime): Timestamp when the user was created.
        updated_at (datetime): Timestamp when the user was last updated.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
