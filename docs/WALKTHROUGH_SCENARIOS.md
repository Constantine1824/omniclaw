# Payment Scenarios Walkthrough

**Specific use cases and how to handle them.**

---

## Scenario 1: Pay for an API

You're building an AI agent that needs to call paid APIs.

### Example: Weather API

```python
from omniclaw import OmniClaw

client = OmniClaw(circle_api_key="KEY", network="BASE-SEPOLIA")
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# Set a reasonable daily limit
await client.add_budget_guard(wallet_id, daily_limit="100.00")

# Pay $0.05 for weather data
result = await client.pay(
    wallet_id=wallet_id,
    recipient="https://api.weatherdata.com/v1/current.json",
    amount="0.05"
)

print(f"Weather data: {result.response_data}")
```

### Example: AI Model API

```python
# Allow AI APIs
await client.add_recipient_guard(wallet_id, mode="whitelist",
    domains=["api.openai.com", "api.anthropic.com"])

# Pay $5.00 for GPT-4 completion
result = await client.pay(
    wallet_id=wallet_id,
    recipient="https://api.openai.com/v1/chat/completions",
    amount="5.00"
)
```

### Example: Data Provider

```python
# Allow data providers
await client.add_recipient_guard(wallet_id, mode="whitelist",
    domains=["data.provider1.com", "data.provider2.com", "market.api.com"])

# Pay for market data
result = await client.pay(
    wallet_id=wallet_id,
    recipient="https://data.provider1.com/v2/stock/AAPL",
    amount="0.50"
)
```

---

## Scenario 2: Transfer USDC to Someone

You're building an app that sends USDC to users.

### Example: P2P Transfer

```python
# Send $25 to a friend
result = await client.pay(
    wallet_id=wallet_id,
    recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
    amount="25.00"
)

print(f"Transfer complete: {result.success}")
print(f"Transaction: {result.blockchain_tx}")
```

### Example: Payout to User

```python
# User earned $50 in your app
result = await client.pay(
    wallet_id=wallet_id,
    recipient="0xUserWalletAddress...",
    amount="50.00",
    purpose="Payout for completed task"
)
```

---

## Scenario 3: Cross-Chain Transfer

You need to send USDC to someone on a different blockchain.

### Example: Base to Polygon

```python
# Recipient is on Polygon, you're on Base
result = await client.pay(
    wallet_id=wallet_id,
    recipient="0xabcd...1234",  # Polygon address
    amount="100.00",
    destination_chain="POLYGON"
)
```

### Example: Ethereum to Base

```python
# You're on Ethereum, recipient is on Base
result = await client.pay(
    wallet_id=wallet_id,
    recipient="0x1234...abcd",  # Base address
    amount="50.00",
    destination_chain="BASE"
)
```

### Cross-Chain Networks

| From | To | destination_chain |
|------|----|-------------------|
| Base Sepolia | Polygon Amoy | `POLYGON-AMOY` |
| Base Sepolia | Ethereum Sepolia | `ETHEREUM-SEPOLIA` |
| Base | Polygon | `POLYGON` |
| Base | Ethereum | `ETHEREUM` |
| Polygon | Base | `BASE` |
| Ethereum | Polygon | `POLYGON` |

---

## Scenario 4: Payroll / Bulk Payments

You need to pay multiple people at once.

### Example: Monthly Payroll

```python
from omniclaw import PaymentRequest

# Define payroll
payments = [
    PaymentRequest(
        wallet_id=wallet_id,
        recipient="0xAlice...",
        amount="5000.00",
        purpose="January Salary"
    ),
    PaymentRequest(
        wallet_id=wallet_id,
        recipient="0xBob...",
        amount="4500.00",
        purpose="January Salary"
    ),
    PaymentRequest(
        wallet_id=wallet_id,
        recipient="0xCharlie...",
        amount="6000.00",
        purpose="January Salary"
    ),
]

# Execute payroll
result = await client.batch_pay(payments)

print(f"Total payments: {result.total}")
print(f"Successful: {result.successful}")
print(f"Failed: {result.failed}")
```

