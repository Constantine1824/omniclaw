"""
Circle Gateway Facilitator for x402 Payments.

This module provides direct integration with Circle's Gateway API to verify
and settle x402 payments without using third-party facilitators.

Circle's Gateway provides:
- POST /gateway/v1/x402/verify - Verify payment payload
- POST /gateway/v1/x402/settle - Settle payment

Usage:
    from omniclaw.seller.facilitator import CircleGatewayFacilitator

    facilitator = CircleGatewayFacilitator(
        circle_api_key="YOUR_API_KEY",
        environment="testnet",  # or "mainnet"
    )

    # Verify payment before serving resource
    result = await facilitator.verify(payment_payload, payment_requirements)

    # Settle payment after serving resource
    result = await facilitator.settle(payment_payload, payment_requirements)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from omniclaw.core.exceptions import ProtocolError


GATEWAY_API_TESTNET = "https://gateway-api-testnet.circle.com"
GATEWAY_API_MAINNET = "https://gateway-api.circle.com"

SETTLE_ENDPOINT = "/v1/x402/settle"
VERIFY_ENDPOINT = "/v1/x402/verify"
SUPPORTED_ENDPOINT = "/v1/x402/supported"


@dataclass
class FacilitatorConfig:
    """Configuration for the Circle Gateway facilitator."""

    circle_api_key: str
    """Circle API key for authentication."""

    environment: str = "testnet"
    """Environment: 'testnet' or 'mainnet'."""

    timeout: float = 30.0
    """HTTP request timeout in seconds."""

    @property
    def base_url(self) -> str:
        """Get the API base URL based on environment."""
        if self.environment == "mainnet":
            return GATEWAY_API_MAINNET
        return GATEWAY_API_TESTNET

    @property
    def headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.circle_api_key}",
        }


@dataclass
class VerifyResult:
    """Result of payment verification."""

    is_valid: bool
    """Whether the payment payload passed all validation checks."""

    payer: str | None
    """The payer address extracted from the payment payload."""

    invalid_reason: str | None = None
    """Reason for validation failure (if invalid)."""


@dataclass
class SettleResult:
    """Result of payment settlement."""

    success: bool
    """Whether the settlement was successful."""

    transaction: str | None
    """Transaction UUID on success, empty string on failure."""

    network: str | None
    """CAIP-2 network identifier."""

    error_reason: str | None = None
    """Error code if settlement failed."""

    payer: str | None = None
    """The sender address."""


class CircleGatewayFacilitator:
    """
    Circle Gateway facilitator for x402 payments.

    This facilitator uses Circle's Gateway API directly to verify and settle
    payments. No third-party facilitator needed.

    Benefits:
    - Direct integration with Circle's infrastructure
    - No additional fees beyond Circle's standard pricing
    - Supports both verify (read-only) and settle (execution)
    - Works with EIP-3009 USDC payments
    """

    def __init__(
        self,
        circle_api_key: str | None = None,
        environment: str = "testnet",
        timeout: float = 30.0,
        base_url: str | None = None,
    ):
        """
        Initialize the Circle Gateway facilitator.

        Args:
            circle_api_key: Circle API key. Falls back to CIRCLE_API_KEY env var.
            environment: 'testnet' or 'mainnet'
            timeout: HTTP request timeout
            base_url: Custom base URL (overrides environment)
        """
        api_key = circle_api_key or os.environ.get("CIRCLE_API_KEY")
        if not api_key:
            raise ValueError("circle_api_key is required")

        self._config = FacilitatorConfig(
            circle_api_key=api_key,
            environment=environment,
            timeout=timeout,
        )

        if base_url:
            self._config.base_url = base_url

        self._client = httpx.AsyncClient(timeout=timeout)

    @property
    def base_url(self) -> str:
        """Get the API base URL."""
        return self._config.base_url

    @property
    def name(self) -> str:
        """Get the facilitator name."""
        return "circle"

    @property
    def environment(self) -> str:
        """Get the environment."""
        return self._config.environment

    async def verify(
        self,
        payment_payload: dict[str, Any],
        payment_requirements: dict[str, Any],
    ) -> VerifyResult:
        """
        Verify an x402 payment payload.

        This performs read-only validation:
        - Scheme validation
        - Network validation
        - Token validation
        - Signature validation
        - Temporal constraints (validBefore, validAfter)
        - Address and amount matching

        Note: This does NOT check balance or nonce - those happen at settle time.

        Args:
            payment_payload: The payment payload from the client's PAYMENT-SIGNATURE header
            payment_requirements: The payment requirements from the 402 response

        Returns:
            VerifyResult with validation status
        """
        url = f"{self._config.base_url}{VERIFY_ENDPOINT}"

        body = {
            "paymentPayload": payment_payload,
            "paymentRequirements": payment_requirements,
        }

        try:
            response = await self._client.post(
                url,
                json=body,
                headers=self._config.headers,
            )

            if response.status_code == 400:
                data = response.json()
                return VerifyResult(
                    is_valid=False,
                    payer=data.get("payer"),
                    invalid_reason=data.get("invalidReason", "invalid_request"),
                )

            response.raise_for_status()
            data = response.json()

            return VerifyResult(
                is_valid=data.get("isValid", False),
                payer=data.get("payer"),
                invalid_reason=data.get("invalidReason"),
            )

        except httpx.TimeoutException as e:
            raise ProtocolError(
                message=f"Facilitator verify timeout: {e}",
                protocol="x402",
                details={"url": url},
            ) from e
        except httpx.HTTPStatusError as e:
            raise ProtocolError(
                message=f"Facilitator verify failed: {e.response.status_code}",
                protocol="x402",
                details={"status": e.response.status_code, "body": e.response.text[:500]},
            ) from e
        except Exception as e:
            raise ProtocolError(
                message=f"Facilitator verify error: {e}",
                protocol="x402",
            ) from e

    async def settle(
        self,
        payment_payload: dict[str, Any],
        payment_requirements: dict[str, Any],
    ) -> SettleResult:
        """
        Settle an x402 payment.

        This submits the payment to Circle Gateway for settlement:
        - Verifies the authorization
        - Locks the sender's balance
        - Queues for batch processing

        Args:
            payment_payload: The payment payload from the client's PAYMENT-SIGNATURE header
            payment_requirements: The payment requirements from the 402 response

        Returns:
            SettleResult with settlement status
        """
        url = f"{self._config.base_url}{SETTLE_ENDPOINT}"

        body = {
            "paymentPayload": payment_payload,
            "paymentRequirements": payment_requirements,
        }

        try:
            response = await self._client.post(
                url,
                json=body,
                headers=self._config.headers,
            )

            if response.status_code == 400:
                data = response.json()
                return SettleResult(
                    success=False,
                    transaction=data.get("transaction", ""),
                    network=data.get("network"),
                    error_reason=data.get("errorReason", "invalid_request"),
                    payer=data.get("payer"),
                )

            response.raise_for_status()
            data = response.json()

            return SettleResult(
                success=data.get("success", False),
                transaction=data.get("transaction"),
                network=data.get("network"),
                error_reason=data.get("errorReason"),
                payer=data.get("payer"),
            )

        except httpx.TimeoutException as e:
            raise ProtocolError(
                message=f"Facilitator settle timeout: {e}",
                protocol="x402",
                details={"url": url},
            ) from e
        except httpx.HTTPStatusError as e:
            raise ProtocolError(
                message=f"Facilitator settle failed: {e.response.status_code}",
                protocol="x402",
                details={"status": e.response.status_code, "body": e.response.text[:500]},
            ) from e
        except Exception as e:
            raise ProtocolError(
                message=f"Facilitator settle error: {e}",
                protocol="x402",
            ) from e

    async def get_supported_networks(self) -> list[dict[str, Any]]:
        """
        Get supported payment schemes and networks.

        Returns:
            List of supported network configurations
        """
        url = f"{self._config.base_url}{SUPPORTED_ENDPOINT}"

        try:
            response = await self._client.get(url, headers=self._config.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("supportedNetworks", [])

        except Exception as e:
            raise ProtocolError(
                message=f"Failed to get supported networks: {e}",
                protocol="x402",
            ) from e

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "CircleGatewayFacilitator":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


def create_facilitator(
    circle_api_key: str | None = None,
    environment: str = "testnet",
    **kwargs,
) -> "CircleGatewayFacilitator":
    """
    Factory function to create a facilitator.

    Supports: circle, coinbase, ordern, rbx, thirdweb

    Args:
        circle_api_key: Circle API key (or use api_key=)
        environment: 'testnet' or 'mainnet'
        **kwargs: Additional arguments

    Returns:
        Facilitator instance
    """
    # Import here to avoid circular imports
    from omniclaw.seller.facilitator_generic import create_facilitator as _create

    # Support both circle_api_key and api_key
    api_key = circle_api_key or kwargs.pop("api_key", None)

    return _create(provider="circle", api_key=api_key, environment=environment, **kwargs)
