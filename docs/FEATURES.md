# OmniClaw Architecture and Features

This document explains how the SDK is structured and what each subsystem is responsible for. Use the [SDK Usage Guide](SDK_USAGE_GUIDE.md) for examples and the [API Reference](API_REFERENCE.md) for method signatures.

## System Overview

OmniClaw is centered on `OmniClaw`, which wires together:

- configuration loading
- wallet management
- storage
- guards
- reservations and fund locking
- payment routing
- ledger persistence
- payment intents
- webhook verification
- optional trust evaluation

## Main Components

### `OmniClaw`

The top-level client in [client.py](../src/omniclaw/client.py). It exposes the public async SDK surface:

- wallet creation and lookup
- payment execution and simulation
- intent creation, confirmation, and cancellation
- guard management helpers
- ledger access
- trust access

### Wallet Service

The wallet layer in [wallet/service.py](../src/omniclaw/wallet/service.py) wraps Circle wallet operations:

- wallet set creation
- wallet creation
- wallet lookup and listing
- balance lookup
- transaction lookup
- direct transfers

Circle client initialization is lazy, so local tests and non-network flows do not require immediate provider calls at client construction time.

### Payment Router

The router in [payment/router.py](../src/omniclaw/payment/router.py) chooses an adapter based on recipient shape and destination chain.

Current routing:

- address -> `TransferAdapter`
- URL -> `X402Adapter`
- `destination_chain` set -> `GatewayAdapter`

### Guards

The guard system in [guards/](../src/omniclaw/guards) is the primary spend-control layer.

Supported guard types:

- `BudgetGuard`
- `RateLimitGuard`
- `SingleTxGuard`
- `RecipientGuard`
- `ConfirmGuard`

Guard checks are integrated with reservation and commit/release behavior so failed payments do not permanently consume policy limits.

### Reservations and Fund Locks

OmniClaw separates two concerns:

- reservations hold spend capacity for intents
- fund locks serialize wallet execution to reduce double-spend races

Relevant modules:

- [intents/reservation.py](../src/omniclaw/intents/reservation.py)
- [ledger/lock.py](../src/omniclaw/ledger/lock.py)

### Ledger

The ledger in [ledger/](../src/omniclaw/ledger) tracks payment records and status transitions.

Typical use cases:

- internal observability
- transaction lookup
- reconciliation
- launch debugging

### Payment Intents

Payment intents provide an authorize/confirm flow:

1. simulate and validate
2. reserve funds
3. wait for confirmation or review
4. execute or cancel

Relevant modules:

- [intents/service.py](../src/omniclaw/intents/service.py)
- [intents/intent_facade.py](../src/omniclaw/intents/intent_facade.py)

### Trust Gate

Trust evaluation lives in [trust/](../src/omniclaw/trust). It is optional, but when enabled it can approve, hold, or block a payment using ERC-8004-related identity and reputation signals.

Current runtime rules:

- trust checks are optional by default
- explicit trust checks require a real `OMNICLAW_RPC_URL`
- simulation and payment execution follow the same trust gating rules

### Storage

Storage backends live in [storage/](../src/omniclaw/storage).

Supported backends:

- in-memory storage for tests and simple local runs
- Redis for shared, concurrent, or production-like execution

Canonical Redis env:

```env
OMNICLAW_STORAGE_BACKEND=redis
OMNICLAW_REDIS_URL=redis://localhost:6379
```

## Environment Model

Core environment variables:

```env
CIRCLE_API_KEY=...
ENTITY_SECRET=...
OMNICLAW_NETWORK=ARC-TESTNET
```

Optional:

```env
OMNICLAW_STORAGE_BACKEND=memory
OMNICLAW_REDIS_URL=redis://localhost:6379
OMNICLAW_LOG_LEVEL=INFO
OMNICLAW_RPC_URL=https://...
OMNICLAW_DEFAULT_WALLET=wallet-id
OMNICLAW_DAILY_BUDGET=100.00
OMNICLAW_HOURLY_BUDGET=20.00
OMNICLAW_TX_LIMIT=50.00
OMNICLAW_RATE_LIMIT_PER_MIN=5
OMNICLAW_WHITELISTED_RECIPIENTS=0xabc,0xdef
OMNICLAW_CONFIRM_ALWAYS=false
OMNICLAW_CONFIRM_THRESHOLD=500.00
```

## Execution Sequence

For a typical `pay()` call, the SDK does the following:

1. validate arguments
2. optionally evaluate trust
3. create a ledger entry
4. reserve guards
5. acquire wallet fund lock
6. verify available balance after reservations
7. pass through the router and chosen adapter
8. commit or release guard reservations
9. update ledger status
10. release wallet lock

## Launch-Focused Recommendations

- Use Redis for any multi-agent or concurrent environment.
- Treat `simulate()` as part of your pre-execution workflow for higher-risk payments.
- Use payment intents for any approval or review-dependent flow.
- Configure `OMNICLAW_RPC_URL` only when you actually want trust evaluation available.
- Keep environment names and network selection explicit in deployment configs.
