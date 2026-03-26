#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║           ABIORH ENTERPRISE - COMPLETE OMNICLAW WALKTHROUGH            ║
║                                                                          ║
║   Your AI agents pay for goods, services, resources, and transfers    ║
║   Everything you need to know about OmniClaw for agent payments        ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

TABLE OF CONTENTS:
══════════════════════════════════════════════════════════════════════════════

PART 1: SETUP & ONBOARDING
  1.1 - What You Need (Just Circle API Key!)
  1.2 - Check Your Setup with Doctor
  1.3 - Initialize OmniClaw Client

PART 2: WALLET MANAGEMENT
  2.1 - Create Agent Wallet (One Call Does Everything)
  2.2 - Fund Your Wallet
  2.3 - Check Balances
  2.4 - Multiple Agents / Multiple Wallets
  2.5 - Wallet Sets (Group-level Controls)

PART 3: SECURITY GUARDS (The Guard Kernel!)
  3.1 - Guard Kernel Overview
  3.2 - Budget Guards (Daily/Hourly Limits)
  3.3 - Single Transaction Limits
  3.4 - Recipient Whitelists/Blacklists
  3.5 - Rate Limiting
  3.6 - Human Confirmation for Large Payments
  3.7 - List & Remove Guards
  3.8 - Guard Chain (How Guards Work Together)

PART 4: TRUST GATE (ERC-8004 Identity Checks)
  4.1 - What is Trust Gate?
  4.2 - Trust Policies
  4.3 - Enable/Disable Trust Checks

PART 5: PAYMENT SCENARIOS (The Meat!)
  5.1 - Pay for x402 Resources (Web APIs, Data, Content)
  5.2 - Pay Another Address (Same Chain - Direct Transfer)
  5.3 - Pay Another Address (Different Chain - Cross-Chain)
  5.4 - Payroll Payments (Batch Payments)
  5.5 - Simulate Before Paying
  5.6 - Payment Intents (2-Phase Commit)

PART 6: THE LEDGER (Transaction History)
  6.1 - View Transaction History
  6.2 - Sync with Blockchain
  6.3 - Ledger Entry Types

PART 7: RESILIENCE & RELIABILITY
  7.1 - Fund Locks (Prevent Double-Spend)
  7.2 - Circuit Breakers
  7.3 - Retry Strategies

PART 8: UNDERSTANDING WHAT HAPPENS INSIDE
  8.1 - How client.pay() Routes Payments
  8.2 - Nanopayment vs Direct x402 vs On-Chain
  8.3 - Network Matching (Why It Matters)
  8.4 - Auto-Topup (How It Works)

PART 9: TROUBLESHOOTING
  9.1 - Common Errors
  9.2 - Debug Mode

══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import os
from decimal import Decimal

# We'll show code examples - actual usage would be:
# from omniclaw import OmniClaw


# ═══════════════════════════════════════════════════════════════════════════════
# PART 1: SETUP & ONBOARDING
# ═══════════════════════════════════════════════════════════════════════════════

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   PART 1: SETUP & ONBOARDING                                           ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 1.1: WHAT YOU NEED (JUST CIRCLE API KEY!)                      ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

NEW USER? Here's ALL you need to get started:

1. Go to https://console.circle.com
2. Sign up for a free account
3. Create a project
4. Get your API Key

That's it! OmniClaw will automatically:
- Generate your Entity Secret
- Register it with Circle
- Save it securely
- Store a recovery file

You don't need to understand Entity Secrets. You don't need to manually create them.
OmniClaw handles it all for you.

OPTION A: Pass API key directly (recommended for getting started)
──────────────────────────────────────────────────────────────────────────
    from omniclaw import OmniClaw
    
    client = OmniClaw(
        circle_api_key="YOUR_CIRCLE_API_KEY",
        network="BASE-SEPOLIA"  # or "POLYGON", "ETHEREUM", etc.
    )

OPTION B: Set environment variables (recommended for production)
──────────────────────────────────────────────────────────────────────────
    # In your .env file:
    CIRCLE_API_KEY=YOUR_CIRCLE_API_KEY
    
    # Then in code:
    client = OmniClaw()  # Reads from .env automatically!

OPTION C: You already have an Entity Secret
──────────────────────────────────────────────────────────────────────────
    # If you already have an Entity Secret from Circle console:
    from omniclaw import OmniClaw
    
    client = OmniClaw(
        circle_api_key="YOUR_API_KEY",
        entity_secret="YOUR_ENTITY_SECRET",  # 64-character hex string
        network="BASE-SEPOLIA"
    )

SUPPORTED NETWORKS:
──────────────────────────────────────────────────────────────────────────
- BASE-SEPOLIA (testnet) - Recommended for testing
- POLYGON-AMOY (testnet) - For Polygon testing  
- ETHEREUM-SEPOLIA (testnet) - For Ethereum testing
- BASE (mainnet) - When ready for production
- POLYGON (mainnet) - Production Polygon
- ETHEREUM (mainnet) - Production Ethereum

"""


async def section_1_2_doctor():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 1.2: CHECK YOUR SETUP WITH DOCTOR                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Before you start, run the doctor to check if everything is set up correctly:

    from omniclaw import doctor, print_doctor_status
    
    # Quick status check
    status = doctor()
    print(f"Ready: {status['ready']}")
    
    # Pretty print
    print_doctor_status()
    
    # Or get JSON for automation
    status_json = doctor(as_json=True)

WHAT DOCTOR CHECKS:
──────────────────────────────────────────────────────────────────────────
✅ Circle SDK installed
✅ CIRCLE_API_KEY set
✅ ENTITY_SECRET set (or can be auto-generated)
✅ Recovery file exists (important for production!)
✅ Managed credentials store

DOCTOR OUTPUT EXAMPLE:
──────────────────────────────────────────────────────────────────────────
    OmniClaw Doctor
    ------------------------------
      [OK] Circle SDK
      [OK] Circle API key
      [MISSING] ENTITY_SECRET in environment
      [OK] Managed entity secret
      [OK] Circle recovery file

      Config dir: /home/user/.config/omniclaw/
      Managed store: /home/user/.config/omniclaw/credentials.json
      Active secret source: managed_config
      Recovery file: /home/user/.config/omniclaw/recovery_file_xxx.dat

    Ready to use.

NEXT STEPS IF NOT READY:
──────────────────────────────────────────────────────────────────────────
- Set CIRCLE_API_KEY in your .env or pass it to OmniClaw()
- OmniClaw will auto-generate ENTITY_SECRET on first use
- Keep your recovery file safe for production!

""")


async def section_1_3_initialize():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 1.3: INITIALIZE OMNICLAW CLIENT                               ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

FULL INITIALIZATION EXAMPLE:
──────────────────────────────────────────────────────────────────────────

    from omniclaw import OmniClaw
    
    # Initialize with your Circle API key
    client = OmniClaw(
        circle_api_key="YOUR_API_KEY",
        network="BASE-SEPOLIA",      # Network for default operations
        log_level="INFO",            # DEBUG for troubleshooting
        trust_policy="standard",     # Trust Gate policy (permissive/standard/strict)
        rpc_url="https://...",       # For ERC-8004 Trust Gate lookups
    )

