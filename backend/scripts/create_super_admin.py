"""Create the initial super admin used to sign in.

Refuses to run unless ENVIRONMENT=development.
The password below is a local sample credential, not a production secret.
Running this again does not change an account that already exists.
"""

from sqlalchemy import select

from app.core.config import get_settings
from app.core.permissions import UserStatus
from app.db.session import SessionLocal
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth_service import create_user

SUPER_ADMIN_EMAIL = "rama.k@amensys.com"
DEV_PASSWORD = "amenGOTO45@@"


def main() -> None:
    settings = get_settings()
    if settings.environment != "development":
        raise SystemExit("create_super_admin.py only runs when ENVIRONMENT=development.")

    db = SessionLocal()
    try:
        existing = db.scalar(select(User).where(User.email == SUPER_ADMIN_EMAIL))
        if existing is not None:
            if not existing.is_super_admin or existing.status != UserStatus.ACTIVE.value:
                raise SystemExit(
                    f"{SUPER_ADMIN_EMAIL} already exists and is not an active super admin."
                )
            print(f"Super admin already exists: {existing.email}")
            return

        admin = create_user(
            db,
            UserCreate(
                email=SUPER_ADMIN_EMAIL,
                password=DEV_PASSWORD,
                first_name="Super",
                last_name="Admin",
                status=UserStatus.ACTIVE,
                is_super_admin=True,
            ),
        )
        print(f"Super admin created: {admin.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
