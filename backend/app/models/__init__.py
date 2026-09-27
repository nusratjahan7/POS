"""Importing this package registers every model on ``Base.metadata``.

Alembic autogenerate and ``Base.metadata.create_all`` rely on this side effect,
so keep every model imported here.
"""

from app.models.associations import role_permissions, user_roles
from app.models.branch import Branch
from app.models.brand import Brand
from app.models.business import Business
from app.models.category import Category
from app.models.password_reset import PasswordResetToken
from app.models.payment_method import PaymentMethod
from app.models.permission import Permission
from app.models.product import Product
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.refresh_token import RefreshToken
from app.models.register import Register
from app.models.role import Role
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.supplier import Supplier
from app.models.supplier_payment import SupplierPayment
from app.models.user import User

__all__ = [
    "Branch",
    "Brand",
    "Business",
    "Category",
    "PasswordResetToken",
    "PaymentMethod",
    "Permission",
    "Product",
    "Purchase",
    "PurchaseItem",
    "RefreshToken",
    "Register",
    "Role",
    "StockLevel",
    "StockMovement",
    "Supplier",
    "SupplierPayment",
    "User",
    "role_permissions",
    "user_roles",
]
