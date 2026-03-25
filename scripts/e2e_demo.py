"""
End-to-End Demo: Buyer Agent + Seller Agent with Facilitator

This demonstrates a complete payment flow:
1. Seller Agent starts server with x402-protected endpoints
2. Buyer Agent requests protected resource
3. Seller returns 402 Payment Required
4. Buyer parses and pays (via Circle Gateway)
5. Seller verifies via facilitator
6. Seller settles via facilitator
7. Buyer gets the resource

Run: python scripts/e2e_demo.py
"""

import asyncio
import json
import base64
import httpx
from eth_account import Account
from web3 import Web3

# OmniClaw imports
from omniclaw.seller import create_seller
from omniclaw import OmniClaw


# =============================================================================
# CONFIG
# =============================================================================

# Use test key for demo (won't do real transactions)
CIRCLE_API_KEY = "TEST_API_KEY:3fc089aeb8f29aca6ef7d3423ad37995:a11e0c4afd034a5a6e228934f18c133a"

# Network
NETWORK = "base-sepolia"
USDC_CONTRACT = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

# Seller address (demo)
SELLER_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123"


# =============================================================================
# SELLER AGENT
# =============================================================================


class SellerAgent:
    """
    Seller Agent - runs a server that accepts x402 payments.
    """

    def __init__(self, seller_address: str, facilitator=None):
        self.seller_address = seller_address
        self.facilitator = facilitator

        # Create OmniClaw seller
        self.seller = create_seller(
            seller_address=seller_address,
            name="Weather API",
            description="Premium weather data service",
            facilitator=facilitator,
        )

        # Add protected endpoints
        self.seller.add_endpoint("/current", "$0.001", "Current weather")
        self.seller.add_endpoint("/forecast", "$0.01", "7-day forecast")
        self.seller.add_endpoint("/alerts", "$0.05", "Weather alerts")

        print(f"🌐 Seller Agent initialized")
        print(f"   Address: {seller_address}")
        print(f"   Facilitator: {facilitator.name if facilitator else 'None'}")
        print(f"   Endpoints:")
        for path, endpoint in self.seller._endpoints.items():
            print(f"     {path}: ${endpoint.price_usd}")

    def create_402_response(self, path: str) -> tuple[int, dict, str]:
        """Generate 402 response for a path."""
        url = f"https://api.weather.com{path}"
        headers, body = self.seller.create_402_response(path, url)
        return 402, headers, body

    def verify_and_settle(self, payment_payload: dict, accepted: dict, settle: bool = True):
        """Verify and optionally settle payment."""
        # For demo, simulate successful verification
        # In real usage, this would call the facilitator
        print(f"   (Simulating facilitator call...)")

        buyer = payment_payload.get("payload", {}).get("authorization", {}).get("from", "unknown")
        amount = payment_payload.get("payload", {}).get("authorization", {}).get("value", "0")

        # Create a mock record
        class MockRecord:
            def __init__(self):
                self.id = "demo_" + buyer[:8]
                self.buyer_address = buyer
                self.amount = int(amount)

        return True, "", MockRecord()


# =============================================================================
# BUYER AGENT
# =============================================================================


