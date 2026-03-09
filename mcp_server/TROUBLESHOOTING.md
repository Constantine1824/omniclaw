# MCP Troubleshooting

## Error: `No adapter found for recipient`

This means the underlying OmniClaw router could not match the request to a supported payment path.

## Common Causes

1. Invalid recipient format.
2. Wallet network and recipient format do not make sense together.
3. Cross-chain arguments are missing or incorrect for the requested route.
4. The wallet ID is wrong or points to a wallet on a different chain than expected.

## Validate the Basics

### 1. Confirm the Wallet Exists

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_wallet",
      "arguments": {
        "wallet_id": "YOUR_WALLET_ID"
      }
    },
    "id": 1
  }'
```

### 2. Use the Current Simulation Tool

The current tool name is `simulate`, not `simulate_payment`.

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "simulate",
      "arguments": {
        "wallet_id": "YOUR_WALLET_ID",
        "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "amount": "10.50"
      }
    },
    "id": 2
  }'
```

If simulation fails with the same error, payment execution will fail too.

### 3. Check Address Format

For EVM routes:

- must start with `0x`
- must include 40 hex characters after `0x`
- total length must be `42`

Example valid address:

```text
0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
```

### 4. Check Route Intent

- same-chain address payment: use `pay` with `wallet_id`, `recipient`, `amount`
- cross-chain address payment: add `destination_chain`
- URL payment: use a valid URL as `recipient`

## Recommended Workflow

1. `get_wallet`
2. `check_balance`
3. `simulate`
4. `pay` or `create_payment_intent`
5. `list_transactions` or `sync_transaction`

## Old Docs vs Current API

If you still see examples using these names, ignore them:

- `simulate_payment` -> use `simulate`
- `pay_recipient` -> use `pay`
- `can_pay_recipient` -> use `can_pay`
- `cancel_payment_intent` -> use `cancel_intent`
- `from_wallet_id` -> use `wallet_id`
- `to_address` -> use `recipient`
- `currency` -> not part of the current MCP tool contract
