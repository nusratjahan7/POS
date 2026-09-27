"""Declarative base and shared metadata.

The naming convention guarantees that every index/constraint gets a stable,
predictable name — required for reliable Alembic autogenerate and rollbacks.
"""

from __future__ import annotations

from typing import ClassVar

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Fetch server-generated values (notably `updated_at`, whose `onupdate` is a
    # SQL expression) with RETURNING as part of the INSERT/UPDATE.
    #
    # Without this the ORM expires those attributes after a flush, because it
    # cannot know the value the database computed. Reading them afterwards
    # becomes a lazy load — which raises MissingGreenlet the moment a response
    # model serialises the instance outside an await.
    __mapper_args__: ClassVar[dict[str, bool]] = {"eager_defaults": True}
