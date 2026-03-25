#!/usr/bin/env python3
"""
UNIFIED x402 PAY DEMO - Complete End-to-End Flow

This demo shows EXACTLY how the unified pay() should work:

1. Request URL
2. Get 402 response
3. Parse accepts array (what SELLER accepts)
4. Match our capabilities to their accepts
5. Execute the best method

THE KEY: The 402 response tells us EVERYTHING about what the seller accepts!

Author: OmniClaw Team
Date: 2026-03-23
"""

import asyncio
import base64
import json
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class PaymentCapability(Enum):
    """What we support."""

    CIRCLE_NANOPAYMENT = "circle_nanopayment"
    DIRECT_X402 = "direct_x402"


@dataclass
class AcceptedMethod:
    """A payment method accepted by the seller."""

    scheme: str
    network: str
    asset: str
    amount: str
    pay_to: str
    max_timeout: int
    extra: dict

    @property
    def is_circle_nanopayment(self) -> bool:
        """Does seller accept Circle nanopayment?"""
        return self.extra.get("name") == "GatewayWalletBatched"

    @property
    def is_direct_x402(self) -> bool:
        """Does seller accept direct x402?"""
        return self.scheme == "exact" and not self.is_circle_nanopayment


@dataclass
class SellerAccepts:
    """What the SELLER accepts (from 402 response)."""

    price: str
    currency: str
    chain: str
    chain_id: int
    methods: List[AcceptedMethod]


def parse_seller_accepts(accepts_data: list) -> List[AcceptedMethod]:
    """Parse accepts array from 402 response."""
    methods = []
    for accept in accepts_data:
        methods.append(
            AcceptedMethod(
                scheme=accept.get("scheme", "exact"),
                network=accept.get("network", ""),
                asset=accept.get("asset", ""),
                amount=accept.get("amount", "0"),
                pay_to=accept.get("payTo", ""),
                max_timeout=accept.get("maxTimeoutSeconds", 3600),
                extra=accept.get("extra", {}),
            )
        )
    return methods


def what_seller_accepts(response_data: dict) -> SellerAccepts:
    """Parse the COMPLETE 402 response."""
    payment = response_data.get("payment", {})
    accepts_data = response_data.get("accepts", [])

    return SellerAccepts(
        price=payment.get("price", "0"),
        currency=payment.get("currency", "USDC"),
        chain=payment.get("chain", "unknown"),
        chain_id=payment.get("chainId", 0),
        methods=parse_seller_accepts(accepts_data),
    )


def match_capabilities(
    seller: SellerAccepts, our_capabilities: List[PaymentCapability]
) -> Optional[AcceptedMethod]:
    """
    Match what SELLER accepts to what WE support.

    Priority:
    1. Circle Nanopayment (best UX - gasless)
    2. Direct x402 (works everywhere)
    """
    print("\n🔍 CHECKING COMPATIBILITY:")
    print(f"   Seller accepts: {[m.extra.get('name', 'direct') for m in seller.methods]}")
    print(f"   We support: {[c.value for c in our_capabilities]}")

    # Priority 1: Circle Nanopayment
    if PaymentCapability.CIRCLE_NANOPAYMENT in our_capabilities:
        for method in seller.methods:
            if method.is_circle_nanopayment:
                print(f"   ✅ MATCH: Circle Nanopayment")
                return method

    # Priority 2: Direct x402
    if PaymentCapability.DIRECT_X402 in our_capabilities:
        for method in seller.methods:
            if method.is_direct_x402:
                print(f"   ✅ MATCH: Direct x402")
                return method

    # No match
    print(f"   ❌ NO MATCH: We can't pay with any accepted method")
    return None


