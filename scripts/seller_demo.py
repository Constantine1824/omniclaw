#!/usr/bin/env python3
"""
OmniClaw Seller Demo - Complete Economic Infrastructure.

This demonstrates the full seller side:
- Multiple protected endpoints
- Both payment methods
- Webhook notifications
- Transaction history
- Earnings tracking

Run:
    python scripts/seller_demo.py
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from omniclaw.seller import create_seller, PaymentScheme


def main():
    print("=" * 60)
    print("🏪 OmniClaw Seller - Economic Infrastructure Demo")
    print("=" * 60)

    # Seller address (use env or generate)
    seller_address = os.environ.get("SELLER_ADDRESS", "0xd5e42B4486a3c51b3b67fE718F2E1885bf693a21")

    # Create seller
    seller = create_seller(
        seller_address=seller_address,
        name="Weather API",
        description="Premium weather data API",
    )

    # Add protected endpoints
    print("\n📡 Adding protected endpoints...")

    seller.add_endpoint(
        path="/weather",
        price="$0.001",
        description="Current weather conditions",
        schemes=[PaymentScheme.EXACT, PaymentScheme.GATEWAY_BATCHED],
    )

    seller.add_endpoint(
        path="/forecast",
        price="$0.01",
        description="7-day forecast",
        schemes=[PaymentScheme.EXACT, PaymentScheme.GATEWAY_BATCHED],
    )

    seller.add_endpoint(
        path="/premium",
        price="$0.05",
        description="Premium analytics",
        schemes=[PaymentScheme.EXACT, PaymentScheme.GATEWAY_BATCHED],
    )

    # Show endpoints
    print("\n📋 Protected Endpoints:")
    for path, ep in seller.get_endpoints().items():
        schemes = ", ".join([s.value for s in ep.schemes])
        print(f"   {path}: ${ep.price_usd} ({schemes})")

    # Show seller info
    print(f"\n📍 Seller Address: {seller.config.seller_address}")
    print(f"🌐 Network: {seller.config.network}")

    # Simulate some payments
    print("\n💰 Simulating payments...")

    # Simulate payment 1
    record1 = seller._payments.copy()
    from omniclaw.seller.seller import PaymentRecord, PaymentStatus
    import time

    seller._payments["test_001"] = PaymentRecord(
        id="test_001",
        scheme="exact",
        buyer_address="0xaaaa1111bbbb2222cccc3333dddd4444eeee5555",
        seller_address=seller_address,
        amount=1000,
        amount_usd=0.001,
        resource_url="http://localhost:4023/weather",
        status=PaymentStatus.VERIFIED,
    )

    seller._payments["test_002"] = PaymentRecord(
        id="test_002",
        scheme="GatewayWalletBatched",
        buyer_address="0xbbbb2222cccc3333dddd4444eeee5555ffff6666",
        seller_address=seller_address,
        amount=10000,
        amount_usd=0.01,
        resource_url="http://localhost:4023/forecast",
        status=PaymentStatus.VERIFIED,
    )

    # Show payments
    print("\n📜 Payment History:")
    for payment in seller.list_payments():
        print(
            f"   {payment.id}: {payment.scheme} - ${payment.amount_usd:.3f} from {payment.buyer_address[:10]}..."
        )

    # Show earnings
    earnings = seller.get_earnings()
    print(f"\n💵 Total Earnings: ${earnings['total_usd']:.3f}")
    print(f"   Transactions: {earnings['count']}")
    print(f"   By scheme:")
    print(f"     - basic x402: ${earnings['by_scheme']['exact']:.3f}")
    print(f"     - Circle: ${earnings['by_scheme']['gateway_batched']:.3f}")

    # Show 402 response
    print("\n📨 Sample 402 Response:")
    headers, body = seller.create_402_response("/weather", "http://localhost/weather")
    import base64
    import json

    decoded = json.loads(base64.b64decode(headers["payment-required"]))
    print(f"   Accepts: {[a['scheme'] for a in decoded['accepts']]}")

    print("\n" + "=" * 60)
    print("✅ Seller infrastructure ready!")
    print("=" * 60)

    print("""
🚀 To start the server:
   
   seller.serve(port=4023)

📡 Endpoints:
   GET /weather    - $0.001
   GET /forecast   - $0.01
   GET /premium    - $0.05

📋 Management:
   GET /_/health     - Health check
   GET /_/payments   - List payments
""")

    return seller


if __name__ == "__main__":
    seller = main()
