# OmniClaw Business Walkthrough

## Scenario: WeatherData Inc. Sells Weather API

**Company:** WeatherData Inc.  
**Product:** Premium weather data API  
**Goal:** Start accepting crypto payments for API access

---

## Step 1: Setup Seller Account

### 1.1 Install OmniClaw
```bash
pip install omniclaw
```

### 1.2 Generate Payment Address
```python
from omniclaw.seller import create_seller
from eth_account import Account

# Generate a new wallet or use existing
account = Account.create()
print(f"Payment Address: {account.address}")
print(f"Private Key: {account.key.hex()}")
```

**Output:**
```
Payment Address: 0x742d35Cc6634C0532925a3b844Bc9e7595f1E123
Private Key: 0xabcd... (save securely!)
```

---

## Step 2: Configure Seller

### 2.1 Create Seller Instance
```python
from omniclaw.seller import create_seller

seller = create_seller(
    seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
    name="WeatherData API",
    description="Premium weather data for developers",
)
```

### 2.2 Add Protected Endpoints
```python
# Free endpoint
seller.add_endpoint(
    path="/health",
    price="$0",
    description="API health check",
    schemes=[]  # No payment required
)

# Basic weather - $0.001
seller.add_endpoint(
    path="/current",
    price="$0.001",
    description="Current weather conditions",
    schemes=["exact", "GatewayWalletBatched"],  # Both methods
)

# Premium - $0.01
seller.add_endpoint(
    path="/forecast",
    price="$0.01", 
    description="7-day forecast",
    schemes=["exact", "GatewayWalletBatched"],
)

# Enterprise - $0.10
seller.add_endpoint(
    path="/historical",
    price="$0.10",
    description="Historical data",
    schemes=["exact", "GatewayWalletBatched"],
)
```

---

## Step 3: Start Server

### 3.1 Basic Server
```python
seller.serve(port=4023)
```

### 3.2 With Webhooks (Optional)
```python
seller = create_seller(
    seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
    name="WeatherData API",
    webhook_url="https://api.weatherdata.com/webhooks/payments",
    webhook_secret="your-secret-key",
)

seller.serve(port=443, ssl_cert="cert.pem", ssl_key="key.pem")
```

---

## Step 4: How Buyers Pay

### 4.1 Buyer Requests Your API
```bash
curl https://api.weatherdata.com/current
```

### 4.2 Your Server Returns 402
```json
{
  "x402Version": 2,
  "error": "Payment required",
  "resource": {
    "url": "https://api.weatherdata.com/current",
    "description": "Current weather conditions"
  },
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:84532",
      "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
      "amount": "1000",
      "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123"
    },
    {
      "scheme": "GatewayWalletBatched", 
      "network": "eip155:84532",
      "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
      "amount": "1000",
      "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123"
    }
  ]
}
```

### 4.3 Buyer Chooses Payment Method
- **Has Circle Gateway balance** → Uses Circle (gasless)
- **No Circle** → Uses basic x402 (on-chain)

### 4.4 Payment Verification
Your server verifies and returns data:
```python
# Your server receives payment header
# Verifies:
# - Amount correct
# - Timeout valid
# - Signature valid
# → Returns weather data!
```

---

## Step 5: Manage Business

### 5.1 View Earnings
```python
earnings = seller.get_earnings()

print(f"Total: ${earnings['total_usd']}")
print(f"Transactions: {earnings['count']}")
print(f"Basic x402: ${earnings['by_scheme']['exact']}")
print(f"Circle: ${earnings['by_scheme']['gateway_batched']}")
```

**Output:**
```
Total: $15.75
Transactions: 42
Basic x402: $3.25
Circle: $12.50
```

### 5.2 List Payments
```python
# All payments
payments = seller.list_payments()

# Filter by buyer
payments = seller.list_payments(
    buyer_address="0xAAAA1111BBBB2222CCCC3333DDDD4444EEEE5555"
)

# Filter by status
verified = seller.list_payments(status=PaymentStatus.VERIFIED)

for p in payments:
    print(f"{p.id}: {p.scheme} - ${p.amount_usd}")
```

