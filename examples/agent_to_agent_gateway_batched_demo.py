#!/usr/bin/env python3
"""
Agent-to-Agent OmniClaw demo:
- Seller exposes a paid resource using x402 requirements with GatewayWalletBatched
- Buyer signs PAYMENT-SIGNATURE via NanoKeyVault
- Buyer retries request and receives content
- Buyer settles payment via mocked Circle Gateway client

This runs locally (no real Circle call) but exercises real OmniClaw flow code.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
from dataclasses import dataclass

import httpx

from omniclaw.protocols.nanopayments.adapter import NanopaymentAdapter
from omniclaw.protocols.nanopayments.types import SettleResponse
from omniclaw.protocols.nanopayments.vault import NanoKeyVault
from omniclaw.seller.seller import PaymentScheme, Seller
from omniclaw.storage.memory import InMemoryStorage


DEMO_NETWORK = "eip155:5042002"
DEMO_USDC = "0x2f3A40A3db8a7e3D09B0adfEfbCe4f6f81927557"
DEMO_GATEWAY = "0x1111111111111111111111111111111111111111"
DEMO_PRICE = "$0.001"
DEMO_URL = "https://demo.seller.local/agent/weather/premium"


@dataclass
class _DemoBalance:
    total: int = 1_000_000_000
    available: int = 1_000_000_000
    formatted_total: str = "1000.000000 USDC"
    formatted_available: str = "1000.000000 USDC"


class DemoGatewayClient:
    """Minimal async client surface required by NanopaymentAdapter."""

    async def settle(self, payload, requirements):  # noqa: ANN001
        payer = payload.payload.authorization.from_address
        return SettleResponse(
            success=True,
            transaction="batch-demo-001",
            payer=payer,
            error_reason=None,
        )

    async def check_balance(self, address: str, network: str):  # noqa: ARG002
        return _DemoBalance()

    async def get_verifying_contract(self, network: str):  # noqa: ARG002
        return DEMO_GATEWAY

    async def get_usdc_address(self, network: str):  # noqa: ARG002
        return DEMO_USDC


async def run_demo() -> None:
    print("\n=== OmniClaw Agent-to-Agent GatewayWalletBatched Demo ===")

    os.environ["CIRCLE_GATEWAY_CONTRACT"] = DEMO_GATEWAY

    # Seller setup
    seller = Seller(
        seller_address="0x8bA1f109551bD432803012645Ac136ddd64DBA72",
        name="AI Weather Seller",
        network=DEMO_NETWORK,
        usdc_contract=DEMO_USDC,
    )
    seller.add_endpoint(
        "/agent/weather/premium",
        DEMO_PRICE,
        "Premium weather data for autonomous agents",
        schemes=[PaymentScheme.GATEWAY_BATCHED],
    )

    # Buyer setup
    vault = NanoKeyVault(
        entity_secret="demo-entity-secret-32-bytes-minimum-aaaaaaaa",
        storage_backend=InMemoryStorage(),
        circle_api_key="demo-circle-key",
        nanopayments_environment="testnet",
    )
    buyer_addr = await vault.generate_key("buyer_agent", network=DEMO_NETWORK)
    print(f"Buyer agent key: {buyer_addr}")
    print(f"Seller payment address: {seller.config.seller_address}")

    # Local "seller server" handler for adapter HTTP calls.
    async def _seller_http_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path != "/agent/weather/premium":
            return httpx.Response(status_code=404, json={"error": "not_found"})

        payment_sig = request.headers.get("PAYMENT-SIGNATURE") or request.headers.get(
            "payment-signature"
        )
        if not payment_sig:
            headers, body = seller.create_402_response("/agent/weather/premium", DEMO_URL)
            return httpx.Response(
                status_code=402,
                headers=headers,
                content=body.encode(),
            )

        payload = json.loads(base64.b64decode(payment_sig))
        accepted = seller._select_accepted_for_payload(payload, "/agent/weather/premium")
        if not accepted:
            return httpx.Response(status_code=402, json={"error": "no matching accepted kind"})

        ok, err, record = await seller.verify_payment_async(
            payload,
            accepted,
            verify_signature=True,
            settle_payment=False,
        )
        if not ok:
            return httpx.Response(status_code=402, json={"error": err})

        return httpx.Response(
            status_code=200,
            json={
                "premium_data": "Rain in 2 hours. Wind 14km/h. Route deviation advised.",
                "seller_record_id": record.id if record else None,
            },
        )

    transport = httpx.MockTransport(_seller_http_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = NanopaymentAdapter(
            vault=vault,
            nanopayment_client=DemoGatewayClient(),  # mocked settlement endpoint
            http_client=client,
            auto_topup_enabled=False,
            strict_settlement=True,
        )

        result = await adapter.pay_x402_url(
            url=DEMO_URL,
            method="GET",
            nano_key_alias="buyer_agent",
        )

    print("\nFlow result:")
    print(f"  success: {result.success}")
    print(f"  amount_usdc: {result.amount_usdc}")
    print(f"  amount_atomic: {result.amount_atomic}")
    print(f"  settlement_tx: {result.transaction}")
    print(f"  payer: {result.payer}")
    print(f"  seller: {result.seller}")
    print(f"  network: {result.network}")
    print(f"  response_data: {result.response_data}")
    print("\nDemo complete.")


if __name__ == "__main__":
    asyncio.run(run_demo())
