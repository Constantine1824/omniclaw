"""
OmniClaw Seller SDK.

x402 payment integration for sellers.

Usage:
    from omniclaw.seller import Seller, create_seller

    seller = create_seller(
        seller_address="0x742d...",
        name="Weather API",
    )

    seller.add_endpoint("/weather", "$0.001", "Current weather")
    seller.serve(port=4023)
"""

# Main Seller class
# Circle Gateway Facilitator
from omniclaw.seller.facilitator import (
    CircleGatewayFacilitator,
    SettleResult,
    VerifyResult,
)

# Multi-facilitator support (Coinbase, OrderN, RBX, Thirdweb)
from omniclaw.seller.facilitator_generic import (
    SUPPORTED_FACILITATORS,
    BaseFacilitator,
    CoinbaseFacilitator,
    OrderNFacilitator,
    RBXFacilitator,
    ThirdwebFacilitator,
    create_facilitator,
)
from omniclaw.seller.seller import (
    Endpoint,
    PaymentRecord,
    PaymentScheme,
    PaymentStatus,
    Seller,
    SellerConfig,
    create_seller,
)

__all__ = [
    # Main classes
    "Seller",
    "create_seller",
    # Types
    "PaymentScheme",
    "PaymentStatus",
    "PaymentRecord",
    "Endpoint",
    "SellerConfig",
    # Circle Gateway Facilitator
    "CircleGatewayFacilitator",
    "VerifyResult",
    "SettleResult",
    # Multi-facilitator
    "CoinbaseFacilitator",
    "OrderNFacilitator",
    "RBXFacilitator",
    "ThirdwebFacilitator",
    "BaseFacilitator",
    "create_facilitator",
    "SUPPORTED_FACILITATORS",
]
