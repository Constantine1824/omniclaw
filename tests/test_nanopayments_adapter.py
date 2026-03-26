"""
Tests for NanopaymentAdapter (Phase 6: buyer-side execution engine).

Tests verify:
- x402 URL payment flow with GatewayWalletBatched
- Graceful fallback when GatewayWalletBatched not supported
- Direct address payment
- Error handling
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omniclaw.protocols.nanopayments import NanopaymentAdapter
from omniclaw.protocols.nanopayments.client import NanopaymentClient
from omniclaw.protocols.nanopayments.exceptions import (
    GatewayAPIError,
    UnsupportedSchemeError,
)
from omniclaw.protocols.nanopayments.types import (
    EIP3009Authorization,
    PaymentPayload,
    PaymentPayloadInner,
    PaymentRequirementsExtra,
    PaymentRequirementsKind,
)
from omniclaw.protocols.nanopayments.vault import NanoKeyVault


# =============================================================================
# TEST HELPERS
# =============================================================================


def _make_requirements_dict() -> dict:
    """Build a valid 402 response requirements dict."""
    return {
        "x402Version": 2,
        "accepts": [
            {
                "scheme": "exact",
                "network": "eip155:5042002",
                "asset": "0xUsdcArcTestnet",
                "amount": "1000000",
                "maxTimeoutSeconds": 345600,
                "payTo": "0x" + "b" * 40,
                "extra": {
                    "name": "GatewayWalletBatched",
                    "version": "1",
                    "verifyingContract": "0x" + "c" * 40,
                },
            },
        ],
    }


def _make_payload_dict() -> dict:
    """Build a valid PaymentPayload dict."""
    return {
        "x402Version": 2,
        "scheme": "exact",
        "network": "eip155:5042002",
        "payload": {
            "signature": "0x" + "d" * 130,
            "authorization": {
                "from": "0x" + "a" * 40,
                "to": "0x" + "b" * 40,
                "value": "1000000",
                "validAfter": "0",
                "validBefore": "9999999999",
                "nonce": "0x" + "c" * 64,
            },
        },
    }


def _mock_http(free: bool = False, status: int = 402) -> MagicMock:
    """Mock httpx.AsyncClient."""
    mock = AsyncMock()
    resp = MagicMock()
    resp.status_code = 200 if free else status
    resp.text = '{"data": "resource data"}'
    resp.headers = {}

    if not free and status == 402:
        req_dict = _make_requirements_dict()
        import base64

        resp.headers = {
            "payment-required": base64.b64encode(json.dumps(req_dict).encode()).decode()
        }

    mock.request.return_value = resp
    return mock


def _mock_vault(
    address: str = "0x" + "a" * 40,
    payload: PaymentPayload | None = None,
) -> MagicMock:
    """Mock NanoKeyVault."""
    mock = MagicMock(spec=NanoKeyVault)
    mock.get_address = AsyncMock(return_value=address)
    if payload is None:
        authorization = EIP3009Authorization.create(
            from_address=address,
            to="0x" + "b" * 40,
            value="1000000",
            valid_before=9999999999,
            nonce="0x" + "c" * 64,
        )
        payload = PaymentPayload(
            x402_version=2,
            scheme="exact",
            network="eip155:5042002",
            payload=PaymentPayloadInner(
                signature="0x" + "d" * 130,
                authorization=authorization,
            ),
        )
    mock.sign = AsyncMock(return_value=payload)
    mock.get_balance = AsyncMock(
        return_value=MagicMock(
            total=5_000_000,
            available=5_000_000,
            formatted_total="5.000000 USDC",
            formatted_available="5.000000 USDC",
            available_decimal="5.000000",
        )
    )
    return mock


def _mock_client() -> MagicMock:
    """Mock NanopaymentClient."""
    mock = MagicMock(spec=NanopaymentClient)
    mock.get_verifying_contract = AsyncMock(return_value="0x" + "c" * 40)
    mock.get_usdc_address = AsyncMock(return_value="0xUsdcArcTestnet")
    mock.settle = AsyncMock(
        return_value=MagicMock(
            success=True,
            transaction="batch-ref-123",
            payer="0x" + "a" * 40,
        )
    )
    return mock


# =============================================================================
# PAY_X402_URL TESTS
# =============================================================================


class TestPayX402Url:
    @pytest.mark.asyncio
    async def test_free_resource_returns_non_nanopayment(self):
        """Non-402 response means free resource."""
        mock_http = _mock_http(free=True)
        adapter = NanopaymentAdapter(
            vault=_mock_vault(),
            nanopayment_client=_mock_client(),
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        result = await adapter.pay_x402_url("https://api.example.com/data")

        assert result.success is True
        assert result.is_nanopayment is False
        assert result.amount_usdc == "0"

    @pytest.mark.asyncio
    async def test_402_with_gateway_batched_succeeds(self):
        """Full flow: 402 response -> sign -> retry -> settle."""
        mock_http = _mock_http(free=False, status=402)
        mock_vault = _mock_vault()
        mock_client = _mock_client()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        result = await adapter.pay_x402_url("https://api.example.com/data")

        # Sign was called
        mock_vault.sign.assert_called_once()
        # Settle was called
        mock_client.settle.assert_called_once()
        # Result is nanopayment
        assert result.is_nanopayment is True
        assert result.success is True
        assert result.transaction == "batch-ref-123"

    @pytest.mark.asyncio
    async def test_402_without_gateway_batched_raises(self):
        """No GatewayWalletBatched scheme: raise for router fallback."""
        import base64

        req_dict = {
            "x402Version": 2,
            "accepts": [
                {
                    "scheme": "exact",
                    "network": "eip155:5042002",
                    "asset": "0xUsdc",
                    "amount": "1000000",
                    "maxTimeoutSeconds": 345600,
                    "payTo": "0x" + "b" * 40,
                    "extra": {
                        "name": "OtherScheme",
                        "version": "1",
                        "verifyingContract": "0x" + "c" * 40,
                    },
                },
            ],
        }

        mock_http = AsyncMock()
        resp = MagicMock()
        resp.status_code = 402
        resp.headers = {
            "payment-required": base64.b64encode(json.dumps(req_dict).encode()).decode()
        }
        mock_http.request.return_value = resp

        adapter = NanopaymentAdapter(
            vault=_mock_vault(),
            nanopayment_client=_mock_client(),
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        with pytest.raises(UnsupportedSchemeError):
            await adapter.pay_x402_url("https://api.example.com/data")

    @pytest.mark.asyncio
    async def test_402_missing_payment_required_header_raises(self):
        """402 response without PAYMENT-REQUIRED header."""
        mock_http = AsyncMock()
        resp = MagicMock()
        resp.status_code = 402
        resp.headers = {}
        resp.text = "{}"
        mock_http.request.return_value = resp

        adapter = NanopaymentAdapter(
            vault=_mock_vault(),
            nanopayment_client=_mock_client(),
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        with pytest.raises(GatewayAPIError) as exc_info:
            await adapter.pay_x402_url("https://api.example.com/data")
        assert "PAYMENT-REQUIRED" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_402_bad_base64_raises(self):
        """Invalid base64 in PAYMENT-REQUIRED header."""
        mock_http = AsyncMock()
        resp = MagicMock()
        resp.status_code = 402
        resp.headers = {"payment-required": "not-valid-base64!!!"}
        resp.text = "{}"
        mock_http.request.return_value = resp

        adapter = NanopaymentAdapter(
            vault=_mock_vault(),
            nanopayment_client=_mock_client(),
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        with pytest.raises(GatewayAPIError) as exc_info:
            await adapter.pay_x402_url("https://api.example.com/data")
        assert "parse" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_auto_topup_skipped_when_disabled(self):
        """When auto_topup_enabled=False, balance is not checked."""
        mock_http = _mock_http(free=False, status=402)
        mock_vault = _mock_vault()
        mock_client = _mock_client()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        await adapter.pay_x402_url("https://api.example.com/data")

        # get_balance should NOT be called (auto_topup disabled)
        mock_vault.get_balance.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_topup_skipped_when_balance_sufficient(self):
        """High balance: no topup needed."""
        mock_http = _mock_http(free=False, status=402)
        mock_vault = _mock_vault()
        mock_vault.get_balance = AsyncMock(
            return_value=MagicMock(
                total=5_000_000,
                available=5_000_000,
                formatted_total="5.000000 USDC",
                formatted_available="5.000000 USDC",
                available_decimal="5.000000",  # Above $1.00 threshold
            )
        )
        mock_client = _mock_client()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=mock_http,
            auto_topup_enabled=True,
        )

        await adapter.pay_x402_url("https://api.example.com/data")

        # sign was still called (balance check passed)
        mock_vault.sign.assert_called_once()


# =============================================================================
# PAY_DIRECT TESTS
# =============================================================================


class TestPayDirect:
    @pytest.mark.asyncio
    async def test_pay_direct_succeeds(self):
        """Direct address payment: build requirements, sign, settle."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
        )

        result = await adapter.pay_direct(
            seller_address="0x" + "b" * 40,
            amount_usdc="0.001",
            network="eip155:5042002",
        )

        assert result.success is True
        assert result.is_nanopayment is True
        assert result.amount_usdc == "0.001"
        assert result.amount_atomic == "1000"
        assert result.transaction == "batch-ref-123"
        mock_vault.sign.assert_called_once()
        mock_client.settle.assert_called_once()

    @pytest.mark.asyncio
    async def test_pay_direct_converts_amount_to_atomic(self):
        """Verify $0.001 = 1000 atomic units."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
        )

        await adapter.pay_direct(
            seller_address="0x" + "b" * 40,
            amount_usdc="0.001",
            network="eip155:5042002",
        )

        # Check the requirements passed to sign
        sign_call = mock_vault.sign.call_args
        assert sign_call.kwargs["amount_atomic"] == 1000

    @pytest.mark.asyncio
    async def test_pay_direct_gets_contract_addresses(self):
        """pay_direct fetches verifying_contract and usdc_address."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
        )

        await adapter.pay_direct(
            seller_address="0x" + "b" * 40,
            amount_usdc="0.5",
            network="eip155:5042002",
        )

        mock_client.get_verifying_contract.assert_called_once_with("eip155:5042002")
        mock_client.get_usdc_address.assert_called_once_with("eip155:5042002")


# =============================================================================
# AUTO TOPUP TESTS
# =============================================================================


class TestAutoTopup:
    @pytest.mark.asyncio
    async def test_check_and_topup_returns_false_when_balance_sufficient(self):
        """Balance above threshold: no action."""
        mock_vault = _mock_vault()
        mock_vault.get_balance = AsyncMock(
            return_value=MagicMock(
                available_decimal="10.000000",
            )
        )

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=True,
        )

        result = await adapter._check_and_topup()

        assert result is False

    @pytest.mark.asyncio
    async def test_configure_auto_topup(self):
        """configure_auto_topup updates settings."""
        mock_vault = _mock_vault()
        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=True,
        )

        adapter.configure_auto_topup(
            enabled=False,
            threshold="5.00",
            amount="20.00",
        )

        assert adapter._auto_topup is False
        assert adapter._topup_threshold == "5.00"
        assert adapter._topup_amount == "20.00"
