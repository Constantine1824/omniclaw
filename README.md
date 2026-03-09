# OmniClaw

OmniClaw is the AI payments SDK from Omnuron AI. It gives developers one execution surface for wallet creation, guarded spending, direct transfers, x402 payments, cross-chain USDC routing, payment intents, and ERC-8004 trust checks on Circle developer-controlled wallets.

The SDK is launch-focused: one client, explicit environment configuration, and a safety model built around guards, reservations, locks, and a ledger.

- Product: `OmniClaw`
- Company: `Omnuron AI`
- Sites: `omniclaw.ai` and `omnuron.ai`
- SDK status: `405` passing SDK tests in `tests/`
- Python: `>=3.10`
- Package: `omniclaw`

## What It Does

- Create and manage Circle wallet sets and wallets
- Execute `pay()` with automatic routing for addresses, URLs, and cross-chain transfers
- Enforce guardrails with budget, rate-limit, recipient, single-tx, and confirm guards
- Support authorize/confirm flows with payment intents
- Simulate payments before execution
- Record transaction history in the built-in ledger
- Optionally run ERC-8004 trust verification when an RPC URL is configured

## Install

```bash
pip install omniclaw
```

For local development in this repo:

```bash
uv sync --extra dev
```

To build release artifacts with one command:

```bash
./build.sh
```

## Required Environment

Minimum runtime configuration:

```env
CIRCLE_API_KEY=your_circle_api_key
ENTITY_SECRET=your_entity_secret
OMNICLAW_NETWORK=ARC-TESTNET
```

Common optional settings:

```env
OMNICLAW_STORAGE_BACKEND=redis
OMNICLAW_REDIS_URL=redis://localhost:6379
OMNICLAW_LOG_LEVEL=INFO
OMNICLAW_RPC_URL=https://your-rpc-provider
```

Notes:

- `OMNICLAW_REDIS_URL` is the only Redis URL env used by the SDK.
- Trust verification is optional by default.
- If you explicitly request trust verification with `check_trust=True`, `OMNICLAW_RPC_URL` must be set to a real RPC endpoint.

## Entity Secret and Recovery

OmniClaw uses Circle's entity secret model:

- `ENTITY_SECRET` is the signing secret the SDK needs to create wallets and sign transactions.
- The Circle recovery file is stored in the user config directory, not in the repo.
- On Linux, that path is `~/.config/omniclaw/`.

Current behavior:

- If `ENTITY_SECRET` is missing and `CIRCLE_API_KEY` is present, the SDK can auto-generate and register a new entity secret.
- During that flow, the Circle recovery file is written to the user config directory.
- If a local `.env` file exists, the generated `ENTITY_SECRET` is appended to it.

Important limitation:

- The recovery file is not the same thing as the entity secret.
- OmniClaw reads the active `ENTITY_SECRET` from constructor arguments or environment.
- If a user loses both the entity secret and the recovery file, the account becomes difficult or impossible to recover without Circle-side reset steps.

Check your machine state any time with:

```bash
omniclaw doctor
```

This reports:

- whether `CIRCLE_API_KEY` is set
- whether `ENTITY_SECRET` is available from env
- whether OmniClaw has a managed secret stored in `~/.config/omniclaw/`
- whether a Circle recovery file exists

Recommended first-run flow:

```bash
omniclaw doctor
```

Use it before sending funds or creating production wallets. A healthy machine should report:

- Circle SDK installed
- `CIRCLE_API_KEY` present
- `ENTITY_SECRET` available from env or managed config
- managed credential store found in `~/.config/omniclaw/`
- Circle recovery file present

For support tooling or automation:

```bash
omniclaw doctor --json
```

## Quick Start

```python
from omniclaw import OmniClaw, Network

client = OmniClaw(network=Network.ARC_TESTNET)

wallet_set, wallet = await client.create_agent_wallet("research-agent")

await client.add_budget_guard(wallet.id, daily_limit="100.00", hourly_limit="20.00")
await client.add_recipient_guard(
    wallet.id,
    mode="whitelist",
    domains=["api.openai.com"],
)

result = await client.pay(
    wallet_id=wallet.id,
    recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
    amount="10.50",
    purpose="model usage",
)
```

## Core Flows

### 1. Wallets

```python
wallet_set = await client.create_wallet_set("prod-agents")
wallet = await client.create_wallet(wallet_set_id=wallet_set.id, blockchain=Network.ETH)
balance = await client.get_balance(wallet.id)
```

### 2. Payments

```python
result = await client.pay(
    wallet_id=wallet.id,
    recipient="https://api.vendor.com/premium-endpoint",
    amount="0.25",
    purpose="pay-per-use API call",
)
```

Routing behavior:

- blockchain address -> direct transfer
- URL -> x402 flow
- `destination_chain` set -> cross-chain gateway flow

### 3. Simulation

```python
sim = await client.simulate(
    wallet_id=wallet.id,
    recipient="0xRecipient",
    amount="25.00",
)

if not sim.would_succeed:
    print(sim.reason)
```

### 4. Payment Intents

```python
intent = await client.create_payment_intent(
    wallet_id=wallet.id,
    recipient="0xRecipient",
    amount="250.00",
    purpose="approved purchase",
)

result = await client.confirm_payment_intent(intent.id)
```

## Guards

Guards are the main safety layer in OmniClaw. They run before execution and are integrated with reservation and lock handling.

```python
await client.add_budget_guard(wallet.id, daily_limit="100.00")
await client.add_rate_limit_guard(wallet.id, max_per_minute=5)
await client.add_single_tx_guard(wallet.id, max_amount="25.00")
await client.add_recipient_guard(wallet.id, mode="whitelist", addresses=["0xTrusted"])
await client.add_confirm_guard(wallet.id, threshold="500.00")
```

Available guards:

- `BudgetGuard`
- `RateLimitGuard`
- `SingleTxGuard`
- `RecipientGuard`
- `ConfirmGuard`

## Trust Gate

OmniClaw can evaluate ERC-8004 trust data before a payment.

```python
result = await client.pay(
    wallet_id=wallet.id,
    recipient="0xRecipient",
    amount="5.00",
    check_trust=True,
)
```

Behavior:

- `check_trust=None`: auto mode
- `check_trust=True`: require trust evaluation and reject if no RPC is configured
- `check_trust=False`: skip trust evaluation

## Documentation

Start here:

- [Docs Index](docs/README.md)
- [SDK Usage Guide](docs/SDK_USAGE_GUIDE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Architecture and Features](docs/FEATURES.md)
- [Cross-Chain Usage](docs/CCTP_USAGE.md)
- [ERC-8004 Spec Notes](docs/erc_804_spec.md)
- [Roadmap](docs/ROADMAP.md)

## Development

```bash
uv sync --extra dev
.venv/bin/pytest tests
```

Useful checks:

```bash
python3 -m compileall src
.venv/bin/ruff check src tests
./build.sh
```

## Repository Layout

```text
src/omniclaw/         SDK source
tests/                SDK test suite
docs/                 User and developer documentation
examples/             Example integrations
mcp-server/           Optional MCP server, not required for SDK usage
```

## Launch Notes

For GitHub publishing, the SDK surface should be treated as the primary product entry point. If you are only shipping the SDK today, keep README and docs centered on:

- environment setup
- wallet creation
- safe payment execution
- intents and simulation
- trust and Redis behavior

That is the path this doc set now follows.