async def unified_pay(
    seller_url: str, amount: str, our_capabilities: List[PaymentCapability] = None
) -> dict:
    """
    UNIFIED PAY - ONE METHOD FOR EVERYTHING!

    This is what the user calls:

    ```python
    result = await unified_pay(
        seller_url="https://api.seller.com/data",
        amount="0.001"
    )
    ```

    Internally it:
    1. Requests the URL
    2. Gets 402 response
    3. Parses what SELLER accepts
    4. Matches to our capabilities
    5. Executes with best method
    """

    if our_capabilities is None:
        # Default: We support both!
        our_capabilities = [
            PaymentCapability.CIRCLE_NANOPAYMENT,
            PaymentCapability.DIRECT_X402,
        ]

    print(f"\n{'=' * 70}")
    print(f"🎯 UNIFIED PAY: {seller_url}")
    print(f"{'=' * 70}")

    # Step 1: In real impl, we'd make HTTP request here
    # For demo, we'll simulate

    # Step 2: Get 402 response (simulated)
    # In real code: response = await http.get(seller_url)

    # Step 3: Parse what SELLER accepts
    # In real code: seller = what_seller_accepts(decode_402(response))

    # For demo, show the flow with mock data

    print(f"""
📤 STEP 1: Request URL
   GET {seller_url}

📥 STEP 2: Get 402 Response (from seller)
   This tells us what the SELLER accepts!

🔍 STEP 3: Parse accepts array
   The accepts[] array tells us what payment methods work.
   We DON'T assume - we READ what they accept.
""")

    return {"status": "ready", "message": "Demo complete"}


async def demo_scenario(seller_402_response: dict, scenario_name: str):
    """Demo a specific seller scenario."""

    print(f"\n{'=' * 70}")
    print(f"📋 SCENARIO: {scenario_name}")
    print(f"{'=' * 70}")

    # Parse what SELLER accepts
    seller = what_seller_accepts(seller_402_response)

    print(f"""
💰 Seller wants: ${seller.price} {seller.currency}
🌐 Network: {seller.chain} (chainId: {seller.chain_id})
📋 Accepted methods: {len(seller.methods)}
""")

    # Show each accepted method
    print("PAYMENT METHODS ACCEPTED BY SELLER:")
    for i, method in enumerate(seller.methods, 1):
        print(f"""
   [{i}] {method.scheme.upper()} on {method.network}
       Pay To: {method.pay_to}
       Amount: {method.amount} atomic units
       Extra:  {method.extra.get("name", "(none)")}""")

    # Check what we support
    print(f"\n{'=' * 70}")
    print("🔍 MATCHING: Our Capabilities vs Seller Accepts")
    print(f"{'=' * 70}")

    # Our capabilities (what OmniClaw supports)
    our_capabilities = [
        PaymentCapability.CIRCLE_NANOPAYMENT,  # We support Circle!
        PaymentCapability.DIRECT_X402,  # We also support direct!
    ]

    matched = match_capabilities(seller, our_capabilities)

    if matched:
        print(f"""
✅ ROUTING DECISION:

   Selected: {matched.scheme.upper()} on {matched.network}
   Pay To:   {matched.pay_to}
   
   """)

        if matched.is_circle_nanopayment:
            return await execute_circle_nanopayment(matched)
        else:
            return await execute_direct_x402(matched)
    else:
        print("""
❌ CANNOT PAY:

   The seller doesn't accept any payment method we support.
   We would need to either:
   1. Ask seller to add support for our method
   2. Use a different payment path
""")


async def execute_circle_nanopayment(method: AcceptedMethod) -> dict:
    """Execute using Circle Nanopayment."""
    print(f"""
✅ EXECUTING: CIRCLE NANOPAYMENT

   🔐 Sign EIP-3009 authorization
   📤 Submit to Circle Gateway API
   ⏳ Circle verifies & updates off-chain balance
   💰 Settlement batched later (buyer pays nothing for gas!)

   Code would be:
   ```python
   result = await omni.nanopayment_adapter.pay_direct(
       seller_address="{method.pay_to}",
       amount_usdc="{int(method.amount) / 1_000_000}",
       nano_key_alias="my-agent"
   )
   ```
""")
    return {
        "method": "circle_nanopayment",
        "pay_to": method.pay_to,
        "amount": method.amount,
        "network": method.network,
    }


