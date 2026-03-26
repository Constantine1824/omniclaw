#!/usr/bin/env python3
"""
SIMPLIFIED FLOW DEMO - How Everything Works Together

This demo shows the SIMPLIFIED flow - ONE call does everything!
Nanopayment is INVISIBLE - developers don't need to know about it.

Author: OmniClaw Team
Date: 2026-03-23
"""

import asyncio


async def demo_complete_flow():
    """Show the simplified flow step by step."""

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           OMNICLAW SIMPLIFIED FLOW DEMO                           ║
║                                                                      ║
║  KEY INSIGHT: Nanopayment is INVISIBLE to developers!              ║
║                                                                      ║
║  1. Create wallet → Auto-enables nanopayment                       ║
║  2. Configure guards → Done                                          ║
║  3. Pay → We handle everything internally                            ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 1: CREATE WALLET                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ONE call creates wallet AND auto-enables nanopayment.               │
│  Developer doesn't need to know nanopayment exists!                  │
│                                                                      │
│  Code:                                                              │
│  ```                                                                 │
│  wallet = await client.create_wallet()                              │
│  wallet_id = wallet.id                                              │
│                                                                      │
│  # That's it! Internally we:                                       │
│  # - Created wallet                                                 │
│  # - Auto-generated nanopayment key                                 │
│  # - Linked to wallet_id                                            │
│  ```                                                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.1)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 2: CONFIGURE GUARDS                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Configure guards on wallet_id. These apply to ALL payments.        │
│                                                                      │
│  Code:                                                              │
│  ```                                                                 │
│  await client.add_budget_guard(                                    │
│      wallet_id=wallet_id,                                          │
│      daily_limit="100.00"                                          │
│  )                                                                  │
│  ```                                                                 │
│                                                                      │
│  Guard kernel works for ALL payment types!                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.1)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 3: PAY                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ONE call. We handle everything internally.                         │
│                                                                      │
│  Code:                                                              │
│  ```                                                                 │
│  result = await client.pay(                                         │
│      wallet_id=wallet_id,                                          │
│      recipient="https://api.seller.com/data",                       │
│      amount="0.001"                                                 │
│  )                                                                  │
│  ```                                                                 │
│                                                                      │
│  Developer doesn't think about nanopayment at all!                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.1)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    WHAT HAPPENS INSIDE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  DEVELOPER CALLS:                                                   │
│                                                                      │
│  client.pay(wallet_id, url, amount)                                 │
│                                                                      │
│  ────────────────────────────────────────────────────────────────  │
│                                                                      │
│  INTERNALLY:                                                        │
│                                                                      │
│  1. GUARD CHECK (wallet_id)                                         │
│     ├─ Check daily budget                                          │
│     ├─ Check hourly budget                                         │
│     ├─ Check recipient whitelist                                    │
│     └─ Check rate limit                                            │
│     └─ If blocked → REJECT                                          │
│                                                                      │
│  2. EXECUTE PAYMENT                                                │
│     └─ Is recipient a URL?                                          │
│         ├─ YES → Request URL                                        │
│         │   └─ Get 402 response                                    │
│         │   └─ Seller accepts Circle nanopayment?                   │
│         │       ├─ YES → Use nanopayment (gasless!)               │
│         │       └─ NO  → Use direct x402 (on-chain)                │
│         └─ NO  → On-chain transfer via Circle                      │
│                                                                      │
│  3. GUARD RECORD                                                   │
│     └─ Record transaction under wallet_id                           │
│     └─ Update spent amounts                                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.1)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    KEY POINTS TO REMEMBER                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ✅ ONE IDENTITY: wallet_id                                         │
│     - Guard kernel tracks everything here                           │
│     - ALL payments go through this                                  │
│                                                                      │
│  ✅ NANOPAYMENT IS INVISIBLE                                      │
│     - Auto-enabled on wallet creation                               │
│     - Developer doesn't need to know                                 │
│     - We handle routing automatically                               │
│                                                                      │
│  ✅ Guard kernel works uniformly                                     │
│     - On-chain payments → ✅                                        │
│     - Direct x402 → ✅                                              │
│     - Nanopayments → ✅                                             │
│                                                                      │
│  ✅ DEVELOPER ONLY CALLS:                                          │
│     client.pay(wallet_id, recipient, amount)                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")


async def demo_code_examples():
    """Show actual code examples."""

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                        CODE EXAMPLES                                 ║
╚══════════════════════════════════════════════════════════════════════╝

# ═══════════════════════════════════════════════════════════════════════
# SETUP - SIMPLIFIED
# ═══════════════════════════════════════════════════════════════════════

from omniclaw import OmniClaw

client = OmniClaw(
    circle_api_key="...",
    entity_secret="...",
    network="BASE-SEPOLIA"
)

# ONE CALL - Creates agent wallet AND auto-enables everything
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# That's it! Guards auto-applied, nanopayment auto-enabled.


# ═══════════════════════════════════════════════════════════════════════
# PAY - SIMPLIFIED
# ═══════════════════════════════════════════════════════════════════════

# ONE CALL - We handle everything internally!
result = await client.pay(
    wallet_id=wallet_id,
    recipient="https://api.tavily.ai/search",
    amount="0.002"
)

print(f"Success: {result.success}")
print(f"Method: {result.method}")
print(f"Tx: {result.blockchain_tx}")


# ═══════════════════════════════════════════════════════════════════════
# THAT'S IT!
# ═══════════════════════════════════════════════════════════════════════
#
# Developer doesn't need to know:
# - What nanopayment is
# - How to generate keys
# - How routing works
# - Circle Gateway details
#
# We handle everything invisibly.
#


# ═══════════════════════════════════════════════════════════════════════
# INTERNAL FLOW (for reference only)
# ═══════════════════════════════════════════════════════════════════════

client.pay(wallet_id, url, amount)
         │
         ▼
┌─────────────────────────────────────────┐
│  Guard Check (wallet_id)                │
│  - Daily budget                         │
│  - Hourly budget                        │
│  - Recipients                           │
│  - Rate limits                          │
└─────────────────────────────────────────┘
         │ (pass)
         ▼
┌─────────────────────────────────────────┐
│  Request URL                           │
│  Get 402 Response                      │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Seller accepts Circle nanopayment?     │
└─────────────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
  YES        NO
    │         │
    ▼         ▼
┌───────────────────┐ ┌──────────────────┐
│  NANOPAYMENT      │ │  Direct x402     │
│  (gasless!)       │ │  (on-chain)       │
│  Auto-used!       │ │                   │
└───────────────────┘ └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Guard records under wallet_id           │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  Return PaymentResult                    │
└─────────────────────────────────────────┘
""")


async def main():
    await demo_complete_flow()
    print("\n" + "=" * 70 + "\n")
    await demo_code_examples()


if __name__ == "__main__":
    asyncio.run(main())