### Example: Vendor Invoices + x402

```python
# Mix of wallet transfers and x402 payments
payments = [
    PaymentRequest(
        wallet_id=wallet_id,
        recipient="0xVendor1...",
        amount="2500.00",
        purpose="Invoice #1234"
    ),
    PaymentRequest(
        wallet_id=wallet_id,
        recipient="https://api.cloudprovider.com/monthly",
        amount="500.00",
        purpose="Cloud services"
    ),
    PaymentRequest(
        wallet_id=wallet_id,
        recipient="0xVendor2...",
        amount="1200.00",
        purpose="Invoice #1235"
    ),
]

result = await client.batch_pay(payments, concurrency=3)
```

---

## Scenario 5: User Approval Required

You need human approval before large payments.

### Example: Approval for $500+

```python
# Require approval for large payments
await client.add_confirm_guard(wallet_id, threshold="500.00")

# Create intent (auto-pauses if over threshold)
intent = await client.create_payment_intent(
    wallet_id=wallet_id,
    recipient="0x742d...4a0",
    amount="1000.00",
    purpose="Equipment Purchase"
)

# Check if approval needed
if intent.status == PaymentIntentStatus.REQUIRES_CONFIRMATION:
    # Show approval UI to user
    await show_approval_ui(intent)
else:
    # Auto-approved (under threshold)
    result = await client.confirm_payment_intent(intent.id)
```

### Example: All Payments Need Approval

```python
# Require approval for EVERY payment
await client.add_confirm_guard(wallet_id, always_confirm=True)

# All payments will pause for approval
intent = await client.create_payment_intent(wallet_id, recipient, amount)
# User must approve via confirm_payment_intent()
```

---

## Scenario 6: Check Before Paying

You want to verify a payment will succeed before spending.

### Example: Pre-flight Check

```python
# Check if payment will work
sim = await client.simulate(
    wallet_id=wallet_id,
    recipient="https://api.expensive-data.com/premium",
    amount="100.00"
)

if sim.would_succeed:
    print(f"Ready to pay! Route: {sim.route}")
    result = await client.pay(wallet_id, recipient, "100.00")
else:
    print(f"Payment blocked: {sim.reason}")
    # Handle the issue
```

### Example: Check Balance

```python
sim = await client.simulate(wallet_id, recipient, "1000.00")

if not sim.would_succeed and "balance" in sim.reason.lower():
    print("Need more funds!")
    # Show UI to fund wallet
```

---

## Scenario 7: Multiple Agents, Different Wallets

Each agent has its own wallet with its own limits.

### Example: Agent Team

```python
# Shopping agent - strict limits
shopping_wallet = await client.create_agent_wallet()
await client.add_budget_guard(shopping_wallet.id, daily_limit="100.00")
await client.add_single_tx_guard(shopping_wallet.id, max_amount="25.00")

# Research agent - medium limits
research_wallet = await client.create_agent_wallet()
await client.add_budget_guard(research_wallet.id, daily_limit="500.00")
await client.add_recipient_guard(research_wallet.id, mode="whitelist",
    domains=["api.openai.com", "api.anthropic.com"])

# Payroll agent - high limits, approval required
payroll_wallet = await client.create_agent_wallet()
await client.add_confirm_guard(payroll_wallet.id, threshold="1000.00")

# Each agent operates independently
result = await client.pay(shopping_wallet.id, "https://api.amazon.com...", "20.00")
result = await client.pay(research_wallet.id, "https://api.openai.com...", "50.00")
```

---

## Scenario 8: Wallet Set (Team Budget)

Multiple wallets share a team budget.

### Example: Research Team

