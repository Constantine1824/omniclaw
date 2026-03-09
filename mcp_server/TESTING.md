# Testing the OmniClaw MCP Server

## Start the Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints:

- MCP: `http://localhost:8000/mcp/`
- Health: `http://localhost:8000/health`

## Authentication

If auth is enabled:

```bash
export MCP_AUTH_TOKEN="your_bearer_token_here"
```

Or configure it in `.env`:

```env
MCP_AUTH_ENABLED=true
MCP_AUTH_TOKEN=your_bearer_token_here
```

## Basic Checks

### List Tools

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'
```

### Check Balance

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "check_balance",
      "arguments": {
        "wallet_id": "your_wallet_id"
      }
    },
    "id": 2
  }'
```

### Create Agent Wallet

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "create_agent_wallet",
      "arguments": {
        "agent_name": "test_agent"
      }
    },
    "id": 3
  }'
```

### Simulate Payment

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "simulate",
      "arguments": {
        "wallet_id": "wallet_123",
        "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "amount": "10.50"
      }
    },
    "id": 4
  }'
```

### Execute Payment

```bash
curl -X POST http://localhost:8000/mcp/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "pay",
      "arguments": {
        "wallet_id": "wallet_123",
        "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "amount": "10.50",
        "purpose": "test payment"
      }
    },
    "id": 5
  }'
```

## Recommended Test Flow

1. hit `/health`
2. call `tools/list`
3. create a wallet with `create_agent_wallet`
4. check the balance
5. run `simulate`
6. run `pay` or create an intent
7. inspect transactions or ledger entry state

## Expected Errors to Watch

- auth failures from missing or invalid bearer token
- Circle credential failures from missing `CIRCLE_API_KEY` or `ENTITY_SECRET`
- routing failures from invalid `recipient` format
- trust failures when trust is requested without a usable RPC configuration

## Notes

- Current tool names differ from older docs: `simulate`, `pay`, `cancel_intent`, `can_pay`.
- Current argument names are `wallet_id`, `recipient`, and `amount`.
- If you need the full current tool shapes, use [TOOLS.md](TOOLS.md) or `tools/list`.
