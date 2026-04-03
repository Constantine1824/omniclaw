from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from omniclaw.protocols.x402 import PaymentRequirements, X402Adapter


@pytest.mark.asyncio
async def test_x402_execute_uses_deterministic_idempotency_for_transfer():
    config = MagicMock()
    wallet_service = MagicMock()
    wallet_service.get_wallet.return_value = MagicMock(blockchain="ETH-SEPOLIA", address="0xabc")

    transfer_result = MagicMock()
    transfer_result.success = True
    transfer_result.tx_hash = "0xhash"
    transfer_result.transaction = MagicMock(id="tx-1")
    wallet_service.transfer = AsyncMock(return_value=transfer_result)

    adapter = X402Adapter(config=config, wallet_service=wallet_service)

    requirements = PaymentRequirements(
        scheme="exact",
        network="eip155:11155111",
        max_amount_required="1000",
        resource="https://api.example.com/data",
        description="test",
        recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
        extra={},
    )
    response_402 = MagicMock(status_code=402)
    response_200 = MagicMock(status_code=200, headers={})
    response_200.json.side_effect = ValueError("not json")
    response_200.text = "ok"

    adapter._request_with_402_check = AsyncMock(return_value=(response_402, requirements))
    adapter._get_http_client = AsyncMock(
        return_value=MagicMock(request=AsyncMock(return_value=response_200))
    )

    await adapter.execute(
        wallet_id="wallet-1",
        recipient="https://api.example.com/data",
        amount=Decimal("1.00"),
        request_json={"query": "a"},
    )
    await adapter.execute(
        wallet_id="wallet-1",
        recipient="https://api.example.com/data",
        amount=Decimal("1.00"),
        request_json={"query": "a"},
    )

    first_key = wallet_service.transfer.await_args_list[0].kwargs["idempotency_key"]
    second_key = wallet_service.transfer.await_args_list[1].kwargs["idempotency_key"]
    assert first_key == second_key