WHAT HAPPENS DURING INIT:
──────────────────────────────────────────────────────────────────────────
1. Reads credentials from environment or uses provided values
2. If ENTITY_SECRET missing, auto-generates and registers with Circle
3. Saves recovery file to ~/.config/omniclaw/
4. Initializes storage backend for ledger/guards
5. Sets up payment router with all protocols
6. If nanopayments enabled (default), initializes Circle Gateway
7. Initializes Trust Gate for ERC-8004 identity checks

WHAT'S ENABLED BY DEFAULT:
──────────────────────────────────────────────────────────────────────────
✅ Developer-Controlled Wallets (Circle)
✅ x402 Protocol Support
✅ Nanopayments (EIP-3009 gasless payments)
✅ Guard System (budget, rate limits, etc.)
✅ Trust Gate (ERC-8004 identity checks)
✅ Ledger (transaction history)
✅ Fund Locks (double-spend prevention)

""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2: WALLET MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   PART 2: WALLET MANAGEMENT                                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 2.1: CREATE AGENT WALLET (ONE CALL DOES EVERYTHING!)          ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

THIS IS THE KEY METHOD: create_agent_wallet()

One call creates:
- Circle wallet (for on-chain operations)
- Nanopayment key (for gasless x402 payments)
- Links them together (so guards work!)
- Applies default security guards

    wallet = await client.create_agent_wallet(
        blockchain="BASE-SEPOLIA",           # Network for this agent
        apply_default_guards=True,          # Use your configured defaults
    )
    
    wallet_id = wallet.id
    print(f"Agent wallet created: {wallet_id}")

WHAT'S CREATED:
──────────────────────────────────────────────────────────────────────────
✅ Circle Wallet - Your on-chain wallet for USDC
✅ Nanopayment Key - EOA key for gasless payments (auto-generated)
✅ Guard Tracking - All spending tracked under wallet_id
✅ Default Guards - If you configured them in SDK

THE NANOPAYMENT KEY IS IMPORTANT:
──────────────────────────────────────────────────────────────────────────
When you create an agent wallet, OmniClaw auto-generates a SEPARATE
EOA key for nanopayments. This key is:
- Generated and encrypted by OmniClaw
- Stored securely in your vault
- Linked to your wallet_id for tracking
- Used automatically for x402 payments

YOU NEVER SEE THE PRIVATE KEY. OmniClaw handles signing.

