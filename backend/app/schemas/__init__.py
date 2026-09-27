"""Pydantic request/response schemas, grouped by domain."""

from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.branch import BranchCreate, BranchRead, BranchSummary, BranchUpdate
from app.schemas.common import ErrorBody, ErrorDetail, ErrorResponse, Message, ORMModel, Page
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
    "ChangePasswordRequest",
    "ErrorBody",
    "ErrorDetail",
    "ErrorResponse",
    "LoginRequest",
    "Message",
    "ORMModel",
    "Page",
    "PermissionRead",
    "RefreshRequest",
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
