"""Pydantic request/response schemas, grouped by domain."""

from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.branch import BranchCreate, BranchRead, BranchSummary, BranchUpdate
from app.schemas.business import BusinessRead, BusinessUpdate
from app.schemas.common import ErrorBody, ErrorDetail, ErrorResponse, Message, ORMModel, Page
from app.schemas.payment_method import (
    PaymentMethodCreate,
    PaymentMethodRead,
    PaymentMethodSummary,
    PaymentMethodUpdate,
)
from app.schemas.register import (
    RegisterCreate,
    RegisterRead,
    RegisterSummary,
    RegisterUpdate,
)
from app.schemas.role import PermissionRead, RoleCreate, RoleRead, RoleSummary, RoleUpdate
from app.schemas.user import (
    UserCreate,
    UserPasswordUpdate,
    UserRead,
    UserSummary,
    UserUpdate,
)

__all__ = [
    "AccessTokenResponse",
    "BranchCreate",
    "BranchRead",
    "BranchSummary",
    "BranchUpdate",
    "BusinessRead",
    "BusinessUpdate",
    "ChangePasswordRequest",
    "ErrorBody",
    "ErrorDetail",
    "ErrorResponse",
    "LoginRequest",
    "Message",
    "ORMModel",
    "Page",
    "PaymentMethodCreate",
    "PaymentMethodRead",
    "PaymentMethodSummary",
    "PaymentMethodUpdate",
    "PermissionRead",
    "RefreshRequest",
    "RegisterCreate",
    "RegisterRead",
    "RegisterSummary",
    "RegisterUpdate",
    "RoleCreate",
    "RoleRead",
    "RoleSummary",
    "RoleUpdate",
    "TokenResponse",
    "UserCreate",
    "UserPasswordUpdate",
    "UserRead",
    "UserSummary",
    "UserUpdate",
]
