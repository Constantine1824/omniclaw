# OmniClaw SDK Usage Guide

This guide covers the common SDK workflows without repeating the full architecture or every method signature.

## 1. Initialize the Client

```python
from omniclaw import OmniClaw, Network

client = OmniClaw(network=Network.ARC_TESTNET)
```

With environment variables:

```env
CIRCLE_API_KEY=your_circle_api_key
ENTITY_SECRET=your_entity_secret
OMNICLAW_NETWORK=ARC-TESTNET
```

Optional runtime settings:

```env
OMNICLAW_STORAGE_BACKEND=redis
OMNICLAW_REDIS_URL=redis://localhost:6379
OMNICLAW_LOG_LEVEL=DEBUG
OMNICLAW_RPC_URL=https://your-rpc-provider
```

### Entity Secret Recovery

When `ENTITY_SECRET` is missing, the SDK can auto-generate and register one if `CIRCLE_API_KEY` is available.

What gets stored:

- active entity secret: environment or `.env`
- Circle recovery file: user config directory

Linux recovery-file location:

```text
~/.config/omniclaw/
```

This matters because Circle entity secret registration is effectively a one-time setup per account until you recover or reset it.

Run the built-in diagnostic command to check the full state:

```bash
omniclaw doctor
```

## 2. Create a Wallet

Fastest path:

```python
wallet_set, wallet = await client.create_agent_wallet("agent-007")
```

Manual path:

```python
wallet_set = await client.create_wallet_set("ops-wallets")
wallet = await client.create_wallet(
    wallet_set_id=wallet_set.id,
    blockchain=Network.ETH,
)
```

Common wallet operations:

```python
wallets = await client.list_wallets(wallet_set_id=wallet_set.id)
wallet_info = await client.get_wallet(wallet.id)
balance = await client.get_balance(wallet.id)
transactions = await client.list_transactions(wallet_id=wallet.id)
```

## 3. Add Safety Guards

```python
await client.add_budget_guard(wallet.id, daily_limit="100.00", hourly_limit="20.00")
await client.add_rate_limit_guard(wallet.id, max_per_minute=5)
await client.add_single_tx_guard(wallet.id, max_amount="25.00")
await client.add_recipient_guard(
    wallet.id,
    mode="whitelist",
    addresses=["0xTrustedRecipient"],
    domains=["api.openai.com"],
)
await client.add_confirm_guard(wallet.id, threshold="500.00")
```

Wallet-set guard helpers apply the same logic across all wallets in a set.

```python
await client.add_budget_guard_for_set(wallet_set.id, daily_limit="500.00")
await client.add_rate_limit_guard_for_set(wallet_set.id, max_per_hour=100)
```

## 4. Execute a Payment

```python
result = await client.pay(
    wallet_id=wallet.id,
    recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
    amount="10.50",
    purpose="vendor payment",
)
```

Key runtime arguments:

- `wallet_id`: required source wallet
- `recipient`: blockchain address or URL
- `amount`: USDC amount
- `destination_chain`: set for cross-chain flows
- `purpose`: audit-friendly note
- `idempotency_key`: caller-controlled dedupe key
- `skip_guards`: bypass guards, only for special cases
- `check_trust`: `None`, `True`, or `False`
- `wait_for_completion`: wait for provider confirmation when supported

## 5. Understand Routing

OmniClaw routes automatically:

- address -> direct transfer
- URL -> x402
- address + `destination_chain` -> gateway/cross-chain

Examples:

```python
await client.pay(wallet_id=wallet.id, recipient="0xRecipient", amount="5.00")
await client.pay(wallet_id=wallet.id, recipient="https://api.vendor.com/paywall", amount="0.05")
await client.pay(
    wallet_id=wallet.id,
    recipient="0xRecipientOnBase",
    amount="20.00",
    destination_chain=Network.BASE,
)
```

## 6. Simulate Before Sending

```python
sim = await client.simulate(
    wallet_id=wallet.id,
    recipient="0xRecipient",
    amount="25.00",
)

if sim.would_succeed:
    print(sim.route)
else:
    print(sim.reason)
```

Simulation checks:

- balance after reservations
- guard outcomes
- trust outcome when enabled
- adapter suitability

## 7. Use Payment Intents for Approval Flows

```python
intent = await client.create_payment_intent(
    wallet_id=wallet.id,
    recipient="0xRecipient",
    amount="250.00",
    purpose="high-value purchase",
)
```

Confirm later:

```python
result = await client.confirm_payment_intent(intent.id)
```

Cancel if needed:

```python
await client.cancel_payment_intent(intent.id, reason="approval denied")
```

Use intents when you need:

- human review
- delayed execution
- serialized approval flows
- explicit reservation of spendable balance

## 8. Enable Trust Checks

Set a real RPC URL:

```env
OMNICLAW_RPC_URL=https://your-rpc-provider
```

Then request trust evaluation:

```python
result = await client.pay(
    wallet_id=wallet.id,
    recipient="0xRecipient",
    amount="10.00",
    check_trust=True,
)
```

Rules:

- `check_trust=True` fails if no real RPC URL is configured
- `check_trust=None` uses auto mode
- `check_trust=False` skips trust evaluation

## 9. Webhooks

Use the webhook parser when handling Circle events:

```python
event = client.webhooks.handle(payload, headers)
```

If signature verification is configured, pass the raw payload and headers so verification can run before parsing.

## 10. Operational Guidance

- Use Redis in any concurrent deployment.
- Keep `OMNICLAW_NETWORK` explicit in every deployed environment.
- Keep trust checks opt-in unless your deployment is prepared with a working RPC provider.
- Prefer `simulate()` for higher-risk or user-approved operations.
- Prefer payment intents for review-required or delayed-execution flows.
