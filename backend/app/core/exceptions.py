"""Domain-level exceptions.

These are transport-agnostic: services and repositories raise them, and the API
layer (``app.api.errors``) translates them into the standard HTTP error
envelope. Keeping them free of FastAPI imports preserves layering.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all intentionally-raised application errors."""

    status_code: int = 500
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.details: list[dict[str, Any]] = details or []
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
    message = "The request could not be processed."


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Authentication is required."


class InvalidCredentialsError(UnauthorizedError):
    code = "invalid_credentials"
    message = "Incorrect email or password."


class TokenError(UnauthorizedError):
    code = "invalid_token"
    message = "The provided token is invalid or expired."


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "The requested resource was not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "The resource already exists or conflicts with existing data."


class UnprocessableError(AppError):
    status_code = 422
    code = "unprocessable_entity"
    message = "The request was well-formed but could not be processed."


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests. Please try again later."

    def __init__(self, retry_after: int, message: str | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after