"""


async def section_2_2_fund_wallet():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 2.2: FUND YOUR WALLET                                          ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

IMPORTANT: You fund ONE wallet, OmniClaw handles the rest!

    # Option 1: Via code (if your Circle account supports it)
    result = await client.fund_wallet(
        wallet_id=wallet_id,
        amount="100.00"  # USDC
    )
    
    # Option 2: Via Circle Console (recommended for initial funding)
    # 1. Go to https://console.circle.com
    # 2. Find your wallet
    # 3. Add USDC via bank transfer or card

HOW FUNDING WORKS:
──────────────────────────────────────────────────────────────────────────
When you pay via:
- Nanopayment (x402 with gasless): OmniClaw auto-transfers from wallet to gateway
- Direct on-chain: Uses wallet balance directly

YOU NEVER MANUALLY MOVE MONEY TO GATEWAY WALLETS!
OmniClaw handles all internal transfers automatically.

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 2.3: CHECK BALANCES                                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

    # Check wallet balance (Circle wallet)
    balance = await client.get_balance(wallet_id)
    print(f"Wallet balance: {balance} USDC")
    
    # Check gateway balance (for nanopayments)
    gateway_balance = await client.get_gateway_balance(wallet_id)
    print(f"Gateway balance: {gateway_balance} USDC")

BALANCE TYPES:
──────────────────────────────────────────────────────────────────────────
Wallet Balance:
- Your Circle wallet balance
- Used for direct on-chain transfers
- Used as source for auto-topup

Gateway Balance:
- Balance in Circle Gateway for gasless nanopayments
- When low, OmniClaw auto-tops up from wallet
- Only needed for x402 payments with nanopayment

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 2.4: MULTIPLE AGENTS / MULTIPLE WALLETS                        ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

You can create unlimited wallets for different agents/purposes:

    # Agent 1: Shopping assistant
    wallet1 = await client.create_agent_wallet()
    wallet1_id = wallet1.id
    
    # Agent 2: Research assistant
    wallet2 = await client.create_agent_wallet()
    wallet2_id = wallet2.id
    
    # Agent 3: Payroll agent
    wallet3 = await client.create_agent_wallet()
    wallet3_id = wallet3.id

Each wallet has:
- Independent balance
- Independent guards
- Independent nanopayment key
- Isolated spending tracking

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 2.5: WALLET SETS (GROUP-LEVEL CONTROLS)                        ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

WALLET SETS let you apply guards to MULTIPLE wallets at once:

    # Create a wallet set for related agents
    wallet_set = await client.create_wallet_set(name="research-team")
    wallet_set_id = wallet_set.id
    
    # Create wallets in the set
    wallet1 = await client.create_agent_wallet(wallet_set_id=wallet_set_id)
    wallet2 = await client.create_agent_wallet(wallet_set_id=wallet_set_id)
    
    # Apply guards to the SET (applies to ALL wallets in set)
    await client.add_budget_guard_for_set(
        wallet_set_id=wallet_set_id,
        daily_limit="10000.00"
    )
    
    await client.add_rate_limit_guard_for_set(
        wallet_set_id=wallet_set_id,
        max_per_minute=50
    )

WHY USE WALLET SETS?
──────────────────────────────────────────────────────────────────────────
✅ Apply limits across ALL agents (team budget)
✅ Top-level controls that override individual limits
✅ Useful for department/organization budgets
✅ Single source of truth for group policies

""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3: SECURITY GUARDS (THE GUARD KERNEL!)
# ═══════════════════════════════════════════════════════════════════════════════


async def section_3_guards():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   PART 3: SECURITY GUARDS (THE GUARD KERNEL!)                           ║
║                                                                          ║
║   The Guard Kernel is the heart of OmniClaw's safety system.            ║
║   It intercepts EVERY payment and enforces your rules.                   ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

THE GUARD KERNEL DECISION FLOW:
──────────────────────────────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────────┐
    │                     YOUR AGENT CALLS pay()                           │
    └─────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    1. TRUST GATE CHECK (ERC-8004)                   │
    │    └─ Is the recipient trusted? (identity, reputation)               │
    │    └─ BLOCKED if untrusted (if policy requires)                      │
    └─────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    2. GUARD KERNEL CHECKS                           │
    │    └─ Budget limits (daily, hourly, total)                          │
    │    └─ Single transaction limits (max/min)                           │
    │    └─ Recipient whitelist/blacklist                                 │
    │    └─ Rate limits (per minute, hour, day)                           │
    │    └─ Confirmation required? (human approval)                       │
    └─────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    3. BALANCE CHECK                                  │
    │    └─ Enough funds available?                                       │
    │    └─ Reserved for pending intents?                                 │
    └─────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    4. FUND LOCK (Mutex)                              │
    │    └─ Acquire lock to prevent double-spend                          │
    │    └─ Release when payment completes                                 │
    └─────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    5. EXECUTE PAYMENT                               │
    │    └─ Route to nanopayment or on-chain                             │
    │    └─ Record to ledger                                              │
    │    └─ Update guard counters                                         │
    └─────────────────────────────────────────────────────────────────────┘

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 3.1: GUARD KERNEL OVERVIEW                                     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Guard Kernel is a chain of individual guards that each check ONE thing:

    from omniclaw.guards import (
        BudgetGuard,        # Time-based spending limits
        SingleTxGuard,      # Per-transaction limits
        RecipientGuard,     # Who can be paid
        RateLimitGuard,     # How often payments can happen
        ConfirmGuard,       # Human approval needed
    )

You can add MULTIPLE guards to a wallet. They ALL run before any payment.

    # Example: Shopping agent with strict controls
    await client.add_budget_guard(          # Don't spend more than $500/day
        wallet_id=wallet_id,
        daily_limit="500.00"
    )
    
    await client.add_single_tx_guard(      # No single purchase over $50
        wallet_id=wallet_id,
        max_amount="50.00"
    )
    
    await client.add_recipient_guard(      # Only these vendors
        wallet_id=wallet_id,
        mode="whitelist",
        addresses=["0x111...", "0x222..."],
        domains=["api.amazon.com", "api.ebay.com"]
    )
    
    await client.add_rate_limit_guard(      # Max 10 payments/minute
        wallet_id=wallet_id,
        max_per_minute=10
    )

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 3.2: BUDGET GUARDS (Daily/Hourly Limits)                       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Limit how much an agent can spend over time periods:

    # Daily limit only
    await client.add_budget_guard(
        wallet_id=wallet_id,
        daily_limit="1000.00"  # Max $1000 per day
    )
    
    # Daily + Hourly limits
    await client.add_budget_guard(
        wallet_id=wallet_id,
        daily_limit="5000.00",
        hourly_limit="500.00"   # Max $500 per hour
    )
    
    # Total lifetime limit
    await client.add_budget_guard(
        wallet_id=wallet_id,
        total_limit="50000.00"  # Max $50k total ever
    )
    
    # All limits combined
    await client.add_budget_guard(
        wallet_id=wallet_id,
        daily_limit="5000.00",
        hourly_limit="500.00",
        total_limit="100000.00"
    )

WHAT HAPPENS:
──────────────────────────────────────────────────────────────────────────
Agent tries to pay $100, but already spent $950 today with $1000 limit.
→ BLOCKED! ("Daily limit exceeded")

Agent tries to pay $100, has $950 remaining in daily limit.
→ ALLOWED! Payment proceeds.

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 3.3: SINGLE TRANSACTION LIMITS                                ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Limit the size of individual transactions:

    # Max per transaction
    await client.add_single_tx_guard(
        wallet_id=wallet_id,
        max_amount="100.00"  # No single payment over $100
    )
    
    # With minimum (prevent dust attacks)
    await client.add_single_tx_guard(
        wallet_id=wallet_id,
        max_amount="100.00",
        min_amount="0.01"    # At least $0.01
    )
    
    # Only minimum (for high-value, allow any size)
    await client.add_single_tx_guard(
        wallet_id=wallet_id,
        min_amount="10.00"   # At least $10
    )

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 3.4: RECIPIENT WHITELISTS / BLACKLISTS                         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Control WHICH recipients can be paid:

    # WHITELIST: Only allow specific recipients
    await client.add_recipient_guard(
        wallet_id=wallet_id,
        mode="whitelist",
        addresses=[
            "0x1234...",           # Specific wallet addresses
            "0xabcd...",
        ],
        domains=[
            "api.openai.com",      # Specific domains (for x402 URLs)
            "data.provider.com",
        ]
    )
    
    # BLACKLIST: Block specific recipients
    await client.add_recipient_guard(
        wallet_id=wallet_id,
        mode="blacklist",
        addresses=["0xSCAM..."],
        domains=["suspicious-site.com"]
    )
    
    # PATTERNS: Use regex for dynamic matching
    await client.add_recipient_guard(
        wallet_id=wallet_id,
        mode="whitelist",
        patterns=[
            r"https://api\\.vendor[0-9]+\\.com/.*",  # Match vendor1, vendor2, etc.
            r"0x[a-fA-F0-9]{40}",                   # Match any valid address
        ]
    )
    
    # Combine addresses, domains, AND patterns
    await client.add_recipient_guard(
        wallet_id=wallet_id,
        mode="whitelist",
        addresses=["0xtrusted..."],
        domains=["trusted-api.com"],
        patterns=[r"https://data\\.provider[0-9]+\\.io/.*"]
    )

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 3.5: RATE LIMITING                                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Limit how many transactions can occur in a time window:

    # Max per minute
    await client.add_rate_limit_guard(
        wallet_id=wallet_id,
        max_per_minute=10  # Max 10 payments per minute
    )
    
    # Multiple time windows
    await client.add_rate_limit_guard(
        wallet_id=wallet_id,
        max_per_minute=10,
        max_per_hour=100,
        max_per_day=1000
    )
    
    # Hourly only
    await client.add_rate_limit_guard(
        wallet_id=wallet_id,
        max_per_hour=50
    )

WHY RATE LIMITS?
──────────────────────────────────────────────────────────────────────────
✅ Prevent runaway spending if agent goes wrong
✅ Protect against compromised credentials
✅ Slow down abuse attempts
✅ Cost control for high-frequency agents

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 3.6: HUMAN CONFIRMATION FOR LARGE PAYMENTS                     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Require human approval for large or suspicious payments:

    # Require confirmation for payments over $500
    await client.add_confirm_guard(
        wallet_id=wallet_id,
        threshold="500.00"
    )
    
    # Require confirmation for ALL payments (most strict)
    await client.add_confirm_guard(
        wallet_id=wallet_id,
        always_confirm=True
    )

WHAT HAPPENS WHEN CONFIRMATION REQUIRED:
──────────────────────────────────────────────────────────────────────────
1. Agent calls pay() for $600
2. Guard sees $600 > $500 threshold
3. Payment is PAUSED (status: PENDING)
4. Human receives notification (you implement via events/webhooks)
5. Human approves via confirm_payment_intent()
6. Payment completes

EXAMPLE: Handling confirmation in your app
──────────────────────────────────────────────────────────────────────────

    # Create payment intent (auto-pauses if confirm guard triggers)
    intent = await client.create_payment_intent(
        wallet_id=wallet_id,
        recipient="0x1234...",
        amount="600.00"
    )
    
    # If intent.status == REQUIRES_CONFIRMATION, show user approval UI
    if intent.status == PaymentIntentStatus.REQUIRES_CONFIRMATION:
        await show_approval_ui(intent)
        return  # Wait for user
    
    # Otherwise, payment continues automatically

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 3.7: LIST & REMOVE GUARDS                                       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

List guards on a wallet:

    # List guard names
    guards = await client.list_guards(wallet_id)
    print(f"Guards: {guards}")
    # Output: ['budget', 'single_tx', 'recipient', 'rate_limit']
    
    # List guards for a wallet set
    set_guards = await client.list_guards_for_set(wallet_set_id)
    print(f"Set guards: {set_guards}")

Remove guards (via GuardManager):
──────────────────────────────────────────────────────────────────────────

    # Get the guard manager
    guard_manager = client.guards
    
    # Remove a specific guard
    await guard_manager.remove_guard(wallet_id, "single_tx")
    
    # Remove all guards
    await guard_manager.clear_guards(wallet_id)

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 3.8: GUARD CHAIN (How Guards Work Together)                    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

The Guard Kernel runs guards in a CHAIN. Each guard:
1. Receives the payment context
2. Checks its specific rule
3. Returns ALLOWED or BLOCKED

    ┌─────────────────────────────────────────────────────────────────────┐
    │                    GUARD CHAIN (order matters!)                      │
    │                                                                      │
    │    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
    │    │ SingleTxGuard│───▶│ BudgetGuard │───▶│RateLimitGuard│───▶PASS │
    │    └─────────────┘    └─────────────┘    └─────────────┘           │
    │         │                  │                  │                      │
    │         ▼                  ▼                  ▼                      │
    │     $50 OK?           $950 left?         < 10/min?                   │
    │         │                  │                  │                      │
    │         ▼                  ▼                  ▼                      │
    │     PASS/FAIL         PASS/FAIL           PASS/FAIL                  │
    └─────────────────────────────────────────────────────────────────────┘

HOW THE CHAIN WORKS:
──────────────────────────────────────────────────────────────────────────
1. SingleTxGuard checks first (fastest check)
2. If PASS → BudgetGuard checks
3. If PASS → RateLimitGuard checks
4. If PASS → RecipientGuard checks
5. If ALL pass → Payment proceeds

First failure stops the chain!

SKIP GUARDS (DANGEROUS!):
──────────────────────────────────────────────────────────────────────────
    # Skip ALL guards (use only for testing!)
    result = await client.pay(
        wallet_id=wallet_id,
        recipient="0x1234...",
        amount="100.00",
        skip_guards=True  # DANGEROUS!
    )

""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4: TRUST GATE (ERC-8004 Identity Checks)
# ═══════════════════════════════════════════════════════════════════════════════


async def section_4_trust_gate():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   PART 4: TRUST GATE (ERC-8004 Identity Checks)                         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 4.1: WHAT IS TRUST GATE?                                       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Trust Gate checks RECIPIENT IDENTITY and REPUTATION before payment:

    ┌─────────────────────────────────────────────────────────────────────┐
    │                    TRUST GATE EVALUATION                             │
    │                                                                      │
    │  1. Resolve recipient address                                        │
    │     └─ Is this an ERC-8004 registered identity?                    │
    │                                                                      │
    │  2. Fetch metadata                                                   │
    │     └─ What is their attestation level?                             │
    │     └─ Who verified them?                                           │
    │                                                                      │
    │  3. Aggregate reputation                                             │
    │     └─ Feedback scores from past transactions                       │
    │     └─ Transaction history                                          │
    │                                                                      │
    │  4. Evaluate policy                                                 │
    │     └─ Does recipient meet your trust requirements?                 │
    │                                                                      │
    │  5. Return verdict                                                   │
    │     ├─ APPROVED: Proceed with payment                               │
    │     ├─ HELD: Review needed (human decision)                         │
    │     └─ BLOCKED: Reject payment                                      │
    └─────────────────────────────────────────────────────────────────────┘

WHY USE TRUST GATE?
──────────────────────────────────────────────────────────────────────────
✅ Verify recipients are who they claim
✅ Check if they've been verified by attestors
✅ See reputation from past transactions
✅ Block known bad actors
✅ Compliance and audit requirements

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 4.2: TRUST POLICIES                                           ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Trust policies define how strict your trust requirements are:

    # Initialize with trust policy
    client = OmniClaw(
        circle_api_key="KEY",
        trust_policy="standard"  # permissive, standard, or strict
    )

TRUST POLICY LEVELS:
──────────────────────────────────────────────────────────────────────────

    PERMISSIVE (default for testing)
    - Trust any recipient unless explicitly blocked
    - No reputation requirements
    - Good for: development, internal agents
    
    STANDARD (recommended for production)
    - Requires identity resolution
    - At least one attestation
    - Basic reputation check
    - Good for: general production use
    
    STRICT
    - High attestation level required
    - Strong positive reputation
    - Manual review for edge cases
    - Good for: high-value transactions

CUSTOM POLICY:
──────────────────────────────────────────────────────────────────────────

    from omniclaw.identity.types import TrustPolicy
    
    policy = TrustPolicy(
        min_attestation_level=2,        # Minimum attestation 1-3
        min_reputation_score=0.7,       # 0.0 - 1.0
        block_unknown_identities=True,  # Reject if not ERC-8004 registered
        require_feedback_history=True,   # Must have past transactions
    )
    
    client = OmniClaw(
        circle_api_key="KEY",
        trust_policy=policy
    )

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 4.3: ENABLE/DISABLE TRUST CHECKS                               ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Control trust checks per payment:

    # Pay WITH trust check (default)
    result = await client.pay(
        wallet_id=wallet_id,
        recipient="0x1234...",
        amount="100.00",
        check_trust=True  # Default
    )
    
    # Pay WITHOUT trust check (skip)
    result = await client.pay(
        wallet_id=wallet_id,
        recipient="0x1234...",
        amount="100.00",
        check_trust=False  # Skip trust check
    )
    
    # Trust check runs by default unless:
    # - skip_guards=True
    # - trust_policy="permissive"

CHECK TRUST GATE STATUS:
──────────────────────────────────────────────────────────────────────────

    # Is Trust Gate configured?
    if client.trust.is_configured:
        print("Trust Gate is active")
    
    # Get trust evaluation without paying
    result = await client.trust.evaluate(
        recipient_address="0x1234...",
        amount=Decimal("100.00"),
        wallet_id=wallet_id
    )
    
    print(f"Verdict: {result.verdict}")
    print(f"Reason: {result.block_reason}")

""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5: PAYMENT SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════


async def section_5_payments():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   PART 5: PAYMENT SCENARIOS - THE MEAT!                                 ║
║                                                                          ║
║   Here's every way your agents can pay using OmniClaw.                   ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


async def section_5_1_x402_resources():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SCENARIO 5.1: PAY FOR x402 RESOURCES (Web APIs, Data, Content)        ║
║                                                                          ║
║   The most common use case: paying sellers who use x402 protocol.         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT IS x402?
──────────────────────────────────────────────────────────────────────────
x402 is a web standard where sellers charge for their APIs/data/content.
Instead of API keys, they use payment headers.

When you request their URL, if payment is required, they return:
- HTTP 402 (Payment Required)
- The price and payment instructions

OmniClaw handles this AUTOMATICALLY.

THE MAGIC METHOD: client.pay() with a URL
──────────────────────────────────────────────────────────────────────────

    # Simple as this!
    result = await client.pay(
        wallet_id=wallet_id,
        recipient="https://api.weatherdata.com/v1/current.json",
        amount="0.05"  # $0.05 for weather data
    )
    
    print(f"Success: {result.success}")
    print(f"Data: {result.response_data}")  # The data you bought!

WHAT HAPPENS INSIDE:
──────────────────────────────────────────────────────────────────────────
1. OmniClaw sends HTTP request to URL
2. Seller returns 402 with price
3. OmniClaw detects "GatewayWalletBatched" (Circle nanopayment)
4. If network matches → Uses GASLESS nanopayment (Circle pays gas!)
5. If network differs → Falls back to direct x402 (on-chain)
6. Payment is signed and submitted
7. Seller verifies and returns the data
8. You get the data in result.response_data

THE RECIPIENT CAN BE:
──────────────────────────────────────────────────────────────────────────
- Full URL: "https://api.weatherdata.com/v1/current.json"
- URL with path: "https://data.vendor.com/premium/records"
- Any HTTP/HTTPS endpoint that supports x402

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SCENARIO 5.2: PAY ANOTHER ADDRESS (SAME CHAIN - Direct Transfer)      ║
║                                                                          ║
║   Send USDC to another wallet on the same blockchain.                    ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHEN TO USE:
──────────────────────────────────────────────────────────────────────────
- Paying employees/vendors with known wallet addresses
- Sending USDC to friends/family
- Moving funds between your own wallets
- Any direct address transfer on the same network

THE CODE:
──────────────────────────────────────────────────────────────────────────

    # Simple transfer to an address
    result = await client.pay(
        wallet_id=wallet_id,
        recipient="0x1234...abcd",  # Recipient's wallet address
        amount="50.00",              # $50 USDC
        destination_chain="BASE-SEPOLIA"  # Same chain
    )
    
    print(f"Transfer success: {result.success}")
    print(f"Transaction: {result.blockchain_tx}")

SAME CHAIN TRANSFER FLOW:
──────────────────────────────────────────────────────────────────────────
1. Trust Gate check (if enabled)
2. Guard chain (budget, limits, etc.)
3. Acquire fund lock (prevent double-spend)
4. Execute on-chain transfer via Circle
5. Wait for confirmation
6. Update guard ledger
7. Return transaction details

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SCENARIO 5.3: PAY ANOTHER ADDRESS (DIFFERENT CHAIN - Cross-Chain)      ║
║                                                                          ║
║   Send USDC to a wallet on a DIFFERENT blockchain.                       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHEN TO USE:
──────────────────────────────────────────────────────────────────────────
- Recipient is on Polygon but you're on Base
- Paying across chains (e.g., Ethereum to Polygon)
- International payments where recipient prefers a specific chain

THE CODE:
──────────────────────────────────────────────────────────────────────────

    # Transfer from Base to Polygon
    result = await client.pay(
        wallet_id=wallet_id,
        recipient="0xabcd...1234",       # Polygon address
        amount="100.00",                  # $100 USDC
        destination_chain="POLYGON-AMOY"  # Target chain
    )
    
    print(f"Cross-chain success: {result.success}")
    print(f"Transaction: {result.blockchain_tx}")

HOW CROSS-CHAIN WORKS:
──────────────────────────────────────────────────────────────────────────
OmniClaw uses Circle's CCTP (Cross-Chain Transfer Protocol):

1. Your USDC is burned on source chain (Base)
2. Circle mint USDC on destination chain (Polygon)
3. Recipient receives USDC on Polygon

BENEFITS OF CCTP:
──────────────────────────────────────────────────────────────────────────
✅ Instant settlement (vs hours for bridges)
✅ No slippage or impermanent loss
✅ Native USDC (not wrapped/bridged)
✅ Lower fees than traditional bridges

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SCENARIO 5.4: PAYROLL PAYMENTS (BATCH PAYMENTS)                        ║
║                                                                          ║
║   Pay multiple recipients in one call.                                   ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHEN TO USE:
──────────────────────────────────────────────────────────────────────────
- Monthly payroll to employees
- Vendor payments (multiple invoices)
- Affiliate commissions
- Any bulk payment scenario

THE CODE:
──────────────────────────────────────────────────────────────────────────

    from omniclaw import PaymentRequest
    
    # Create batch of payments
    payments = [
        PaymentRequest(
            wallet_id=wallet_id,
            recipient="0x1234...abcd",  # Alice
            amount="5000.00",
            purpose="January Salary"
        ),
        PaymentRequest(
            wallet_id=wallet_id,
            recipient="0x5678...efgh",  # Bob
            amount="3500.00",
            purpose="January Salary"
        ),
        PaymentRequest(
            wallet_id=wallet_id,
            recipient="https://api.vendor.com/invoice/123",  # Vendor x402
            amount="1200.00",
            purpose="Monthly Services"
        ),
        PaymentRequest(
            wallet_id=wallet_id,
            recipient="0xABCD...WXYZ",  # Charlie
            amount="7500.00",
            purpose="Contractor Payment"
        ),
    ]
    
    # Execute batch
    result = await client.batch_pay(
        requests=payments,
        concurrency=5  # Up to 5 payments at once
    )
    
    print(f"Total payments: {result.total}")
    print(f"Successful: {result.successful}")
    print(f"Failed: {result.failed}")
    
    # Check individual results
    for payment_result in result.results:
        print(f"  {payment_result.recipient}: {payment_result.status}")

BATCH PAYMENT RULES:
──────────────────────────────────────────────────────────────────────────
- All payments use the same wallet_id
- Each payment is checked by guards individually
- Failed payments don't block other payments
- Concurrency limit prevents overwhelming the system

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SCENARIO 5.5: SIMULATE BEFORE PAYING                                  ║
║                                                                          ║
║   Check if a payment will succeed BEFORE spending anything.               ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHEN TO USE:
──────────────────────────────────────────────────────────────────────────
- Before making important payments
- To check if guards will block
- To estimate fees
- For payment confirmation UI
- To verify recipient trust status

THE CODE:
──────────────────────────────────────────────────────────────────────────

    # Simulate a payment (no actual spending)
    sim = await client.simulate(
        wallet_id=wallet_id,
        recipient="https://api.data.com/premium",
        amount="25.00"
    )
    
    print(f"Would succeed: {sim.would_succeed}")
    print(f"Route: {sim.route}")  # NANOPAYMENT, X402, TRANSFER, etc.
    print(f"Reason: {sim.reason}")  # Why it would fail (if any)
    print(f"Guards that would pass: {sim.guards_that_would_pass}")
    
    if sim.would_succeed:
        # Proceed with actual payment
        result = await client.pay(...)
    else:
        print(f"Payment would fail: {sim.reason}")

SIMULATE CHECKS EVERYTHING:
──────────────────────────────────────────────────────────────────────────
✅ Trust Gate verdict (if enabled)
✅ Balance sufficient?
✅ Budget limits OK?
✅ Single tx limit OK?
✅ Recipient allowed?
✅ Rate limit OK?
✅ Route available?

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SCENARIO 5.6: PAYMENT INTENTS (2-PHASE COMMIT)                         ║
║                                                                          ║
║   Authorize a payment, then confirm later. Good for:                     ║
║   - User approval flows                                                   ║
║   - Scheduled payments                                                    ║
║   - Complex workflows                                                      ║
║   - Pending confirmation guards                                            ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

THE FLOW:
──────────────────────────────────────────────────────────────────────────
1. CREATE intent (authorize) - Funds are RESERVED
2. User confirms or cancels
3. CONFIRM executes the payment

CREATE THE INTENT:
──────────────────────────────────────────────────────────────────────────

    # Step 1: Authorize (reserve funds)
    intent = await client.create_payment_intent(
        wallet_id=wallet_id,
        recipient="0x1234...abcd",
        amount="1000.00",
        purpose="Equipment Purchase",
        expires_in=3600  # Expires in 1 hour
    )
    
    intent_id = intent.id
    print(f"Intent created: {intent_id}")
    print(f"Status: {intent.status}")  # REQUIRES_CONFIRMATION
    print(f"Reserved: {intent.reserved_amount}")  # $1000 held

WHAT IS "RESERVED"?
──────────────────────────────────────────────────────────────────────────
When you create an intent, the amount is "reserved" from your wallet.
This means:
- The $1000 can't be spent by other payments
- It shows as "reserved" not "available"
- If you cancel, the reservation releases
- If you confirm, the reservation becomes the payment

CONFIRM LATER:
──────────────────────────────────────────────────────────────────────────

    # Step 2: Confirm (execute payment)
    result = await client.confirm_payment_intent(intent_id)
    
    print(f"Payment success: {result.success}")
    print(f"Transaction: {result.blockchain_tx}")

CANCEL IF NEEDED:
──────────────────────────────────────────────────────────────────────────

    # Cancel before confirming
    cancelled = await client.cancel_payment_intent(
        intent_id,
        reason="User cancelled"
    )
    print(f"Intent cancelled: {cancelled.status}")
    # Reservation is released, funds available again

GET INTENT STATUS:
──────────────────────────────────────────────────────────────────────────

    intent = await client.get_payment_intent(intent_id)
    print(f"Status: {intent.status}")
    # Possible statuses:
    # - REQUIRES_CONFIRMATION: Waiting for user
    # - PROCESSING: Payment in progress
    # - SUCCEEDED: Payment completed
    # - FAILED: Payment failed
    # - CANCELLED: User cancelled

WHY USE INTENTS?
──────────────────────────────────────────────────────────────────────────
✅ Funds are held (not double-spent)
✅ Implement approval workflows
✅ Scheduled payments
✅ Complex multi-step transactions
✅ Triggered by ConfirmGuard

""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 6: THE LEDGER (Transaction History)
# ═══════════════════════════════════════════════════════════════════════════════


async def section_6_ledger():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   PART 6: THE LEDGER (Transaction History)                               ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 6.1: VIEW TRANSACTION HISTORY                                 ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Every payment is recorded in the ledger:

    # Get all transactions for a wallet
    transactions = await client.list_transactions(wallet_id=wallet_id)
    
    for tx in transactions:
        print(f"ID: {tx.id}")
        print(f"Amount: {tx.amount}")
        print(f"Status: {tx.status}")
        print(f"Recipient: {tx.recipient}")
        print(f"Timestamp: {tx.created_at}")
        print("---")
    
    # Get transactions for a specific chain
    transactions = await client.list_transactions(
        wallet_id=wallet_id,
        blockchain="BASE-SEPOLIA"
    )

LEDGER ENTRY STATUSES:
──────────────────────────────────────────────────────────────────────────
- PENDING: Payment in progress
- COMPLETED: Successfully completed
- FAILED: Payment failed
- BLOCKED: Blocked by guard
- CANCELLED: User cancelled

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 6.2: SYNC WITH BLOCKCHAIN                                      ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Sync ledger entries with on-chain status:

    # Sync a specific ledger entry
    entry = await client.sync_transaction(ledger_entry_id)
    
    print(f"Status: {entry.status}")
    print(f"Blockchain tx: {entry.blockchain_tx}")
    print(f"Last synced: {entry.metadata.get('last_synced')}")

WHY SYNC?
──────────────────────────────────────────────────────────────────────────
✅ Verify payment is confirmed on-chain
✅ Get actual transaction hash
✅ Check gas fees paid
✅ Verify settlement status

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 6.3: LEDGER ENTRY TYPES                                        ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

The ledger tracks different types of entries:

    from omniclaw.ledger import LedgerEntryType
    
    # Payment (sent USDC)
    entry.type == LedgerEntryType.PAYMENT
    
    # Deposit (received USDC)
    entry.type == LedgerEntryType.DEPOSIT
    
    # Withdrawal (withdrew USDC)
    entry.type == LedgerEntryType.WITHDRAWAL
    
    # Fee (gas fees paid)
    entry.type == LedgerEntryType.FEE

ACCESS THE LEDGER DIRECTLY:
──────────────────────────────────────────────────────────────────────────

    ledger = client.ledger
    
    # Record a custom entry
    await ledger.record(LedgerEntry(...))
    
    # Update entry status
    await ledger.update_status(entry_id, status, tx_hash)
    
    # Get entry by ID
    entry = await ledger.get(entry_id)

""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 7: RESILIENCE & RELIABILITY
# ═══════════════════════════════════════════════════════════════════════════════


async def section_7_resilience():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   PART 7: RESILIENCE & RELIABILITY                                      ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 7.1: FUND LOCKS (Prevent Double-Spend)                         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Fund Locks prevent double-spending when multiple agents share a wallet:

    ┌─────────────────────────────────────────────────────────────────────┐
    │                    WITHOUT FUND LOCK (Dangerous!)                    │
    │                                                                      │
    │  Agent A: Check balance → $100                                      │
    │  Agent B: Check balance → $100                                      │
    │  Agent A: Pay $80 → Success                                          │
    │  Agent B: Pay $80 → Success (but only $20 left!)                    │
    │  Result: $160 paid from $100 = DOUBLE-SPEND!                        │
    └─────────────────────────────────────────────────────────────────────┘
    
    ┌─────────────────────────────────────────────────────────────────────┐
    │                    WITH FUND LOCK (Safe!)                            │
    │                                                                      │
    │  Agent A: Acquire lock → Token ABC                                  │
    │  Agent B: Acquire lock → WAITING...                                 │
    │  Agent A: Pay $80 → Success → Release lock                          │
    │  Agent B: Acquire lock → Token DEF → Now checks $20                  │
    │  Agent B: Pay $80 → FAILS (insufficient funds)                       │
    └─────────────────────────────────────────────────────────────────────┘

FUND LOCKS ARE AUTOMATIC:
──────────────────────────────────────────────────────────────────────────
You never call fund locks directly. OmniClaw handles them automatically
when you call pay(). The lock is:
1. Acquired before checking balance
2. Held during payment execution
3. Released after payment completes (success or failure)

MANUAL LOCK (For complex flows):
──────────────────────────────────────────────────────────────────────────

    from omniclaw.ledger import FundLockService
    
    lock_service = FundLockService(storage)
    
    # Acquire lock
    token = await lock_service.acquire(wallet_id, amount, ttl=30)
    
    if token:
        try:
            # Do multiple operations under lock
            await operation_1()
            await operation_2()
            await operation_3()
        finally:
            # Always release
            await lock_service.release_with_key(wallet_id, token)

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 7.2: CIRCUIT BREAKERS                                          ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Circuit breakers prevent cascading failures:

    ┌─────────────────────────────────────────────────────────────────────┐
    │                    CIRCUIT BREAKER STATES                            │
    │                                                                      │
    │  CLOSED (Normal):                                                    │
    │    └─ All requests go through                                        │
    │    └─ Failures are counted                                          │
    │                                                                      │
    │  OPEN (Failing Fast):                                                │
    │    └─ Requests fail immediately (no retry)                          │
    │    └─ After recovery period, try again                              │
    │                                                                      │
    │  HALF-OPEN (Testing):                                                │
    │    └─ One trial request                                             │
    │    └─ Success → CLOSED                                              │
    │    └─ Failure → OPEN again                                          │
    └─────────────────────────────────────────────────────────────────────┘

CIRCUIT BREAKERS IN OMNICLAW:
──────────────────────────────────────────────────────────────────────────
✅ Circle API circuit breaker
✅ Nanopayment settlement circuit breaker
✅ Trust Gate circuit breaker

CUSTOMIZE CIRCUIT BREAKERS:
──────────────────────────────────────────────────────────────────────────

    from omniclaw.resilience.circuit import CircuitBreaker
    
    # Create custom circuit breaker
    circuit = CircuitBreaker(
        name="my_api",
        storage=storage,
        failure_threshold=5,      # Trip after 5 failures
        recovery_timeout=60,       # Wait 60 seconds before retry
    )
    
    # Check if available
    if await circuit.is_available():
        result = await make_api_call()
        await circuit.record_success()
    else:
        raise CircuitOpenError(...)

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 7.3: RETRY STRATEGIES                                         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

Choose how payments handle failures:

    from omniclaw import PaymentStrategy
    
    # Strategy per payment
    result = await client.pay(
        wallet_id=wallet_id,
        recipient="0x1234...",
        amount="100.00",
        strategy=PaymentStrategy.RETRY_THEN_FAIL  # Default
    )

PAYMENT STRATEGIES:
──────────────────────────────────────────────────────────────────────────

    FAIL_FAST
    - Try once, fail immediately on error
    - Best for: real-time user-facing payments
    
    RETRY_THEN_FAIL
    - Retry transient failures (timeout, network)
    - Fail on permanent errors (invalid recipient)
    - Best for: most payments (default)
    
    QUEUE_BACKGROUND
    - If fails, queue for later retry
    - Returns success immediately
    - Best for: batch payments, non-critical payments

CUSTOMIZE RETRY:
──────────────────────────────────────────────────────────────────────────

    from omniclaw.resilience.retry import execute_with_retry
    
    result = await execute_with_retry(
        func,
        max_attempts=3,
        base_delay=1.0,
        exponential_backoff=True,
        retriable_exceptions=[TimeoutError, NetworkError],
    )

""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 8: UNDERSTANDING WHAT HAPPENS INSIDE
# ═══════════════════════════════════════════════════════════════════════════════


async def section_8_internals():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   PART 8: UNDERSTANDING WHAT HAPPENS INSIDE                              ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")


async def section_8_1_routing():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 8.1: HOW client.pay() ROUTES PAYMENTS                          ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

When you call client.pay(), OmniClaw follows this decision tree:

    ┌─────────────────────────────────────────────────────────────────────┐
    │                    client.pay()                                       │
    └─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │  RECIPIENT TYPE DETECTED    │
                    └─────────────────────────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              ▼                                       ▼
    ┌─────────────────────┐               ┌─────────────────────┐
    │  URL (x402 seller)  │               │  ADDRESS (wallet)   │
    └─────────────────────┘               └─────────────────────┘
              │                                       │
              ▼                                       ▼
    ┌─────────────────────┐               ┌─────────────────────┐
    │  1. Trust Gate      │               │  1. Trust Gate      │
    │  2. Guard Chain     │               │  2. Guard Chain     │
    │  3. Request URL     │               │  3. Fund Lock       │
    │  4. Get 402         │               │  4. Transfer        │
    │  5. Parse response  │               └─────────────────────┘
    └─────────────────────┘
              │
              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    SELLER ACCEPTS NANOPAYMENT?                    │
    │              (GatewayWalletBatched in 402 response)               │
    └─────────────────────────────────────────────────────────────────┘
              │
      ┌───────┴───────┐
      ▼               ▼
    ┌─────────┐     ┌─────────┐
    │   YES   │     │   NO    │
    └─────────┘     └─────────┘
      │               │
      ▼               ▼
┌────────────────┐  ┌────────────────┐
│NETWORK MATCH?  │  │ DIRECT x402   │
│                │  │ (On-chain)    │
└────────────────┘  └────────────────┘
      │
┌─────┴─────┐
▼           ▼
┌─────────┐ ┌─────────┐
│   YES   │ │   NO    │
└─────────┘ └─────────┘
  │           │
  ▼           ▼
┌───────────┐ ┌───────────┐
│NANOPAYMENT│ │ DIRECT x402│
│ (Gasless) │ │ (On-chain) │
└───────────┘ └───────────┘

THE THREE PAYMENT METHODS:
──────────────────────────────────────────────────────────────────────────
1. NANOPAYMENT (Best!)
   - Seller accepts Circle Gateway
   - Networks match (buyer's gateway on seller's network)
   - GASLESS for buyer! Circle pays gas via EIP-3009
   - Auto-topup from wallet if gateway balance low

2. DIRECT x402
   - Seller accepts x402 but not Circle nanopayment
   - OR networks don't match
   - On-chain transaction, buyer pays gas
   - Cross-chain via CCTP

3. DIRECT TRANSFER
   - Paying an address (not x402 URL)
   - On-chain transfer via Circle
   - Same or cross-chain

""")


