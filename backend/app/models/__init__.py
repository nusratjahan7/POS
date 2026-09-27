"""Importing this package registers every model on ``Base.metadata``.

Alembic autogenerate and ``Base.metadata.create_all`` rely on this side effect,
so keep every model imported here.
"""

from app.models.associations import role_permissions, user_roles
from app.models.branch import Branch
from app.models.password_reset import PasswordResetToken
from app.models.permission import Permission
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User

__all__ = [
    "Branch",
    "PasswordResetToken",
    "Permission",
    "RefreshToken",
    "Role",
    "User",
    "role_permissions",
    "user_roles",
]
