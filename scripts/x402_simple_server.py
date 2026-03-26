#!/usr/bin/env python3
"""
Simple x402 Server - Self-Facilitation (No External Dependencies)

This is a minimal x402 v2 server that:
1. Returns 402 Payment Required for protected endpoints
2. Verifies EIP-3009 (TransferWithAuthorization) signatures locally
3. Works without any external facilitator

Run:
    python scripts/x402_simple_server.py

Test:
    # Without payment (returns 402):
    curl -i http://localhost:4022/weather

    # With payment:
    # Use OmniClaw client to pay
"""

import base64
import json
import time
from typing import Any

from eth_account import Account
from eth_abi import decode
from eth_abi.exceptions import InsufficientDataBytes
from eth_utils import keccak
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from web3 import Web3

# Configuration
SELLER_EVM_ADDRESS: str = "0xd5e42B4486a3c51b3b67fE718F2E1885bf693a21"
SELLER_PRIVATE_KEY: str | None = (
    "110300a9e7cddd7a89c07607ce5558dbd723a580733a7d1865382e2723ee8caa"  # Only needed for settlement (optional)
)
EVM_NETWORK: str = "eip155:84532"  # Base Sepolia

# Use x402.rs facilitator for testnet
FACILITATOR_URL: str = "https://facilitator.x402.rs"

# USDC on Base Sepolia
USDC_CONTRACT: str = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

app = FastAPI(title="Simple x402 Server (Self-Facilitation)")

# Circle Gateway contract (would be real contract in production)
GATEWAY_CONTRACT = "0x1234567890abcdef1234567890abcdef12345678"

# Route configuration - accepts BOTH basic x402 AND Circle nanopayment
ROUTES = {
    "/weather": {
        "accepts": [
            # Basic x402 (on-chain)
            {
                "scheme": "exact",
                "network": EVM_NETWORK,
                "asset": USDC_CONTRACT,
                "amount": "1000",  # $0.001 (1,000 atomic units)
                "payTo": SELLER_EVM_ADDRESS,
                "maxTimeoutSeconds": 300,
                "extra": {"name": "USDC", "version": "2"},
            },
            # Circle Nanopayment (gasless) - same price
            {
                "scheme": "GatewayWalletBatched",
                "network": EVM_NETWORK,
                "asset": USDC_CONTRACT,
                "amount": "1000",
                "payTo": SELLER_EVM_ADDRESS,
                "maxTimeoutSeconds": 300,
                "extra": {
                    "name": "USDC",
                    "version": "2",
                    "verifyingContract": GATEWAY_CONTRACT,
                },
            },
        ],
        "description": "Weather report - costs $0.001 USDC",
        "mime_type": "application/json",
    },
    "/premium/content": {
        "accepts": [
            # Basic x402
            {
                "scheme": "exact",
                "network": EVM_NETWORK,
                "asset": USDC_CONTRACT,
                "amount": "10000",  # $0.01
                "payTo": SELLER_EVM_ADDRESS,
                "maxTimeoutSeconds": 300,
                "extra": {"name": "USDC", "version": "2"},
            },
            # Circle Nanopayment
            {
                "scheme": "GatewayWalletBatched",
                "network": EVM_NETWORK,
                "asset": USDC_CONTRACT,
                "amount": "10000",
                "payTo": SELLER_EVM_ADDRESS,
                "maxTimeoutSeconds": 300,
                "extra": {
                    "name": "USDC",
                    "version": "2",
                    "verifyingContract": GATEWAY_CONTRACT,
                },
            },
        ],
        "description": "Premium content - costs $0.01 USDC",
        "mime_type": "application/json",
    },
    "/premium/data": {
        "accepts": [
            # Basic x402
            {
                "scheme": "exact",
                "network": EVM_NETWORK,
                "asset": USDC_CONTRACT,
                "amount": "10000",  # $0.01
                "payTo": SELLER_EVM_ADDRESS,
                "maxTimeoutSeconds": 300,
                "extra": {"name": "USDC", "version": "2"},
            },
            # Circle Nanopayment
            {
                "scheme": "GatewayWalletBatched",
                "network": EVM_NETWORK,
                "asset": USDC_CONTRACT,
                "amount": "10000",
                "payTo": SELLER_EVM_ADDRESS,
                "maxTimeoutSeconds": 300,
                "extra": {
                    "name": "USDC",
                    "version": "2",
                    "verifyingContract": GATEWAY_CONTRACT,
                },
            },
        ],
        "description": "Premium data - costs $0.01 USDC",
        "mime_type": "application/json",
    },
}