async def section_8_2_network_matching():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 8.2: NETWORK MATCHING (WHY IT MATTERS)                         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

NANOPAYMENT REQUIREMENT: Networks must match!
──────────────────────────────────────────────────────────────────────────

When you create a wallet, you choose a network:
    wallet = await client.create_agent_wallet(
        blockchain="BASE-SEPOLIA"  # Your gateway is on Base Sepolia
    )

This creates your Gateway EOA on BASE-SEPOLIA.

When paying an x402 seller:
    - Seller is on POLYGON-AMOY
    - Your gateway is on BASE-SEPOLIA
    - NETWORKS DON'T MATCH!

WHAT HAPPENS:
──────────────────────────────────────────────────────────────────────────
Seller accepts Circle nanopayment (GatewayWalletBatched)
BUT
Buyer's gateway is on Base, seller is on Polygon
→ Networks differ → Nanopayment WON'T WORK

OmniClaw DETECTS this and falls back to DIRECT x402:
- On-chain transaction
- Buyer pays gas fees
- Cross-network supported via CCTP

THE RULE:
──────────────────────────────────────────────────────────────────────────
For GASLESS nanopayment:
  ✅ Buyer's gateway network == Seller's network

For DIRECT x402 (on-chain, buyer pays gas):
  ✅ Always works, cross-network supported

