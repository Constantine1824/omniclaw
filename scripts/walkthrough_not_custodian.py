#!/usr/bin/env python3
"""
Developer Walkthrough: How OmniClaw Works - NO CUSTODY

OmniClaw is NOT a custodian. Here's why:

1. We NEVER hold USDC - USDC stays in developer's EOA address
2. We NEVER move USDC without developer's command (pay())
3. We generate keys, but developer can delete their vault anytime
4. Developer funds their own address from their own wallet
"""

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║        OMNICLAW - NOT A CUSTODIAN                                      ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHY WE'RE NOT A CUSTODIAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  WE NEVER HOLD YOUR USDC                                                   │
│                                                                              │
│  • USDC stays in YOUR EOA address (0x123...abc)                          │
│  • YOU fund the EOA from your own wallet/exchange                         │
│  • WE never touch the USDC - we just sign payments when you ask           │
│  • For nanopayment, YOU call deposit_to_gateway() - we don't move it    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  WE NEVER MOVE YOUR FUNDS WITHOUT YOUR COMMAND                            │
│                                                                              │
│  • pay() - YOU call this to make payments                                 │
│  • deposit_to_gateway() - YOU call this to deposit to Gateway             │
│  • We just execute what you command                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE FLOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    1. Create Wallet (we generate key, store in YOUR vault)
    ┌─────────────────────────────────────────────────────────────────────┐
    │  wallet = await client.create_agent_wallet()                       │
    │  wallet_id = wallet.id                                             │
    │  // We're just generating infrastructure here                       │
    └─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    2. Get EOA Address (for YOU to fund)
    ┌─────────────────────────────────────────────────────────────────────┐
    │  address = await client.get_payment_address(wallet_id)              │
    │  // Output: 0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0           │
    │                                                                              │
    │  YOU send USDC from your wallet to this address                       │
    │  (Exchange, MetaMask, Ledger - anywhere)                              │
    └─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    3. Pay (YOU control when)
    ┌─────────────────────────────────────────────────────────────────────┐
    │  result = await client.pay(wallet_id, url, amount)                 │
    │                                                                              │
    │  // We sign the payment (EIP-3009)                                    │
    │  // USDC moves from YOUR EOA → Seller                                 │
    │  // YOU called pay(), we just sign                                     │
    └─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
    4. For Nanopayment (YOU control when)
    ┌─────────────────────────────────────────────────────────────────────┐
    │  await client.deposit_to_gateway(wallet_id, amount="100")          │
    │                                                                              │
    │  // YOU call this - we deposit from YOUR EOA to Gateway            │
    │  // Now nanopayments work                                             │
    │                                                                              │
    │  result = await client.pay(wallet_id, url, amount)                 │
    │  // Gasless! Circle pays gas from the batch                          │
    └─────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLETE CODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    from omniclaw import OmniClaw

    # 1. Initialize - bring your Circle API key
    client = OmniClaw(
        circle_api_key="YOUR_CIRCLE_API_KEY",
        network="BASE-SEPOLIA"
    )

    # 2. Create wallet - we generate fresh keys, store in YOUR vault
    wallet = await client.create_agent_wallet()
    wallet_id = wallet.id

    # 3. Get YOUR address - YOU fund this
    address = await client.get_payment_address(wallet_id)
    print(f"Fund this address with USDC: {address}")
    # Send USDC from your wallet/exchange to this address

    # 4. Export your key (optional - for backup or use elsewhere)
    private_key = await client.export_key(wallet_id)
    # Store this securely!

    # 5. Add controls
    await client.add_budget_guard(wallet_id, daily_limit="1000.00")

    # 6. Pay - YOUR command
    result = await client.pay(wallet_id, "https://api.weather.com", "0.05")

    # 7. For nanopayment - YOUR command
    await client.deposit_to_gateway(wallet_id, amount="50.00")
    result = await client.pay(wallet_id, "https://api.weather.com", "0.05")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHO CONTROLS WHAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────┬───────────────────────────────────────────────┐
│  OMNICLAW DOES         │  DEVELOPER CONTROLS                           │
├─────────────────────────┼───────────────────────────────────────────────┤
│ Generate EOA key        │ When to fund address                          │
│ Store key encrypted     │ How much to fund                              │
│ Sign when pay() called  │ When to call pay()                            │
│ Route payments          │ When to deposit to Gateway                     │
│ Provide infrastructure  │ How much to deposit to Gateway                │
└─────────────────────────┴───────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  OMNICLAW CANNOT:                                                     │
│                                                                          │
│  ❌ Access your USDC without you calling pay()                        │
│  ❌ Move USDC without your command                                      │
│  ❌ See your private key (encrypted, stored in your vault)             │
│  ❌ Delete your funds                                                   │
│  ❌ Control when payments happen                                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TECHNICAL DETAILS (for transparency)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What We Generate:
───────────────────────────────────────────────────────────────────────────────
• EOA private key (stored encrypted in developer's vault)
• EOA address (derived from private key)
• Circle Wallet (for Circle operations)
• Linked tracking via wallet_id

What's Stored Where:
───────────────────────────────────────────────────────────────────────────────
• Encrypted EOA key: Developer's vault (not on our servers)
• Circle Wallet ID: Developer's storage
• Payment tracking: Developer's ledger

What's Standard:
───────────────────────────────────────────────────────────────────────────────
• EOA address is just an Ethereum address
• Private key is standard EVM format
• USDC stays in standard ERC-20 contract
• No proprietary tokens or locked funds

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
