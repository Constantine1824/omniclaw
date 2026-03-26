# Gateway Middleware Guide

**Protect your endpoints with x402 payments.**

---

## What is Gateway Middleware?

Gateway middleware is OmniClaw's way of protecting HTTP endpoints with payment requirements. When a buyer calls your endpoint:

1. If they include valid payment headers → Serve the request
2. If they don't include payment → Return 402 with requirements
3. If payment fails → Return 402 with error

---

## Basic Usage

```python
from omniclaw import OmniClaw
from omniclaw.gateway import GatewayMiddleware, Price

client = OmniClaw(circle_api_key="KEY", network="BASE-SEPOLIA")

# Create gateway middleware
gateway = client.gateway()

# Protect an endpoint
@gateway.protect(price=Price.usdc("0.50"))
async def get_data(location: str):
    return {"data": f"Result for {location}", "cost": "$0.50"}
```

---

## How It Works

### Buyer Side (Automatic)

When you call `client.pay()` with a URL, OmniClaw:

1. Sends initial request without payment
2. If 402 received, extracts payment requirements
3. Executes payment via nanopayment or direct x402
4. Retries request with payment headers
5. Returns result

### Seller Side (Your Code)

When buyers call your protected endpoint:

```python
@gateway.protect(price=Price.usdc("1.00"))
async def get_premium_data(query: str):
    # This only runs if payment was successful!
    return {"query": query, "data": expensive_data()}
```

---

## Price Configuration

```python
from omniclaw.gateway import Price

# Fixed price in USDC
gateway.protect(price=Price.usdc("1.00"))

# Dynamic price based on request
def dynamic_price(request):
    size = len(request.body) if request.body else 0
    return Price.usdc(f"{size * 0.001:.2f}")

gateway.protect(price=dynamic_price)

# Free (shows price is $0)
gateway.protect(price=Price.free())
```

---

## Protected Endpoint Example

```python
from omniclaw import OmniClaw
from omniclaw.gateway import GatewayMiddleware, Price
import asyncio

client = OmniClaw(circle_api_key="KEY", network="BASE-SEPOLIA")
gateway = client.gateway()

# Protect weather endpoint - $0.05 per request
@gateway.protect(price=Price.usdc("0.05"))
async def weather(current_weather: bool):
    return {
        "temp": 72,
        "conditions": "sunny",
        "cost": "$0.05"
    }

# Protect AI endpoint - varies by tokens
def ai_price(request):
    tokens = estimate_tokens(request.body)
    return Price.usdc(f"{tokens * 0.00001:.4f}")

@gateway.protect(price=ai_price)
async def ai_completion(prompt: str):
    # Expensive AI call
    return {"completion": "..."}

# Run the server
async def main():
    await gateway.run(host="0.0.0.0", port=8000)

asyncio.run(main())
```

---

## Verifying Payment in Handlers

Sometimes you need access to payment details:

```python
@gateway.protect(price=Price.usdc("1.00"))
async def paid_api endpoint(gateway_request):
    # Access payment info
    payment = gateway_request.payment
    
    print(f"Paid: {payment.amount}")
    print(f"Payer: {payment.payer}")
    print(f"Tx: {payment.transaction_id}")
    
    # Your logic here
    return {"result": "..."}
```

---

## Excluding Paths

```python
# Protect all except health check
@gateway.protect(price=Price.usdc("0.01"), exclude=["/health", "/metrics"])
async def api_handler(request):
    return {"data": "..."}
```

---

## Error Handling

```python
@gateway.protect(price=Price.usdc("1.00"))
async def api_endpoint(gateway_request):
    try:
        return await process_request(gateway_request)
    except ValueError as e:
        # Return error but don't refund payment
        return {"error": str(e)}, 400
```

---

## For FastAPI Users

```python
from fastapi import FastAPI
from omniclaw.gateway import GatewayMiddleware, Price

app = FastAPI()
client = OmniClaw(circle_api_key="KEY", network="BASE-SEPOLIA")
gateway = client.gateway()

# Wrap FastAPI app
app = gateway.fastapi(app)

@app.get("/weather")
@gateway.protect(Price.usdc("0.05"))
async def weather():
    return {"temp": 72}

@app.post("/analyze")
@gateway.protect(Price.usdc("0.50"))
async def analyze(data: str):
    return {"result": analyze(data)}
```

---

## Standalone Server

```python
from omniclaw.gateway import GatewayMiddleware, Price

async def my_handler(gateway_request):
    return {"message": "Hello, paid world!"}

async def main():
    gateway = GatewayMiddleware(
        circle_api_key="KEY",
        network="BASE-SEPOLIA"
    )
    
    gateway.add_route("/hello", my_handler, price=Price.usdc("0.01"))
    
    await gateway.run(host="0.0.0.0", port=8000)

asyncio.run(main())
```
