#!/usr/bin/env python3
"""
x402 LIVE DEMO CLIENT

This script makes a real HTTP request to the x402 test server
and demonstrates facilitator detection.

Run the server first:
    python scripts/x402_test_server.py

Then run this client:
    python scripts/demo_x402_client.py

This shows:
1. Making a request to a paywalled endpoint
2. Receiving 402 with payment requirements
3. Detecting the facilitator from the response
4. Routing to appropriate payment method
"""

import asyncio
import base64
import json
import httpx
from dataclasses import dataclass
from enum import Enum


class FacilitatorType(Enum):
    CIRCLE = "circle"
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass
class PaymentRequirements:
    version: int
    price: str
    currency: str
    chain: str
    chain_id: int
    network: str
    asset: str
    amount: str
    max_timeout_seconds: int
    pay_to: str
    facilitator: FacilitatorType
    raw: dict


def detect_facilitator(data: dict, scheme: dict) -> FacilitatorType:
    """Detect facilitator from 402 response."""
    extra = scheme.get("extra", {})

    # Check 1: Circle signature
    if extra.get("name") == "GatewayWalletBatched":
        return FacilitatorType.CIRCLE

    # Check 2: Circle verifying contract
    if extra.get("verifyingContract") == "0x0077777d7EBA4688BDeF3E311b846F25870A19B9":
        return FacilitatorType.CIRCLE

    # Check 3: Direct field
    facilitator_field = data.get("facilitator", "").lower()
    if facilitator_field == "circle":
        return FacilitatorType.CIRCLE

    # Check 4: Known Circle chains
    chain = data.get("payment", {}).get("chain", "").lower()
    if chain in ["base", "polygon", "solana"]:
        return FacilitatorType.CIRCLE

    # Check 5: Network
    network = scheme.get("network", "")
    if network in ["eip155:8453", "eip155:84532", "eip155:137"]:
        return FacilitatorType.CIRCLE

    return FacilitatorType.UNKNOWN


def parse_402_response(headers: dict, body: dict) -> PaymentRequirements:
    """Parse 402 response into structured data."""
    encoded = headers.get("payment-required") or headers.get("Payment-Required")

    if not encoded:
        raise ValueError("No Payment-Required header found")

    decoded = json.loads(base64.b64decode(encoded))
    payment = decoded.get("payment", {})
    accepts = decoded.get("accepts", [])
    scheme = accepts[0] if accepts else {}

    return PaymentRequirements(
        version=decoded.get("x402Version", 1),
        price=payment.get("price", "0"),
        currency=payment.get("currency", "USDC"),
        chain=payment.get("chain", "unknown"),
        chain_id=payment.get("chainId", 0),
        network=scheme.get("network", ""),
        asset=scheme.get("asset", ""),
        amount=scheme.get("amount", "0"),
        max_timeout_seconds=scheme.get("maxTimeoutSeconds", 3600),
        pay_to=scheme.get("payTo", ""),
        facilitator=detect_facilitator(decoded, scheme),
        raw=decoded,
    )


async def request_with_402_handling(url: str) -> tuple[dict, PaymentRequirements | None]:
    """
    Make a request and handle 402 responses.

    Returns:
        Tuple of (response_data, payment_requirements)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)

        if response.status_code == 402:
            # Payment required!
            reqs = parse_402_response(dict(response.headers), response.json())
            return {"status": "payment_required", "body": response.json()}, reqs

        elif response.status_code == 200:
            # Success
            return {"status": "success", "body": response.json()}, None

        else:
            # Other response
            return {"status": "error", "code": response.status_code, "body": response.text}, None


async def demo_client():
    """Run the demo client."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                  x402 CLIENT DEMO                                    ║
