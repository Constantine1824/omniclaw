"""
Simple Seller Agent for x402.

This is a simple implementation that generates 402 responses manually.
For official SDK integration, see create_fastapi_seller().

Usage:
    from omniclaw.seller import SimpleSeller

    seller = SimpleSeller(
        seller_address="0x742d...",
        accepts_circle=True,
    )

    @seller.protected("$0.001")
    async def get_data(request):
        return {"data": "value"}
"""

import base64
import json
from typing import Callable, Optional


class SimpleSeller:
    """
    Simple seller that generates 402 responses manually.

    This is a standalone implementation that doesn't require
    the official x402 SDK. For official SDK, use create_fastapi_seller().
    """

    def __init__(
        self,
        seller_address: str,
        accepts_circle: bool = True,
    ):
        """
        Initialize seller.

        Args:
            seller_address: EVM address that receives payments
            accepts_circle: Whether to accept Circle nanopayments
        """
        self.seller_address = seller_address
        self.accepts_circle = accepts_circle
        self._endpoints: dict[str, dict] = {}

    def add_endpoint(
        self,
        path: str,
        price: str,
        description: Optional[str] = None,
        method: str = "GET",
    ):
        """
        Add a protected endpoint.

        Args:
            path: Route path (e.g., "/weather")
            price: Price in USD format (e.g., "$0.001")
            description: Description of the resource
            method: HTTP method
        """
        # Parse price: "$0.001" -> 1000 atomic
        price_cents = int(price.replace("$", "").replace(".", ""))
        amount = price_cents * 100

        accepts = [
            {
                "scheme": "exact",
                "network": "eip155:84532",
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "amount": str(amount),
                "payTo": self.seller_address,
                "maxTimeoutSeconds": 300,
                "extra": {"name": "USDC", "version": "2"},
            }
        ]

        if self.accepts_circle:
            accepts.append(
                {
                    "scheme": "GatewayWalletBatched",
                    "network": "eip155:84532",
                    "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                    "amount": str(amount),
                    "payTo": self.seller_address,
                    "maxTimeoutSeconds": 300,
                    "extra": {
                        "name": "USDC",
                        "version": "2",
                        "verifyingContract": "0x1234567890abcdef",
                    },
                }
            )

        self._endpoints[path] = {
            "accepts": accepts,
            "description": description or f"Access to {path}",
            "price": price,
            "method": method,
        }

    def protected(
        self,
        price: str,
        description: Optional[str] = None,
    ) -> Callable:
        """
        Decorator to protect an endpoint.

        Usage:
            @seller.protected("$0.001", "Weather data")
            async def weather(request):
                return {"temp": 72}

        Args:
            price: Price in USD format
            description: Description

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            path = f"/{func.__name__}"
            self.add_endpoint(path, price, description)
            return func

        return decorator

    def check_payment(self, payment_header: Optional[str]) -> tuple[bool, str]:
        """
        Check if payment is valid.

        Args:
            payment_header: The PAYMENT-SIGNATURE header value

        Returns:
            (is_valid, error_message)
        """
        if not payment_header:
            return False, "No payment provided"

        # In production, verify with facilitator
        # For now, just check header exists
        return True, ""

    def create_402_response(self, path: str, url: str) -> tuple[dict, str]:
        """
        Create 402 response for a path.

        Args:
            path: The endpoint path
            url: The full URL

        Returns:
            (headers, body)
        """
        endpoint = self._endpoints.get(path)

        if not endpoint:
            return {}, "Endpoint not found"

        payment_required = {
            "x402Version": 2,
            "error": "Payment required",
            "resource": {
                "url": url,
                "description": endpoint["description"],
                "mimeType": "application/json",
            },
            "accepts": endpoint["accepts"],
        }

        header = base64.b64encode(json.dumps(payment_required).encode()).decode()

        return {"payment-required": header}, json.dumps({"error": "Payment required"})

    def get_endpoints(self) -> dict:
        """Get all configured endpoints."""
        return self._endpoints


# =============================================================================
# FASTAPI INTEGRATION
# =============================================================================


def create_fastapi_seller(
    seller_address: str,
    facilitator_url: str = "https://x402.org/facilitator",
):
    """
    Create FastAPI seller with official x402 SDK.

    Args:
        seller_address: EVM payment address
        facilitator_url: Facilitator URL

    Returns:
        tuple: (seller, app)

    Usage:
        seller, app = create_fastapi_seller(
            seller_address="0x742d..."
        )

        @app.get("/weather")
        @seller.protected("$0.001", "Weather")
        async def weather():
            return {"temp": 72}
    """
    try:
        from fastapi import FastAPI
        import uvicorn  # noqa: F401
    except ImportError:
        print("FastAPI required: pip install fastapi uvicorn")
        return None, None

    # Simple seller for now
    seller = SimpleSeller(
        seller_address=seller_address,
        accepts_circle=True,
    )

    # Create app
    app = FastAPI(title="x402 Seller API")

    @app.get("/health")
    async def health():
        return {"status": "ok", "seller": seller_address[:20] + "..."}

    return seller, app


def run_server(
    seller_address: str,
    port: int = 4023,
):
    """
    Run standalone x402 seller server.

    Args:
        seller_address: EVM payment address
        port: Server port
    """
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        import uvicorn  # noqa: F401
    except ImportError:
        print("FastAPI required: pip install fastapi uvicorn")
        return

    # Create seller
    seller = SimpleSeller(
        seller_address=seller_address,
        accepts_circle=True,
    )

    # Add endpoints
    seller.add_endpoint("/weather", "$0.001", "Weather report")
    seller.add_endpoint("/premium", "$0.01", "Premium content")
    seller.add_endpoint("/api/data", "$0.05", "API access")

    # Create app
    app = FastAPI(title="x402 Seller Server")

    @app.get("/health")
    async def health():
        return {"status": "ok", "seller": seller_address[:20] + "..."}

    @app.get("/weather")
    async def weather(request: Request):
        payment = request.headers.get("payment-signature")
        is_valid, error = seller.check_payment(payment)

        if not is_valid:
            headers, body = seller.create_402_response("/weather", str(request.url))
            return JSONResponse(
                status_code=402,
                content=json.loads(body),
                headers=headers,
            )

        return {"temp": 72, "condition": "sunny"}

    @app.get("/premium")
    async def premium(request: Request):
        payment = request.headers.get("payment-signature")
        is_valid, error = seller.check_payment(payment)

        if not is_valid:
            headers, body = seller.create_402_response("/premium", str(request.url))
            return JSONResponse(
                status_code=402,
                content=json.loads(body),
                headers=headers,
            )

        return {"secret": "premium data!", "level": "pro"}

    print(f"Starting x402 seller on port {port}")
    print(f"Seller: {seller_address}")
    print("Endpoints:")
    for path, config in seller.get_endpoints().items():
        print(f"  {path}: {config['price']}")

    uvicorn.run(app, host="0.0.0.0", port=port)


# Alias for backwards compatibility
SellerAgent = SimpleSeller
