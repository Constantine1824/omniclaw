# OmniClaw MCP Server Tools

This file documents the current FastMCP tool surface exposed by [app/mcp/fastmcp_server.py](app/mcp/fastmcp_server.py).

Current total: `18` tools.

## Wallet Tools

### `create_agent_wallet`

```json
{
  "agent_name": "string (required)",
  "blockchain": "string | null (optional)",
  "apply_default_guards": "boolean (default: true)"
}
```

### `list_wallets`

```json
{
  "wallet_set_id": "string | null (optional)"
}
```

### `get_wallet`

```json
{
  "wallet_id": "string (required)"
}
```

### `check_balance`

```json
{
  "wallet_id": "string (required)"
}
```

### `get_balances`

```json
{
  "wallet_id": "string (required)"
}
```

## Payment Tools

### `simulate`

```json
{
  "wallet_id": "string (required)",
  "recipient": "string (required)",
  "amount": "string (required)",
  "wallet_set_id": "string | null (optional)",
  "check_trust": "boolean | null (optional)"
}
```

### `pay`

```json
{
  "wallet_id": "string (required)",
  "recipient": "string (required)",
  "amount": "string (required)",
  "destination_chain": "string | null (optional)",
  "wallet_set_id": "string | null (optional)",
  "purpose": "string | null (optional)",
  "idempotency_key": "string | null (optional)",
  "fee_level": "string (default: medium)",
  "strategy": "string (default: retry_then_fail)",
  "check_trust": "boolean | null (optional)",
  "consume_intent_id": "string | null (optional)",
  "wait_for_completion": "boolean (default: false)",
  "timeout_seconds": "float | null (optional)"
}
```

### `batch_pay`

```json
{
  "requests": [
    {
      "wallet_id": "string (required)",
      "recipient": "string (required)",
      "amount": "string (required)",
      "fee_level": "string | null (optional)",
      "destination_chain": "string | null (optional)",
      "idempotency_key": "string | null (optional)"
    }
  ]
}
```

## Payment Intent Tools

### `create_payment_intent`

```json
{
  "wallet_id": "string (required)",
  "recipient": "string (required)",
  "amount": "string (required)",
  "destination_chain": "string | null (optional)",
  "purpose": "string | null (optional)",
  "expires_in": "integer | null (optional)",
  "idempotency_key": "string | null (optional)",
  "metadata": "object | null (optional)"
}
```

### `get_payment_intent`

```json
{
  "intent_id": "string (required)"
}
```

### `confirm_payment_intent`

```json
{
  "intent_id": "string (required)"
}
```

### `cancel_intent`

```json
{
  "intent_id": "string (required)",
  "reason": "string | null (optional)"
}
```

## Transaction and Ledger Tools

### `list_transactions`

```json
{
  "wallet_id": "string | null (optional)",
  "blockchain": "string | null (optional)"
}
```

### `sync_transaction`

```json
{
  "ledger_entry_id": "string (required)"
}
```

### `ledger_get_entry`

```json
{
  "entry_id": "string (required)"
}
```

## Routing and Trust Tools

### `can_pay`

```json
{
  "recipient": "string (required)"
}
```

### `detect_payment_method`

```json
{
  "recipient": "string (required)"
}
```

### `trust_lookup`

```json
{
  "recipient_address": "string (required)",
  "amount": "string (default: 0)",
  "wallet_id": "string | null (optional)",
  "network": "string | null (optional)"
}
```

## Notes

- The tool name is `simulate`, not `simulate_payment`.
- The cancel tool name is `cancel_intent`, not `cancel_payment_intent`.
- The routing capability tool name is `can_pay`, not `can_pay_recipient`.
- Current MCP payloads use `wallet_id`, `recipient`, and `amount`.