```python
# Create wallet set for the team
team_set = await client.create_wallet_set(name="research-team")
team_set_id = team_set.id

# Team-wide budget
await client.add_budget_guard_for_set(team_set_id, daily_limit="2000.00")

# Individual wallets
wallet1 = await client.create_agent_wallet(wallet_set_id=team_set_id)
wallet2 = await client.create_agent_wallet(wallet_set_id=team_set_id)

# Both wallets share the $2000/day team budget
result = await client.pay(wallet1.id, "https://api.openai.com...", "100.00")  # $100 used
result = await client.pay(wallet2.id, "https://api.anthropic.com...", "150.00")  # $250 total
```

---

## Scenario 9: Scheduled Payments

Schedule payments for later execution.

### Example: Subscription

```python
# Create intent for subscription
intent = await client.create_payment_intent(
    wallet_id=wallet_id,
    recipient="0xSubscriptionService...",
    amount="99.00",
    purpose="Monthly subscription",
    expires_in=86400  # 24 hours
)

# Store intent ID for later
schedule_id = intent.id

# Later (when subscription renews):
result = await client.confirm_payment_intent(schedule_id)
```

### Example: Milestone Payment

```python
# Phase 1: Create intent, don't confirm yet
intent = await client.create_payment_intent(
    wallet_id=wallet_id,
    recipient="0xContractor...",
    amount="5000.00",
    purpose="Project milestone 1",
    expires_in=2592000  # 30 days
)

# Wait for milestone completion...

# Phase 2: Confirm when milestone is done
result = await client.confirm_payment_intent(intent.id)
```

---

## Scenario 10: Rate Limiting Protection

Protect against runaway agents or abuse.

### Example: Prevent Spam

```python
# Allow max 10 payments per minute
await client.add_rate_limit_guard(wallet_id, max_per_minute=10)

# Agent tries to make 15 payments
for i in range(15):
    try:
        await client.pay(wallet_id, recipient, "1.00")
    except RateLimitError:
        print(f"Rate limited! Only {i} payments went through")
        break
```

### Example: Hourly Spending Cap

```python
# Max 50 payments per hour
await client.add_rate_limit_guard(wallet_id, max_per_hour=50)

# Max $500 per hour
await client.add_budget_guard(wallet_id, hourly_limit="500.00")
```

---

## Scenario 11: Whitelist Specific Sellers

Only allow payments to approved sellers.

### Example: Approved Vendor List

```python
await client.add_recipient_guard(wallet_id, mode="whitelist",
    addresses=[
        "0xAmazon...",
        "0xOpenAI...",
        "0xAnthropic...",
    ],
    domains=[
        "api.amazon.com",
        "api.openai.com",
        "api.anthropic.com",
        "api.stripe.com",
    ]
)

# These work:
await client.pay(wallet_id, "https://api.openai.com...", "10.00")
await client.pay(wallet_id, "0xAmazon...", "100.00")

# This is BLOCKED:
await client.pay(wallet_id, "https://random-site.com...", "10.00")  # ❌
```

### Example: Block Known Bad Actors

```python
await client.add_recipient_guard(wallet_id, mode="blacklist",
    addresses=["0xScammerWallet..."],
    domains=["known-scam-site.com"]
)
```

---

## Scenario 12: Combined Guards

Stack multiple guards for maximum safety.

### Example: Shopping Agent with Full Controls

```python
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# Budget: $500/day, $100/hour, $10k total
await client.add_budget_guard(wallet_id, 
    daily_limit="500.00",
    hourly_limit="100.00",
    total_limit="10000.00"
)

# Single transaction: $50-$100
await client.add_single_tx_guard(wallet_id,
    max_amount="100.00",
    min_amount="5.00"
)

# Only approved vendors
await client.add_recipient_guard(wallet_id, mode="whitelist",
    domains=["api.amazon.com", "api.ebay.com", "api.alibaba.com"]
)

# Max 20 payments/minute
await client.add_rate_limit_guard(wallet_id, max_per_minute=20)

# Large payments need approval
await client.add_confirm_guard(wallet_id, threshold="200.00")

# Now this agent is very safe!
result = await client.pay(wallet_id, "https://api.amazon.com...", "50.00")
```
