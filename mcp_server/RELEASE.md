# MCP Server Release Notes

## Current Status

The MCP server documentation in this directory now reflects the current FastMCP tool surface implemented in `app/mcp/fastmcp_server.py`.

This server exposes:

- wallet creation and lookup
- balance lookup
- payment simulation and execution
- payment intent lifecycle
- transaction sync
- read-only routing, trust, and ledger lookup tools

## Important Naming Updates

Older docs and examples used tool names that are no longer current. The active tool names are:

- `simulate`
- `pay`
- `cancel_intent`
- `can_pay`

Not the older names:

- `simulate_payment`
- `pay_recipient`
- `cancel_payment_intent`
- `can_pay_recipient`

## Configuration Contract

Canonical MCP environment names:

```env
CIRCLE_API_KEY=...
ENTITY_SECRET=...
OMNICLAW_NETWORK=ARC-TESTNET
MCP_AUTH_ENABLED=true
MCP_REQUIRE_AUTH=true
MCP_AUTH_TOKEN=...
```

Backward-compatible `OMNIAGENTPAY_*` aliases may still be accepted by config, but they should not be treated as the primary documented contract.

## Reference

- [README.md](README.md)
- [TOOLS.md](TOOLS.md)
- [TESTING.md](TESTING.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