### 5.3 Webhook Notifications
When payment received:
```json
POST https://your-webhook.com/payments
{
  "event": "payment.received",
  "payment": {
    "id": "abc123",
    "scheme": "GatewayWalletBatched",
    "buyer": "0xAAAA1111...",
    "amount": "1000",
    "amount_usd": "0.001",
    "status": "verified",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

## Step 6: Production Checklist

### Required
- [ ] Payment address (EVM wallet)
- [ ] Endpoint pricing configured
- [ ] Server deployed (HTTPS recommended)

### Recommended
- [ ] Webhook for payment notifications
- [ ] SSL certificate
- [ ] Domain name

### Optional
- [ ] Circle Gateway for gasless payments
- [ ] Multiple seller addresses (per product)
- [ ] Rate limiting
- [ ] Analytics integration

---

## Complete Code Example

```python
from omniclaw.seller import create_seller, PaymentScheme

# 1. Create seller
seller = create_seller(
    seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
    name="WeatherData API",
    description="Premium weather data for developers",
    webhook_url="https://api.weatherdata.com/webhooks/payments",
)

# 2. Add endpoints
seller.add_endpoint("/health", "$0", "Health check", [])
seller.add_endpoint("/current", "$0.001", "Current weather", 
                   [PaymentScheme.EXACT, PaymentScheme.GATEWAY_BATCHED])
seller.add_endpoint("/forecast", "$0.01", "7-day forecast",
                   [PaymentScheme.EXACT, PaymentScheme.GATEWAY_BATCHED])
seller.add_endpoint("/historical", "$0.10", "Historical data",
                   [PaymentScheme.EXACT, PaymentScheme.GATEWAY_BATCHED])

# 3. Start server
print("Starting WeatherData API...")
seller.serve(port=443, host="0.0.0.0")
```

---

## What Happens Behind the Scenes

### Payment Flow

```
1. Buyer → GET /current
2. Seller → 402 Payment Required (accepts: exact, GatewayWalletBatched)
3. Buyer → Detects payment methods
4. Buyer → Chooses method:
   - Has Circle balance → Circle Nanopayment
   - No Circle → Basic x402
5. Buyer → Signs authorization
6. Buyer → Sends PAYMENT-SIGNATURE header
7. Seller → Verifies payment
8. Seller → Returns weather data!
9. Seller → Records payment
10. Seller → Sends webhook (if configured)
```

### Settlement

| Method | Settlement | When |
|--------|-----------|------|
| Basic x402 | On-chain | Immediate |
| Circle | Off-chain batched | Periodic |

---

## Revenue Dashboard

```python
# Real-time dashboard
print("=" * 50)
print("WeatherData API - Revenue Dashboard")
print("=" * 50)

earnings = seller.get_earnings()

print(f"\n💰 Total Revenue: ${earnings['total_usd']}")
print(f"📊 Transactions: {earnings['count']}")

print(f"\n📈 By Payment Method:")
print(f"   Basic x402 (on-chain): ${earnings['by_scheme']['exact']}")
print(f"   Circle (gasless):      ${earnings['by_scheme']['gateway_batched']}")

print(f"\n📋 Recent Payments:")
for p in seller.list_payments(limit=5):
    print(f"   {p.created_at.strftime('%Y-%m-%d %H:%M')}: "
          f"${p.amount_usd} ({p.scheme})")
```

---

## Summary

| Step | Action |
|------|--------|
| 1 | Generate payment address |
| 2 | Create seller instance |
| 3 | Add protected endpoints |
| 4 | Start server |
| 5 | Receive payments! |
| 6 | Track earnings |

**WeatherData Inc. is now accepting crypto payments!**

🎉🎉🎉
