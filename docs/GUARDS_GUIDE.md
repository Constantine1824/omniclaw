# Guards Guide

**The Guard Kernel protects your agent's spending.**

---

## What Are Guards?

Guards are security rules that run BEFORE every payment. They can:
- Block payments that exceed limits
- Require human approval
- Allow only specific recipients

OmniClaw guards run in a **chain** - all guards must pass for a payment to proceed.

---

## Guard Flow

```
Payment Request
      │
      ▼
┌─────────────────┐
│   Trust Gate    │ ← Check recipient identity
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Guard Kernel   │ ← All guards check here
│  ┌───────────┐ │
│  │   Budget  │ │
│  └─────┬─────┘ │
│  ┌─────┴─────┐ │
│  │   SingleTx │ │
│  └─────┬─────┘ │
│  ┌─────┴─────┐ │
│  │ Recipient │ │
│  └─────┬─────┘ │
│  ┌─────┴─────┐ │
│  │   Rate    │ │
│  └─────┬─────┘ │
│  ┌─────┴─────┐ │
│  │  Confirm  │ │
│  └───────────┘ │
└────────┬────────┘
         │
    ┌────┴────┐
    │ PASS?   │
    └────┬────┘
         │
    ┌────┴────┐
    │   YES   │
    └────┬────┘
         │
         ▼
   Execute Payment
```

---

## Available Guards

### 1. BudgetGuard

Limits total spending over time periods.

```python
await client.add_budget_guard(
    wallet_id=wallet_id,
    daily_limit="1000.00",      # Max per 24 hours
    hourly_limit="100.00",       # Max per hour
    total_limit="50000.00"       # Max ever
)
```

**Example:**
```python
# Agent already spent $950 today, tries to pay $100
await client.pay(wallet_id, recipient, "100.00")
# BLOCKED: "Daily limit exceeded ($950 of $1000 used)"
```

---

### 2. SingleTxGuard

Limits individual transaction size.

```python
# Max per transaction
await client.add_single_tx_guard(wallet_id, max_amount="100.00")

# With minimum (prevent dust)
await client.add_single_tx_guard(wallet_id,
    max_amount="100.00",
    min_amount="0.01"
)
```

**Example:**
```python
# Agent tries to pay $150, limit is $100
await client.pay(wallet_id, recipient, "150.00")
# BLOCKED: "Single transaction limit exceeded ($150 > $100 max)"
```

---

### 3. RecipientGuard

Controls which recipients can be paid.

```python
# Whitelist mode (only these can be paid)
await client.add_recipient_guard(
    wallet_id=wallet_id,
    mode="whitelist",
    addresses=["0x742d...4a0"],           # Specific wallets
    domains=["api.openai.com"],           # x402 domains
    patterns=[r"https://data\.vendor[0-9]+\.com"]  # Regex
)

# Blacklist mode (block specific recipients)
await client.add_recipient_guard(
    wallet_id=wallet_id,
    mode="blacklist",
    addresses=["0xSCAM...wallet"],
    domains=["known-bad-site.com"]
)
```

**Example:**
```python
# Agent tries to pay unapproved vendor
await client.add_recipient_guard(wallet_id, mode="whitelist",
    domains=["api.openai.com", "api.anthropic.com"])

await client.pay(wallet_id, "https://api.unknown-vendor.com...", "10.00")
# BLOCKED: "Recipient not in whitelist"
```

---

### 4. RateLimitGuard

Limits payment frequency.

```python
await client.add_rate_limit_guard(
    wallet_id=wallet_id,
    max_per_minute=10,    # Max per minute
    max_per_hour=100,     # Max per hour
    max_per_day=500       # Max per day
)
```

**Example:**
```python
# Agent already made 10 payments this minute
for i in range(10):
    await client.pay(wallet_id, recipient, "1.00")  # OK

await client.pay(wallet_id, recipient, "1.00")
# BLOCKED: "Rate limit exceeded (10/10 per minute)"
```