async def execute_direct_x402(method: AcceptedMethod) -> dict:
    """Execute using direct x402."""
    print(f"""
⚠️  EXECUTING: DIRECT x402

   🔐 Sign EIP-3009 authorization
   📤 Submit to facilitator API (verify + settle)
   ⛽ Facilitator pays gas OR buyer pays gas
   🔄 Immediate on-chain settlement

   Code would be:
   ```python
   result = await omni.x402_adapter.pay(
       seller_address="{method.pay_to}",
       amount="{int(method.amount) / 1_000_000}",
       network="{method.network}"
   )
   ```
""")
    return {
        "method": "direct_x402",
        "pay_to": method.pay_to,
        "amount": method.amount,
        "network": method.network,
    }


async def demo_all_scenarios():
    """Demo all possible seller scenarios."""

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           COMPLETE x402 FLOW DEMO                                   ║
║                                                                      ║
║  THE KEY: We read what the SELLER accepts from the 402 response    ║
║  and match it to what WE support!                                   ║
║                                                                      ║
║  What we support:                                                   ║
║  ✅ Circle Nanopayment (GatewayWalletBatched)                      ║
║  ✅ Direct x402 (standard EIP-3009)                                 ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    # SCENARIO 1: Seller accepts Circle Nanopayment
    seller_circle = {
        "x402Version": 2,
        "payment": {
            "price": "0.001",
            "currency": "USDC",
            "chain": "base",
            "chainId": 84532,
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": "eip155:84532",
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "amount": "1000000",
                "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
                "maxTimeoutSeconds": 3600,
                "extra": {
                    "name": "GatewayWalletBatched",  # ← CIRCLE NANOPAYMENT
                },
            }
        ],
    }
    await demo_scenario(seller_circle, "Seller accepts Circle Nanopayment")

    # SCENARIO 2: Seller accepts Direct x402 (no Circle)
    seller_direct = {
        "x402Version": 2,
        "payment": {
            "price": "0.001",
            "currency": "USDC",
            "chain": "polygon",
            "chainId": 137,
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": "eip155:137",
                "asset": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
                "amount": "1000000",
                "payTo": "0xabc123def456789ABCDEF123456789012345678",
                "maxTimeoutSeconds": 3600,
                # No extra.name = Direct x402
            }
        ],
    }
    await demo_scenario(seller_direct, "Seller accepts Direct x402 only")

    # SCENARIO 3: Seller accepts BOTH
    seller_both = {
        "x402Version": 2,
        "payment": {
            "price": "0.001",
            "currency": "USDC",
            "chain": "base",
            "chainId": 84532,
        },
        "accepts": [
            {
                "scheme": "exact",
                "network": "eip155:84532",
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "amount": "1000000",
                "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
                "maxTimeoutSeconds": 3600,
                "extra": {
                    "name": "GatewayWalletBatched",  # ← CIRCLE
                },
            },
            {
                "scheme": "exact",
                "network": "eip155:84532",
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "amount": "1000000",
                "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
                "maxTimeoutSeconds": 3600,
                # No extra.name = Direct fallback
            },
        ],
    }
    await demo_scenario(seller_both, "Seller accepts BOTH (we pick Circle)")

    # Show summary
    print(f"\n{'=' * 70}")
    print("📋 SUMMARY: How Routing Works")
    print(f"{'=' * 70}")
    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                        UNIFIED pay() FLOW                            │
├─────────────────────────────────────────────────────────────────────┤
│  1. Request URL                                                     │
│     GET https://api.seller.com/data                                 │
│                                                                      │
│  2. Get 402 Response                                                 │
│     Parse: accepts[] array                                           │
│     └─> This tells us what SELLER accepts                           │
│                                                                      │
│  3. Match to Our Capabilities                                        │
│     ✅ We support: Circle Nanopayment, Direct x402                   │
│                                                                      │
│  4. Route Based on Match:                                            │
│     accepts[].extra.name = "GatewayWalletBatched"?                   │
│     ├─ YES → Circle Nanopayment (gasless!)                          │
│     └─ NO  → Direct x402 (may need gas)                             │
│                                                                      │
│  5. Execute & Return                                                │
└─────────────────────────────────────────────────────────────────────┘

THE KEY INSIGHT:
- We DON'T assume what sellers accept
- We READ it from the 402 response
- We MATCH to our capabilities
- We pick the BEST available option
""")


async def main():
    await demo_all_scenarios()


if __name__ == "__main__":
    asyncio.run(main())
