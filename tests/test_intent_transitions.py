from decimal import Decimal

import pytest

from omniclaw.core.exceptions import ValidationError
from omniclaw.core.types import PaymentIntentStatus
from omniclaw.intents.service import PaymentIntentService
from omniclaw.storage.memory import InMemoryStorage


@pytest.mark.asyncio
async def test_intent_service_rejects_invalid_terminal_transition():
    storage = InMemoryStorage()
    service = PaymentIntentService(storage)

    intent = await service.create(
        wallet_id="w1",
        recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
        amount=Decimal("1.00"),
    )
    await service.update_status(intent.id, PaymentIntentStatus.PROCESSING)
    await service.update_status(intent.id, PaymentIntentStatus.SUCCEEDED)

    with pytest.raises(ValidationError, match="Invalid payment_intent status transition"):
        await service.update_status(intent.id, PaymentIntentStatus.PROCESSING)


@pytest.mark.asyncio
async def test_intent_service_rejects_cancel_after_succeeded():
    storage = InMemoryStorage()
    service = PaymentIntentService(storage)

    intent = await service.create(
        wallet_id="w1",
        recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
        amount=Decimal("1.00"),
    )
    await service.update_status(intent.id, PaymentIntentStatus.PROCESSING)
    await service.update_status(intent.id, PaymentIntentStatus.SUCCEEDED)

    with pytest.raises(ValidationError, match="Invalid payment_intent status transition"):
        await service.cancel(intent.id)
