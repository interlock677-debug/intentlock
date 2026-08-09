from fastapi import APIRouter

from app.presentation.api.v1.routes import auth, health, intent

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(intent.router)
