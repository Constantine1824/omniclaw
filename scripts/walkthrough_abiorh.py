#!/usr/bin/env python3
"""
THE COMPLETE FLOW - As if you're ABIORH

You help people buy goods online. Sellers now accept USDC via x402.
You want to use OmniClaw to handle everything.

Let's walk through EVERY step you need to take.
"""

import asyncio


async def walkthrough():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   HI ABIORH! Let's set you up to buy goods with USDC via x402      ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    await asyncio.sleep(0.5)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 1: SIGN UP FOR CIRCLE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Before anything, you need a Circle account.                        │
│                                                                      │
│  Go to: https://console.circle.com                                   │
│                                                                      │
│  1. Sign up / Log in                                                │
│  2. Create a new Project                                            │
│  3. Get your API Key and Entity Secret                              │
│                                                                      │
│  You'll get something like:                                          │
│  - API Key: TEST_API_KEY:3fc089aeb8f29aca6ef7d3...                │
│  - Entity Secret: 215ab50d081424dfb1076ab3d0dbaf7281e57...         │
│                                                                      │
│  That's it for Circle! You don't need to understand anything else.   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.5)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 2: SETUP OMNICLAW                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Now you tell OmniClaw your Circle credentials.                      │
│  OmniClaw handles EVERYTHING else.                                  │
│                                                                      │
│  Code:                                                              │
│  ```                                                                 │
│  from omniclaw import OmniClaw                                       │
│                                                                      │
│  client = OmniClaw(                                                  │
│      circle_api_key="YOUR_API_KEY",                                 │
│      entity_secret="YOUR_ENTITY_SECRET",                             │
│      network="BASE-SEPOLIA"  # Use Base Sepolia for testing        │
│  )                                                                  │
│  ```                                                                 │
│                                                                      │
│  That's it! You don't need to understand x402, nanopayments,         │
│  EIP-3009, Circle Gateway, or anything else.                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.5)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 3: CREATE YOUR AGENT WALLET                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ONE call creates everything you need:                               │
│  - Your wallet (to track spending & guards)                          │
│  - Your nanopayment key (for gasless x402 payments)                 │
│  - Links them together (so guards work!)                             │
│                                                                      │
│  Code:                                                              │
│  ```                                                                 │
│  wallet = await client.create_agent_wallet()                        │
│  wallet_id = wallet.id                                              │
│                                                                      │
│  print(f"Your wallet ID: {wallet_id}")                               │
│  # Output: "1314b3bf-e9c5-5c4d-b60c-3ef1e8692b5f"                  │
│  ```                                                                 │
│                                                                      │
│  What happens internally:                                           │
│  ✅ Created Circle wallet                                           │
│  ✅ Generated nanopayment key                                        │
│  ✅ Linked them together                                            │
│  ✅ Applied default guards                                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.5)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 4: FUND YOUR WALLET                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  You only fund ONE wallet - wallet_id!                             │
│                                                                      │
│  OmniClaw handles everything else automatically:                   │
│  - If you pay via nanopayment, we auto-transfer to gateway         │
│  - If you pay via on-chain, we use the wallet directly             │
│                                                                      │
│  Code:                                                              │
│  ```                                                                 │
│  # Fund your wallet with USDC                                       │
│  result = await client.fund_wallet(                                  │
│      wallet_id=wallet_id,                                           │
│      amount="100.00"                                               │
│  )                                                                  │
│  ```                                                                 │
│                                                                      │
│  Or use Circle console to add funds.                                 │
│                                                                      │
│  That's it! You NEVER think about gateway wallets!                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.5)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 5: SET YOUR LIMITS                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  You want to control spending for your customers, right?             │
│  Set up guards - how much can be spent, where, etc.                  │
│                                                                      │
│  Code:                                                              │
│  ```                                                                 │
│  # Set daily spending limit                                         │
│  await client.add_budget_guard(                                      │
│      wallet_id=wallet_id,                                            │
│      daily_limit="1000.00"                                          │
│  )                                                                  │
│                                                                      │
│  # Or limit to specific sellers                                     │
│  await client.add_recipient_guard(                                   │
│      wallet_id=wallet_id,                                            │
│      mode="whitelist",                                               │
│      addresses=[                                                     │
│          "https://api.amazon.com",                                  │
│          "https://api.ebay.com",                                    │
│      ]                                                               │
│  )                                                                  │
│  ```                                                                 │
│                                                                      │
│  OmniClaw will BLOCK any payment that exceeds these limits!          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.5)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 6: BUY SOMETHING!                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  A customer wants to buy something from a seller who accepts x402.   │
│  You just call ONE method:                                          │
│                                                                      │
│  Code:                                                              │
│  ```                                                                 │
│  result = await client.pay(                                          │
│      wallet_id=wallet_id,                                            │
│      recipient="https://seller-api.example.com/checkout",             │
│      amount="25.99"                                                  │
│  )                                                                  │
│                                                                      │
│  print(f"Success: {result.success}")                                 │
│  print(f"Method: {result.method}")                                  │
│  print(f"Transaction: {result.blockchain_tx}")                      │
│  ```                                                                 │
│                                                                      │
│  That's it! You don't think about HOW it works!                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.5)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    WHAT HAPPENS INSIDE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  You call: client.pay(wallet_id, url, amount)                      │
│                                                                      │
│  ────────────────────────────────────────────────────────────────   │
│                                                                      │
│  1. GUARD CHECK                                                    │
│     └─ Is $25.99 within daily limit?                                │
│     └─ Is seller in whitelist?                                      │
│     └─ If NO → BLOCKED!                                             │
│                                                                      │
│  2. REQUEST SELLER                                                 │
│     └─ GET https://seller-api.example.com/checkout                  │
│     └─ Seller says: "402 Payment Required - $25.99 USDC"           │
│                                                                      │
│  3. DETECT PAYMENT METHOD                                          │
│     └─ Seller accepts Circle nanopayment?                            │
│         ├─ YES → Use gasless nanopayment!                          │
│         └─ NO  → Use on-chain payment                              │
│                                                                      │
│  4. EXECUTE PAYMENT                                                │
│     └─ Sign with your private key                                    │
│     └─ Circle verifies & settles                                     │
│     └─ Seller gets paid                                              │
│                                                                      │
│  5. RECORD                                                         │
│     └─ Guard kernel updates: "$25.99 spent today"                    │
│     └─ Transaction logged                                           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")
    await asyncio.sleep(0.5)

    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    WHAT YOU NEVER THINK ABOUT                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  As abiorh, you NEVER need to understand:                         │