---

### 5. ConfirmGuard

Requires human approval for large payments.

```python
# Threshold mode
await client.add_confirm_guard(
    wallet_id=wallet_id,
    threshold="500.00"  # Payments over $500 need approval
)

# Always confirm mode
await client.add_confirm_guard(
    wallet_id=wallet_id,
    always_confirm=True  # ALL payments need approval
)
```

**Example:**
```python
# Agent tries to pay $1000, threshold is $500
await client.add_confirm_guard(wallet_id, threshold="500.00")

intent = await client.create_payment_intent(wallet_id, recipient, "1000.00")
# Status: REQUIRES_CONFIRMATION

# Human approves:
result = await client.confirm_payment_intent(intent.id)
# Payment executes
```

---

## Guard Combinations

### Shopping Agent

```python
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# $500/day, $50 per purchase
await client.add_budget_guard(wallet_id, daily_limit="500.00")
await client.add_single_tx_guard(wallet_id, max_amount="50.00")

# Only approved vendors
await client.add_recipient_guard(wallet_id, mode="whitelist",
    domains=["api.amazon.com", "api.ebay.com", "api.alibaba.com"])

# Max 10 purchases/minute
await client.add_rate_limit_guard(wallet_id, max_per_minute=10)
```

### Research Agent

```python
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# $200/day, $20 per API call
await client.add_budget_guard(wallet_id, daily_limit="200.00")
await client.add_single_tx_guard(wallet_id, max_amount="20.00")

# Only AI APIs
await client.add_recipient_guard(wallet_id, mode="whitelist",
    domains=["api.openai.com", "api.anthropic.com", "api.google.com"])
```

### Payroll Agent

```python
wallet = await client.create_agent_wallet()
wallet_id = wallet.id

# Large payments need approval
await client.add_confirm_guard(wallet_id, threshold="5000.00")

# Whitelist employees
await client.add_recipient_guard(wallet_id, mode="whitelist",
    addresses=[
        "0xAlice...",
        "0xBob...",
        "0xCharlie...",
    ]
)
```

---

## Wallet Sets (Group Guards)

Apply guards to MULTIPLE wallets at once.

```python
# Create team wallet set
team = await client.create_wallet_set(name="research-team")
team_id = team.id

# Create wallets in the set
wallet1 = await client.create_agent_wallet(wallet_set_id=team_id)
wallet2 = await client.create_agent_wallet(wallet_set_id=team_id)

# Apply team budget (shared by all)
await client.add_budget_guard_for_set(team_id, daily_limit="5000.00")

# Both wallets share the $5000/day budget
result = await client.pay(wallet1.id, recipient, "1000.00")  # $1000 used
result = await client.pay(wallet2.id, recipient, "2000.00")  # $3000 total
```

---

## List Guards

```python
# List guards on a wallet
guards = await client.list_guards(wallet_id)
print(guards)  # ['budget', 'single_tx', 'recipient']

# List guards on a wallet set
guards = await client.list_guards_for_set(wallet_set_id)
```

---

## Remove Guards

```python
guard_manager = client.guards

# Remove specific guard
await guard_manager.remove_guard(wallet_id, "rate_limit")

# Clear all guards
await guard_manager.clear_guards(wallet_id)
```

---

## Skip Guards (Testing Only)

```python
# Skip ALL guards (dangerous!)
result = await client.pay(
    wallet_id=wallet_id,
    recipient=recipient,
    amount=amount,
    skip_guards=True  # NEVER use in production!
)
```

---

## Guard Precedence

When multiple guards apply:

1. **Trust Gate** runs first (identity check)
2. **SingleTxGuard** runs second (fastest check)
3. **BudgetGuard** runs third
4. **RecipientGuard** runs fourth
5. **RateLimitGuard** runs fifth
6. **ConfirmGuard** runs last

First failure stops the chain.
