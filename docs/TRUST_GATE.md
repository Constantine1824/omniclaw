# Trust Gate Guide

**Verify recipient identity and trust before paying.**

---

## What is Trust Gate?

Trust Gate checks if a payment recipient is trustworthy using ERC-8004 identity and reputation data.

### Trust Evaluation Checks

1. **Identity Resolution** - Is this a registered ERC-8004 identity?
2. **Attestation Level** - Has the identity been verified?
3. **Reputation Score** - What do past transactions say?
4. **Policy Evaluation** - Does the recipient meet your requirements?

### Trust Verdicts

| Verdict | Meaning |
|---------|---------|
| `APPROVED` | Trust check passed, proceed with payment |
| `HELD` | Trust uncertain, require human review |
| `BLOCKED` | Trust check failed, reject payment |

---

## Setup

### Basic Setup (Permissive)

```python
client = OmniClaw(
    circle_api_key="KEY",
    network="BASE-SEPOLIA",
    trust_policy="permissive"  # Default - allow anything unless blocked
)
```

### Production Setup (Standard)

```python
client = OmniClaw(
    circle_api_key="KEY",
    network="BASE-SEPOLIA",
    trust_policy="standard",  # Require basic trust signals
    rpc_url="https://mainnet.infura.io/v3/YOUR_KEY"  # Required for trust checks
)
```

---

## Trust Policies

### Permissive (Testing)

```python
client = OmniClaw(
    circle_api_key="KEY",
    trust_policy="permissive"  # Allow all, trust checks optional
)
```

Best for: Development, internal agents, trusted environments.

### Standard (Recommended)

```python
client = OmniClaw(
    circle_api_key="KEY",
    trust_policy="standard"
)
```

Best for: Production use with basic trust requirements.

### Strict

```python
client = OmniClaw(
    circle_api_key="KEY",
    trust_policy="strict"
)
```

Best for: High-value transactions, untrusted recipients.

### Custom Policy

```python
from omniclaw.identity.types import TrustPolicy

policy = TrustPolicy(
    min_attestation_level=2,           # 1-3, higher is more trusted
    min_reputation_score=0.7,          # 0.0 - 1.0
    block_unknown_identities=True,      # Reject if not ERC-8004 registered
    require_feedback_history=True,      # Must have past transactions
)

client = OmniClaw(
    circle_api_key="KEY",
    trust_policy=policy
)
```

---

## Using Trust Checks

### Per-Payment Control

```python
# Trust check enabled (default if configured)
result = await client.pay(
    wallet_id=wallet_id,
    recipient="0x742d...4a0",
    amount="50.00",
    check_trust=True
)

# Skip trust check for specific payment
result = await client.pay(
    wallet_id=wallet_id,
    recipient="0x742d...4a0",
    amount="50.00",
    check_trust=False
)
```

### Evaluate Without Paying

```python
# Check trust without spending
result = await client.trust.evaluate(
    recipient_address="0x742d...4a0",
    amount=Decimal("50.00"),
    wallet_id=wallet_id
)

print(f"Verdict: {result.verdict}")
print(f"Reason: {result.block_reason}")

if result.verdict == TrustVerdict.APPROVED:
    print("Safe to pay!")
elif result.verdict == TrustVerdict.HELD:
    print("Review needed")
else:
    print("Blocked: do not pay")
```

### Simulate with Trust

```python
sim = await client.simulate(
    wallet_id=wallet_id,
    recipient="0x742d...4a0",
    amount="50.00",
    check_trust=True  # Include trust in simulation
)

print(f"Would succeed: {sim.would_succeed}")
print(f"Reason: {sim.reason}")
```

---

## Trust Signals

### Attestation Level

| Level | Meaning |
|-------|---------|
| 1 | Basic (email verified) |
| 2 | Standard (identity documents) |
| 3 | Enhanced (in-person verification) |

### Reputation Score

