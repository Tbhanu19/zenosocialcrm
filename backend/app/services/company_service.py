"""Company creation and validation."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError
from app.models.company import Company
from app.schemas.company import CompanyCreate


def create_company(db: Session, data: CompanyCreate) -> Company:
    name = data.name.strip()
    if not name:
        raise BadRequestError("Company name is required.")

    company = Company(
        name=name,
        business_type=data.business_type,
        phone=data.phone,
        email=data.email,
        website=data.website,
        address=data.address,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        status=data.status.value,
    )
    db.add(company)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BadRequestError("Company could not be saved.") from None
    db.refresh(company)
    return company
