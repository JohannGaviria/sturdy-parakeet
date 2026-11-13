from fastapi import FastAPI

from src.modules.auth.register.exception_handlers import register_exception_handlers


def auth_exception_handlers(app: FastAPI) -> None:
    register_exception_handlers(app)
