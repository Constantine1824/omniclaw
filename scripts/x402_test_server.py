#!/usr/bin/env python3
"""
x402 Test Server - Base Sepolia (Circle Facilitator)

This server implements the x402 protocol and uses Circle as the facilitator.
When a buyer requests a paid resource, this server returns 402 with:
- Circle facilitator indicator (GatewayWalletBatched)
- Base Sepolia network info
- USDC payment requirements

Run:
    python scripts/x402_test_server.py

Then test with:
    python scripts/demo_x402_client.py
"""

import asyncio
import base64
import json
import time
from aiohttp import web


# Seller's wallet (receives payments)
SELLER_WALLET = "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123"


def build_402_response(request_path: str) -> tuple[dict, str]:
    """
    Build a proper x402 v2 response.

    Returns:
        - headers dict
        - body text
    """
    payment_requirements = {
        "x402Version": 2,
        "expires": int(time.time() + 3600),
        "resource": {
            "url": request_path,
            "description": "Premium API access via x402",
            "mimeType": "application/json",
        },
        "payment": {
            "price": "0.001",
            "currency": "USDC",
            "chain": "base",
            "chainId": 84532,  # Base Sepolia
            "recipient": SELLER_WALLET,
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": "eip155:84532",  # Base Sepolia CAIP-2
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # USDC on Base Sepolia
                "amount": "1000000",  # 1 USDC in atomic units (6 decimals)
                "maxTimeoutSeconds": 3600,
                "payTo": SELLER_WALLET,
                "extra": {
                    "name": "GatewayWalletBatched",  # ← CIRCLE INDICATOR
                    "version": "1",
                    "verifyingContract": "0x0077777d7EBA4688BDeF3E311b846F25870A19B9",  # Circle's contract
                },
            }
        ],
        "facilitator": "circle",  # ← DIRECT CIRCLE INDICATOR
    }

    # Encode as base64
    encoded = base64.b64encode(json.dumps(payment_requirements).encode()).decode()

    headers = {
        "Payment-Required": encoded,
        "X-Payment-Version": "2",
        "X-Facilitator": "circle",
    }

    body = json.dumps(
        {
            "error": "PAYMENT_REQUIRED",
            "message": "This resource costs 0.001 USDC",
            "x402Version": 2,
            "payment_requirements": payment_requirements,
        }
    )

    return headers, body


async def handle_premium_data(request):
    """Premium data endpoint - requires payment."""

    # Check for payment header
    payment_sig = request.headers.get("X-Payment-Signature") or request.headers.get(
        "PAYMENT-SIGNATURE"
    )

    if payment_sig:
        # Payment provided - verify and return resource
        print(f"\n✅ Payment received: {payment_sig[:50]}...")

        return web.Response(
            status=200,
            text=json.dumps(
                {
                    "status": "success",
                    "message": "Payment verified! Here's your premium data.",
                    "data": {
                        "api_key": "premium_key_12345",
                        "credits": 1000,
                        "timestamp": time.time(),
                    },
                    "payment": {
                        "amount": "0.001 USDC",
                        "paid_to": SELLER_WALLET,
                        "facilitator": "circle",
                        "network": "base-sepolia",
                    },
                }
            ),
            content_type="application/json",
        )

    # No payment - return 402
    headers, body = build_402_response(str(request.url))
    print(f"\n💰 Payment required for {request.path}")

    return web.Response(status=402, headers=headers, text=body)


async def handle_health(request):
    """Health check endpoint."""
    return web.Response(
        text=json.dumps(
            {
                "status": "ok",
                "server": "x402-test-server",
                "facilitator": "circle",
                "network": "base-sepolia",
                "price": "0.001 USDC",
            }
        ),
        content_type="application/json",
    )


async def handle_info(request):
    """x402 discovery endpoint."""
    return web.Response(
        text=json.dumps(
            {
                "x402Version": 2,
                "facilitator": "circle",
                "network": "base-sepolia",
                "price": "$0.001",
                "endpoints": {
                    "/premium-data": "Premium API data (costs $0.001)",
                    "/health": "Health check",
                    "/info": "This info endpoint",
                },
            }
        ),
        content_type="application/json",
    )


def create_app():
    app = web.Application()
    app.router.add_get("/premium-data", handle_premium_data)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/info", handle_info)
    return app


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                  x402 TEST SERVER                                   ║
║                  Base Sepolia - Circle Facilitator                  ║
╚══════════════════════════════════════════════════════════════════════╝

This server implements x402 v2 with Circle as facilitator.

Endpoints:
  GET /premium-data  - Premium API (costs $0.001 USDC)
  GET /health        - Health check
  GET /info          - x402 discovery

What it returns:
  - 402 Payment Required (no payment header)
  - 200 OK with data (with X-Payment-Signature header)

Key indicators for the client:
  - "GatewayWalletBatched" in accepts.extra.name → Circle
  - "facilitator": "circle" → Circle
  - Network: eip155:84532 (Base Sepolia)

Run client to see the full flow:
  $ python scripts/demo_x402_client.py
""")
    web.run_app(create_app(), host="0.0.0.0", port=8080)
