# OmniClaw

**The payment infrastructure for autonomous AI agents.**

Programmable wallets. Real-time settlement. Trust-aware execution.

Create agent wallets. Simulate payments. Enforce spending controls. Move USDC safely.

If you are building AI agents that need to pay, charge, subscribe, purchase, or settle onchain, OmniClaw gives you the layer between raw wallet infrastructure and production payment execution.

Instead of wiring wallets, payment routing, guardrails, intents, trust checks, and recovery flows by hand, you get one SDK that handles:

- wallet creation and management
- guarded `pay()` execution
- `simulate()` before funds move
- x402 and direct transfer routing
- cross-chain USDC flows
- payment intents with reservation handling
- ERC-8004-style trust-aware checks

This is the missing execution layer for agent payments.

- Product: `OmniClaw`
- Company: `Omnuron AI`
- Sites: `omniclaw.ai` and `omnuron.ai`
- SDK status: `405` passing SDK tests in `tests/`
- Python: `>=3.10`
- Package: `omniclaw`

## Why Developers Try OmniClaw

- Ship agent payments without building your own execution layer from scratch
- Use one SDK across wallets, simulation, execution, guardrails, and trust-aware payments
- Give operators controls before an autonomous agent can spend
- Evaluate identity and trust signals, not just bare wallet addresses

## Why OmniClaw Wins The First Test

- You can understand the product in one minute.
- You can verify your setup with `omniclaw doctor`.
- You can create a wallet, simulate a payment, and execute it with one client.
- You can see immediately that trust, safety, and operator control are core product features, not future ideas.

## Get Running Fast

1. Install the SDK.
2. Run `omniclaw doctor` to verify credentials and recovery state.
3. Create an agent wallet.
4. Run `simulate()` before moving funds.
5. Execute `pay()` once the route and guardrails look right.

```bash
pip install omniclaw
omniclaw doctor
```

```python
from omniclaw import Network, OmniClaw

client = OmniClaw(network=Network.ARC_TESTNET)

wallet_set, wallet = await client.create_agent_wallet("research-agent")

simulation = await client.simulate(
    wallet_id=wallet.id,
    recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
    amount="2.50",
)

if simulation.would_succeed:
    result = await client.pay(
        wallet_id=wallet.id,
        recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0",
        amount="2.50",
        purpose="agent purchase",
    )
```

That is the core OmniClaw workflow: verify setup, create a wallet, simulate the payment, then execute safely.

## What It Does

- Create and manage Circle wallet sets and wallets
- Execute `pay()` with automatic routing for addresses, URLs, and cross-chain transfers
- Enforce guardrails with budget, rate-limit, recipient, single-tx, and confirm guards
- Support authorize/confirm flows with payment intents
- Simulate payments before execution
- Record transaction history in the built-in ledger
- Optionally run ERC-8004 trust verification when an RPC URL is configured

## Why Now

The market is moving in pieces:

- Circle is pushing wallet infrastructure and USDC nanopayments for agentic commerce.
- Coinbase is pushing x402 and agentic wallets.
- OKX is pushing AI-native onchain operating systems.
- Privy is pushing wallet infrastructure for apps and agents.

That is good for builders, but it still leaves a real gap: most teams do not need just another wallet API. They need a reliable execution layer that lets agents actually move money safely.

OmniClaw is built for that gap.

## Why Teams Use OmniClaw

- Raw wallet APIs are not enough. Agents need policy, simulation, reservations, idempotency, and failure handling before they are allowed to spend.
- x402 is powerful, but it is only one rail. Most production products need one SDK that can handle wallet transfers, x402 endpoints, and cross-chain USDC movement together.
- Payment safety cannot live in ad hoc app code. OmniClaw ships budget guards, rate limits, recipient controls, single-tx limits, confirm thresholds, payment intents, and ledger tracking as first-class primitives.
- Trust matters when an agent pays another agent. OmniClaw surfaces ERC-8004-style trust evaluation so developers can make decisions with more context than a bare address.
- Developer adoption matters. The entry point stays simple: initialize `OmniClaw`, create a wallet, run `simulate()`, then call `pay()`.

## Why Trust Matters

Most payment SDKs stop at settlement. Autonomous agents need more.

When one agent pays another, developers increasingly want to know:

- who is receiving this payment
- whether trust metadata exists for that recipient
- whether the payment should proceed automatically or be held
- whether the operator can enforce a policy around risky recipients

OmniClaw makes that visible through ERC-8004-style trust evaluation and integrates it directly into the payment workflow.

## What Makes OmniClaw Different

- Use Circle for wallet custody and transaction infrastructure.
- Use x402 where pay-per-request HTTP payments make sense.
- Use OmniClaw to orchestrate execution safely across those systems.

That means fewer one-off payment scripts, less duplicated safety code, and a faster path from demo agent to production agent.

OmniClaw is not trying to replace the wallet or settlement providers already entering this market. It is the layer that makes them usable for autonomous execution.

## Proof Points

- `pay()` routes across direct transfers, x402-style URLs, and cross-chain USDC flows.
- `simulate()` lets agents and operators know whether a payment would succeed before funds move.
- Payment intents provide authorize/confirm/cancel flows with reservation handling.
- Built-in guards give operators programmable spending controls.
- `omniclaw doctor` gives developers and operators one command to verify credential, recovery, and setup state.
- ERC-8004 support makes trust and identity part of the product story, not an afterthought.

## Trust-Aware By Design

Autonomous payments need more than successful settlement. They need better answers to questions like:

- who is this agent?
- what trust signals exist for it?
- should this payment proceed automatically?
- when should a payment be held, confirmed, or blocked?

OmniClaw integrates ERC-8004-style trust evaluation into the SDK so developers can add trust-aware payment logic without building a separate reputation and validation layer first.

For teams building agent-to-agent markets, autonomous service providers, or machine-to-machine commerce, that matters.

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

## Operator UX

OmniClaw is not only a payment SDK. It also tries to reduce setup and recovery friction for developers and operators.

- `omniclaw doctor` checks whether your machine is ready
- managed credentials are stored in `~/.config/omniclaw/`
- Circle recovery files are surfaced as part of the doctor output
- `omniclaw doctor --json` supports support tooling and automation

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
