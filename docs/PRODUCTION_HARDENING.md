# Production Hardening

This document covers required runtime controls for production OmniClaw deployments.

## Required Environment

Set these for production (`OMNICLAW_ENV=production` or `mainnet`):

```env
OMNICLAW_ENV=production
OMNICLAW_STRICT_SETTLEMENT=true
OMNICLAW_SELLER_NONCE_REDIS_URL=redis://localhost:6379/1
OMNICLAW_WEBHOOK_VERIFICATION_KEY=your_public_key
OMNICLAW_WEBHOOK_DEDUP_DB_PATH=/var/lib/omniclaw/webhook_dedup.sqlite3
```

Startup fails fast if these are missing or if strict settlement is disabled.

## Webhook Security Model

- Signature verification is enforced when `OMNICLAW_WEBHOOK_VERIFICATION_KEY` is configured.
- Replay protection checks:
  - max replay age window (default 12h, configurable)
  - max future skew (default 5m, configurable)
- Persistent deduplication:
  - `notificationId` is stored in a SQLite table.
  - duplicate deliveries of the same `notificationId` are rejected deterministically.

Optional tuning:

```env
OMNICLAW_WEBHOOK_MAX_REPLAY_AGE_SECONDS=43200
OMNICLAW_WEBHOOK_MAX_FUTURE_SKEW_SECONDS=300
OMNICLAW_WEBHOOK_DEDUP_ENABLED=true
```

## Nonce Replay Protection

Production seller flows must use distributed nonce storage:

- `OMNICLAW_SELLER_NONCE_REDIS_URL` points to Redis.
- in-memory nonce replay protection is not accepted in production mode.

## Settlement Semantics

- `OMNICLAW_STRICT_SETTLEMENT=true` ensures success reflects irreversible settlement states.
- Do not disable strict settlement in production.

## Canary and SLA

Use the canary script to validate end-to-end payment lifecycle before/after deploys:

```bash
python scripts/payment_canary.py \
  --wallet-id <wallet_id> \
  --recipient <recipient> \
  --amount 0.10 \
  --network ARC-TESTNET \
  --sla-seconds 300
```

Exit behavior:

- `0`: final success within SLA
- non-zero: final failure, missing transaction tracking metadata, or SLA breach

## Rollout Checklist

1. Apply required production env vars.
2. Run `omniclaw doctor`.
3. Run canary in target environment.
4. Deploy with staged traffic.
5. Monitor:
   - settlement latency
   - webhook duplicate reject counts
   - pending settlement age distribution
6. Keep rollback path ready (app + env).

