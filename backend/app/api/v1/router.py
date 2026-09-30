"""API v1 router — every module mounts here."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    branches,
    brands,
    business,
    categories,
    customers,
    discounts,
    expenses,
    health,
    inventory,
    payment_methods,
    permissions,
    pos,
    products,
    purchases,
    register_sessions,
    registers,
    reports,
    roles,
    sales,
    suppliers,
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
api_router.include_router(inventory.router)
api_router.include_router(suppliers.router)
api_router.include_router(purchases.router)
api_router.include_router(customers.router)
api_router.include_router(pos.router)
api_router.include_router(sales.router)
api_router.include_router(discounts.router)
api_router.include_router(expenses.router)
api_router.include_router(register_sessions.router)
api_router.include_router(reports.router)
api_router.include_router(uploads.router)

__all__ = ["api_router"]