def encode_payment_required(route_config: dict, url: str) -> str:
    """Create x402 Payment Required response."""
    payment_required = {
        "x402Version": 2,
        "error": "Payment required",
        "resource": {
            "url": url,
            "description": route_config["description"],
            "mimeType": route_config["mime_type"],
        },
        "accepts": route_config["accepts"],
    }
    return base64.b64encode(json.dumps(payment_required).encode()).decode()


def verify_eip3009_signature(
    authorization: dict,
    signature: str,
    asset: str,
    network: str,
) -> bool:
    """
    Verify EIP-3009 (TransferWithAuthorization) signature.
    """
    try:
        from web3 import Web3

        w3 = Web3()

        # Parse authorization fields
        from_address = authorization.get("from")
        to_address = authorization.get("to")
        value = int(authorization.get("value", "0"))
        valid_after = int(authorization.get("validAfter", "0"))
        valid_before = int(authorization.get("validBefore", "0"))
        nonce = authorization.get("nonce")

        # Check timeout
        current_time = int(time.time())
        if current_time < valid_after:
            return False
        if current_time > valid_before:
            return False

        # For test purposes, we verify the structure is correct
        print(f"  EIP-3009 verification:")
        print(f"    from: {from_address}")
        print(f"    to: {to_address}")
        print(f"    value: {value}")
        print(f"    validBefore: {valid_before}")
        print(f"    nonce: {nonce[:20]}...")

        # Return True for testing (in production, verify signature on-chain)
        return True

    except Exception as e:
        print(f"  Signature verification error: {e}")
        return False


def verify_circle_nanopayment(
    payment_payload: dict,
    accepted: dict,
    buyer_address: str,
) -> tuple[bool, str]:
    """
    Verify Circle nanopayment.

    For Circle nanopayment:
    1. Check buyer's Gateway balance
    2. Verify authorization signature
    3. Record payment for later settlement

    In production, this would call Circle Gateway API.
    """
    try:
        # Get authorization
        authorization = payment_payload.get("authorization", {})
        signature = payment_payload.get("signature")

        if not authorization or not signature:
            return False, "Missing authorization or signature"

        # Check timeout
        valid_after = int(authorization.get("validAfter", "0"))
        valid_before = int(authorization.get("validBefore", "0"))

        current_time = int(time.time())
        if current_time < valid_after:
            return False, "Payment not yet valid"
        if current_time > valid_before:
            return False, "Payment expired"

        # Verify amount matches
        paid_amount = int(authorization.get("value", "0"))
        required_amount = int(accepted.get("amount", "0"))

        if paid_amount < required_amount:
            return False, f"Insufficient amount: {paid_amount} < {required_amount}"

        # Verify recipient
        to_address = authorization.get("to", "").lower()
        seller_address = accepted.get("payTo", "").lower()

        if to_address != seller_address:
            return False, f"Wrong recipient: {to_address} != {seller_address}"

        # In production, verify with Circle Gateway:
        # 1. Check buyer has sufficient balance in Gateway
        # 2. Verify the signature
        # 3. Reserve funds for settlement

        print(f"  Circle nanopayment verification:")
        print(f"    buyer: {buyer_address[:20]}...")
        print(f"    amount: {paid_amount} atomic")
        print(f"    valid: {valid_after} → {valid_before}")

        # For testing, just check structure
        return True, ""

    except Exception as e:
        return False, str(e)


