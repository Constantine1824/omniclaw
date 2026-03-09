import structlog
from fastapi import FastAPI

from app.core.config import settings
from app.payments.omniclaw_client import OmniclawPaymentClient
from omniclaw.onboarding import load_managed_entity_secret

logger = structlog.get_logger(__name__)


async def startup_event(app: FastAPI) -> None:
    """Application startup validation and warmup."""
    logger.info(
        "mcp_startup",
        env=settings.ENVIRONMENT,
        project=settings.PROJECT_NAME,
        network=settings.OMNICLAW_NETWORK,
    )

    if settings.ENVIRONMENT == "prod":
        if not settings.CIRCLE_API_KEY:
            raise RuntimeError("Missing CIRCLE_API_KEY in production")
        api_key = settings.CIRCLE_API_KEY.get_secret_value() if settings.CIRCLE_API_KEY else None
        managed_secret = load_managed_entity_secret(api_key) if api_key else None
        if not settings.ENTITY_SECRET and not managed_secret:
            raise RuntimeError("Missing ENTITY_SECRET in production")

    # Warm up singleton early so configuration issues fail fast.
    await OmniclawPaymentClient.get_instance()
    logger.info("mcp_startup_ready")


async def shutdown_event(app: FastAPI) -> None:
    """Application shutdown cleanup."""
    await OmniclawPaymentClient.close_instance()
    logger.info("mcp_shutdown_complete")