TO ENABLE NANOPAYMENT FOR A SELLER:
──────────────────────────────────────────────────────────────────────────
If you frequently pay a seller on Polygon:
1. Create wallet with blockchain="POLYGON-AMOY"
2. Fund your gateway ON Polygon
3. Now nanopayment works for Polygon sellers

OR

Just use direct x402 (still works, just pays gas).

""")


async def section_8_3_auto_topup():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 8.3: AUTO-TOPUP (HOW IT WORKS)                                 ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

AUTO-TOPUP makes nanopayments seamless:
──────────────────────────────────────────────────────────────────────────

You fund ONE place (wallet_id)
OmniClaw auto-transfers to gateway as needed

HOW IT WORKS:
──────────────────────────────────────────────────────────────────────────

1. You call pay() for $10 worth of x402 data

2. OmniClaw checks gateway balance
   Gateway has: $3.00
   Need: $10.00
   Shortfall: $7.00

3. OmniClaw auto-transfers $7 from wallet to gateway
   (This is an on-chain transaction, you pay gas)

4. Gateway now has: $10.00

5. Nanopayment executes (gasless!)
   Circle pays the gas for the actual payment

6. Gateway now has: $0.00 (after payment)

BENEFIT:
──────────────────────────────────────────────────────────────────────────
✅ You never think about gateway balances
✅ Seamless nanopayment experience
✅ Only pay gas for topups (not each payment)
✅ One balance to manage

DISABLE IF NEEDED:
──────────────────────────────────────────────────────────────────────────

    client.configure_nanopayments(
        auto_topup_enabled=False
    )

    # Then manually manage gateway balance:
    await client.deposit_to_gateway(
        amount_usdc="100.00",
        nano_key_alias="my-key"
    )

""")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 9: TROUBLESHOOTING
# ═══════════════════════════════════════════════════════════════════════════════


