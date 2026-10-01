"""Import models so SQLAlchemy registers them on the shared metadata."""

from app.models.campaign import MarketingCampaign
from app.models.company import Company
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.lead_metrics_type import LeadMetricsType
from app.models.message import Message
from app.models.pipeline import SalesPipeline
from app.models.pipeline_stage import SalesPipelineStage
from app.models.user import User
from app.models.user_company import UserCompany

__all__ = [
    "Company",
    "Contact",
    "Lead",
    "LeadMetricsType",
    "MarketingCampaign",
    "Message",
    "SalesPipeline",
    "SalesPipelineStage",
    "User",
    "UserCompany",
]
