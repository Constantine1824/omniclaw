#!/usr/bin/env python3
"""
COMPLETE x402 FLOW DEMO - How Everything Works Together

This demo shows the complete flow of OmniClaw's x402 support:

1. SETUP: Create wallet + vault key
2. GUARD: Budget limits enforced per wallet_id
3. x402 FLOW:
   - Request URL
   - Get 402 response
   - Detect seller capabilities
   - Route to appropriate method
4. EXECUTE: Guard check → Vault key signs → Circle settles

Author: OmniClaw Team
Date: 2026-03-23
"""

import asyncio
from decimal import Decimal


async def demo_complete_flow():
    """
    Complete flow showing how OmniClaw's x402 works with guards.
    """

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           OMNICLAW x402 COMPLETE FLOW                             ║
║                                                                      ║
║  Key Insight: Guards + Gasless Nanopayments = Perfect Together     ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                         STEP 1: SETUP                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User creates a wallet with OmniClaw:                               │
│                                                                      │
│  wallet = await client.create_wallet()                             │
│  wallet_id = wallet.id  # "1314b3bf-e9c5-..."                      │
│                                                                      │
│  User generates a vault key for gasless payments:                   │
│                                                                      │
│  address = await client.generate_key("my-agent")                    │
│  # Creates: 0xaba5705ae09ff41313b10418801015a3a71c1b6e           │
│                                                                      │
│  Now we have:                                                      │
│  ✅ wallet_id - for guards & tracking                               │
│  ✅ vault_key - for signing EIP-3009 (gasless)                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.1)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                     STEP 2: CONFIGURE GUARDS                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User sets up budget guards on wallet_id:                           │
│                                                                      │
│  await client.add_budget_guard(                                    │
│      wallet_id="wallet-123",                                        │
│      daily_limit="100.00",  # Max $100/day                         │
│      hourly_limit="10.00",   # Max $10/hour                        │
│  )                                                                  │
│                                                                      │
│  Now OmniClaw will enforce:                                         │
│  ✅ Daily spending limit: $100                                       │
│  ✅ Hourly spending limit: $10                                       │
│  ✅ Single transaction limit: enforced                               │
│  ✅ Recipient whitelist: configurable                                │
│                                                                      │
│  These guards work for ALL payment types!                           │
│  - On-chain transfers                                                │
│  - x402 URLs (Circle nanopayment)                                   │
│  - x402 URLs (direct)                                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.1)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 3: x402 URL PAYMENT                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  User pays for an API resource:                                    │
│                                                                      │
│  result = await client.pay(                                         │
│      wallet_id="wallet-123",   # REQUIRED - for guards!             │
│      recipient="https://api.example.com/data",                      │
│      amount="0.001"                                                 │
│  )                                                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.1)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    INTERNAL FLOW                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐ │
│  │   OmniClaw  │────▶│  Guard Check    │────▶│  Vault Key      │ │
│  │   pay()     │     │  (wallet_id)    │     │  (Signs EIP-3009)│ │
│  └─────────────┘     └─────────────────┘     └─────────────────┘ │
│                            │                        │              │
│                            │                        │              │
│  ┌─────────────────────────┴────────────────────────┴──────────┐  │
│  │                     STEP 3a: Guard Check                    │  │
│  │                                                               │  │
│  │  1. Check daily budget: $0.00 / $100.00                      │  │
│  │  2. Check hourly budget: $0.00 / $10.00                        │  │
│  │  3. Check single tx limit                                     │  │
│  │  4. If OK → Reserve $0.001 from budget                       │  │
│  │  5. If fail → REJECT payment                                │  │
│  │                                                               │  │
│  │  IF GUARD BLOCKS: Return PaymentResult(success=False)        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     STEP 3b: x402 Flow                        │  │
│  │                                                               │  │
│  │  1. Request URL: GET https://api.example.com/data            │  │
│  │  2. Get 402 Response                                        │  │
│  │  3. Parse accepts[] array                                    │  │
│  │  4. Check seller capabilities                                │  │
│  │                                                               │  │
│  │  SELLER ACCEPTS:                                            │  │
│  │  ├─ "GatewayWalletBatched" → Circle Nanopayment (gasless!)  │  │
│  │  └─ Direct x402 → On-chain transfer                          │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     STEP 3c: Execute                           │  │
│  │                                                               │  │
│  │  IF Circle Nanopayment:                                      │  │
│  │  ├─ Vault key signs EIP-3009 authorization                  │  │
│  │  ├─ Submit to Circle Gateway API                              │  │
│  │  ├─ Circle verifies signature                                 │  │
│  │  ├─ Circle settles on-chain (buyer pays NO gas!)            │  │
│  │  └─ Return result with tx hash                              │  │
│  │                                                               │  │
│  │  IF Direct x402:                                              │  │
│  │  ├─ Transfer USDC from wallet_id                             │  │
│  │  ├─ Wait for confirmation                                    │  │
│  │  └─ Return result with tx hash                              │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.1)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 4: RESULT                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PaymentResult:                                                     │
│  {                                                                 │
│      success: True,                                                 │
│      amount: Decimal("0.001"),                                     │
│      recipient: "https://api.example.com/data",                     │
│      method: PaymentMethod.NANOPAYMENT,                            │
│      status: PaymentStatus.COMPLETED,                              │
│      blockchain_tx: "0x...",                                       │
│      metadata: {                                                   │
│          "guards_passed": ["daily_budget", "hourly_budget"],        │
│          "nanopayment": True,                                      │
│          "payer": "0x...vault_key",                               │
│          "seller": "0x...seller_address",                         │
│      }                                                             │
│  }                                                                 │
│                                                                      │
│  Guard budget updated:                                              │
│  - Daily: $0.001 / $100.00                                        │
│  - Hourly: $0.001 / $10.00                                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.1)

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                      KEY TAKEAWAYS                                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  1. ✅ wallet_id IS REQUIRED for ALL payments                      ║
║     - Enables guard enforcement (budget, rate limits, etc.)           ║
║     - Tracks spending across all payment types                       ║
║                                                                      ║
║  2. ✅ Vault key is used for signing (gasless)                    ║
║     - EIP-3009 authorization via vault key                         ║
║     - User pays NO gas for Circle nanopayments                      ║
║                                                                      ║
║  3. ✅ Guards work for ALL payment types                            ║
║     - On-chain transfers → ✅                                       ║
║     - Circle nanopayment → ✅                                        ║
║     - Direct x402 → ✅                                              ║
║                                                                      ║
║  4. ✅ x402 auto-detection                                         ║
║     - Seller accepts Circle nanopayment? → gasless                  ║
║     - Seller only accepts direct? → on-chain                       ║
║                                                                      ║
║  THE FLOW:                                                         ║
║  client.pay(wallet_id, url, amount)                                 ║
║      │                                                              ║
║      ├─▶ Guard Check (wallet_id) ← BUDGET ENFORCED HERE           ║
║      │                                                              ║
║      ├─▶ x402 Request → 402 Response                                ║
║      │                                                              ║
║      ├─▶ Detect: Circle nanopayment or Direct?                       ║
║      │                                                              ║
║      └─▶ Execute: Vault key signs EIP-3009                         ║
║              │                                                      ║
║              └─▶ Circle settles (gasless!)                          ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")


