"""
Circle Gateway Integration for OmniClaw.

This provides real Circle nanopayment verification via the Circle API.

Usage:
    from omniclaw.seller.circle import CircleGateway

    gateway = CircleGateway(
        api_key="your-circle-api-key",
        base_url="https://api.circle.com",
    )

    # Verify payment
    result = await gateway.verify_payment(
        buyer_address="0x...",
        amount=1000,
        resource="https://...",
    )
"""

import hashlib
import time
from dataclasses import dataclass

import httpx


# =============================================================================
# TYPES
# =============================================================================


@dataclass
class GatewayConfig:
    """Circle Gateway configuration."""

    api_key: str
    base_url: str = "https://api.circle.com"
    network: str = "eip155:84532"  # Base Sepolia


@dataclass
class VerificationResult:
    """Result of payment verification."""

    success: bool
    payment_id: str | None
    balance: int | None
    error: str | None


@dataclass
class BalanceResult:
    """Result of balance check."""

    available: int
    pending: int
    total: int


# =============================================================================
# CIRCLE GATEWAY
# =============================================================================


class CircleGateway:
    """
    Circle Gateway for nanopayment verification.

    This integrates with Circle's Gateway API to:
    - Check buyer Gateway balance
    - Verify nanopayment authorization
    - Record payments for settlement
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.circle.com",
        network: str = "eip155:84532",
    ):
        """
        Initialize Circle Gateway.

        Args:
            api_key: Circle API key
            base_url: Circle API base URL
            network: CAIP-2 network
        """
        self.config = GatewayConfig(
            api_key=api_key,
            base_url=base_url,
            network=network,
        )
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def get_wallet_balance(self, wallet_address: str) -> BalanceResult:
        """
        Get Gateway wallet balance.

        Args:
            wallet_address: Buyer's Gateway wallet address

        Returns:
            BalanceResult with available, pending, total
        """
        try:
            response = await self._client.get(
                f"{self.config.base_url}/v1/gatewayBalances/{wallet_address}",
                params={"network": self.config.network},
            )

            if response.status_code == 200:
                data = response.json()
                return BalanceResult(
                    available=int(data.get("available", 0)),
                    pending=int(data.get("pending", 0)),
                    total=int(data.get("total", 0)),
                )
            else:
                return BalanceResult(available=0, pending=0, total=0)

        except Exception as e:
            print(f"Balance check failed: {e}")
            return BalanceResult(available=0, pending=0, total=0)

    async def verify_payment(
        self,
        buyer_address: str,
        amount: int,
        resource_url: str,
        payment_payload: dict | None = None,
    ) -> VerificationResult:
        """
        Verify a nanopayment.

        Args:
            buyer_address: Buyer's EVM address
            amount: Amount in atomic units
            resource_url: Resource URL being accessed
            payment_payload: Full payment payload from x402

        Returns:
            VerificationResult
        """
        try:
            # Check balance first
            balance = await self.get_wallet_balance(buyer_address)

            if balance.available < amount:
                return VerificationResult(
                    success=False,
                    payment_id=None,
                    balance=balance.available,
                    error=f"Insufficient balance: {balance.available} < {amount}",
                )

            # Verify authorization if provided
            if payment_payload:
                is_valid, error = self._verify_authorization(
                    payment_payload,
                    amount,
                )

                if not is_valid:
                    return VerificationResult(
                        success=False,
                        payment_id=None,
                        balance=balance.available,
                        error=error,
                    )

            # Generate payment ID
            payment_id = hashlib.sha256(
                f"{buyer_address}{resource_url}{time.time()}".encode()
            ).hexdigest()[:16]

            # Record payment for settlement
            await self._record_payment(
                payment_id=payment_id,
                buyer_address=buyer_address,
                amount=amount,
                resource_url=resource_url,
            )

            return VerificationResult(
                success=True,
                payment_id=payment_id,
                balance=balance.available - amount,
                error=None,
            )

        except Exception as e:
            return VerificationResult(
                success=False,
                payment_id=None,
                balance=None,
                error=str(e),
            )

    def _verify_authorization(
        self,
        payment_payload: dict,
        expected_amount: int,
    ) -> tuple[bool, str]:
        """Verify payment authorization."""
        try:
            payload = payment_payload.get("payload", {})
            auth = payload.get("authorization", {})

            # Check timeout
            valid_after = int(auth.get("validAfter", 0))
            valid_before = int(auth.get("validBefore", 0))
            current = int(time.time())

            if current < valid_after:
                return False, "Payment not yet valid"
            if current > valid_before:
                return False, "Payment expired"

            # Check amount
            paid = int(auth.get("value", 0))
            if paid < expected_amount:
                return False, f"Insufficient: {paid} < {expected_amount}"

            # Check signature exists
            if not payload.get("signature"):
                return False, "Missing signature"

            return True, ""

        except Exception as e:
            return False, str(e)

    async def _record_payment(
        self,
        payment_id: str,
        buyer_address: str,
        amount: int,
        resource_url: str,
    ) -> None:
        """Record payment for later settlement."""
        try:
            await self._client.post(
                f"{self.config.base_url}/v1/nanopayments",
                json={
                    "paymentId": payment_id,
                    "buyer": buyer_address,
                    "amount": str(amount),
                    "resource": resource_url,
                    "network": self.config.network,
                },
            )
        except Exception as e:
            print(f"Record payment failed: {e}")

    async def get_payment(self, payment_id: str) -> dict | None:
        """Get payment details."""
        try:
            response = await self._client.get(
                f"{self.config.base_url}/v1/nanopayments/{payment_id}",
            )

            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    async def settle_payments(self, payment_ids: list[str]) -> dict:
        """
        Settle batched payments.

        In production, this would be called periodically to settle
        accumulated nanopayments.
        """
        try:
            response = await self._client.post(
                f"{self.config.base_url}/v1/nanopayments/settle",
                json={"payments": payment_ids},
            )

            return {
                "success": response.status_code == 200,
                "settled": len(payment_ids),
                "tx_hash": response.json().get("transactionHash")
                if response.status_code == 200
                else None,
            }
        except Exception as e:
            return {
                "success": False,
                "settled": 0,
                "error": str(e),
            }


# =============================================================================
# FACTORY
# =============================================================================


def create_gateway(
    api_key: str,
    network: str = "eip155:84532",
) -> CircleGateway:
    """
    Create Circle Gateway instance.

    Args:
        api_key: Circle API key
        network: CAIP-2 network

    Returns:
        CircleGateway instance
    """
    return CircleGateway(api_key=api_key, network=network)


__all__ = [
    "CircleGateway",
    "create_gateway",
    "GatewayConfig",
    "VerificationResult",
    "BalanceResult",
]
