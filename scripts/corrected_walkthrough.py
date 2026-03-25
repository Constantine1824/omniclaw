#!/usr/bin/env python3
"""
OmniClaw Nanopayments - CORRECTED Buyer/Seller Walkthrough

KEY POINT:
- Buyer needs a key (to sign payments)
- Seller just needs to provide their address (no key needed!)
"""

import asyncio
import os
import sys

PROJECT_ROOT = "/home/abiorh/omnuron-labs/omniclaw"
sys.path.insert(0, PROJECT_ROOT)

print("=" * 70)
print("OMNICLAW - CORRECTED BUYER/SELLER FLOW")
print("=" * 70)

# Setup
os.environ["CIRCLE_API_KEY"] = (
    "TEST_API_KEY:3fc089aeb8f29aca6ef7d3423ad37995:a11e0c4afd034a5a6e228934f18c133a"
)
os.environ["ENTITY_SECRET"] = "215ab50d081424dfb1076ab3d0dbaf7281e57c8be1cfe1e3677dfeabcab7b4c0"
os.environ["OMNICLAW_RPC_URL"] = "https://rpc-amoy.polygon.technology"

from omniclaw import OmniClaw


async def main():
    omni = OmniClaw()

    # ========================================================================
    # STEP 1: CREATE BUYER AGENT (needs key for signing!)
    # ========================================================================
    print("\n[STEP 1] Creating Buyer Agent (needs key)...")

    buyer_address = await omni.vault.generate_key(alias="buyer_agent", network="eip155:80002")
    print(f"✅ Buyer created!")
    print(f"   Alias: buyer_agent")
    print(f"   Address: {buyer_address}")
    print(f"   Has private key: YES (stored in vault)")

    # ========================================================================
    # STEP 2: SELLER - Just give us their address!
    # ========================================================================
    print("\n[STEP 2] Seller Setup (just needs address!)...")

    # Option A: Use any existing Ethereum address (from MetaMask, etc.)
    # Just paste their address here:
    seller_address = "0x seller put your address here"  # Replace with real address

    # Option B: If they don't have one, create one (optional)
    # seller_address = await omni.vault.generate_key("seller_wallet", "eip155:80002")

    print(f"✅ Seller identified!")
    print(f"   Address: {seller_address}")
    print(f"   Has private key: NO (not needed!)")

    # ========================================================================
    # STEP 3: Check Buyer Balance
    # ========================================================================
    print("\n[STEP 3] Checking Buyer Gateway Balance...")

    balance = await omni.get_gateway_balance(nano_key_alias="buyer_agent")
    print(f"   Balance: {balance.formatted_total}")

    if float(balance.total) == 0:
        print(f"\n⚠️  Need to fund buyer!")
        print(f"   Address: {buyer_address}")
        print(f"   Go to Circle Console → Faucet → Polygon Amoy → USDC")
        return

    # ========================================================================
    # STEP 4: Make Payment
    # ========================================================================
    print("\n[STEP 4] Making Payment...")
    print(f"   From (signer): {buyer_address}")
    print(f"   To (recipient): {seller_address}")
    print(f"   Amount: 0.001 USDC")

    result = await omni.nanopayment_adapter.pay_direct(
        seller_address=seller_address,  # ← Just an address string
        amount_usdc="0.001",
        network="eip155:80002",
        nano_key_alias="buyer_agent",  # ← Uses BUYER's key to sign
    )

    print(f"\n   Result:")
    print(f"   Success: {result.success}")
    print(f"   Amount: {result.amount_usdc} USDC")
    print(f"   TX: {result.transaction or 'delayed batch settlement'}")


asyncio.run(main())