async def demo_code():
    """Show the actual code users would write."""

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                        CODE EXAMPLES                                 ║
╚══════════════════════════════════════════════════════════════════════╝

# ═══════════════════════════════════════════════════════════════════════
# SETUP
# ═══════════════════════════════════════════════════════════════════════

from omniclaw import OmniClaw

omni = OmniClaw(
    circle_api_key="...",
    entity_secret="...",
    network="BASE-SEPOLIA"  # Use Base Sepolia for x402!
)

# Create wallet (for tracking & guards)
wallet = await omni.create_wallet()
wallet_id = wallet.id

# Generate vault key (for signing)
address = await omni.generate_key("my-agent")

# Configure guards
await omni.add_budget_guard(
    wallet_id=wallet_id,
    daily_limit="100.00",
    hourly_limit="10.00"
)

# ═══════════════════════════════════════════════════════════════════════
# PAY FOR x402 RESOURCE
# ═══════════════════════════════════════════════════════════════════════

# ONE CALL - Guards + Nanopayment + x402 routing = ALL AUTOMATIC!
result = await omni.pay(
    wallet_id=wallet_id,      # REQUIRED for guards!
    recipient="https://api.tavily.ai/search",
    amount="0.002",
    nano_key_alias="my-agent"  # Optional: specify which vault key
)

print(f"Success: {result.success}")
print(f"Method: {result.method}")  # NANOPAYMENT if Circle accepted
print(f"Tx: {result.blockchain_tx}")

# ═══════════════════════════════════════════════════════════════════════
# WHAT HAPPENS INTERNALLY
# ═══════════════════════════════════════════════════════════════════════

# 1. Guard check on wallet_id ✅
#    - Daily budget OK?
#    - Hourly budget OK?
#    - Single tx limit OK?

# 2. Request URL
#    GET https://api.tavily.ai/search

# 3. Get 402 Response
#    Check accepts[] array:
#    - "GatewayWalletBatched"? → Circle Nanopayment (gasless!)
#    - Otherwise → Direct x402 (on-chain)

# 4. Execute
#    - Circle Nanopayment: Vault key signs, Circle settles
#    - Direct x402: On-chain transfer with wallet_id

# 5. Result
#    PaymentResult with guards_passed, tx hash, etc.
""")


async def main():
    await demo_complete_flow()
    print("\n" + "=" * 70)
    await demo_code()


if __name__ == "__main__":
    asyncio.run(main())
