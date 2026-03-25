"""
OmniClaw Seller SDK.

x402 payment integration for sellers.

Usage:
    from omniclaw.seller import create_seller

    seller = create_seller(
        seller_address="0x742d...",
        name="Weather API",
    )

    seller.add_endpoint("/weather", "$0.001", "Current weather")
    seller.serve(port=4023)
"""

# Main Seller class
from omniclaw.seller.seller import (
    Seller,
    create_seller,
    PaymentScheme,
    PaymentStatus,
    PaymentRecord,
    Endpoint,
    SellerConfig,
    SimpleSeller,
)

# Facilitators - Top 5 supported
from omniclaw.seller.facilitator import (
    CircleGatewayFacilitator,
    VerifyResult,
    SettleResult,
)

from omniclaw.seller.facilitator_generic import (
    BaseFacilitator,
    CoinbaseFacilitator,
    OrderNFacilitator,
    RBXFacilitator,
    ThirdwebFacilitator,
    create_facilitator,
    SUPPORTED_FACILITATORS,
)

__all__ = [
    # Main classes
    "Seller",
    "create_seller",
    "SimpleSeller",
    # Types
    "PaymentScheme",
    "PaymentStatus",
    "PaymentRecord",
    "Endpoint",
    "SellerConfig",
    # Facilitators
    "CircleGatewayFacilitator",
    "CoinbaseFacilitator",
    "OrderNFacilitator",
    "RBXFacilitator",
    "ThirdwebFacilitator",
    "BaseFacilitator",
    "create_facilitator",
    "SUPPORTED_FACILITATORS",
    # Results
    "VerifyResult",
    "SettleResult",
]
