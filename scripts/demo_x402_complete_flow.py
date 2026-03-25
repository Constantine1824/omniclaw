#!/usr/bin/env python3
"""
x402 DEMO: Complete Flow with Facilitator Detection

This demo shows the complete x402 payment flow:
1. Buyer makes a request to a seller server
2. Server returns 402 with payment requirements
3. We detect the facilitator from the 402 response
4. If Circle → use nanopayment (gasless EIP-3009)
5. If other → use on-chain transfer (with gas)

IMPORTANT: This demo shows the FLOW without actually executing payments.
To execute real payments, you need:
- USDC in your wallet on the seller's network
- Gas for on-chain transactions (unless using Circle nanopayment)

NETWORK SUPPORT:
- Circle CDP: Base, Polygon, Solana (mainnet + testnet)
- x402.org: Base Sepolia only (testnet only)
- ARC testnet: NOT SUPPORTED by any x402 facilitator yet

Author: OmniClaw Team
Date: 2026-03-23
"""

import asyncio
import base64
import json
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FacilitatorType(Enum):
    """Types of facilitators we can detect."""

    CIRCLE = "circle"  # EIP-3009 nanopayment (gasless)
    OTHER = "other"  # Regular on-chain (with gas)
    UNKNOWN = "unknown"


@dataclass
class PaymentRequirements:
    """Parsed x402 payment requirements."""

    version: int
    price: str
    currency: str
    chain: str
    chain_id: int
    recipient: str
    network: str  # CAIP-2 format
    asset: str  # Token address
    amount: str  # Atomic units
    max_timeout_seconds: int
    pay_to: str
    facilitator: FacilitatorType
    raw_data: dict


def parse_payment_requirements(response_headers: dict, response_body: dict) -> PaymentRequirements:
    """
    Parse the 402 response to extract payment requirements.

    x402 v2 uses base64-encoded JSON in the Payment-Required header.
    """
    # Try both header variations (lowercase and uppercase)
    payment_required = response_headers.get("payment-required") or response_headers.get(
        "Payment-Required"
    )

    if not payment_required:
        raise ValueError("No Payment-Required header found in response")

    # Decode base64
    decoded = base64.b64decode(payment_required).decode("utf-8")
    data = json.loads(decoded)

    print("\n" + "=" * 70)
    print("📋 RAW 402 RESPONSE DATA (Decoded)")
    print("=" * 70)
    print(json.dumps(data, indent=2))

    # Extract payment info
    payment = data.get("payment", {})

    # Extract accepts array (first scheme)
    accepts = data.get("accepts", [])
    scheme = accepts[0] if accepts else {}

    # Detect facilitator
    facilitator = detect_facilitator(data, scheme)

    return PaymentRequirements(
        version=data.get("x402Version", 1),
        price=payment.get("price", "0"),
        currency=payment.get("currency", "USDC"),
        chain=payment.get("chain", "unknown"),
        chain_id=payment.get("chainId", 0),
        recipient=payment.get("recipient", ""),
        network=scheme.get("network", ""),
        asset=scheme.get("asset", ""),
        amount=scheme.get("amount", "0"),
        max_timeout_seconds=scheme.get("maxTimeoutSeconds", 3600),
        pay_to=scheme.get("payTo", ""),
        facilitator=facilitator,
        raw_data=data,
    )


def detect_facilitator(data: dict, scheme: dict) -> FacilitatorType:
    """
    Detect which facilitator the seller uses.

    Key indicators:
    1. "GatewayWalletBatched" in scheme.extra.name → Circle
    2. "facilitator" field in data → direct indicator
    3. Verifying contract 0x0077777d7EBA4688BDeF3E311b846F25870A19B9 → Circle
    """
    print("\n" + "=" * 70)
    print("🔍 FACILITATOR DETECTION")
    print("=" * 70)

    # Check 1: Circle's signature scheme
    extra = scheme.get("extra", {})
    if extra.get("name") == "GatewayWalletBatched":
        print("✅ Detected: GatewayWalletBatched → CIRCLE (EIP-3009 nanopayment)")
        print("   → Use nanopayment_adapter.pay_direct() for gasless payment")
        return FacilitatorType.CIRCLE

    # Check 2: Verifying contract
    if extra.get("verifyingContract") == "0x0077777d7EBA4688BDeF3E311b846F25870A19B9":
        print("✅ Detected: Circle verifying contract → CIRCLE (EIP-3009 nanopayment)")
        return FacilitatorType.CIRCLE

    # Check 3: Direct facilitator field
    facilitator_field = data.get("facilitator", "").lower()
    if facilitator_field == "circle":
        print("✅ Detected: facilitator='circle' → CIRCLE (EIP-3009 nanopayment)")
        return FacilitatorType.CIRCLE

    # Check 4: Chain-based heuristic
    chain = data.get("payment", {}).get("chain", "").lower()
    if chain in ["base", "polygon", "solana"]:
        print(f"⚠️  Chain '{chain}' supported by Circle, but no explicit Circle indicator")
        print("   → Assuming Circle (default for these chains)")
        return FacilitatorType.CIRCLE

    # Check 5: Network in accepts
    network = scheme.get("network", "")
    if network in ["eip155:8453", "eip155:84532", "eip155:137"]:
        print(f"⚠️  Network '{network}' typically uses Circle")
        return FacilitatorType.CIRCLE

    # Unknown
    print(f"❓ Unknown facilitator")
    print(f"   Chain: {chain}")
    print(f"   Network: {network}")
    print(f"   Facilitator field: {facilitator_field}")
    print("   → Use regular on-chain transfer")
    return FacilitatorType.UNKNOWN


