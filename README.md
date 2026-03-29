# OmniClaw

<div align="center">

[![GitHub Stars](https://img.shields.io/github/stars/omnuron/omniclaw?style=flat&color=gold)](https://github.com/omnuron/omniclaw/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/omnuron/omniclaw?style=flat&color=blue)](https://github.com/omnuron/omniclaw/network/members)
[![PyPI](https://img.shields.io/pypi/v/omniclaw?color=green)](https://pypi.org/project/omniclaw/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Website](https://img.shields.io/badge/website-omniclaw.ai-purple)](https://www.omniclaw.ai/)

</div>

**OmniClaw is the economic control and trust infrastructure for autonomous agents — enabling them to pay, get paid, and transact securely under real-time policy enforcement.**

OmniClaw is the full payment layer for AI agents — not just paying, but earning too. It sits between raw wallet infrastructure and production payment flows so AI agents and AI-powered apps can move money with better safety, trust, and operator control.

Instead of wiring wallets, payment routing, guardrails, intents, trust checks, and recovery flows by hand, OmniClaw gives you one SDK for:

**For Agents That Pay:**
- wallet creation and management
- guarded `pay()` execution
- `simulate()` before funds move
- x402 and direct transfer routing
- cross-chain USDC flows
- payment intents with reservation handling
- nanopayments — gas-free EIP-3009 USDC transfers via Circle Gateway

**For Agents That Earn:**
- Seller SDK — accept payments with automatic 402 responses
- `sell()` decorator — protect endpoints and get paid automatically
- Facilitated transfers — handle settlement on behalf of agents
- Trust-gated access — only pay verified agents

**For Operators That Control:**
- policy enforcement at the payment layer
- spending limits, velocity controls, and circuit breakers
- audit-ready transaction logs
- recovery flows and SLA enforcement

## Trust Layer

Agentic payments require a new kind of trust evaluation. When an autonomous agent initiates a payment, that means better answers to questions like:

- who is this agent?
- what trust signals exist for it?
- should this payment proceed automatically?
- when should a payment be held, confirmed, or blocked?

OmniClaw integrates ERC-8004-style trust evaluation into the SDK so developers can add trust-aware payment logic without building a separate reputation and validation layer first.

## 🔒 Compliance Architecture

Agentic payments introduce a question that traditional compliance frameworks weren't built to answer: **who authorized this transaction — and is that authorization provable?**

OmniClaw is designed with this question at the center of its execution layer:

- **Authorization traceability** — every payment call is tied to an explicit agent identity and operator policy, creating an auditable authorization chain from instruction to settlement
- **Pre-execution simulation** — `simulate()` creates a compliance checkpoint before funds move, letting operators review high-value or anomalous transactions before they execute
- **Operator-controlled guardrails** — spending limits, velocity checks, and trust thresholds are set at the operator level, not hardcoded, supporting jurisdiction-specific policy enforcement
- **Regulatory alignment** — OmniClaw's architecture anticipates emerging frameworks like the CLARITY Act, where the core question is whether payment flows were *actively authorized* vs passively accrued. Every OmniClaw transaction has an explicit authorization event on record.
- **Separation of concerns** — the agent executes; the operator controls policy; the compliance layer enforces. No single point conflates all three, making audit and oversight tractable.

For a deeper dive into the compliance design decisions: [Compliance Architecture →](docs/compliance-architecture.md)

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

## Quick Setup

1. Create a `.env` file:

```
CIRCLE_API_KEY=your_circle_api_key
ENTITY_SECRET=your_entity_secret
```

2. Configure in code:

```python
from omniclaw import OmniClaw, Network

client = OmniClaw(network=Network.BASE_SEPOLIA)
```

Network is set in code, RPC from `.env`.

## Environment Variables

### Required
```
CIRCLE_API_KEY=your_circle_api_key
ENTITY_SECRET=your_entity_secret
```

### Optional (set as needed)
```
# RPC endpoint (for trust gate)
OMNICLAW_RPC_URL=https://sepolia.base.org
```

## Entity Secret and Recovery

OmniClaw uses Circle's entity secret model:

- `ENTITY_SECRET` is the signing secret the SDK needs to create wallets and sign transactions.
- The Circle recovery file is stored in the user config directory, not in the repo.
- On Linux, that path is `~/.config/omniclaw/`.

Current behavior:
- If `ENTITY_SECRET` is missing and `CIRCLE_API_KEY` is present, the SDK can auto-generate and register a new entity secret.
- During that flow, the Circle recovery file is written to the user config directory.
- If a local `.env` file exists, the generated `ENTITY_SECRET` is appended to it.

**Important limitation:**
- The recovery file is not the same thing as the entity secret.
- OmniClaw reads the active `ENTITY_SECRET` from constructor arguments or environment.
- If a user loses both the entity secret and the recovery file, the account becomes difficult or impossible to recover without Circle-side reset steps.

Check your machine state any time with:

```bash
omniclaw doctor
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and how to submit pull requests.

## License

MIT — see [LICENSE](LICENSE) for details.
