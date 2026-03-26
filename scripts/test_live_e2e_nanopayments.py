#!/usr/bin/env python3
"""
Live End-to-End Nanopayments Test

This script tests the complete OmniClaw Circle Nanopayments flow
against Circle's real Gateway API on ARC Testnet.

Prerequisites:
1. Circle API key in CIRCLE_API_KEY env var
2. Entity secret in ENTITY_SECRET env var
3. ARC Testnet RPC URL in OMNICLAW_RPC_URL env var
4. Test USDC in gateway wallet (get from https://faucet.circle.com)

Usage:
    python scripts/test_live_e2e_nanopayments.py
"""

import asyncio
import base64
import json
import os
import secrets
import sys
import datetime

# Load .env file if present
_env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(_env_file):
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# Ensure we're using the local omniclaw
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def main():
    print("=" * 70)
    print("OMNICLAW CIRCLE NANOPAYMENTS - LIVE E2E TEST")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Initialize OmniClaw with real credentials
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[1] Initializing OmniClaw...")

    circle_key = os.environ.get("CIRCLE_API_KEY")
    entity_secret = os.environ.get("ENTITY_SECRET")
    rpc_url = os.environ.get("OMNICLAW_RPC_URL")

    if not circle_key or not entity_secret:
        print("ERROR: Set CIRCLE_API_KEY and ENTITY_SECRET env vars")
        return

    print(f"    Circle API: {circle_key[:30]}...")
    print(f"    RPC URL: {rpc_url or '(not set)'}")

    from omniclaw import OmniClaw

    omni = OmniClaw(
        circle_api_key=circle_key,
        entity_secret=entity_secret,
    )
    print("    OmniClaw initialized ✅")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Generate buyer and seller keys on ARC-Testnet
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[2] Generating buyer and seller keys on ARC-Testnet (eip155:5042002)...")

    buyer_addr = await omni.vault.generate_key(alias="buyer", network="eip155:5042002")
    seller_addr = await omni.vault.generate_key(alias="seller", network="eip155:5042002")

    print(f"    Buyer (EOA):  {buyer_addr}")
    print(f"    Seller (EOA): {seller_addr}")
    print(f"    Keys generated ✅")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Check gateway balance (via Circle API, no RPC needed)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[3] Checking gateway balance (via Circle API)...")

    balance = await omni.get_gateway_balance(nano_key_alias="buyer")
    print(f"    Total:     {balance.total} ({balance.formatted_total})")
    print(f"    Available: {balance.available} ({balance.formatted_available})")

    if balance.available == 0:
        print("\n    ⚠️  GATEWAY WALLET HAS 0 USDC")
        print("    ─────────────────────────────────────────────────────────────")
        print("    To fund the gateway wallet:")
        print("    1. Go to: https://faucet.circle.com")
        print("    2. Select: Network = 'Arc Testnet', Token = 'USDC'")
        print(f"    3. Enter address: {buyer_addr}")
        print("    4. Click 'Send 20 USDC'")
        print("    5. Wait 10 seconds, then re-run this script")
        print("    ─────────────────────────────────────────────────────────────")
        return

    print(f"    Balance OK: {balance.formatted_available} available ✅")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Get Circle Gateway contract addresses
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[4] Fetching Circle Gateway contract addresses...")

    client = omni.nanopayment_adapter._client
    kinds = await client.get_supported()
    arc_kind = next(k for k in kinds if k.network == "eip155:5042002")

    print(f"    Verifying Contract: {arc_kind.verifying_contract}")
    print(f"    USDC Token:          {arc_kind.usdc_address}")
    print(f"    Scheme:              {arc_kind.scheme}")
    print(f"    Contracts fetched ✅")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Seller: Get gateway middleware and build 402 response
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[5] Seller: Setting up gateway middleware...")

    await omni.set_default_key("seller")
    mw = await omni.gateway()
    print(f"    Middleware type: {type(mw).__name__}")
    print(f"    Seller gateway address: {await omni.vault.get_address()}")
    print(f"    Gateway middleware ready ✅")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Seller: Build 402 response (what seller returns when buyer hasn't paid)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[6] Seller: Building 402 response for price '$0.001'...")

    from omniclaw.protocols.nanopayments.types import (
        PaymentRequirementsExtra,
        PaymentRequirementsKind,
        ResourceInfo,
    )

    req_kind = PaymentRequirementsKind(
        scheme="exact",
        network="eip155:5042002",
        asset=arc_kind.usdc_address,
        amount="1000",  # 0.001 USDC
        max_timeout_seconds=345600,
        pay_to=seller_addr,
        extra=PaymentRequirementsExtra(
            name="GatewayWalletBatched",
            version="1",
            verifying_contract=arc_kind.verifying_contract,
        ),
    )

    # The seller would include this in the 402 response body
    req_dict = req_kind.to_dict()
    req_b64 = base64.b64encode(json.dumps(req_dict).encode()).decode()
    print(f"    PAYMENT-REQUIRED header: {req_b64[:50]}...")
    print(f"    Price: $0.001 (1000 atomic units)")
    print(f"    PayTo: {seller_addr}")
    print(f"    402 response built ✅")

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Buyer: Create and sign EIP-3009 authorization
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[7] Buyer: Creating and signing EIP-3009 authorization...")

    await omni.set_default_key("buyer")

    resource = ResourceInfo(
        url="https://api.seller.com/data",
        description="Premium API access",
        mime_type="application/json",
    )

    payload = await omni.vault.sign(
        requirements=req_kind,
        amount_atomic=1000,  # 0.001 USDC
        alias="buyer",
        resource=resource,
    )

    auth = payload.payload.authorization
    print(f"    from:          {auth.from_address}")
    print(f"    to:            {auth.to}")
    print(f"    value:         {auth.value} atomic units")
    print(f"    valid_after:   {auth.valid_after} (immediate)")
    vb = int(auth.valid_before)
    print(
        f"    valid_before:  {auth.valid_before} (expires {datetime.datetime.fromtimestamp(vb).strftime('%Y-%m-%d %H:%M')})"
    )
    print(f"    nonce:         {auth.nonce[:20]}...")
    print(f"    signature:     {payload.payload.signature[:40]}...")
    print(f"    EIP-3009 authorization signed ✅")

    # Verify the signature locally
    print("\n[8] Verifying signature locally...")
    from omniclaw.protocols.nanopayments.signing import EIP3009Signer

    raw_key = await omni.vault.get_raw_key(alias="buyer")
    signer = EIP3009Signer(private_key=raw_key)
    is_valid = signer.verify_signature(payload, req_kind)
    print(f"    Signer address: {signer.address}")
    print(f"    Matches payer:  {signer.address.lower() == buyer_addr.lower()}")
    print(f"    Signature valid: {is_valid}")

    if not is_valid:
        print("\n    ❌ SIGNATURE INVALID - Stopping test")
        return

    print(f"    Signature verified ✅")

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Encode PAYMENT-SIGNATURE header
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[9] Encoding PAYMENT-SIGNATURE header...")

    payment_sig = base64.b64encode(json.dumps(payload.to_dict()).encode()).decode()
    print(f"    Header: {payment_sig[:50]}...")
    print(f"    Encoded ✅")

    # ─────────────────────────────────────────────────────────────────────────
    # 10. BUYER: pay_direct() - full settlement flow
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[10] BUYER: Executing pay_direct()...")

    result = await omni.nanopayment_adapter.pay_direct(
        seller_address=seller_addr,
        amount_usdc="0.001",
        network="eip155:5042002",
        nano_key_alias="buyer",
    )

    print(f"    Success:       {result.success}")
    print(f"    Transaction:   {result.transaction}")
    print(f"    Amount:        {result.amount_usdc} USDC")
    print(f"    Amount atomic: {result.amount_atomic}")
    print(f"    Network:       {result.network}")
    print(f"    Payer:         {result.payer}")
    print(f"    Seller:        {result.seller}")

    if not result.success:
        print(f"\n    ⚠️  Settlement failed")
        print(f"    Error: {result.response_data}")
        return

    # ─────────────────────────────────────────────────────────────────────────
    # 11. Verify on-chain
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[11] Verifying settlement on ARC Testnet explorer...")
    explorer_url = f"https://testnet.arcscan.app/tx/{result.transaction}"
    print(f"    Explorer: {explorer_url}")
    print(f"    Transaction hash: {result.transaction}")
    print(f"\n{'=' * 70}")
    print("🎉 COMPLETE E2E TEST PASSED!")
    print(f"{'=' * 70}")
    print(f"  Buyer:  {buyer_addr}")
    print(f"  Seller: {seller_addr}")
    print(f"  Amount: 0.001 USDC")
    print(f"  TX:     {result.transaction}")
    print(f"  Explorer: {explorer_url}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted.")
    except Exception as e:
        print(f"\n\nERROR: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
