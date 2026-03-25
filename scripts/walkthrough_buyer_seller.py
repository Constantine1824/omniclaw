#!/usr/bin/env python3
"""
OmniClaw Nanopayments - Complete Buyer/Seller Walkthrough Script

This script walks through the complete scenario:
1. Create buyer agent with key
2. Create seller agent with key
3. Check buyer balance
4. Fund (if needed)
5. Make payment
6. Verify received

Run step by step to understand the flow.
"""

import asyncio
import os
import sys

# Add project to path
PROJECT_ROOT = "/home/abiorh/omnuron-labs/omniclaw"
sys.path.insert(0, PROJECT_ROOT)

# ============================================================================
# STEP 1: SETUP ENVIRONMENT
# ============================================================================

print("=" * 70)
print("STEP 1: ENVIRONMENT SETUP")
print("=" * 70)

# Set your credentials here (or use .env)
os.environ["CIRCLE_API_KEY"] = (
    "TEST_API_KEY:3fc089aeb8f29aca6ef7d3423ad37995:a11e0c4afd034a5a6e228934f18c133a"
)
os.environ["ENTITY_SECRET"] = "215ab50d081424dfb1076ab3d0dbaf7281e57c8be1cfe1e3677dfeabcab7b4c0"
os.environ["OMNICLAW_RPC_URL"] = "https://rpc-amoy.polygon.technology"

from omniclaw import OmniClaw


async def run_step_1():
    # Initialize OmniClaw
    omni = OmniClaw()
    print("✅ OmniClaw initialized successfully!")
    print(f"   Network: eip155:80002 (Polygon Amoy)")
    return omni


omni = asyncio.run(run_step_1())

# ============================================================================
# STEP 2: CREATE BUYER AGENT
# ============================================================================

print("\n" + "=" * 70)
print("STEP 2: CREATE BUYER AGENT")
print("=" * 70)


async def run_step_2():
    # Generate a key for the buyer agent
    buyer_address = await omni.vault.generate_key(alias="buyer_agent", network="eip155:80002")
    print(f"✅ Buyer Agent Created!")
    print(f"   Alias: buyer_agent")
    print(f"   Address: {buyer_address}")
    print(f"   Network: eip155:80002")
    return buyer_address


buyer_address = asyncio.run(run_step_2())

# ============================================================================
# STEP 3: CREATE SELLER AGENT
# ============================================================================

print("\n" + "=" * 70)
print("STEP 3: CREATE SELLER AGENT")
print("=" * 70)


async def run_step_3():
    # Generate a key for the seller agent
    seller_address = await omni.vault.generate_key(alias="seller_agent", network="eip155:80002")
    print(f"✅ Seller Agent Created!")
    print(f"   Alias: seller_agent")
    print(f"   Address: {seller_address}")
    print(f"   Network: eip155:80002")
    return seller_address


seller_address = asyncio.run(run_step_3())

# ============================================================================
# STEP 4: CHECK BUYER BALANCE
# ============================================================================

print("\n" + "=" * 70)
print("STEP 4: CHECK BUYER GATEWAY BALANCE")
print("=" * 70)


async def run_step_4():
    balance = await omni.get_gateway_balance(nano_key_alias="buyer_agent")
    print(f"Buyer Gateway Balance:")
    print(f"   Atomic: {balance.total}")
    print(f"   Formatted: {balance.formatted_total}")
    print(f"   Available: {balance.formatted_available}")

    if float(balance.total) == 0:
        print("\n⚠️  BALANCE IS ZERO!")
        print(f"   To fund, go to: https://console.circle.com/wallets")
        print(f"   Navigate to Faucet → Polygon Amoy → USDC")
        print(f"   Enter address: {await omni.vault.get_address('buyer_agent')}")
        print("\n   Then run this script again!")
        return False

    print("\n✅ Balance is funded! Ready to pay.")
    return True


has_funds = asyncio.run(run_step_4())

if not has_funds:
    print("\n❌ Cannot continue - need funds!")
    sys.exit(1)

# ============================================================================
# STEP 5: MAKE PAYMENT
# ============================================================================

print("\n" + "=" * 70)
print("STEP 5: MAKE PAYMENT (Buyer → Seller)")
print("=" * 70)


async def run_step_5():
    print(f"Payment Details:")
    print(f"   From: {buyer_address}")
    print(f"   To: {seller_address}")
    print(f"   Amount: 0.001 USDC")
    print(f"   Network: eip155:80002")
    print(f"   Key Alias: buyer_agent")
    print()

    result = await omni.nanopayment_adapter.pay_direct(
        seller_address=seller_address,
        amount_usdc="0.001",
        network="eip155:80002",
        nano_key_alias="buyer_agent",
    )

    print(f"Payment Result:")
    print(f"   Success: {result.success}")
    print(f"   Amount: {result.amount_usdc} USDC")
    print(f"   Amount (atomic): {result.amount_atomic}")
    print(f"   Transaction: {result.transaction or 'N/A (delayed settlement)'}")
    print(f"   Payer: {result.payer}")
    print(f"   Seller: {result.seller}")
    print(f"   Network: {result.network}")

    return result


result = asyncio.run(run_step_5())

# ============================================================================
# STEP 6: VERIFY SELLER RECEIVED
# ============================================================================

print("\n" + "=" * 70)
print("STEP 6: VERIFY SELLER RECEIVED PAYMENT")
print("=" * 70)


async def run_step_6():
    balance = await omni.get_gateway_balance(nano_key_alias="seller_agent")
    print(f"Seller Gateway Balance:")
    print(f"   Atomic: {balance.total}")
    print(f"   Formatted: {balance.formatted_total}")


asyncio.run(run_step_6())

# ============================================================================
# COMPLETE
# ============================================================================

print("\n" + "=" * 70)
print("COMPLETE!")
print("=" * 70)
print(f"""
Summary:
  • Buyer Agent: {buyer_address}
  • Seller Agent: {seller_address}
  • Payment: 0.001 USDC
  • Status: {"Success" if result.success else "Failed"}
""")
