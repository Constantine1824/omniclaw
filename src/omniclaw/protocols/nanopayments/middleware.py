"""
GatewayMiddleware: Seller-side x402 payment gate for FastAPI/Starlette.

The Python equivalent of Circle's createGatewayMiddleware().
Sellers use this to protect their endpoints with x402 payments.

Usage:
    @app.get("/premium")
    async def premium(payment=Depends(gateway.require("$0.001"))):
        return {"data": "paid content", "paid_by": payment.payer}

The 402 response structure (x402 v2):
    {
        "x402Version": 2,
        "accepts": [{
            "scheme": "exact",
            "network": "eip155:5042002",
            "asset": "0xUSDC",
            "amount": "1000",  # atomic units
            "maxTimeoutSeconds": 345600,
            "payTo": "0xSeller",
            "extra": {
                "name": "GatewayWalletBatched",
                "version": "1",
                "verifyingContract": "0xGateway"
            }
        }]
    }
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from omniclaw.protocols.nanopayments import (
    MAX_TIMEOUT_SECONDS,
    X402_VERSION,
)
from omniclaw.protocols.nanopayments.client import NanopaymentClient
from omniclaw.protocols.nanopayments.exceptions import (
    InvalidPriceError,
    NoNetworksAvailableError,
)
from omniclaw.protocols.nanopayments.types import (
    PaymentInfo,
    PaymentPayload,
    PaymentRequirements,
    SupportedKind,
)

# =============================================================================
# SETTLEMENT RESPONSE (x402 v2 PAYMENT-RESPONSE header format)
# =============================================================================


@dataclass
class SettlementResponse:
    """
    x402 v2 SettlementResponse format for PAYMENT-RESPONSE header.

    Per x402 v2 spec, this header is required on ALL responses (success AND failure)
    from paid endpoints. The header is base64-encoded JSON with:
        {success, transaction, network, payer, errorReason?}
    """

    success: bool
    transaction: str
    network: str
    payer: str
    errorReason: str | None = None

    def to_base64_header(self) -> str:
        """Encode as base64 for the PAYMENT-RESPONSE header."""
        return base64.b64encode(json.dumps(self.to_dict()).encode()).decode()

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        d = {
            "success": self.success,
            "transaction": self.transaction,
            "network": self.network,
            "payer": self.payer,
        }
        if self.errorReason:
            d["errorReason"] = self.errorReason
        return d


# =============================================================================
# PRICE PARSING
# =============================================================================


def parse_price(price_str: str) -> int:
    """
    Parse a price string to USDC atomic units (6 decimals).

    Accepts:
        "$0.001" -> 1000
        "0.001"  -> 1000
        "$1"     -> 1000000
        "1000000" -> 1000000 (atomic)
        "1000"   -> 1000000 (dollars)

    Returns:
        Amount in USDC atomic units (int).

    Raises:
        InvalidPriceError: If the price string cannot be parsed.
    """
    if not price_str:
        raise InvalidPriceError(price=price_str)

    original = price_str.strip()

    # Remove dollar sign
    numeric = original[1:].strip() if original.startswith("$") else original

    # Check if it's a decimal (has a decimal point)
    if "." in numeric:
        # It's a dollar amount with decimals — convert to atomic
        try:
            from decimal import Decimal, InvalidOperation

            value = Decimal(numeric)
            return int(value * Decimal(1_000_000))
        except (ValueError, InvalidOperation, ArithmeticError):
            raise InvalidPriceError(price=price_str)

    # It's a plain integer — treat as atomic units if >= 1M,
    # otherwise as whole dollars multiplied by 1M
    try:
        value = int(numeric)
    except ValueError:
        raise InvalidPriceError(price=price_str)

    if value >= 1_000_000:
        return value
    return value * 1_000_000


# =============================================================================
# GATEWAY MIDDLEWARE
# =============================================================================


class GatewayMiddleware:
    """
    FastAPI/Starlette middleware for x402 payment gating.

    Sellers use this to protect their endpoints.
    When a buyer requests without payment: returns 402.
    When a buyer requests with valid payment: settles and serves content.

    Args:
        seller_address: EOA address that receives payments.
        nanopayment_client: NanopaymentClient for fetching supported networks.
        supported_kinds: Pre-fetched supported payment kinds. If None, fetches automatically.
        auto_fetch_networks: If True, fetches networks on first request if not provided.
    """

    def __init__(
        self,
        seller_address: str,
        nanopayment_client: NanopaymentClient,
        supported_kinds: list[SupportedKind] | None = None,
        auto_fetch_networks: bool = True,
    ) -> None:
        # Validate seller_address is a valid EVM address
        if not seller_address:
            raise ValueError("seller_address is required")
        if not seller_address.startswith("0x"):
            raise ValueError("seller_address must be an EVM address (starts with 0x)")
        if len(seller_address) != 42:
            raise ValueError(
                f"seller_address must be 42 characters (42 hex chars), got {len(seller_address)}"
            )
        # Validate hex characters
        try:
            int(seller_address[2:], 16)
        except ValueError:
            raise ValueError("seller_address contains invalid hex characters")

        self._seller_address = seller_address.lower()  # Normalize to lowercase
        self._client = nanopayment_client
        self._supported_kinds: list[SupportedKind] | None = supported_kinds
        self._auto_fetch = auto_fetch_networks

    # -------------------------------------------------------------------------
    # Supported networks management
    # -------------------------------------------------------------------------

    async def _get_supported_kinds(self) -> list[SupportedKind]:
        """Get supported payment kinds, fetching if needed."""
        if self._supported_kinds is not None:
            return self._supported_kinds
        self._supported_kinds = await self._client.get_supported(force_refresh=True)
        if not self._supported_kinds:
            raise NoNetworksAvailableError()
        return self._supported_kinds

    # -------------------------------------------------------------------------
    # Accepts array builder
    # -------------------------------------------------------------------------

    def _build_accepts_array(
        self,
        price_atomic: int,
        kinds: list[SupportedKind] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Build the accepts array for a 402 response.

        Args:
            price_atomic: Price in USDC atomic units.
            kinds: Optional pre-fetched kinds. If None, fetches synchronously.

        For each supported network, creates an entry with:
        - scheme: "exact"
        - network: CAIP-2
        - asset: USDC address
        - amount: price in atomic units
        - maxTimeoutSeconds: 345600 (4 days)
        - payTo: seller address
        - extra: GatewayWalletBatched metadata
        """
        if kinds is None:
            kinds = self._supported_kinds
        if kinds is None:
            return []  # No networks available

        accepts = []
        for kind in kinds:
            verifying_contract = kind.verifying_contract
            usdc_address = kind.usdc_address

            if not verifying_contract or not usdc_address:
                continue

            accepts.append(
                {
                    "scheme": "exact",
                    "network": kind.network,
                    "asset": usdc_address,
                    "amount": str(price_atomic),
                    "maxTimeoutSeconds": MAX_TIMEOUT_SECONDS,
                    "payTo": self._seller_address,
                    "extra": {
                        "name": "GatewayWalletBatched",
                        "version": "1",
                        "verifyingContract": verifying_contract,
                    },
                }
            )

        return accepts

    # -------------------------------------------------------------------------
    # 402 response builder
    # -------------------------------------------------------------------------

    def _build_402_response(
        self,
        price_usd: str,
    ) -> dict[str, Any]:
        """
        Build the x402 v2 402 response body.

        Returns:
            Dict with x402Version and accepts array.
        """
        price_atomic = parse_price(price_usd)
        accepts = self._build_accepts_array(price_atomic)

        return {
            "x402Version": X402_VERSION,
            "accepts": accepts,
        }

    # -------------------------------------------------------------------------
    # Payment handling
    # -------------------------------------------------------------------------

    def _parse_payment_signature(
        self,
        header_value: str,
    ) -> PaymentPayload:
        """
        Parse and validate the PAYMENT-SIGNATURE header.

        Args:
            header_value: The base64-encoded JSON PaymentPayload.

        Returns:
            Parsed PaymentPayload.

        Raises:
            ValueError: If parsing fails.
        """
        try:
            decoded = base64.b64decode(header_value)
            data = json.loads(decoded)
            return PaymentPayload.from_dict(data)
        except Exception as exc:
            raise ValueError(f"Failed to parse PAYMENT-SIGNATURE: {exc}") from exc

    def _encode_requirements(
        self,
        body: dict[str, Any],
    ) -> str:
        """Encode requirements dict as base64 for the PAYMENT-REQUIRED header."""
        return base64.b64encode(json.dumps(body).encode()).decode()

    # -------------------------------------------------------------------------
    # Public handler
    # -------------------------------------------------------------------------

    async def handle(
        self,
        request_headers: dict[str, str],
        price_usd: str,
    ) -> PaymentInfo:
        """
        Handle payment for a request.

        Checks for PAYMENT-SIGNATURE header. If present, verifies and settles.
        If absent, raises HTTPException(402).

        Args:
            request_headers: Request headers dict.
            price_usd: Price in USD string (e.g. "$0.001").

        Returns:
            PaymentInfo if payment verified and settled.

        Raises:
            HTTPException(402): If payment is missing or invalid.
                The detail dict contains the requirements for payment.
        """
        # Check for PAYMENT-SIGNATURE header
        sig_header = request_headers.get("payment-signature") or request_headers.get(
            "PAYMENT-SIGNATURE"
        )

        if not sig_header:
            # Build 402 response
            body = self._build_402_response(price_usd)
            header_value = self._encode_requirements(body)
            raise PaymentRequiredHTTPException(
                status_code=402,
                detail=body,
                headers={"PAYMENT-REQUIRED": header_value},
            )

        # Parse and verify payment
        try:
            payload = self._parse_payment_signature(sig_header)
        except ValueError as exc:
            raise PaymentRequiredHTTPException(
                status_code=402,
                detail={"error": str(exc)},
                headers={},
            )

        # Build requirements from the payment payload
        # We need to match the requirements that the buyer used
        gateway_kind = None
        if payload.payload.authorization:
            auth = payload.payload.authorization
            expected_amount = str(parse_price(price_usd))
            if str(auth.value) != expected_amount:
                raise PaymentRequiredHTTPException(
                    status_code=402,
                    detail={
                        "error": (
                            f"Amount mismatch. Expected {expected_amount} atomic units, "
                            f"got {auth.value}."
                        )
                    },
                    headers={},
                )
            # Build requirements from payload
            from omniclaw.protocols.nanopayments.types import (
                PaymentRequirementsExtra,
                PaymentRequirementsKind,
            )

            # Get supported kinds and find matching network
            supported_kinds = await self._get_supported_kinds()

            # Find the kind matching the payment's network
            matching_kind = None
            verifying_contract = None
            usdc_address = None

            for kind in supported_kinds:
                if kind.network == payload.network:
                    matching_kind = kind
                    verifying_contract = kind.verifying_contract
                    usdc_address = kind.usdc_address
                    break

            # If no supported kinds at all, we can't process this payment
            if not supported_kinds:
                raise PaymentRequiredHTTPException(
                    status_code=502,
                    detail={"error": "No supported payment networks available"},
                    headers={},
                )

            if matching_kind is None:
                raise PaymentRequiredHTTPException(
                    status_code=402,
                    detail={"error": f"Unsupported payment network: {payload.network}"},
                    headers={},
                )

            if not verifying_contract or not usdc_address:
                raise PaymentRequiredHTTPException(
                    status_code=502,
                    detail={"error": f"Missing contract addresses for network {payload.network}"},
                    headers={},
                )

            gateway_kind = PaymentRequirementsKind(
                scheme="exact",
                network=payload.network,
                asset=usdc_address,  # Use actual USDC address from supported kinds
                amount=auth.value,
                max_timeout_seconds=MAX_TIMEOUT_SECONDS,
                pay_to=self._seller_address,
                extra=PaymentRequirementsExtra(
                    name="GatewayWalletBatched",
                    version="1",
                    verifying_contract=verifying_contract,
                ),
            )

        if gateway_kind is None:
            raise PaymentRequiredHTTPException(
                status_code=402,
                detail={"error": "Missing authorization in PAYMENT-SIGNATURE payload"},
                headers={},
            )

        requirements = PaymentRequirements(
            x402_version=X402_VERSION,
            accepts=(gateway_kind,) if gateway_kind else (),
        )

        # Settle the payment
        try:
            settle_resp = await self._client.settle(
                payload=payload,
                requirements=requirements,
            )
        except Exception as exc:
            raise PaymentRequiredHTTPException(
                status_code=402,
                detail={"error": f"Settlement failed: {exc}"},
                headers={},
            )

        return PaymentInfo(
            verified=settle_resp.success,
            payer=settle_resp.payer or payload.payload.authorization.from_address,
            amount=payload.payload.authorization.value,
            network=payload.network,
            transaction=settle_resp.transaction,
        )

    # -------------------------------------------------------------------------
    # FastAPI dependency
    # -------------------------------------------------------------------------

    def require(self, price: str):
        """
        Returns a FastAPI dependency for route protection.

        Usage:
            @app.get("/premium")
            async def premium(payment=Depends(gateway.require("$0.001"))):
                return {"data": "paid content", "paid_by": payment.payer}

        Note:
            This requires a Request object to be in scope. Use the `handle`
            method directly for more control.

        IMPORTANT: Per x402 v2 spec, you MUST include the PAYMENT-RESPONSE header
        in your response. Use build_payment_response_header() or payment_response_headers()
        to get the header value.
        """
        from fastapi import HTTPException, Request

        async def dependency(request: Request) -> PaymentInfo:
            headers = dict(request.headers)
            try:
                return await self.handle(headers, price)
            except PaymentRequiredHTTPException as exc:
                raise HTTPException(
                    status_code=exc.status_code,
                    detail=exc.detail,
                    headers=exc.headers,
                )

        return dependency

    # -------------------------------------------------------------------------
    # PAYMENT-RESPONSE header helpers (x402 v2 spec)
    # -------------------------------------------------------------------------

    def build_payment_response_header(self, payment_info: PaymentInfo) -> str:
        """
        Build PAYMENT-RESPONSE header value from PaymentInfo.

        Per x402 v2 spec, this header is required on ALL responses (success AND failure)
        from paid endpoints. The header is base64-encoded JSON.

        Args:
            payment_info: The PaymentInfo returned by handle() or require()

        Returns:
            Base64-encoded JSON string for the PAYMENT-RESPONSE header.
        """
        return SettlementResponse(
            success=payment_info.verified,
            transaction=payment_info.transaction or "",
            network=payment_info.network,
            payer=payment_info.payer,
        ).to_base64_header()

    def payment_response_headers(self, payment_info: PaymentInfo) -> dict[str, str]:
        """
        Get headers dict including PAYMENT-RESPONSE for route handlers.

        Convenience method that returns a dict with the PAYMENT-RESPONSE header
        already set. Merge this with your response headers.

        Usage:
            @app.get("/premium")
            async def premium(payment=Depends(gateway.require("$0.001"))):
                return JSONResponse(
                    {"data": "premium data"},
                    headers=gateway.payment_response_headers(payment)
                )

        Args:
            payment_info: The PaymentInfo returned by handle() or require()

        Returns:
            Dict with "PAYMENT-RESPONSE" key.
        """
        return {"PAYMENT-RESPONSE": self.build_payment_response_header(payment_info)}


# =============================================================================
# HTTP EXCEPTION HELPER
# =============================================================================


class PaymentRequiredHTTPException(Exception):
    """
    Raised internally to trigger a 402 response.

    Not a real HTTPException — caught by the FastAPI dependency wrapper.
    """

    def __init__(
        self,
        status_code: int,
        detail: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
        super().__init__(str(detail))
