#!/usr/bin/env python3
"""
Developer Walkthrough: How OmniClaw x402 Payments Work

ONE wallet, ONE EOA key, ONE address, TWO payment types
"""

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║        OMNICLAW x402 PAYMENTS - DEVELOPER GUIDE                         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TL;DR - The Flow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    wallet = await client.create_agent_wallet()
    wallet_id = wallet.id

    # ONE address to fund everything
    address = await client.get_payment_address(wallet_id)
    # Developer sends USDC here (from anywhere)

    # BASIC x402 (USDC stays in EOA):
    result = await client.pay(wallet_id, url, amount)

    # NANOPAYMENT (deposit to Gateway first):
    await client.deposit_to_gateway(wallet_id, amount="100.00")
    result = await client.pay(wallet_id, url, amount)  # gasless!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP BY STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Create Wallet
───────────────────────────────────────────────────────────────────────────────
    wallet = await client.create_agent_wallet()
    wallet_id = wallet.id

    This creates:
    - Circle Wallet (for Circle operations)
    - NanoKeyVault EOA Key (for signing payments)
    - Linked together via wallet_id


Step 2: Get EOA Address to Fund
───────────────────────────────────────────────────────────────────────────────
    address = await client.get_payment_address(wallet_id)
    print(f"Fund this address with USDC: {address}")

    This is the SAME address for:
    - Basic x402 (USDC stays here)
    - Nanopayment (deposit from here to Gateway)


Step 3: Fund the Address
───────────────────────────────────────────────────────────────────────────────
    Send USDC to this address from anywhere:
    - Another wallet
    - Crypto exchange
    - Friend

    This is just a regular Ethereum address. No custody!


Step 4: Pay - Choose Your Method
───────────────────────────────────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  BASIC x402 (On-chain transfer)                                       │
    │                                                                         │
    │  • USDC stays in EOA                                                  │
    │  • Each payment is on-chain                                           │
    │  • Gas usually paid by seller/facilitator                              │
    │                                                                         │
    │  Code:                                                                │
    │      result = await client.pay(wallet_id, url, amount)                │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────┐
    │  NANOPAYMENT (Off-chain, gasless)                                     │
    │                                                                         │
    │  • First: Deposit USDC to Gateway (one-time on-chain)                 │
    │  • Then: Payments are off-chain (Circle pays gas)                      │
    │  • Great for high-frequency, small payments                            │
    │                                                                         │
    │  Code:                                                                │
    │      await client.deposit_to_gateway(wallet_id, amount="100.00")      │
    │      result = await client.pay(wallet_id, url, amount)                │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHERE IS USDC?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────────────────┐
│  BASIC x402                                                             │
│                                                                              │
│   You (or exchange) sends USDC to EOA address                              │
│                    │                                                     │
│                    ▼                                                     │
│   ┌───────────────────────────────┐                                     │
│   │  EOA Address                │ ← USDC lives here for basic x402     │
│   └───────────────────────────────┘                                     │
│                    │                                                     │
│                    │ EIP-3009 transfer (on-chain)                         │
│                    ▼                                                     │
│               Seller gets paid                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  NANOPAYMENT                                                             │
│                                                                              │
│   EOA Address                                                            │
│                    │                                                     │
│                    │ deposit_to_gateway() (on-chain, you pay gas)          │
│                    ▼                                                     │
│   ┌───────────────────────────────┐                                     │
│   │  Circle Gateway Contract     │ ← USDC deposited here                  │
│   └───────────────────────────────┘                                     │
│                    │                                                     │
│                    │ Off-chain transfer (NO gas per payment!)             │
│                    ▼                                                     │
│               Seller gets paid                                           │
│               (Circle batches and settles later)                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLETE CODE EXAMPLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    from omniclaw import OmniClaw

    # 1. Initialize
    client = OmniClaw(
        circle_api_key="YOUR_KEY",
        network="BASE-SEPOLIA"
    )

    # 2. Create wallet (generates EOA key automatically)
    wallet = await client.create_agent_wallet()
    wallet_id = wallet.id

    # 3. Get address to fund
    address = await client.get_payment_address(wallet_id)
    print(f"Fund this address: {address}")
    # Developer sends USDC here

    # 4. Add spending controls (optional)
    await client.add_budget_guard(wallet_id, daily_limit="1000.00")
    await client.add_single_tx_guard(wallet_id, max_amount="100.00")

    # 5. CHOOSE YOUR PAYMENT METHOD:

    # For BASIC x402 (on-chain):
    result = await client.pay(wallet_id, "https://api.weather.com", "0.05")

    # For NANOPAYMENT (off-chain, gasless):
    # First deposit USDC to Gateway:
    await client.deposit_to_gateway(wallet_id, amount="50.00")
    # Then pay (no gas per payment!):
    result = await client.pay(wallet_id, "https://api.weather.com", "0.05")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPARISON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────┬──────────────────────┬──────────────────────────┐
│                 │  BASIC x402          │  NANOPAYMENT             │
├─────────────────┼──────────────────────┼──────────────────────────┤
│ USDC Location   │ EOA Address          │ Gateway Contract         │
│ Gas             │ Usually seller pays  │ Circle pays (batched)   │
│ Speed           │ Immediate            │ Immediate (off-chain)    │
│ Best For        │ One-time payments    │ High-frequency payments  │
│ Setup           │ Fund EOA             │ Fund EOA + deposit       │
└─────────────────┴──────────────────────┴──────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KEY METHODS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    get_payment_address(wallet_id)
        → Returns EOA address to fund

    deposit_to_gateway(wallet_id, amount)
        → Deposits USDC from EOA to Gateway
        → Needed for nanopayment (one-time)

    pay(wallet_id, recipient, amount)
        → Works for both basic x402 AND nanopayment
        → If Gateway has balance → uses nanopayment
        → If EOA has balance → uses basic x402

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
