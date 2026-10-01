"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin_companies,
    admin_users,
    auth,
    companies,
    company_users,
    contacts,
    health,
    lead_metrics_types,
    leads,
    marketing,
    messages,
    metrics,
    pipelines,
    sales_metrics,
)
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.security_headers import SecurityHeadersMiddleware
from app.models import campaign as _campaign_model
from app.models import company as _company_model
from app.models import contact as _contact_model
from app.models import lead as _lead_model
from app.models import lead_metrics_type as _lead_metrics_type_model
from app.models import message as _message_model
from app.models import organisation_company as _organisation_company_model
from app.models import pipeline as _pipeline_model
from app.models import pipeline_stage as _pipeline_stage_model
from app.models import user as _user_model
from app.models import user_company as _user_company_model

logger = logging.getLogger("zenosocialcrm")

# Importing the model modules registers them on the SQLAlchemy metadata.
_REGISTERED_MODELS = (
    _user_model,
    _company_model,
    _organisation_company_model,
    _user_company_model,
    _contact_model,
    _message_model,
    _campaign_model,
    _lead_model,
    _lead_metrics_type_model,
    _pipeline_model,
    _pipeline_stage_model,
)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    application = FastAPI(
        title="ZenoSocialCRM",
        version="0.1.0",
        docs_url="/docs" if settings.expose_api_docs else None,
        redoc_url="/redoc" if settings.expose_api_docs else None,
        openapi_url="/openapi.json" if settings.expose_api_docs else None,
    )
    register_exception_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Company-Id"],
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.include_router(health.router, prefix="/api")
    application.include_router(auth.router, prefix="/api")
    application.include_router(companies.router, prefix="/api")
    application.include_router(admin_companies.router, prefix="/api")
    application.include_router(admin_users.router, prefix="/api")
    application.include_router(company_users.router, prefix="/api")
    application.include_router(contacts.router, prefix="/api")
    application.include_router(messages.router, prefix="/api")
    application.include_router(marketing.router, prefix="/api")
    application.include_router(leads.router, prefix="/api")
    application.include_router(metrics.router, prefix="/api")
    application.include_router(lead_metrics_types.router, prefix="/api")
    application.include_router(pipelines.router, prefix="/api")
    application.include_router(sales_metrics.router, prefix="/api")
    logger.info("application configured environment=%s", settings.environment)
    return application


app = create_app()