async def demonstrate_flow():
    """Demonstrate the complete x402 flow."""

    print("\n" + "=" * 70)
    print("🚀 x402 PAYMENT FLOW DEMONSTRATION")
    print("=" * 70)
    print("""
This demo shows how x402 protocol works:
1. Buyer requests a resource
2. Server returns 402 with payment requirements
3. We detect the facilitator from the response
4. Route to appropriate payment method

Since we're not making real requests, we'll simulate the 402 response.
""")

    # Simulate what a real x402 server would return
    # This is what our x402_test_server.py returns
    simulated_402_response = {
        "headers": {
            "payment-required": base64.b64encode(
                json.dumps(
                    {
                        "x402Version": 2,
                        "expires": 1742784000,
                        "resource": {
                            "url": "https://api.example.com/premium-data",
                            "description": "Premium API access - Base network payment",
                            "mimeType": "application/json",
                        },
                        "payment": {
                            "price": "0.001",
                            "currency": "USDC",
                            "chain": "base",
                            "chainId": 84532,  # Base Sepolia
                            "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
                        },
                        "accepts": [
                            {
                                "scheme": "exact",
                                "network": "eip155:84532",  # Base Sepolia CAIP-2
                                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
                                "amount": "1000000",  # 1 USDC in atomic units (6 decimals)
                                "maxTimeoutSeconds": 3600,
                                "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
                                "extra": {
                                    "name": "GatewayWalletBatched",  # ← CIRCLE INDICATOR!
                                    "version": "1",
                                    "verifyingContract": "0x0077777d7EBA4688BDeF3E311b846F25870A19B9",
                                },
                            }
                        ],
                        "facilitator": "circle",  # ← DIRECT CIRCLE INDICATOR
                    }
                ).encode()
            ).decode()
        },
        "body": {"error": "Payment Required", "message": "This resource costs 0.001 USDC"},
    }

    print("\n" + "=" * 70)
    print("📤 STEP 1: Request a paid resource")
    print("=" * 70)
    print("""
GET /premium-data HTTP/1.1
Host: api.example.com
Accept: application/json

""")

    print("=" * 70)
    print("📥 STEP 2: Receive 402 Payment Required")
    print("=" * 70)
    print("""
HTTP/1.1 402 Payment Required
Content-Type: application/json
Payment-Required: <base64-encoded-json>

{
  "error": "Payment Required",
  "message": "This resource costs 0.001 USDC"
}
""")

    # Parse the 402 response
    reqs = parse_payment_requirements(
        simulated_402_response["headers"], simulated_402_response["body"]
    )

    # Show parsed requirements
    print("\n" + "=" * 70)
    print("📋 PARSED PAYMENT REQUIREMENTS")
    print("=" * 70)
    print(f"  Version:       x402 v{reqs.version}")
    print(f"  Price:         ${reqs.price} {reqs.currency}")
    print(f"  Chain:         {reqs.chain} (chainId: {reqs.chain_id})")
    print(f"  Network:       {reqs.network}")
    print(f"  Recipient:     {reqs.recipient}")
    print(f"  Pay To:        {reqs.pay_to}")
    print(f"  Amount:        {reqs.amount} atomic units")
    print(f"  Asset:         {reqs.asset}")
    print(f"  Max Timeout:   {reqs.max_timeout_seconds}s")
    print(f"  Facilitator:   {reqs.facilitator.value}")

    # Show routing decision
    print("\n" + "=" * 70)
    print("🔀 ROUTING DECISION")
    print("=" * 70)

    if reqs.facilitator == FacilitatorType.CIRCLE:
        print("""
✅ ROUTING: CIRCLE NANOPAYMENT (EIP-3009)

Payment Method: Gasless via Circle Gateway
- No gas required from buyer!
- Sign EIP-3009 TransferWithAuthorization
- Circle facilitator verifies and settles on-chain
- Buyer pays only the USDC amount

How it works:
1. Buyer signs EIP-3009 authorization with vault key
2. Server verifies with Circle Gateway API
3. Circle batches and settles on-chain
4. Seller receives USDC, buyer gets resource

Implementation:
""")
        show_nanopayment_code(reqs)

    elif reqs.facilitator == FacilitatorType.OTHER:
        print("""
⚠️  ROUTING: ON-CHAIN TRANSFER

Payment Method: Regular blockchain transfer
- Requires gas from buyer
- Direct USDC transfer to seller
- Buyer pays gas + USDC amount

How it works:
1. Buyer initiates on-chain transfer
2. Transaction submitted to network
3. Wait for confirmation
4. Seller receives USDC

Implementation:
""")
        show_onchain_code(reqs)
    else:
        print("""
❓ ROUTING: UNKNOWN FACILITATOR

Cannot determine payment method.
Please check the 402 response format.
""")

    # Show unified flow (what we're building)
    print("\n" + "=" * 70)
    print("🎯 UNIFIED FLOW (What We're Building)")
    print("=" * 70)
    show_unified_flow()


