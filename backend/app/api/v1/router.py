"""API v1 router — every module mounts here."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, branches, health, permissions, roles, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(branches.router)

__all__ = ["api_router"]