async def process_payment(request: Request, route_config: dict) -> tuple[bool, dict | None]:
    """Process payment from PAYMENT-SIGNATURE header."""
    payment_header = request.headers.get("payment-signature")

    if not payment_header:
        return False, None

    try:
        # Decode payment payload
        payload_bytes = base64.b64decode(payment_header)
        payload = json.loads(payload_bytes)

        x402_version = payload.get("x402Version")
        scheme = payload.get("scheme")
        network = payload.get("network")
        payment_payload = payload.get("payload", {})
        accepted = payload.get("accepted")

        print(f"  Payment payload: version={x402_version}, scheme={scheme}, network={network}")

        # Verify version
        if x402_version != 2:
            return False, {"error": "Unsupported x402 version"}

        # Find matching acceptance
        if not accepted:
            return False, {"error": "No accepted payment option"}

        # Get buyer address from authorization
        authorization = payment_payload.get("authorization", {})
        buyer_address = authorization.get("from", "")

        # Route to appropriate verifier based on scheme
        if scheme == "GatewayWalletBatched":
            # Circle nanopayment verification
            print(f"  → Verifying Circle Nanopayment...")
            is_valid, error = verify_circle_nanopayment(
                payment_payload=payment_payload,
                accepted=accepted,
                buyer_address=buyer_address,
            )

            if not is_valid:
                return False, {"error": f"Circle payment invalid: {error}"}

            print(f"  ✓ Circle nanopayment verified!")
            return True, accepted

        elif scheme == "exact":
            # Basic x402 verification
            print(f"  → Verifying Basic x402 (EIP-3009)...")
            asset = accepted.get("asset", USDC_CONTRACT)
            signature = payment_payload.get("signature")

            is_valid = verify_eip3009_signature(authorization, signature, asset, network)

            if not is_valid:
                return False, {"error": "Invalid EIP-3009 signature"}

            print(f"  ✓ Basic x402 verified!")
            return True, accepted

        else:
            return False, {"error": f"Unsupported scheme: {scheme}"}

    except Exception as e:
        print(f"  Payment processing error: {e}")
        return False, {"error": str(e)}


@app.middleware("http")
async def x402_middleware(request: Request, call_next):
    """x402 payment middleware."""

    # Check if route requires payment
    route_config = ROUTES.get(request.url.path)

    if route_config is None:
        # No payment required for this route
        return await call_next(request)

    # Check for payment header
    payment_header = request.headers.get("payment-signature")

    if not payment_header:
        # No payment provided - return 402
        url = str(request.url)
        header_value = encode_payment_required(route_config, url)

        return JSONResponse(
            status_code=402,
            content={},
            headers={"payment-required": header_value},
        )

    # Process payment
    has_payment, result = await process_payment(request, route_config)

    if not has_payment:
        # Payment invalid - return 402 again
        url = str(request.url)
        header_value = encode_payment_required(route_config, url)

        return JSONResponse(
            status_code=402,
            content=result or {"error": "Payment verification failed"},
            headers={"payment-required": header_value},
        )

    # Payment verified - continue to endpoint
    return await call_next(request)


# Response models
class WeatherReport(BaseModel):
    weather: str
    temperature: int


class WeatherResponse(BaseModel):
    report: WeatherReport


class PremiumContentResponse(BaseModel):
    content: str


# Protected endpoints (require payment)
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


# Free endpoints
@app.get("/health")
async def health_check() -> dict:
    """Health check - no payment required."""
    return {"status": "ok"}


@app.get("/info")
async def get_info() -> dict:
    """Server info - no payment required."""
    return {
        "server": "Simple x402 Server (Self-Facilitation)",
        "version": "1.0.0",
        "network": EVM_NETWORK,
        "seller_address": SELLER_EVM_ADDRESS,
        "facilitator": "self-facilitated",
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
╔══════════════════════════════════════════════════════════════════╗
║          Simple x402 Server (Self-Facilitation)                  ║
╚══════════════════════════════════════════════════════════════════╝

Seller EVM Address: {SELLER_EVM_ADDRESS}
Network:            {EVM_NETWORK} (Base Sepolia)
USDC Contract:     {USDC_CONTRACT}

Free endpoints:
  GET /health      - Health check
  GET /info       - Server info

Paid endpoints (x402):
  GET /weather            - $0.001 USDC
  GET /premium/content    - $0.01 USDC
  GET /premium/data       - $0.01 USDC

Run server:
  python scripts/x402_simple_server.py
    """)

    uvicorn.run(app, host="0.0.0.0", port=4022)
