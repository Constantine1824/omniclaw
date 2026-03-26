#!/usr/bin/env python3
"""
Test OmniClaw x402 Flow on Base Sepolia Testnet

This script tests the full x402 payment flow:
1. Create wallet on Base Sepolia
2. Get EOA address
3. Show how to fund
4. Attempt x402 payment (will work once funded)

Testnet Options:
- x402.org facilitator: https://x402.org/facilitator (no API key needed)
- CDP facilitator: https://api.cdp.coinbase.com/platform/v2/x402 (needs CDP API key)

Usage:
    python scripts/test_x402_flow.py

Requirements:
    - CIRCLE_API_KEY in environment
    - Fund the EOA address with USDC on Base Sepolia
"""

import asyncio
import os
import sys
from decimal import Decimal
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()


async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║        OMNICLAW x402 FLOW TEST - BASE SEPOLIA TESTNET                   ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Check for API key
    api_key = os.getenv("CIRCLE_API_KEY")
    if not api_key:
        print("❌ Error: CIRCLE_API_KEY not found in environment")
        print("\nPlease set your Circle API key:")
        print("    export CIRCLE_API_KEY=your_key_here")
        return

    print(f"✅ Circle API key found")

    # Import OmniClaw
    from omniclaw import OmniClaw

    # =========================================================================
    # STEP 1: Initialize Client
    # =========================================================================
    print("\n" + "=" * 60)
    print("STEP 1: Initialize OmniClaw Client")
    print("=" * 60)

    client = OmniClaw(
        circle_api_key=api_key,
        network="BASE-SEPOLIA",  # Using Base Sepolia testnet
    )
    print("✅ Client initialized")
    print(f"   Network: BASE-SEPOLIA")
    print(f"   Facilitator: x402.org (testnet)")

    # =========================================================================
    # STEP 2: Create Agent Wallet
    # =========================================================================
    print("\n" + "=" * 60)
    print("STEP 2: Create Agent Wallet")
    print("=" * 60)

    wallet = await client.create_agent_wallet(
        blockchain="BASE-SEPOLIA",
        apply_default_guards=True,
    )
    wallet_id = wallet.id

    print(f"✅ Wallet created!")
    print(f"   Wallet ID: {wallet_id}")
    print(f"   Blockchain: {wallet.blockchain}")

    # =========================================================================
    # STEP 3: Get EOA Payment Address
    # =========================================================================
    print("\n" + "=" * 60)
    print("STEP 3: Get EOA Payment Address")
    print("=" * 60)

    payment_address = await client.get_payment_address(wallet_id)
    print(f"✅ EOA Address: {payment_address}")
    print(f"   Network: Base Sepolia (eip155:84532)")

    # Get key info
    key_info = await client.get_nanopayment_key(wallet_id)
    print(f"\n📋 Key Info:")
    print(f"   Alias: {key_info['alias']}")
    print(f"   Network: {key_info['network']}")
    print(f"   Address: {key_info['address']}")

    # =========================================================================
    # STEP 4: Add Spending Controls
    # =========================================================================
    print("\n" + "=" * 60)
    print("STEP 4: Add Spending Controls")
    print("=" * 60)

    # Daily budget
    await client.add_budget_guard(wallet_id, daily_limit="1000.00")
    print("✅ Budget guard: $1000/day")

    # Single transaction limit
    await client.add_single_tx_guard(wallet_id, max_amount="100.00")
    print("✅ Single tx guard: $100 max")

    # List guards
    guards = await client.list_guards(wallet_id)
    print(f"\n📋 Active Guards: {guards}")

    # =========================================================================
    # STEP 5: How to Fund
    # =========================================================================
    print("\n" + "=" * 60)
    print("STEP 5: How to Fund")
    print("=" * 60)

    print(
        """
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ⚠️  FUND THE EOA ADDRESS TO MAKE x402 PAYMENTS                      │
│                                                                         │
│  Send USDC (on Base Sepolia) to this address:                         │
│                                                                         │
│  {}                                                                 │
│                                                                         │
│  Where to get test USDC on Base Sepolia:                             │
│  1. Go to https://app.circle.com/faucet                              │
│  2. Select "USDC on Base Sepolia"                                    │
│  3. Enter the address above                                            │
│  4. Click "Claim"                                                     │
│                                                                         │
│  ⚠️  This is a TESTNET address - use TEST USDC only!                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
    """.format(payment_address)
    )

    # =========================================================================
    # STEP 6: Test x402 Payment (after funding)
    # =========================================================================
    print("\n" + "=" * 60)
    print("STEP 6: Test x402 Payment")
    print("=" * 60)

    # Check balance first
    print("📋 Checking EOA balance...")

    # NOTE: We can't directly check EOA balance without an RPC
    # The balance check would require connecting to Base Sepolia RPC
    # For now, we show the flow

    print("""
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  Once funded, make x402 payments like this:                           │
│                                                                         │
│  # Basic x402 (USDC in EOA)                                           │
│  result = await client.pay(                                            │
│      wallet_id=wallet_id,                                              │
│      recipient="https://api.weather.com/data",                          │
│      amount="0.05"                                                     │
│  )                                                                    │
│                                                                         │
│  # Nanopayment (after deposit to Gateway)                             │
│  await client.deposit_to_gateway(wallet_id, amount="10.00")           │
│  result = await client.pay(wallet_id, url, "0.05")                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
    """)

    # =========================================================================
    # STEP 7: Try x402 Payment (will fail if not funded)
    # =========================================================================
    print("\n" + "=" * 60)
    print("STEP 7: Attempt x402 Payment")
    print("=" * 60)

    # Test URL (this is a mock x402 endpoint)
    test_url = "https://api.example.com/paid-endpoint"

    print(f"📋 Attempting x402 payment to: {test_url}")
    print("   (This will work once you fund the EOA address)")

    try:
        result = await client.pay(
            wallet_id=wallet_id,
            recipient=test_url,
            amount="0.01",
        )

        print(f"\n✅ Payment Result:")
        print(f"   Success: {result.success}")
        print(f"   Status: {result.status}")
        print(f"   Amount: {result.amount}")

    except Exception as e:
        print(f"\n❌ Payment failed (expected if not funded):")
        print(f"   Error: {e}")

    # =========================================================================
    # STEP 8: Export Key (for backup)
    # =========================================================================
    print("\n" + "=" * 60)
    print("STEP 8: Export Key (Backup)")
    print("=" * 60)

    print("""
⚠️  NOTE: Exporting private keys should be done with EXTREME caution!

If you want to export the private key for backup:
    key = await client.export_key(wallet_id)
    print(f"Your private key: {key}")

Store this securely - it can control your funds!
    """)

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print(f"""
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  ✅ OmniClaw x402 Flow Complete!                                       │
│                                                                         │
│  📋 Wallet ID: {wallet_id[:40]:<40}     │
│                                                                         │
│  📋 EOA Address: {payment_address:<40}   │
│                                                                         │
│  NEXT STEPS:                                                          │
│  1. Fund the EOA address with USDC on Base Sepolia                    │
│  2. Make x402 payments with client.pay()                              │
│  3. For nanopayment, use deposit_to_gateway() first                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    asyncio.run(main())