│                                                                      │
│  ❌ What x402 is                                                   │
│  ❌ What nanopayment is                                             │
│  ❌ What EIP-3009 means                                           │
│  ❌ What Circle Gateway is                                         │
│  ❌ How signing works                                              │
│  ❌ What "GatewayWalletBatched" means                              │
│  ❌ How routing works                                              │
│                                                                      │
│  You just call:                                                    │
│                                                                      │
│  client.pay(wallet_id, url, amount)                                │
│                                                                      │
│  And it works!                                                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
""")


async def complete_code_example():
    """Show the complete working code."""

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                        COMPLETE WORKING CODE                          ║
╚══════════════════════════════════════════════════════════════════════╝

```python
# ═══════════════════════════════════════════════════════════════════
# ABIORH'S COMPLETE SETUP
# ═══════════════════════════════════════════════════════════════════

from omniclaw import OmniClaw

# 1. Connect to Circle
client = OmniClaw(
    circle_api_key="YOUR_CIRCLE_API_KEY",
    entity_secret="YOUR_CIRCLE_ENTITY_SECRET",
    network="BASE-SEPOLIA"
)

# 2. Create your agent wallet (ONE call does everything!)
wallet = await client.create_agent_wallet()
wallet_id = wallet.id
print(f"Your wallet: {wallet_id}")

# 3. Set spending limits
await client.add_budget_guard(
    wallet_id=wallet_id,
    daily_limit="1000.00"
)

# 4. Fund your wallet (ONE place - we handle gateway automatically!)
result = await client.fund_wallet(
    wallet_id=wallet_id,
    amount="100.00"
)

# 5. Buy stuff!
result = await client.pay(
    wallet_id=wallet_id,
    recipient="https://api.seller.com/checkout",
    amount="25.99"
)

print(f"Payment success: {result.success}")
print(f"Payment method: {result.method}")
print(f"Transaction: {result.blockchain_tx}")

# That's it! You never think about:
# ❌ Gateway wallets
# ❌ Nanopayments
# ❌ x402 protocol
# ❌ EIP-3009
# ❌ Auto-topup
#
# OMNICLAW HANDLES IT ALL!
```


╔══════════════════════════════════════════════════════════════════════╗
║                     WHAT YOU ACTUALLY DO                            ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  1. Sign up for Circle (get API key)                               ║
║  2. Create wallet: client.create_agent_wallet()                   ║
║  3. Set limits: client.add_budget_guard(...)                       ║
║  4. Fund wallet: client.fund_wallet(wallet_id, amount)           ║
║  5. Buy stuff: client.pay(wallet_id, url, amount)                 ║
║                                                                      ║
║  OMNICLAW HANDLES EVERYTHING ELSE!                                 ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")


async def what_omniclaw_does_internally():
    """Show what OmniClaw does that you never see."""

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              WHAT OMNICLAW DOES (THAT YOU NEVER SEE)               ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  create_agent_wallet() internally does:                           ║
║  ──────────────────────────────────────────────────────────────   ║
║  ✅ Create wallet in Circle                                        ║
║  ✅ Generate EOA private key for nanopayments                      ║
║  ✅ Encrypt and store private key securely                         ║
║  ✅ Link nanopayment key to wallet_id                               ║
║  ✅ Register wallet for guard tracking                             ║
║  ✅ Apply default security guards                                   ║
║                                                                      ║
║  pay() internally does:                                           ║
║  ──────────────────────────────────────────────────────────────   ║
║  ✅ Check guard limits (budget, recipients, rate limits)            ║
║  ✅ Make HTTP request to seller                                   ║
║  ✅ Parse 402 response                                             ║
║  ✅ Detect if seller accepts Circle nanopayment                      ║
║  ✅ Check gateway balance                                          ║
║  ✅ AUTO-TOPUP gateway if needed (from wallet_id)                  ║
║  ✅ Sign EIP-3009 authorization (if nanopayment)                  ║
║  ✅ Submit to Circle Gateway                                         ║
║  ✅ Wait for confirmation                                          ║
║  ✅ Update guard ledger                                            ║
║  ✅ Return result to you                                          ║
║                                                                      ║
║  YOU NEVER SEE ANY OF THIS!                                       ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
""")


async def main():
    await walkthrough()
    print("\n" + "=" * 70 + "\n")
    await complete_code_example()
    print("\n" + "=" * 70 + "\n")
    await what_omniclaw_does_internally()


if __name__ == "__main__":
    asyncio.run(main())
