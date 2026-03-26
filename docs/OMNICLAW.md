# OmniClaw - Autonomous Agent Economic Infrastructure

**OmniClaw** is the economic control and trust infrastructure for autonomous agents — enabling them to pay, get paid, and transact securely under real-time policy enforcement.

---

## Quick Start

### Buyer Side (Pay for things)

```python
from omniclaw import OmniClaw

# Create client
client = OmniClaw(
    circle_api_key="your-key",
    entity_secret="your-secret",
)

# Create agent wallet
wallet = await client.create_agent_wallet()

# Get payment address (fund with USDC)
address = await client.get_payment_address(wallet.id)
print(f"Fund this: {address}")

# Pay for URL-based resource
result = await client.pay(
    wallet_id=wallet.id,
    recipient="https://api.weather.com/data",
    amount="0.01"
)
```

### Seller Side (Get paid)

```python
from omniclaw.seller import SellerAgent

# Create seller agent
seller = SellerAgent(
    seller_address="0x742d...",
    accepts_circle=True,  # Accept Circle nanopayments
)

# Protect endpoints
@seller.protected("$0.001", "Weather data")
async def weather(request):
    return {"temp": 72}

@seller.protected("$0.01", "Premium content") 
async def premium(request):
    return {"secret": "data"}
```

---

## Architecture

### Buyer Flow
```
Agent Wallet → EOA Key → x402 Request → Seller 402 Response
    ↓                                    ↓
Smart Routing ← Parse accepts → Circle? → Nanopayment
    ↓                              ↓
Basic x402 (on-chain)      Circle (gasless)
```

### Seller Flow
```
Request → Check payment header → No? → 402 Response
    ↓ Yes
Verify Payment → Invalid? → 402 Response
    ↓ Valid
Return Data
```

---

## Payment Methods

| Method | Gas | Settlement | Requires |
|--------|-----|------------|----------|
| Basic x402 | Yes (buyer) | On-chain | USDC in EOA |
| Circle Nanopayment | No | Off-chain (batched) | USDC in Gateway |

---

## Key Features

### 1. Smart Routing
The client automatically detects what payment methods the seller supports:
- Seller accepts `GatewayWalletBatched` → Use Circle (gasless)
- Seller only accepts `exact` → Use basic x402 (on-chain)

### 2. Guards
Enforce spending policies per wallet:
- Daily/hourly budget limits
- Rate limits
- Recipient whitelists/blacklists

### 3. One Key Per Wallet
Same EOA key used for both payment types:
- Basic x402: USDC stays in EOA
- Circle: Deposit to Gateway first

---

## API Reference

### Buyer (OmniClaw)

```python
# Wallet creation
wallet = await client.create_agent_wallet()

# Get payment address
address = await client.get_payment_address(wallet_id)

# Make payment
result = await client.pay(
    wallet_id="wallet-123",
    recipient="https://api.example.com/data",  # or 0x address
    amount="0.01"
)

# Gateway operations
await client.deposit_to_gateway(wallet_id, "100.00")
await client.withdraw_from_gateway(wallet_id, "50.00")
balance = await client.get_gateway_balance(wallet_id)
```

### Seller (SellerAgent)

```python
# Create seller
seller = SellerAgent(
    seller_address="0x742d...",
    accepts_circle=True,
)

# Protect endpoint
@seller.protected("$0.001", "Description")
async def endpoint(request):
    return {"data": "value"}

# Or run standalone server
from omniclaw.seller import run_seller_server
run_seller_server(seller_address="0x742d...", port=4023)
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CIRCLE_API_KEY` | Circle API key |
| `ENTITY_SECRET` | Entity secret for signing |
| `OMNICLAW_RPC_URL` | RPC URL for ERC-8004 |
| `NANOPAYMENTS_DEFAULT_NETWORK` | Default network |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_x402_full_flow.py -v

# Run with server
# Terminal 1: python scripts/x402_simple_server.py
# Terminal 2: pytest tests/test_server_integration.py -v
```