class BuyerAgent:
    """
    Buyer Agent - pays for x402-protected resources.
    """

    def __init__(self, wallet_address: str, private_key: str):
        self.wallet_address = wallet_address
        self.private_key = private_key

        # Create OmniClaw client (for reference)
        # In real usage, you'd use OmniClaw to create wallet
        print(f"💰 Buyer Agent initialized")
        print(f"   Wallet: {wallet_address}")

    async def request_resource(self, url: str) -> dict:
        """Request a resource - returns 402 if payment required."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                return {
                    "status": response.status_code,
                    "data": response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else response.text,
                    "headers": dict(response.headers),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

    def parse_402_response(self, headers: dict) -> dict | None:
        """Parse 402 Payment Required header."""
        header_value = headers.get("payment-required")
        if not header_value:
            return None

        # Decode base64
        decoded = base64.b64decode(header_value).decode()
        return json.loads(decoded)

    def create_payment_payload(self, requirements: dict, url: str) -> dict:
        """Create signed payment payload."""
        import time

        # For demo, create mock authorization
        # In real implementation, would use OmniClaw to sign EIP-3009 authorization
        valid_after = 0
        valid_before = int(time.time()) + 3600  # 1 hour
        nonce = Web3.keccak(text=f"{self.wallet_address}{int(time.time())}").hex()

        authorization = {
            "from": self.wallet_address,
            "to": requirements["payTo"],
            "value": requirements["amount"],
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce,
        }

        # Create payload
        payload = {
            "x402Version": 2,
            "scheme": requirements["scheme"],
            "resource": {
                "url": url,
            },
            "accepted": requirements,
            "payload": {
                "authorization": authorization,
                # In real impl, would be actual EIP-712 signature
                "signature": "0x" + "00" * 65,
            },
        }

        return payload

    async def pay_and_request(self, url: str) -> dict:
        """Full flow: request, handle 402, pay, retry."""

        # Step 1: Initial request
        print(f"\n📤 Step 1: Requesting {url}")
        result = await self.request_resource(url)

        if result["status"] != 402:
            print(f"   Result: {result['status']} - No payment needed")
            return result

        # Step 2: Parse 402
        print(f"   Got 402 - parsing payment requirements...")
        requirements = self.parse_402_response(result["headers"])

        if not requirements:
            print("   ❌ No payment requirements found!")
            return {"status": "error", "error": "No payment requirements"}

        print(
            f"   ✓ Payment required: {requirements.get('accepts', [{}])[0].get('amount', '?')} USDC"
        )

        # Show accepts
        accepts = requirements.get("accepts", [])
        print(f"   Accepts: {', '.join([a.get('scheme', '?') for a in accepts])}")

        # Step 3: Choose payment method (prefer Circle if available)
        selected = accepts[0]  # Demo: just pick first
        print(f"   → Using: {selected.get('scheme', '?')}")

        # Step 4: Create payment payload
        print(f"\n📝 Step 2: Creating payment payload")
        payment_payload = self.create_payment_payload(selected, url)
        print(f"   From: {payment_payload['payload']['authorization']['from']}")
        print(f"   To: {payment_payload['payload']['authorization']['to']}")
        print(f"   Amount: {payment_payload['payload']['authorization']['value']}")

        # Step 5: Retry with payment
        print(f"\n📤 Step 3: Retrying with payment")

        # Encode payload
        payload_b64 = base64.b64encode(json.dumps(payment_payload).encode()).decode()

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers={"PAYMENT-SIGNATURE": payload_b64},
                    timeout=10.0,
                )

                return {
                    "status": response.status_code,
                    "data": response.json()
                    if response.headers.get("content-type", "").startswith("application/json")
                    else response.text,
                    "headers": dict(response.headers),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}


# =============================================================================
# MAIN DEMO
# =============================================================================


async def run_demo():
    print("=" * 60)
    print("🌟 OmniClaw End-to-End Demo")
    print("   Buyer Agent → x402 Payment → Seller Agent")
    print("=" * 60)

    # Create facilitator (Circle)
    print("\n🔧 Setting up Circle Gateway Facilitator...")
    from omniclaw.seller import create_facilitator

    facilitator = create_facilitator(
        provider="circle",
        api_key=CIRCLE_API_KEY,
        environment="testnet",
    )
    print(f"   Facilitator: {facilitator.name}")
    print(f"   URL: {facilitator.base_url}")

    # Create seller
    print("\n🏪 Creating Seller Agent...")
    seller = SellerAgent(SELLER_ADDRESS, facilitator=facilitator)

    # Create buyer (demo wallet)
    print("\n👤 Creating Buyer Agent...")
    buyer = BuyerAgent(
        wallet_address="0xBuyer1234567890abcdef1234567890abcdef12",
        private_key="0x" + "00" * 32,
    )

    # Simulate the flow
    print("\n" + "=" * 60)
    print("💸 PAYMENT FLOW DEMO")
    print("=" * 60)

    # Step 1: Request without payment
    print("\n📤 Step 1: Requesting /current without payment...")
    status_code, headers, body = seller.create_402_response("/current")
    print(f"   Seller returns: {status_code}")
    print(f"   Header: payment-required = {headers.get('payment-required', '')[:50]}...")

    # Parse for buyer
    header_value = headers.get("payment-required")
    decoded = json.loads(base64.b64decode(header_value).decode())
    accepts = decoded.get("accepts", [])
    print(f"   Payment required: {accepts[0].get('amount')} USDC")
    print(f"   Schemes: {[a.get('scheme') for a in accepts]}")

    # Step 2: Create payment payload
    print("\n📝 Step 2: Buyer creates payment payload...")
    payment_payload = buyer.create_payment_payload(accepts[0], "/current")
    print(f"   Authorization: from={payment_payload['payload']['authorization']['from']}")
    print(f"                  to={payment_payload['payload']['authorization']['to']}")
    print(f"                  value={payment_payload['payload']['authorization']['value']}")

    # Step 3: Verify via facilitator
    print("\n🔐 Step 3: Seller verifies via facilitator...")
    is_valid, error, record = seller.verify_and_settle(
        payment_payload=payment_payload,
        accepted=accepts[0],
        settle=True,
    )

    if is_valid:
        print(f"   ✓ Payment verified!")
        print(f"   ✓ Settled! (tx would go on-chain)")
        print(f"   Payment ID: {record.id if record else 'N/A'}")
        print(f"   Amount: {record.amount if record else 'N/A'} USDC")
        print(f"   Buyer: {record.buyer_address if record else 'N/A'}")
    else:
        print(f"   ❌ Verification failed: {error}")

    print("\n" + "=" * 60)
    print("✅ Demo Complete!")
    print("=" * 60)

    # Cleanup
    await facilitator.close()

    return {
        "seller": seller.seller_address,
        "buyer": buyer.wallet_address,
        "verified": is_valid,
        "error": error,
    }


if __name__ == "__main__":
    result = asyncio.run(run_demo())
    print(f"\nFinal result: {json.dumps(result, indent=2)}")
