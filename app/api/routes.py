from fastapi import APIRouter
from app.api.endpoints import vinyls, integrations, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(vinyls.router, prefix="/vinyls", tags=["vinyls"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
