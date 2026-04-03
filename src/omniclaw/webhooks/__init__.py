"""
Webhook handling infrastructure.
"""

from omniclaw.webhooks.parser import DuplicateWebhookError, WebhookParser

__all__ = ["WebhookParser", "DuplicateWebhookError"]
