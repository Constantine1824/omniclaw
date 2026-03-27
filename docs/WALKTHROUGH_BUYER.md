# Complete Buyer Walkthrough

**For AI agents that need to pay for things.**

This guide covers everything you need to know about using OmniClaw as a buyer (payer).

---

## Table of Contents

1. [Setup](#1-setup)
2. [Create Wallet](#2-create-wallet)
3. [Add Guards](#3-add-guards)
4. [Fund Wallet](#4-fund-wallet)
5. [Pay for x402 Resources](#5-pay-for-x402-resources)
6. [Transfer to Addresses](#6-transfer-to-addresses)
7. [Cross-Chain Transfers](#7-cross-chain-transfers)
8. [Simulate Before Paying](#8-simulate-before-paying)
9. [Payment Intents](#9-payment-intents)
10. [Batch Payments](#10-batch-payments)
11. [View Transaction History](#11-view-transaction-history)

---

## 1. Setup

### What You Need

Only your **Circle API Key**. Get one at [console.circle.com](https://console.circle.com).

### Check Your Setup

```bash
omniclaw doctor
```

Should show:
- ✅ Circle SDK installed
- ✅ Circle API key
- ✅ Entity Secret (auto-generated)
- ✅ Recovery file

### Initialize OmniClaw

```python
from omniclaw import OmniClaw

client = OmniClaw(
    circle_api_key="YOUR_CIRCLE_API_KEY",
    network="BASE-SEPOLIA",  # or BASE, POLYGON-AMOY, etc.
)
```

**OmniClaw auto-handles:**
- Entity Secret generation
- Circle registration
- Recovery file storage

---

## 2. Create Wallet

One call creates everything:

```python
wallet = await client.create_agent_wallet()
wallet_id = wallet.id
```

What it creates:
- ✅ Circle wallet (for tracking)
- ✅ EOA signing key (for x402 payments)
- ✅ Gateway wallet (same address as EOA, for nanopayments)
- ✅ Ready to use

### Get Payment Address

```python
# Get the EOA address to fund
address = await client.get_payment_address(wallet_id)
print(address)  # e.g., "0x742d..."
```

**Important:** This address is used for:
1. Basic x402 payments - fund with USDC directly
2. Circle Gateway payments - fund with USDC, then deposit to Gateway

### Supported Networks

| Network | Use Case |
|---------|----------|
| `BASE-SEPOLIA` | Testing (recommended) |
| `POLYGON-AMOY` | Testing |
| `ETHEREUM-SEPOLIA` | Testing |
| `BASE` | Production |
| `POLYGON` | Production |
| `ETHEREUM` | Production |

### Getting Testnet Funds

To test with real funds, use Base Sepolia testnet:

**1. Configure your environment:**

```bash
# .env file
OMNICLAW_NANOPAYMENTS_DEFAULT_NETWORK=eip155:84532  # Base Sepolia
OMNICLAW_RPC_URL=https://sepolia.base.org
```

**2. Get ETH (for gas):**
- https://faucets.chain.link/base-sepolia
- https://www.alchemy.com/faucets/base-sepolia
- https://bwarelabs.com/faucets/base-sepolia

**3. Get USDC (for payments):**
- Go to: https://faucet.circle.com/
- Select: **Base Sepolia**
- Click: **Send 20 USDC** (free, every 2 hours)

**4. Fund your wallet:**

```python
# Get your payment addresses
wallet_set, wallet = await client.get_or_create_agent_wallet("my-agent")

# Circle wallet address (for transfers)
circle_address = wallet.address

# Nano/Gateway address (for nanopayments)
nano_address = await client._nano_vault.get_address(alias=f"wallet-{wallet.id}")
```

---

## 3. Add Guards

Guards control WHAT your agent can pay for and HOW MUCH.

### Budget Guard (Spending Limits)

```python
# Daily limit
await client.add_budget_guard(wallet_id, daily_limit="1000.00")

# With hourly and total limits
await client.add_budget_guard(
    wallet_id,
    daily_limit="5000.00",
    hourly_limit="500.00",
    total_limit="50000.00"
)
```

### Single Transaction Guard

```python
# Max per transaction
await client.add_single_tx_guard(wallet_id, max_amount="100.00")

# With minimum (prevent tiny payments)
await client.add_single_tx_guard(wallet_id, max_amount="100.00", min_amount="0.01")
```

### Recipient Guard (Who Can Be Paid)

```python
# Whitelist specific addresses
await client.add_recipient_guard(
    wallet_id,
    mode="whitelist",
    addresses=["0x742d...4a0", "0x1234...abcd"]
)

# Whitelist domains (for x402 URLs)
await client.add_recipient_guard(
    wallet_id,
    mode="whitelist",
    domains=["api.openai.com", "api.anthropic.com", "api.weather.com"]
)

# Blacklist specific addresses
await client.add_recipient_guard(
    wallet_id,
    mode="blacklist",
    addresses=["0xSCAM...wallet"]
)
```

### Rate Limit Guard

```python
# Max payments per time window
await client.add_rate_limit_guard(
    wallet_id,
    max_per_minute=10,
    max_per_hour=100,
    max_per_day=500
)
```

### Confirm Guard (Human Approval)

```python
# Require approval for large payments
await client.add_confirm_guard(
    wallet_id,
    threshold="500.00"  # Payments over $500 need approval
)

# Require approval for ALL payments
await client.add_confirm_guard(
    wallet_id,
    always_confirm=True
)
```

---

## 4. Fund Wallet

### Option 1: Fund EOA Address Directly (for x402)

Get your payment address and fund it with USDC:

```python
address = await client.get_payment_address(wallet_id)
print(f"Fund this address with USDC: {address}")
```

Send USDC to this address from any wallet/exchange.

### Option 2: Deposit to Gateway (for gasless nanopayments)

After funding the EOA, you can deposit to Gateway for gasless payments:

```python
# Deposit USDC from EOA to Gateway
result = await client.deposit_to_gateway(
    wallet_id=wallet_id,
    amount_usdc="10.00"  # Amount in USDC
)
```

This requires ETH for gas. Gateway payments are batched and gas-free.

### Check Balances

```python
# Get EOA balance (on-chain)
# Query via blockchain explorer

# Get Gateway balance (for nanopayments)
balance = await client.get_gateway_balance(wallet_id=wallet_id)
print(f"Gateway balance: {balance.formatted_available}")
```

### Option 3: Circle Console

For traditional Circle wallet funding:

1. Go to console.circle.com
2. Find your wallet
3. Add USDC via bank transfer or card

---

## 5. Pay for x402 Resources

x402 is a web standard where sellers charge for APIs/data/content.

### Simple Payment

```python
# Pay $0.05 for weather data
result = await client.pay(
    wallet_id=wallet_id,
    recipient="https://api.weatherdata.com/v1/current.json",
    amount="0.05"
)

print(f"Success: {result.success}")
print(f"Data: {result.resource_data}")  # The data you bought!
```

### How Payment Works

```
1. OmniClaw requests the URL
2. Seller returns HTTP 402 (Payment Required)
3. OmniClaw parses payment requirements
4. OmniClaw signs EIP-3009 authorization with your EOA key
5. OmniClaw retries with payment proof
6. Seller verifies and returns data
7. You get the data!
```

**You never see x402, EIP-3009, or anything else!**

### Payment Methods

The seller/facilitator determines which payment method is used:
- Basic x402: Direct EIP-3009 transfer from your EOA
- Circle Gateway: Batched nanopayment (if seller supports it)

---

## 5b. Gateway Operations

Manage your Gateway wallet for gasless nanopayments.

### Deposit to Gateway

Move USDC from your EOA to Gateway contract:

```python
result = await client.deposit_to_gateway(
    wallet_id=wallet_id,
    amount_usdc="10.00"
)

print(f"Approval tx: {result.approval_tx_hash}")
print(f"Deposit tx: {result.deposit_tx_hash}")
```

**Note:** Requires ETH for gas.

### Withdraw from Gateway

Move USDC from Gateway back to your EOA:

```python
result = await client.withdraw_from_gateway(
    wallet_id=wallet_id,
    amount_usdc="5.00"
)

print(f"Withdraw tx: {result.mint_tx_hash}")
```

### Check Gateway Balance

```python
balance = await client.get_gateway_balance(wallet_id=wallet_id)
print(f"Total: {balance.formatted_total}")
print(f"Available: {balance.formatted_available}")
```

---

## 6. Transfer to Addresses

Send USDC to any wallet address on the same network.

### Simple Transfer

```python
result = await client.pay(
    wallet_id=wallet_id,
    recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
    amount="50.00"
)

print(f"Success: {result.success}")
print(f"Transaction: {result.blockchain_tx}")
```

### Use Cases

- Pay employees/vendors
- Send to friends/family
- Move funds between wallets
- Any direct transfer

---

## 7. Cross-Chain Transfers

Send USDC to a different blockchain using Circle's CCTP.

### Cross-Chain Payment

```python
# Transfer from Base to Polygon
result = await client.pay(
    wallet_id=wallet_id,
    recipient="0xabcd...1234",  # Polygon address
    amount="100.00",
    destination_chain="POLYGON"  # or POLYGON-AMOY for testnet
)

print(f"Cross-chain success: {result.success}")
```

### Using Gateway Wallet

You can also transfer from your Gateway balance:

```python
from omniclaw.protocols.nanopayments.wallet import GatewayWalletManager

# Create manager with your key
manager = GatewayWalletManager(
    private_key=raw_key,
    network="eip155:84532",  # Base
    rpc_url="YOUR_RPC_URL",
    nanopayment_client=client._nano_client
)

# Cross-chain transfer from Gateway
result = await manager.transfer_crosschain(
    amount_usdc="10.00",
    destination_chain="eip155:137",  # Polygon
    recipient="0xabcd...1234"
)
```

### How It Works

```
1. Your USDC burns on Base
2. Circle mints USDC on Polygon
3. Recipient receives on Polygon
```

### Benefits

- ✅ Instant (vs hours for bridges)
- ✅ No slippage
- ✅ Native USDC (not wrapped)
- ✅ Lower fees

---

## 8. Simulate Before Paying

Check if a payment will succeed BEFORE spending anything.

### Simulate a Payment

```python
sim = await client.simulate(
    wallet_id=wallet_id,
    recipient="https://api.data.com/premium",
    amount="25.00"
)

print(f"Would succeed: {sim.would_succeed}")
print(f"Route: {sim.route}")  # NANOPAYMENT, X402, TRANSFER
print(f"Reason: {sim.reason}")  # Why it would fail

if sim.would_succeed:
    result = await client.pay(wallet_id, recipient, "25.00")
else:
    print(f"Payment blocked: {sim.reason}")
```

### What Simulate Checks

- ✅ Balance sufficient
- ✅ Guards would pass (budget, rate limits, etc.)
- ✅ Recipient allowed
- ✅ Trust Gate verdict (if enabled)
- ✅ Route available

---

## 9. Payment Intents

2-phase commit for payments that need approval or scheduling.

### Create Intent (Authorize)

```python
intent = await client.create_payment_intent(
    wallet_id=wallet_id,
    recipient="0x742d...4a0",
    amount="1000.00",
    purpose="Equipment Purchase",
    expires_in=3600  # Expires in 1 hour
)

print(f"Intent ID: {intent.id}")
print(f"Status: {intent.status}")  # REQUIRES_CONFIRMATION
```

### Confirm Later (Capture)

```python
result = await client.confirm_payment_intent(intent.id)
print(f"Success: {result.success}")
```

### Cancel if Needed

```python
cancelled = await client.cancel_payment_intent(intent.id, reason="User cancelled")
```

### When to Use Intents

- User approval flows
- Scheduled payments
- Complex multi-step transactions
- When ConfirmGuard triggers

---

## 10. Batch Payments

Pay multiple recipients in one call.

### Batch Payment

```python
from omniclaw import PaymentRequest

payments = [
    PaymentRequest(wallet_id=wallet_id, recipient="0x111...", amount="5000.00", purpose="Salary"),
    PaymentRequest(wallet_id=wallet_id, recipient="0x222...", amount="3500.00", purpose="Salary"),
    PaymentRequest(wallet_id=wallet_id, recipient="https://api.vendor.com/invoice/123", amount="1200.00"),
]

result = await client.batch_pay(payments, concurrency=5)

print(f"Total: {result.total}")
print(f"Successful: {result.successful}")
print(f"Failed: {result.failed}")
```

---

## 11. View Transaction History

### List Transactions

```python
transactions = await client.list_transactions(wallet_id=wallet_id)

for tx in transactions:
    print(f"ID: {tx.id}")
    print(f"Amount: {tx.amount}")
    print(f"Status: {tx.status}")  # COMPLETED, FAILED, BLOCKED
    print(f"Recipient: {tx.recipient}")
    print("---")
```

### Sync with Blockchain

```python
entry = await client.sync_transaction(entry_id)
print(f"On-chain tx: {entry.blockchain_tx}")
print(f"Status: {entry.status}")
```

---

## Quick Reference

```python
# Setup
client = OmniClaw(circle_api_key="KEY", network="BASE-SEPOLIA")

# Create wallet
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# Get payment address (fund this with USDC)
address = await client.get_payment_address(wallet_id)
print(f"Fund this address: {address}")

# Add guards
await client.add_budget_guard(wallet_id, daily_limit="1000")
await client.add_single_tx_guard(wallet_id, max_amount="100")
await client.add_recipient_guard(wallet_id, mode="whitelist", domains=["api.vendor.com"])
await client.add_rate_limit_guard(wallet_id, max_per_minute=10)

# Gateway operations
balance = await client.get_gateway_balance(wallet_id=wallet_id)
await client.deposit_to_gateway(wallet_id=wallet_id, amount_usdc="10.00")
await client.withdraw_from_gateway(wallet_id=wallet_id, amount_usdc="5.00")

# Pay for x402 URL
result = await client.pay(wallet_id, "https://api.weather.com", "0.05")

# Transfer to address
result = await client.pay(wallet_id, "0x742d...4a0", "25.00")

# Cross-chain
result = await client.pay(wallet_id, "0x5678...bcd", "100.00", destination_chain="POLYGON")

# Simulate first
sim = await client.simulate(wallet_id, recipient, amount)
if sim.would_succeed:
    result = await client.pay(wallet_id, recipient, amount)

# Payment intent
intent = await client.create_payment_intent(wallet_id, recipient, amount)
result = await client.confirm_payment_intent(intent.id)

# Batch payment
result = await client.batch_pay([PaymentRequest(...), ...])

# View history
transactions = await client.list_transactions(wallet_id)
```

---

## Common Patterns

### Pattern 1: Shopping Agent

```python
# Create wallet for shopping
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# Set strict limits for shopping
await client.add_budget_guard(wallet_id, daily_limit="500.00")
await client.add_single_tx_guard(wallet_id, max_amount="100.00")
await client.add_recipient_guard(wallet_id, mode="whitelist",
    domains=["api.amazon.com", "api.ebay.com", "api.alibaba.com"])

# Shop away!
result = await client.pay(wallet_id, "https://api.amazon.com/products/123", "50.00")
```

### Pattern 2: Research Agent

```python
# Create wallet for research
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# Allow data APIs
await client.add_budget_guard(wallet_id, daily_limit="200.00")
await client.add_recipient_guard(wallet_id, mode="whitelist",
    domains=["api.openai.com", "api.anthropic.com", "api.weather.com", "news.api.com"])

# Research!
result = await client.pay(wallet_id, "https://api.openai.com/v1/completions", "5.00")
```

### Pattern 3: Payroll Agent

```python
# Create wallet for payroll
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# High limits but requires approval for large payments
await client.add_single_tx_guard(wallet_id, max_amount="100000.00")
await client.add_confirm_guard(wallet_id, threshold="10000.00")

# Monthly payroll
await client.batch_pay([
    PaymentRequest(wallet_id=wallet_id, recipient="0xAlice...", amount="5000.00"),
    PaymentRequest(wallet_id=wallet_id, recipient="0xBob...", amount="4500.00"),
    PaymentRequest(wallet_id=wallet_id, recipient="0xCharlie...", amount="6000.00"),
])
```

---

## Troubleshooting

### Error: "wallet_id is required"
- You're calling pay() without passing wallet_id
- Solution: Always pass wallet_id

### Error: "Insufficient available balance"
- Your wallet doesn't have enough USDC
- Solution: Fund your wallet via Circle console

### Error: "Blocked by guard: Daily limit exceeded"
- You've hit your spending limit
- Solution: Wait for reset or adjust limit

### Error: "Wallet is busy"
- Another payment is in progress
- Solution: Wait and retry

### Enable Debug Logging

```python
client = OmniClaw(
    circle_api_key="KEY",
    log_level="DEBUG"  # Gets verbose output
)
```