async def section_9_troubleshooting():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   PART 9: TROUBLESHOOTING                                               ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 9.1: COMMON ERRORS                                             ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

ERROR: "wallet_id is required"
→ You're calling pay() without a wallet_id
→ Solution: Always pass wallet_id

ERROR: "Insufficient available balance"
→ Your wallet doesn't have enough USDC
→ Solution: Fund your wallet via Circle console

ERROR: "Insufficient available balance (Total: X, Reserved: Y)"
→ You have funds but some are reserved for pending intents
→ Solution: Cancel or confirm pending intents

ERROR: "Blocked by guard: Daily limit exceeded"
→ You've hit your spending limit
→ Solution: Wait for reset or adjust limit

ERROR: "Trust Gate blocked"
→ The recipient failed ERC-8004 trust check
→ Solution: Check recipient reputation or disable trust check

ERROR: "Wallet is busy (locked by another transaction)"
→ Another payment is in progress
→ Solution: Wait and retry

ERROR: "Payment intent expired"
→ Intent expired before confirmation
→ Solution: Create a new intent

ERROR: "Circuit breaker is open"
→ Too many failures, system is protecting itself
→ Solution: Wait for recovery period

ERROR: "Entity secret already registered"
→ You already have an entity secret for this API key
→ Solution: Use existing secret or reset via Circle console

