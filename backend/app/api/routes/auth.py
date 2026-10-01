"""Login, logout, and current-user endpoints."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import UnauthorizedError
from app.core.login_throttle import login_throttle
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import ProfileUpdate, UserRead
from app.services.auth_service import authenticate, revoke_access_tokens, update_profile

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    address = request.client.host if request.client is not None else "unknown"
    email = str(body.email)
    login_throttle.check(address, email)
    try:
        user = authenticate(db, email, body.password)
    except UnauthorizedError:
        login_throttle.record_failure(address, email)
        raise
    login_throttle.record_success(address, email)
    return TokenResponse(access_token=create_access_token(user.id, user.token_version))


@router.post("/logout", status_code=204)
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    revoke_access_tokens(db, current_user)
    return Response(status_code=204)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_current_user(
    body: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    return update_profile(db, current_user, body)