- **0.0 - 0.3**: Negative reputation (scams, disputes)
- **0.3 - 0.6**: Neutral reputation (few transactions)
- **0.6 - 0.8**: Positive reputation (good track record)
- **0.8 - 1.0**: Excellent reputation (trusted partner)

### Feedback History

- Number of past transactions
- Average transaction size
- Dispute rate
- Response time

---

## Implementation Details

### How Trust Gate Works

```
Payment Request
      │
      ▼
┌─────────────────┐
│ Check Cache     │ ← Is this recipient cached?
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Resolve Identity │ ← ERC-8004 on-chain lookup
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fetch Metadata  │ ← Attestation, attestors
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Aggregate Rep   │ ← Calculate reputation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Evaluate Policy │ ← Compare against requirements
└────────┬────────┘
         │
         ▼
    ┌────┴────┐
    │ Verdict │
    └────┬────┘
         │
    ┌────┼────┐
    ▼    ▼    ▼
APPROVED HELD BLOCKED
```

### RPC URL Configuration

Trust Gate requires an RPC URL for on-chain lookups:

```env
# .env file
OMNICLAW_RPC_URL=https://mainnet.infura.io/v3/YOUR_KEY
```

Or in code:

```python
client = OmniClaw(
    circle_api_key="KEY",
    rpc_url="https://mainnet.infura.io/v3/YOUR_KEY"
)
```

---

## Common Patterns

### Pattern 1: Trust Known Partners

```python
# Check trust before paying new partners
result = await client.trust.evaluate(recipient, amount, wallet_id)

if result.verdict == TrustVerdict.APPROVED:
    # Known good, auto-pay
    await client.pay(wallet_id, recipient, amount)
elif result.verdict == TrustVerdict.HELD:
    # Uncertain, require approval
    intent = await client.create_payment_intent(wallet_id, recipient, amount)
else:
    # Blocked, don't pay
    print(f"Cannot pay {recipient}: {result.block_reason}")
```

### Pattern 2: Higher Trust for Higher Value

```python
async def pay_with_adaptive_trust(wallet_id, recipient, amount):
    amount_decimal = Decimal(amount)
    
    if amount_decimal > 1000:
        # High value - strict trust
        trust_policy = TrustPolicy(
            min_attestation_level=3,
            min_reputation_score=0.8
        )
    elif amount_decimal > 100:
        # Medium value - standard trust
        trust_policy = "standard"
    else:
        # Low value - permissive
        trust_policy = "permissive"
    
    result = await client.pay(
        wallet_id=wallet_id,
        recipient=recipient,
        amount=amount,
        trust_policy=trust_policy
    )
    return result
```

### Pattern 3: Trust with Fallback

```python
async def pay_with_trust_fallback(wallet_id, recipient, amount):
    # First try with trust check
    try:
        result = await client.pay(
            wallet_id=wallet_id,
            recipient=recipient,
            amount=amount,
            check_trust=True
        )
        return result
    except TrustGateBlockedError:
        # Trust failed, maybe skip for internal testing
        if is_internal_recipient(recipient):
            return await client.pay(
                wallet_id=wallet_id,
                recipient=recipient,
                amount=amount,
                check_trust=False
            )
        raise
```

---

## Troubleshooting

### Error: "Trust Gate requires OMNICLAW_RPC_URL"

```python
# Set RPC URL
client = OmniClaw(
    circle_api_key="KEY",
    rpc_url="https://mainnet.infura.io/v3/YOUR_KEY"
)
```

### Error: "Trust evaluation failed"

Check if:
1. RPC URL is valid
2. Recipient is a valid EVM address
3. Network is supported

### Trust returns HELD

```python
result = await client.trust.evaluate(recipient, amount, wallet_id)

if result.verdict == TrustVerdict.HELD:
    print(f"Uncertain: {result.block_reason}")
    # Options:
    # 1. Require manual approval
    # 2. Request more info from recipient
    # 3. Proceed with caution
```