║                                                                      ║
║  This client requests a paywalled resource and shows how x402 works  ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    # Default server URL (run x402_test_server.py first)
    default_url = "http://localhost:8080/premium-data"

    print(f"Requesting: {default_url}")
    print("-" * 70)

    result, reqs = await request_with_402_handling(default_url)

    if reqs:
        print("\n✅ RECEIVED 402 PAYMENT REQUIRED")
        print("=" * 70)
        print(f"Version:      x402 v{reqs.version}")
        print(f"Price:        ${reqs.price} {reqs.currency}")
        print(f"Chain:        {reqs.chain} (chainId: {reqs.chain_id})")
        print(f"Network:      {reqs.network}")
        print(f"Pay To:       {reqs.pay_to}")
        print(f"Amount:       {reqs.amount} atomic units")
        print(f"Asset:        {reqs.asset}")
        print(f"Timeout:      {reqs.max_timeout_seconds}s")

        print("\n" + "=" * 70)
        print("🔍 FACILITATOR DETECTION")
        print("=" * 70)
        print(f"Detected:     {reqs.facilitator.value.upper()}")

        if reqs.facilitator == FacilitatorType.CIRCLE:
            print("""
✅ ROUTING: CIRCLE NANOPAYMENT (EIP-3009)
   
   This payment will use Circle's gasless EIP-3009 flow!
   
   Steps:
   1. Sign EIP-3009 TransferWithAuthorization with your vault key
   2. Server verifies with Circle Gateway
   3. Circle settles on-chain (batched)
   4. NO GAS required from you!
   
   Code:
""")
            print(f"""   omni.nanopayment_adapter.pay_direct(
       seller_address="{reqs.pay_to}",
       amount_usdc="{reqs.price}",
       nano_key_alias="your-key-alias"
   )""")

        elif reqs.facilitator == FacilitatorType.OTHER:
            print("""
⚠️  ROUTING: ON-CHAIN TRANSFER
   
   This payment requires gas!
   
   Steps:
   1. Initiate on-chain USDC transfer
   2. Pay gas for transaction
   3. Wait for confirmation
   
   Code:
""")
            print(f"""   omni.pay(
       wallet_id="your-wallet-id",
       recipient="{reqs.pay_to}",
       amount="{reqs.price}",
       destination_chain="{reqs.network}"
   )""")

        else:
            print("""
❓ ROUTING: UNKNOWN
   
   Cannot determine payment method.
   Check the 402 response format.
""")

        # Show raw response for debugging
        print("\n" + "=" * 70)
        print("📋 RAW 402 RESPONSE (for debugging)")
        print("=" * 70)
        print(json.dumps(reqs.raw, indent=2))

    else:
        if result["status"] == "success":
            print("✅ SUCCESS: Resource accessed!")
            print(json.dumps(result["body"], indent=2))
        else:
            print(f"❌ ERROR: Status {result.get('code')}")
            print(result.get("body", "")[:500])


async def demo_without_server():
    """Demo without running server - shows expected flow."""
    print("""
If the server is not running, here's what happens:

1. Request to GET /premium-data
   └─> Server returns 402 Payment Required

2. 402 Response contains:
   └─> Payment-Required header (base64 encoded)
   └─> Body with error message

3. Decode header to get payment requirements:
   {
     "x402Version": 2,
     "payment": {
       "price": "0.001",
       "currency": "USDC",
       "chain": "base",
       "chainId": 84532,
       "recipient": "0x..."
     },
     "accepts": [{
       "scheme": "exact",
       "network": "eip155:84532",
       "asset": "0x...",
       "amount": "1000000",
       "payTo": "0x...",
       "extra": {
         "name": "GatewayWalletBatched"  <-- CIRCLE INDICATOR!
       }
     }],
     "facilitator": "circle"  <-- DIRECT INDICATOR
   }

4. Detect facilitator:
   └─> "GatewayWalletBatched" in extra.name = CIRCLE
   
5. Route to nanopayment:
   └─> Use EIP-3009 (gasless)
   
To test with real server:
1. python scripts/x402_test_server.py
2. python scripts/demo_x402_client.py
""")


async def main():
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--no-server":
        await demo_without_server()
    else:
        try:
            await demo_client()
        except httpx.ConnectError:
            print("❌ Cannot connect to server")
            print("Make sure x402 test server is running:")
            print("  python scripts/x402_test_server.py")
            print("")
            await demo_without_server()


if __name__ == "__main__":
    asyncio.run(main())
