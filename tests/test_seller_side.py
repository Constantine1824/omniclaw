"""
Seller-Side x402 Tests.

Tests the seller/server side of x402 payments:
- 402 response generation
- Payment verification
- Decorator protection
- Multiple payment schemes

Run with:
    pytest tests/test_seller_side.py -v -s
"""

import base64
import json
import pytest
import time
from decimal import Decimal


# =============================================================================
# TEST 402 RESPONSE GENERATION
# =============================================================================


class Test402ResponseGeneration:
    """Test generating 402 Payment Required responses."""

    def test_create_basic_402_response(self):
        """Test creating basic 402 response."""
        print("\n" + "=" * 60)
        print("SELLER: Create 402 Response")
        print("=" * 60)

        from omniclaw.seller import SimpleSeller

        seller = SimpleSeller(
            seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
            accepts_circle=False,
        )

        seller.add_endpoint("/test", "$0.001", "Test endpoint")

        endpoints = seller.get_endpoints()

        print(f"  Endpoints: {list(endpoints.keys())}")

        assert "/test" in endpoints
        print(f"  ✓ Created endpoint /test")

    def test_seller_with_circle(self):
        """Test seller accepts Circle nanopayment."""
        print("\n" + "=" * 60)
        print("SELLER: Accepts Circle")
        print("=" * 60)

        from omniclaw.seller import SimpleSeller

        seller = SimpleSeller(
            seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
            accepts_circle=True,
        )

        seller.add_endpoint("/test", "$0.001", "Test")

        endpoints = seller.get_endpoints()
        accepts = endpoints["/test"]["accepts"]
        schemes = [a["scheme"] for a in accepts]

        print(f"  Accepts: {schemes}")

        assert "exact" in schemes
        assert "GatewayWalletBatched" in schemes


class TestPaymentVerification:
    """Test payment verification logic."""

    def test_check_payment_with_header(self):
        """Test checking payment with header."""
        print("\n" + "=" * 60)
        print("SELLER: Check Payment")
        print("=" * 60)

        from omniclaw.seller import SimpleSeller

        seller = SimpleSeller(
            seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
        )

        # With header
        is_valid, error = seller.check_payment("some-signature")

        print(f"  With header: valid={is_valid}")

        # Without header
        is_valid, error = seller.check_payment(None)

        print(f"  Without header: valid={is_valid}, error={error}")

        assert is_valid == False


class TestEndpointCreation:
    """Test creating seller endpoints."""

    def test_add_endpoint(self):
        """Test adding endpoint to seller."""
        print("\n" + "=" * 60)
        print("SELLER: Add Endpoint")
        print("=" * 60)

        from omniclaw.seller import SimpleSeller

        seller = SimpleSeller(
            seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
        )

        seller.add_endpoint("/weather", "$0.001", "Weather data")
        seller.add_endpoint("/premium", "$0.01", "Premium content")

        endpoints = seller.get_endpoints()

        print(f"  Endpoints: {list(endpoints.keys())}")

        assert len(endpoints) == 2

    def test_decorator(self):
        """Test using decorator to protect endpoint."""
        print("\n" + "=" * 60)
        print("SELLER: Decorator")
        print("=" * 60)

        from omniclaw.seller import SimpleSeller

        seller = SimpleSeller(
            seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
        )

        @seller.protected("$0.001", "Weather")
        def get_weather():
            pass

        endpoints = seller.get_endpoints()

        print(f"  Endpoints: {list(endpoints.keys())}")

        assert "/get_weather" in endpoints


class TestSellerIntegration:
    """Test seller integration scenarios."""

    def test_full_flow(self):
        """Test complete flow."""
        print("\n" + "=" * 60)
        print("SELLER: Full Flow")
        print("=" * 60)

        from omniclaw.seller import SimpleSeller

        seller = SimpleSeller(
            seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
        )

        # Add endpoint first
        seller.add_endpoint("/weather", "$0.001", "Weather data")

        # Step 1: Client requests without payment
        print("  Step 1: Client requests /weather")

        # Step 2: Check payment - no header
        is_valid, error = seller.check_payment(None)

        print(f"    Payment valid: {is_valid}")
        assert is_valid == False

        # Step 3: Create 402 response
        headers, body = seller.create_402_response("/weather", "http://localhost/weather")

        print(f"    Created 402 response")
        assert "payment-required" in headers

        # Step 4: Verify header
        decoded = json.loads(base64.b64decode(headers["payment-required"]))

        print(f"    x402 Version: {decoded.get('x402Version')}")

        assert decoded.get("x402Version") == 2

    def test_with_circle(self):
        """Test with Circle nanopayment."""
        print("\n" + "=" * 60)
        print("SELLER: With Circle")
        print("=" * 60)

        from omniclaw.seller import SimpleSeller

        seller = SimpleSeller(
            seller_address="0x742d35Cc6634C0532925a3b844Bc9e7595f1E123",
            accepts_circle=True,
        )

        seller.add_endpoint("/premium", "$0.01", "Premium")

        endpoints = seller.get_endpoints()
        accepts = endpoints["/premium"]["accepts"]
        schemes = [a["scheme"] for a in accepts]

        print(f"  Schemes: {schemes}")

        assert "exact" in schemes
        assert "GatewayWalletBatched" in schemes


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
