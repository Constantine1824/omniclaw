#!/usr/bin/env python3
"""
x402 Test Server - FastAPI with Official x402 SDK

This server uses the official x402 Python SDK server-side to implement
x402 v2 payments. It mimics the production x402 server from:
https://github.com/coinbase/x402/blob/main/examples/python/servers/fastapi/main.py

Run:
    python scripts/x402_fastapi_server.py

Test:
    # Without payment (returns 402):
    curl -i http://localhost:4021/weather

    # With payment (OmniClaw client):
    python scripts/test_x402_fastapi_flow.py
"""

import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

from x402 import FacilitatorConfig
from x402.http import HTTPFacilitatorClient, PaymentOption
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.http.types import RouteConfig
from x402.mechanisms.evm.exact import ExactEvmServerScheme
from x402.server import x402ResourceServer

load_dotenv()

# Configuration
# Seller's wallet address that receives payments (on Base Sepolia)
# For testing, you can set EVM_ADDRESS env var, or use the default below.
# This address should have USDC on Base Sepolia to test receiving payments.
SELLER_EVM_ADDRESS: str = os.getenv("EVM_ADDRESS", "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123")

# Network: Base Sepolia (testnet)
EVM_NETWORK: str = "eip155:84532"

# Facilitator URL - use self-facilitation for testing (no external facilitator needed)
# Set to "https://x402.org/facilitator" to use external facilitator
# Set to None for self-facilitation (seller verifies their own payments)
FACILITATOR_URL: str | None = os.getenv("FACILITATOR_URL", None)

if not SELLER_EVM_ADDRESS:
    raise ValueError("Missing EVM_ADDRESS environment variable")


# Response schemas
class WeatherReport(BaseModel):
    weather: str
    temperature: int


class WeatherResponse(BaseModel):
    report: WeatherReport


class PremiumContentResponse(BaseModel):
    content: str


# App
app = FastAPI(title="OmniClaw x402 Test Server")


# x402 Server setup
if FACILITATOR_URL:
    facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=FACILITATOR_URL))
    print(f"Using facilitator: {FACILITATOR_URL}")
else:
    facilitator = None
    print("Self-facilitation mode (no external facilitator)")

server = x402ResourceServer(facilitator)
server.register(EVM_NETWORK, ExactEvmServerScheme())

# Initialize server to register schemes with facilitator
if facilitator:
    try:
        server.initialize()
        print(f"Server initialized with facilitator schemes")
    except Exception as e:
        print(f"Warning: Server initialization failed: {e}")


# Route configuration
# These routes are protected by x402 paywall
routes: dict[str, RouteConfig] = {
    "GET /weather": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=SELLER_EVM_ADDRESS,
                price="$0.001",  # $0.001 USDC
                network=EVM_NETWORK,
            ),
        ],
        mime_type="application/json",
        description="Weather report - costs $0.001 USDC",
    ),
    "GET /premium/content": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=SELLER_EVM_ADDRESS,
                price="$0.01",  # $0.01 USDC
                network=EVM_NETWORK,
            ),
        ],
        mime_type="application/json",
        description="Premium content - costs $0.01 USDC",
    ),
    "GET /premium/data": RouteConfig(
        accepts=[
            PaymentOption(
                scheme="exact",
                pay_to=SELLER_EVM_ADDRESS,
                price="$0.01",  # $0.01 USDC
                network=EVM_NETWORK,
            ),
        ],
        mime_type="application/json",
        description="Premium data - costs $0.01 USDC",
    ),
}


# Add x402 middleware - this handles 402 responses automatically
app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)


# Routes (protected by x402 middleware)
@app.get("/weather")
async def get_weather() -> WeatherResponse:
    """Weather endpoint - requires x402 payment."""
    return WeatherResponse(report=WeatherReport(weather="sunny", temperature=70))


@app.get("/premium/content")
async def get_premium_content() -> PremiumContentResponse:
    """Premium content endpoint - requires x402 payment."""
    return PremiumContentResponse(content="This is premium content accessible via x402 payment!")


@app.get("/premium/data")
async def get_premium_data() -> dict:
    """Premium data endpoint - requires x402 payment."""
    return {
        "api_key": "premium_key_12345",
        "credits": 1000,
        "features": ["advanced", "priority", "unlimited"],
    }


# Unprotected routes (no payment needed)
@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check - no payment required."""
    return {"status": "ok"}


@app.get("/info")
async def get_info() -> dict:
    """Server info - no payment required."""
    return {
        "server": "OmniClaw x402 Test Server",
        "version": "1.0.0",
        "network": EVM_NETWORK,
        "seller_address": SELLER_EVM_ADDRESS,
        "facilitator": FACILITATOR_URL or "self-facilitated",
        "endpoints": {
            "/health": "Health check (free)",
            "/info": "Server info (free)",
            "/weather": "Weather report ($0.001 USDC)",
            "/premium/content": "Premium content ($0.01 USDC)",
            "/premium/data": "Premium data ($0.01 USDC)",
        },
    }


if __name__ == "__main__":
    import uvicorn

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║          OmniClaw x402 Test Server (FastAPI)                  ║
╚══════════════════════════════════════════════════════════════╝

Seller EVM Address: {SELLER_EVM_ADDRESS}
Network:            {EVM_NETWORK} (Base Sepolia)
Facilitator:       {FACILITATOR_URL or "self-facilitated"}

Free endpoints:
  GET /health      - Health check
  GET /info       - Server info

Paid endpoints (x402):
  GET /weather            - $0.001 USDC
  GET /premium/content    - $0.01 USDC
  GET /premium/data       - $0.01 USDC

Run server:
  python scripts/x402_fastapi_server.py

Test with curl:
  curl -i http://localhost:4021/weather
""")

    uvicorn.run(app, host="0.0.0.0", port=4021)
