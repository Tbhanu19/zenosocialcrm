"""Central role and status definitions.

Import these enums everywhere a role or status is stored, compared, or returned.
Do not scatter raw role strings through the application.
"""

from collections.abc import Iterable
from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    OWNER = "owner"
    COMPANY_MANAGER = "company_manager"
    MARKETING_MANAGER = "marketing_manager"
    EMPLOYEE = "employee"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    INVITED = "invited"


class CompanyStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ContactStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class ContactSource(StrEnum):
    MANUAL = "manual"
    WEBSITE = "website"
    IMPORT = "import"
    CAMPAIGN = "campaign"
    REFERRAL = "referral"
    OTHER = "other"


class MessageType(StrEnum):
    EMAIL = "email"
    SMS = "sms"


class MessageDirection(StrEnum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"


class MessageStatus(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class CampaignType(StrEnum):
    PROMOTION = "promotion"
    EMAIL = "email"
    SMS = "sms"
    SOCIAL = "social"
    PAID_AD = "paid_ad"
    SEARCH = "search"
    REFERRAL = "referral"
    EVENT = "event"
    OTHER = "other"


class CampaignChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    GOOGLE = "google"
    WEBSITE = "website"
    REFERRAL = "referral"
    DIRECT = "direct"
    OTHER = "other"


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"
    LOST = "lost"
    ARCHIVED = "archived"


class LeadPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PipelineStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class PreferredContactType(StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    IN_PERSON = "in_person"
    OTHERS = "others"


class StageStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class StageColor(StrEnum):
    """Theme tokens. Stages do not store arbitrary color values."""

    COPPER = "copper"
    PINE = "pine"
    MOSS = "moss"
    INK = "ink"
    DANGER = "danger"


class LeadBusinessType(StrEnum):
    HOTELS = "hotels"
    PLUMBING = "plumbing"
    HVAC = "hvac"


class LeadSource(StrEnum):
    """Lead acquisition source. Contact sources stay separate."""

    MANUAL = "manual"
    WEBSITE = "website"
    EMAIL = "email"
    SMS = "sms"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    GOOGLE = "google"
    REFERRAL = "referral"
    CAMPAIGN = "campaign"
    OTHER = "other"


# Roles that may be stored on a company membership. Super admin is platform-level
# and is never a row in user_companies.
COMPANY_MEMBERSHIP_ROLES: frozenset[UserRole] = frozenset(
    {
        UserRole.OWNER,
        UserRole.COMPANY_MANAGER,
        UserRole.MARKETING_MANAGER,
        UserRole.EMPLOYEE,
    }
)

# Contact changes, campaigns, and leads. Employees can read contacts but not these records.
CRM_WRITER_ROLES: frozenset[UserRole] = frozenset(
    {
        UserRole.SUPER_ADMIN,
        UserRole.OWNER,
        UserRole.COMPANY_MANAGER,
        UserRole.MARKETING_MANAGER,
    }
)

# Company user management. Marketing managers and employees are not included.
USER_MANAGER_ROLES: frozenset[UserRole] = frozenset(
    {
        UserRole.SUPER_ADMIN,
        UserRole.OWNER,
        UserRole.COMPANY_MANAGER,
    }
)


def roles_assignable_by(actor: UserRole) -> frozenset[UserRole]:
    """Company roles this actor may grant. Super admin is never included."""
    if actor is UserRole.SUPER_ADMIN:
        return COMPANY_MEMBERSHIP_ROLES
    if actor is UserRole.OWNER:
        return frozenset(
            {
                UserRole.COMPANY_MANAGER,
                UserRole.MARKETING_MANAGER,
                UserRole.EMPLOYEE,
            }
        )
    if actor is UserRole.COMPANY_MANAGER:
        return frozenset({UserRole.MARKETING_MANAGER, UserRole.EMPLOYEE})
    return frozenset()


def sql_in_list(values: Iterable[StrEnum | str]) -> str:
    """Build a sorted SQL IN-list from trusted enum values only."""
    rendered: list[str] = []
    for value in values:
        raw = str(value.value) if isinstance(value, StrEnum) else value
        if not raw.replace("_", "").isalnum():
            raise ValueError(f"Refusing to embed unsafe SQL literal: {raw}")
        rendered.append(f"'{raw}'")
    return ", ".join(sorted(rendered))
