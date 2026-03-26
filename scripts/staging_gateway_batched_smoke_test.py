#!/usr/bin/env python3
"""
One-command staging smoke test for OmniClaw GatewayWalletBatched flow.

What it verifies:
1. Buyer agent key signs a real PAYMENT-SIGNATURE payload (EIP-3009).
2. Seller agent issues x402 402 requirements and verifies signed payload.
3. Buyer receives paid resource response.
4. Settlement path:
   - Default: real Circle Gateway settle call
   - Optional: mocked settle (for local validation only)
5. Replay protection: reusing same payload is rejected by seller.

Usage:
  uv run python scripts/staging_gateway_batched_smoke_test.py

Optional local-only mode (no real Circle settle):
  uv run python scripts/staging_gateway_batched_smoke_test.py --mock-settlement
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from omniclaw import OmniClaw
from omniclaw.protocols.nanopayments.adapter import NanopaymentAdapter
from omniclaw.protocols.nanopayments.types import SettleResponse
from omniclaw.seller.seller import PaymentScheme, Seller


def _load_dotenv() -> None:
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


@dataclass
class _CapturedPaidRequest:
    payload: dict[str, Any] | None = None
    accepted: dict[str, Any] | None = None


@dataclass
class _MockBalance:
    total: int = 500_000_000
    available: int = 500_000_000
    formatted_total: str = "500.000000 USDC"
    formatted_available: str = "500.000000 USDC"


class _MockSettlementClient:
    def __init__(self, payer: str) -> None:
        self._payer = payer

    async def settle(self, payload, requirements):  # noqa: ANN001, ARG002
        return SettleResponse(
            success=True,
            transaction="mock-batch-0001",
            payer=self._payer,
            error_reason=None,
        )

    async def check_balance(self, address: str, network: str):  # noqa: ARG002
        return _MockBalance()

    async def get_verifying_contract(self, network: str):  # noqa: ARG002
        return os.environ.get("CIRCLE_GATEWAY_CONTRACT", "")

    async def get_usdc_address(self, network: str):  # noqa: ARG002
        return os.environ.get("OMNICLAW_SMOKE_USDC_ADDRESS", "")


async def _build_buyer(args: argparse.Namespace) -> OmniClaw:
    circle_api_key = _require_env("CIRCLE_API_KEY")
    entity_secret = _require_env("ENTITY_SECRET")

    buyer = OmniClaw(
        circle_api_key=circle_api_key,
        entity_secret=entity_secret,
    )

    if not buyer.vault or not buyer.nanopayment_adapter:
        raise RuntimeError("Nanopayments are not initialized on buyer OmniClaw instance")

    alias = args.buyer_alias
    exists = await buyer.vault.has_key(alias)
    if not exists:
        network = args.network
        addr = await buyer.vault.generate_key(alias=alias, network=network)
        print(f"[buyer] generated key '{alias}': {addr} ({network})")
    else:
        addr = await buyer.vault.get_address(alias=alias)
        net = await buyer.vault.get_network(alias=alias)
        print(f"[buyer] using existing key '{alias}': {addr} ({net})")
        if net != args.network:
            raise RuntimeError(
                f"Buyer key network mismatch: alias '{alias}' is {net}, expected {args.network}"
            )

    return buyer


async def _select_supported_kind(buyer: OmniClaw, network: str):
    client = buyer.nanopayment_adapter._client  # type: ignore[attr-defined]
    kinds = await client.get_supported(force_refresh=True)
    for kind in kinds:
        if kind.network == network and kind.verifying_contract and kind.usdc_address:
            return kind
    raise RuntimeError(
        f"No supported GatewayWalletBatched kind found for network {network}. "
        "Check Circle Gateway /v1/x402/supported."
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description="Staging smoke test for GatewayWalletBatched flow")
    parser.add_argument("--mock-settlement", action="store_true", help="Skip real Circle settle call")
    parser.add_argument("--network", default=os.environ.get("OMNICLAW_SMOKE_NETWORK", "eip155:5042002"))
    parser.add_argument("--buyer-alias", default=os.environ.get("OMNICLAW_SMOKE_BUYER_KEY_ALIAS", "smoke-buyer"))
    parser.add_argument("--seller-address", default=os.environ.get("OMNICLAW_SMOKE_SELLER_ADDRESS", "0x8bA1f109551bD432803012645Ac136ddd64DBA72"))
    parser.add_argument("--price", default=os.environ.get("OMNICLAW_SMOKE_PRICE", "$0.001"))
    args = parser.parse_args()

    _load_dotenv()

    print("=== OmniClaw GatewayWalletBatched Staging Smoke Test ===")
    print(f"network={args.network} price={args.price} mock_settlement={args.mock_settlement}")

    buyer = await _build_buyer(args)
    vault = buyer.vault
    assert vault is not None

    supported_kind = await _select_supported_kind(buyer, args.network)
    os.environ["CIRCLE_GATEWAY_CONTRACT"] = supported_kind.verifying_contract or ""
    os.environ.setdefault("OMNICLAW_SELLER_STRICT_GATEWAY_CONTRACT", "true")

    seller = Seller(
        seller_address=args.seller_address,
        name="Staging Seller Agent",
        network=args.network,
        usdc_contract=supported_kind.usdc_address or "",
    )
    seller.add_endpoint(
        "/premium/route-intelligence",
        args.price,
        "AI route intelligence premium feed",
        schemes=[PaymentScheme.GATEWAY_BATCHED],
    )

    captured = _CapturedPaidRequest()
    url = "https://staging.seller.local/premium/route-intelligence"

    async def _seller_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path != "/premium/route-intelligence":
            return httpx.Response(status_code=404, json={"error": "not_found"})

        sig = request.headers.get("PAYMENT-SIGNATURE") or request.headers.get("payment-signature")
        if not sig:
            headers, body = seller.create_402_response("/premium/route-intelligence", url)
            return httpx.Response(status_code=402, headers=headers, content=body.encode())

        payload = json.loads(base64.b64decode(sig))
        accepted = seller._select_accepted_for_payload(payload, "/premium/route-intelligence")
        if not accepted:
            return httpx.Response(status_code=402, json={"error": "no_matching_payment_requirement"})

        ok, err, record = await seller.verify_payment_async(
            payload,
            accepted,
            verify_signature=True,
            settle_payment=False,
        )
        if not ok:
            return httpx.Response(status_code=402, json={"error": err})

        captured.payload = payload
        captured.accepted = accepted

        return httpx.Response(
            status_code=200,
            json={
                "signal": "route-shift-detected",
                "confidence": 0.94,
                "seller_record_id": record.id if record else None,
            },
        )

    transport = httpx.MockTransport(_seller_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        settlement_client = (
            _MockSettlementClient(await vault.get_address(args.buyer_alias))
            if args.mock_settlement
            else buyer.nanopayment_adapter._client  # type: ignore[attr-defined]
        )

        adapter = NanopaymentAdapter(
            vault=vault,
            nanopayment_client=settlement_client,
            http_client=http_client,
            auto_topup_enabled=False,
            strict_settlement=True,
        )

        if not args.mock_settlement:
            bal = await buyer.get_gateway_balance(nano_key_alias=args.buyer_alias)
            print(f"[buyer] gateway balance: {bal.formatted_available}")
            if Decimal(bal.available_decimal) <= Decimal("0"):
                raise RuntimeError(
                    "Buyer gateway balance is zero. Fund gateway balance before running smoke test."
                )

        result = await adapter.pay_x402_url(
            url=url,
            method="GET",
            nano_key_alias=args.buyer_alias,
        )

    if not result.success:
        raise RuntimeError(f"Payment flow failed: {result}")

    print("[ok] buyer -> seller flow succeeded")
    print(f"     settlement_tx={result.transaction} amount={result.amount_usdc} network={result.network}")
    print(f"     seller_response={result.response_data}")

    if not captured.payload or not captured.accepted:
        raise RuntimeError("Replay check cannot run: no captured paid payload")

    replay_ok, replay_err, _ = await seller.verify_payment_async(
        captured.payload,
        captured.accepted,
        verify_signature=True,
        settle_payment=False,
    )
    if replay_ok:
        raise RuntimeError("Replay protection failed: duplicate payload was accepted")
    print(f"[ok] replay attempt rejected: {replay_err}")

    print("=== Smoke test PASSED ===")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print(f"=== Smoke test FAILED ===\n{exc}")
        raise SystemExit(1)
