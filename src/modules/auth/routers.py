from fastapi import APIRouter

from src.modules.auth.register.router import router as register_router

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Auth"],
)

router.include_router(register_router)
