"""API v1 router — every module mounts here."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    branches,
    brands,
    business,
    categories,
    health,
    payment_methods,
    permissions,
    products,
    registers,
    roles,
    uploads,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(business.router)
api_router.include_router(branches.router)
api_router.include_router(registers.router)
api_router.include_router(payment_methods.router)
api_router.include_router(categories.router)
api_router.include_router(brands.router)
api_router.include_router(products.router)
api_router.include_router(uploads.router)

__all__ = ["api_router"]