def show_nanopayment_code(reqs: PaymentRequirements):
    """Show code for Circle nanopayment."""
    print(
        """
```python
from omniclaw import OmniClaw

async def pay_with_nanopayment():
    omni = OmniClaw(...)
    
    # Check your gateway balance first
    balance = await omni.get_gateway_balance()
    print(f"Gateway Balance: {balance.available}")
    
    # Make the payment (gasless!)
    result = await omni.nanopayment_adapter.pay_direct(
        seller_address="""
        + f'"{reqs.pay_to}"'
        + """,
        amount_usdc="""
        + f'"{reqs.price}"'
        + """,
        nano_key_alias="my-agent-key"  # Your vault key
    )
    
    print(f"Payment: {result}")
    return result
```
"""
    )

    print("""
Key requirements for nanopayment:
1. ✅ Generate a vault key: omni.generate_key("my-agent-key")
2. ✅ Fund the key address with USDC
3. ✅ Deposit USDC to gateway: omni.deposit_to_gateway("10.0")
4. ✅ Sign with vault key (no gas needed)
""")


def show_onchain_code(reqs: PaymentRequirements):
    """Show code for regular on-chain transfer."""
    print(
        """
```python
from omniclaw import OmniClaw

async def pay_onchain():
    omni = OmniClaw(...)
    
    # Get your wallet
    wallets = await omni.list_wallets()
    wallet_id = wallets[0].id
    
    # Make on-chain payment (requires gas!)
    result = await omni.pay(
        wallet_id=wallet_id,
        recipient="""
        + f'"{reqs.pay_to}"'
        + """,
        amount="""
        + f'"{reqs.price}"'
        + """,
        destination_chain="""
        + f'"{reqs.network}"'
        + """
    )
    
    print(f"Payment: {result}")
    return result
```
"""
    )

    print("""
⚠️  IMPORTANT: On-chain payments require:
1. ✅ USDC in your wallet
2. ✅ Native gas token for transaction fees
3. ❌ Gas cost borne by buyer
""")


def show_unified_flow():
    """Show the unified flow we're building."""
    print("""
The goal is a SINGLE client.pay() that handles everything:

```python
from omniclaw import OmniClaw

async def unified_payment():
    omni = OmniClaw(...)
    
    # ONE call does everything:
    # 1. Makes request to seller
    # 2. Gets 402 response
    # 3. Detects facilitator
    # 4. Routes to appropriate method
    result = await omni.pay_x402(
        url="https://api.seller.com/premium-data",
        amount="0.001",
        wallet_id="my-wallet-id"  # or nano_key_alias
    )
    
    # Under the hood:
    # - If Circle detected → uses nanopayment (gasless)
    # - If other → uses on-chain (with gas)
    print(f"Result: {result}")
```

Decision tree:
┌─────────────────┐
│ Get 402 Response │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Detect Facilitator │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
  Circle    Other
    │         │
    ▼         ▼
 Nanopay   On-chain
 (EIP-3009) (Transfer)
""")


async def main():
    """Run the demonstration."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    x402 PAYMENT FLOW DEMO                           ║
║                                                                      ║
║  This demo shows how x402 protocol enables:                          ║
║  • HTTP-native micropayments using USDC                              ║
║  • Automatic facilitator detection                                    ║
║  • Smart routing (nanopayment vs on-chain)                            ║
║                                                                      ║
║  Networks:                                                            ║
║  • Base (mainnet + sepolia) - BEST SUPPORTED                         ║
║  • Polygon (mainnet + amoy)                                          ║
║  • Solana                                                            ║
║  • ARC testnet - NOT YET SUPPORTED by x402 facilitators              ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    await demonstrate_flow()

    print("\n" + "=" * 70)
    print("📚 NEXT STEPS")
    print("=" * 70)
    print("""
1. Start the test server:
   $ python scripts/x402_test_server.py

2. Run this demo to see the flow:
   $ python scripts/demo_x402_complete_flow.py

3. To test REAL payments:
   - Use Base Sepolia testnet
   - Get test USDC from faucet
   - Use Circle CDP facilitator

4. For ARC testnet:
   - Not yet supported by x402
   - Need to wait for facilitator support OR
   - Use CCTP to bridge to Base
""")


if __name__ == "__main__":
    asyncio.run(main())