ENABLE DEBUG LOGGING:
──────────────────────────────────────────────────────────────────────────

    client = OmniClaw(
        circle_api_key="YOUR_KEY",
        log_level="DEBUG"  # Gets verbose output
    )

DEBUG OUTPUT SHOWS:
──────────────────────────────────────────────────────────────────────────
- Trust Gate evaluation
- Guard checks and results
- Payment routing decisions
- Nanopayment vs direct x402 choice
- Network matching decisions
- Settlement results
- Lock acquisition/release

""")

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   SECTION 9.2: QUICK REFERENCE CARD                                       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

QUICK COMMANDS:

# ───────────────────────────────────────────────────────────────────────────
# SETUP
# ───────────────────────────────────────────────────────────────────────────
    from omniclaw import OmniClaw
    
    client = OmniClaw(circle_api_key="KEY", network="BASE-SEPOLIA")

# ───────────────────────────────────────────────────────────────────────────
# WALLET
# ───────────────────────────────────────────────────────────────────────────
    wallet = await client.create_agent_wallet()
    wallet_id = wallet.id
    balance = await client.get_balance(wallet_id)
    gateway_balance = await client.get_gateway_balance(wallet_id)

# ───────────────────────────────────────────────────────────────────────────
# GUARDS
# ───────────────────────────────────────────────────────────────────────────
    await client.add_budget_guard(wallet_id, daily_limit="1000")
    await client.add_single_tx_guard(wallet_id, max_amount="100")
    await client.add_recipient_guard(wallet_id, mode="whitelist", addresses=[...])
    await client.add_rate_limit_guard(wallet_id, max_per_minute=10)
    await client.add_confirm_guard(wallet_id, threshold="500")
    guards = await client.list_guards(wallet_id)

# ───────────────────────────────────────────────────────────────────────────
# PAYMENTS
# ───────────────────────────────────────────────────────────────────────────
    # x402 URL
    result = await client.pay(wallet_id, "https://api.vendor.com/data", "5")
    
    # Address (same chain)
    result = await client.pay(wallet_id, "0x...", "100")
    
    # Address (cross-chain)
    result = await client.pay(wallet_id, "0x...", "100", destination_chain="POLYGON")
    
    # Batch
    from omniclaw import PaymentRequest
    result = await client.batch_pay([PaymentRequest(...), ...])
    
    # Simulate
    sim = await client.simulate(wallet_id, recipient, amount)
    
    # Payment Intent
    intent = await client.create_payment_intent(wallet_id, recipient, amount)
    result = await client.confirm_payment_intent(intent.id)
    await client.cancel_payment_intent(intent.id)

# ───────────────────────────────────────────────────────────────────────────
# LEDGER
# ───────────────────────────────────────────────────────────────────────────
    transactions = await client.list_transactions(wallet_id)
    entry = await client.sync_transaction(entry_id)

# ───────────────────────────────────────────────────────────────────────────
# TRUST GATE
# ───────────────────────────────────────────────────────────────────────────
    trust_result = await client.trust.evaluate(recipient, amount, wallet_id)

""")


