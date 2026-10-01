"""Application errors and API exception handlers.

Client responses stay generic. Diagnostic detail is logged on the server and
must not include passwords, tokens, or connection strings.
"""

import logging
import re
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("zenosocialcrm")


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class BadRequestError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(400, "bad_request", message)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication is required.") -> None:
        super().__init__(401, "unauthorized", message)


class ForbiddenError(AppError):
    def __init__(self, message: str = "You do not have access to this company.") -> None:
        super().__init__(403, "forbidden", message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(404, "not_found", message)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(409, "conflict", message)


class TooManyRequestsError(AppError):
    def __init__(self, message: str = "Too many attempts. Try again later.") -> None:
        super().__init__(429, "too_many_requests", message)


def error_body(
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"error": error}


def _sanitize_validation_errors(errors: Sequence[Any]) -> list[dict[str, Any]]:
    """Drop raw input values so passwords never echo back to the client."""
    sanitized: list[dict[str, Any]] = []
    for error in errors:
        if not isinstance(error, dict):
            continue
        sanitized.append(
            {
                "loc": error.get("loc"),
                "msg": error.get("msg"),
                "type": error.get("type"),
            }
        )
    return sanitized


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_body(
                "validation_error",
                "Request validation failed.",
                _sanitize_validation_errors(exc.errors()),
            ),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_request: Request, exc: IntegrityError) -> JSONResponse:
        # Do not log the driver message: it can contain submitted values such as emails.
        logger.info("integrity constraint violation")
        constraint = _constraint_name(exc)
        if constraint == "uq_users_email":
            message = "A user with this email already exists."
        elif constraint == "uq_user_companies_user_company":
            message = "This user already has a membership for that company."
        elif constraint == "uq_contacts_company_email":
            message = "A contact with this email already exists in this company."
        else:
            message = "The request conflicts with existing data."
        return JSONResponse(status_code=409, content=error_body("conflict", message))

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        # The driver message can include bound parameter values. Log the type only.
        logger.error("database error type=%s", exc.__class__.__name__)
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "An unexpected error occurred."),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error type=%s", exc.__class__.__name__)
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "An unexpected error occurred."),
        )


def _constraint_name(exc: IntegrityError) -> str | None:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    name = getattr(diag, "constraint_name", None)
    if isinstance(name, str):
        return name
    # MySQL names the key in the driver error. Do not return or log the rest of
    # that message, because it includes the rejected value.
    raw_args: object = getattr(orig, "args", None)
    if not isinstance(raw_args, tuple) or len(raw_args) < 2:
        return None
    message = raw_args[1]
    if isinstance(message, str):
        match = re.search(r"for key '([^']+)'", message)
        if match:
            return match.group(1).rsplit(".", 1)[-1]
    return None
