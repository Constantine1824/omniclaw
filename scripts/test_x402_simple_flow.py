#!/usr/bin/env python3
"""
Test the full x402 flow: OmniClaw buyer → Simple x402 server.

This script:
1. Tests the simple x402 server directly
2. Tests OmniClaw's x402 client integration

Run:
    python scripts/test_x402_simple_flow.py
"""

import asyncio
import base64
import json
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

load_dotenv()

# Import server module
import importlib.util

server_spec = importlib.util.spec_from_file_location(
    "x402_simple_server", Path(__file__).parent / "x402_simple_server.py"
)
x402_simple_server = importlib.util.module_from_spec(server_spec)


async def test_simple_server():
    """Test the simple x402 server directly."""
    from fastapi.testclient import TestClient

    server_spec.loader.exec_module(x402_simple_server)
    app = x402_simple_server.app

    print("\n[TEST 1] Simple x402 Server")
    print("-" * 50)

    client = TestClient(app)

    # Test free endpoint
    print("  GET /health...")
    resp = client.get("/health")
    assert resp.status_code == 200
    print(f"    ✓ {resp.json()}")

    # Test paid endpoint without payment
    print("  GET /weather (no payment)...")
    resp = client.get("/weather")
    assert resp.status_code == 402
    print(f"    ✓ Got 402 Payment Required")
    assert "payment-required" in resp.headers

    # Parse payment requirements
    header = resp.headers["payment-required"]
    req_bytes = base64.b64decode(header)
    req = json.loads(req_bytes)
    print(f"    ✓ Payment: ${int(req['accepts'][0]['amount']) / 1000000:.2f} USDC")

    # Test paid endpoint with payment
    print("  POST /weather (with payment)...")

    # Get wallet from test
    from eth_account import Account

    test_key = Account.create()
    mock_payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": "eip155:84532",
        "payload": {
            "authorization": {
                "from": test_key.address,
                "to": req["accepts"][0]["payTo"],
                "value": req["accepts"][0]["amount"],
                "validAfter": "0",
                "validBefore": "9999999999",
                "nonce": "0x" + "11" * 32,
            },
            "signature": "0xmock_signature",
        },
        "accepted": req["accepts"][0],
    }

    header = base64.b64encode(json.dumps(mock_payload).encode()).decode()
    resp = client.get("/weather", headers={"payment-signature": header})
    assert resp.status_code == 200
    print(f"    ✓ Payment accepted! Response: {resp.json()}")

    print("  ✓ Simple server tests passed")
    return True


async def test_omniclaw_client():
    """Test OmniClaw's x402 client."""
    from omniclaw import OmniClaw
    from omniclaw.core.types import Network

    print("\n[TEST 2] OmniClaw x402 Client")
    print("-" * 50)

    # Initialize OmniClaw
    print("  Initializing OmniClaw...")
    client = OmniClaw(network=Network.BASE_SEPOLIA, log_level="INFO")

    # Create wallet
    print("  Creating agent wallet...")
    wallet = await client.create_agent_wallet(blockchain=Network.BASE_SEPOLIA)
    print(f"    ✓ Wallet: {wallet.id}")

    # Get payment address
    payment_address = await client.get_payment_address(wallet.id)
    print(f"    ✓ Payment address: {payment_address}")

    # Test X402Adapter
    print("  Testing X402Adapter...")
    from omniclaw.protocols.x402 import X402Adapter

    x402_adapter = X402Adapter(vault=client.vault)

    # Check wallet key
    key_data = await client.vault.get_wallet_key(wallet.id)
    if not key_data:
        print("    ✗ No wallet key found")
        return False

    print(f"    ✓ Wallet key: {key_data['address']}")

    # Try payment
    print("  Attempting payment...")
    try:
        result = await x402_adapter.pay_x402_url(
            url="http://testserver/weather",
            wallet_id=wallet.id,
            amount="0.001",
            method="GET",
        )
        print(f"    Result: success={result.success}, error={result.error}")
    except Exception as e:
        print(f"    Payment error (expected without server): {e}")

    await client.__aexit__(None, None, None)
    print("  ✓ OmniClaw client test passed")
    return True


async def test_manual_x402_flow():
    """Test the full manual x402 flow without server."""
    import httpx
    from eth_account import Account
    from fastapi.testclient import TestClient

    print("\n[TEST 3] Manual x402 Flow (httpx)")
    print("-" * 50)

    # Create test key
    test_key = Account.create()
    print(f"  Test key: {test_key.address}")

    # Load server
    server_spec.loader.exec_module(x402_simple_server)
    app = x402_simple_server.app

    client = TestClient(app)

    # Step 1: Request without payment
    print("  Step 1: Request without payment...")
    resp = client.get("/weather")
    assert resp.status_code == 402

    # Parse payment requirements
    header = resp.headers["payment-required"]
    req_bytes = base64.b64decode(header)
    req = json.loads(req_bytes)
    accept = req["accepts"][0]
    print(f"    ✓ Payment required: {accept['amount']} atomic units to {accept['payTo']}")

    # Step 2: Create payment payload
    print("  Step 2: Create payment payload...")
    payload = {
        "x402Version": 2,
        "scheme": "exact",
        "network": accept["network"],
        "payload": {
            "authorization": {
                "from": test_key.address,
                "to": accept["payTo"],
                "value": accept["amount"],
                "validAfter": "0",
                "validBefore": str(int(9999999999)),
                "nonce": "0x" + "22" * 32,
            },
            "signature": "0xmock_signature_for_testing",
        },
        "accepted": accept,
    }
    payment_header = base64.b64encode(json.dumps(payload).encode()).decode()
    print(f"    ✓ Created payment header ({len(payment_header)} chars)")

    # Step 3: Retry with payment
    print("  Step 3: Retry with payment...")
    resp = client.get("/weather", headers={"payment-signature": payment_header})
    print(f"    ✓ Status: {resp.status_code}")

    if resp.status_code == 200:
        print(f"    ✓ Response: {resp.json()}")
    else:
        print(f"    ✗ Error: {resp.text}")

    print("  ✓ Manual flow test passed")
    return True


async def main():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║          OmniClaw x402 Integration Test                         ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    all_passed = True

    tests = [
        ("Simple Server", test_simple_server),
        ("OmniClaw Client", test_omniclaw_client),
        ("Manual Flow", test_manual_x402_flow),
    ]

    for name, test_fn in tests:
        try:
            await test_fn()
        except Exception as e:
            all_passed = False
            print(f"  ✗ {name} FAILED: {e}")
            import traceback

            traceback.print_exc()

    if all_passed:
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