# ═══════════════════════════════════════════════════════════════════════════════
# RUN THE WALKTHROUGH
# ═══════════════════════════════════════════════════════════════════════════════


async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║           ABIORH ENTERPRISE - COMPLETE OMNICLAW WALKTHROUGH           ║
║                                                                          ║
║                      LOADING...                                          ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    await asyncio.sleep(1)

    # Part 1: Setup
    await section_1_2_doctor()
    await asyncio.sleep(0.5)
    await section_1_3_initialize()
    await asyncio.sleep(0.5)

    # Part 2: Wallet Management
    await section_2_2_fund_wallet()
    await asyncio.sleep(0.5)

    # Part 3: Guards
    await section_3_guards()
    await asyncio.sleep(0.5)

    # Part 4: Trust Gate
    await section_4_trust_gate()
    await asyncio.sleep(0.5)

    # Part 5: Payments
    await section_5_payments()
    await asyncio.sleep(0.5)

    # Part 6: Ledger
    await section_6_ledger()
    await asyncio.sleep(0.5)

    # Part 7: Resilience
    await section_7_resilience()
    await asyncio.sleep(0.5)

    # Part 8: Internals
    await section_8_internals()
    await asyncio.sleep(0.5)

    # Part 9: Troubleshooting
    await section_9_troubleshooting()


if __name__ == "__main__":
    asyncio.run(main())
