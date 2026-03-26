"""
Tests for NanopaymentClient (Phase 3: Circle Gateway REST API client).

Phase 3: NanopaymentClient

All tests use mocked HTTP responses to avoid network calls.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

import pytest
from eth_account import Account

from omniclaw.protocols.nanopayments import (
    NanopaymentClient,
    NanopaymentHTTPClient,
)
from omniclaw.protocols.nanopayments.exceptions import (
    GatewayAPIError,
    GatewayConnectionError,
    GatewayTimeoutError,
    InsufficientBalanceError,
    InsufficientGatewayBalanceError,
    NonceReusedError,
    SettlementError,
    UnsupportedNetworkError,
)
from omniclaw.protocols.nanopayments.signing import generate_eoa_keypair
from omniclaw.protocols.nanopayments.types import (
    EIP3009Authorization,
    PaymentPayload,
    PaymentPayloadInner,
    PaymentRequirements,
    PaymentRequirementsExtra,
    PaymentRequirementsKind,
    SettleResponse,
    SupportedKind,
    VerifyResponse,
)


# =============================================================================
# TEST HELPERS
# =============================================================================


def _make_supported_response(
    networks=None,
) -> dict:
    """Default /x402/v1/supported response fixture."""
    if networks is None:
        networks = [
            {
                "x402Version": 2,
                "scheme": "exact",
                "network": "eip155:5042002",
                "extra": {
                    "verifyingContract": "0xVerifyingContractArcTestnet",
                    "usdcAddress": "0xUsdcArcTestnet",
                },
            },
            {
                "x402Version": 2,
                "scheme": "exact",
                "network": "eip155:1",
                "extra": {
                    "verifyingContract": "0xVerifyingContractMainnet",
                    "usdcAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                },
            },
        ]
    return {"kinds": networks}


def _make_payload() -> PaymentPayload:
    """Minimal valid PaymentPayload for settle/verify tests."""
    authorization = EIP3009Authorization.create(
        from_address="0x" + "a" * 40,
        to="0x" + "b" * 40,
        value="1000000",
        valid_before=int(time.time()) + 345600,
        nonce="0x" + "c" * 64,
    )
    return PaymentPayload(
        x402_version=2,
        scheme="exact",
        network="eip155:5042002",
        payload=PaymentPayloadInner(
            signature="0x" + "d" * 130,
            authorization=authorization,
        ),
    )


def _make_requirements() -> PaymentRequirements:
    return PaymentRequirements(
        x402_version=2,
        accepts=(
            PaymentRequirementsKind(
                scheme="exact",
                network="eip155:5042002",
                asset="0xUsdcArcTestnet",
                amount="1000000",
                max_timeout_seconds=345600,
                pay_to="0x" + "b" * 40,
                extra=PaymentRequirementsExtra(
                    name="GatewayWalletBatched",
                    version="1",
                    verifying_contract="0xVerifyingContractArcTestnet",
                ),
            ),
        ),
    )


# =============================================================================
# NanopaymentHTTPClient TESTS
# =============================================================================


class TestNanopaymentHTTPClientInit:
    def test_stores_config(self):
        client = NanopaymentHTTPClient(
            base_url="https://api.example.com",
            api_key="test-key",
            timeout=15.0,
        )
        assert client._base_url == "https://api.example.com"
        assert client._api_key == "test-key"
        assert client._timeout == 15.0

    def test_strips_trailing_slash(self):
        client = NanopaymentHTTPClient(
            base_url="https://api.example.com/",
            api_key="key",
        )
        assert client._base_url == "https://api.example.com"


class TestNanopaymentHTTPClientContextManager:
    @pytest.mark.asyncio
    async def test_opens_and_closes_client(self):
        client = NanopaymentHTTPClient(
            base_url="https://api.example.com",
            api_key="key",
        )
        async with client as c:
            assert c._client is not None
        assert client._client is None

    @pytest.mark.asyncio
    async def test_get_returns_response(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"kinds": []}
        mock_response.text = ""

        with patch("httpx.AsyncClient") as MockAsyncClient:
            instance = AsyncMock()
            instance.get.return_value = mock_response
            instance.aclose.return_value = None
            MockAsyncClient.return_value = instance

            async with NanopaymentHTTPClient(
                base_url="https://api.example.com",
                api_key="key",
            ) as http:
                resp = await http.get("/test")

        assert resp.status_code == 200
        instance.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_raises_timeout_on_timeout(self):
        with patch("httpx.AsyncClient") as MockAsyncClient:
            instance = AsyncMock()
            instance.get.side_effect = httpx.TimeoutException("read timeout")
            instance.aclose.return_value = None
            MockAsyncClient.return_value = instance

            async with NanopaymentHTTPClient(
                base_url="https://api.example.com",
                api_key="key",
            ) as http:
                with pytest.raises(GatewayTimeoutError) as exc_info:
                    await http.get("/test")
            assert exc_info.value.code == "GATEWAY_TIMEOUT"

    @pytest.mark.asyncio
    async def test_post_raises_connection_error(self):
        with patch("httpx.AsyncClient") as MockAsyncClient:
            instance = AsyncMock()
            instance.post.side_effect = httpx.ConnectError("connection refused")
            instance.aclose.return_value = None
            MockAsyncClient.return_value = instance

            async with NanopaymentHTTPClient(
                base_url="https://api.example.com",
                api_key="key",
            ) as http:
                with pytest.raises(GatewayConnectionError) as exc_info:
                    await http.post("/test", json={})
            assert exc_info.value.code == "GATEWAY_CONNECTION_ERROR"


# =============================================================================
# NanopaymentClient CONSTRUCTOR TESTS
# =============================================================================


class TestNanopaymentClientInit:
    def test_defaults_to_testnet(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient"):
                client = NanopaymentClient(api_key="key")
        assert client._environment == "testnet"
        assert client._base_url == "https://gateway-api-testnet.circle.com"

    def test_mainnet_url(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient"):
                client = NanopaymentClient(environment="mainnet", api_key="key")
        assert client._environment == "mainnet"
        assert client._base_url == "https://gateway-api.circle.com"

    def test_reads_api_key_from_env(self):
        with patch.dict("os.environ", {"CIRCLE_API_KEY": "env-api-key"}, clear=True):
            with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient"):
                client = NanopaymentClient()
        assert client._api_key == "env-api-key"

    def test_explicit_api_key_overrides_env(self):
        with patch.dict("os.environ", {"CIRCLE_API_KEY": "env-key"}, clear=True):
            with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient"):
                client = NanopaymentClient(api_key="explicit-key")
        assert client._api_key == "explicit-key"

    def test_reads_environment_from_env(self):
        with patch.dict("os.environ", {"NANOPAYMENTS_ENVIRONMENT": "mainnet"}, clear=True):
            with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient"):
                client = NanopaymentClient(api_key="key")
        assert client._environment == "mainnet"
        assert client._base_url == "https://gateway-api.circle.com"

    def test_rejects_invalid_environment(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                NanopaymentClient(environment="invalid", api_key="key")
        assert "invalid" in str(exc_info.value)

    def test_custom_base_url(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient"):
                client = NanopaymentClient(base_url="https://mock.local/ gateway", api_key="key")
        assert client._base_url == "https://mock.local/ gateway"

    def test_custom_timeout(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient"):
                client = NanopaymentClient(timeout=60.0, api_key="key")
        assert client._timeout == 60.0


# =============================================================================
# GET_SUPPORTED TESTS
# =============================================================================


class TestGetSupported:
    @pytest.mark.asyncio
    async def test_parses_supported_kinds(self):
        response_data = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = response_data
            mock_resp.text = ""
            mock_ctx.get.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            kinds = await client.get_supported()

        assert len(kinds) == 2
        assert kinds[0].network == "eip155:5042002"
        assert kinds[0].verifying_contract == "0xVerifyingContractArcTestnet"
        assert kinds[0].usdc_address == "0xUsdcArcTestnet"
        assert kinds[1].network == "eip155:1"
        assert kinds[1].verifying_contract == "0xVerifyingContractMainnet"

    @pytest.mark.asyncio
    async def test_uses_cache_on_second_call(self):
        response_data = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = response_data
            mock_resp.text = ""
            mock_ctx.get.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            kinds1 = await client.get_supported()
            kinds2 = await client.get_supported()

        assert kinds1 == kinds2
        # Only one HTTP call
        mock_ctx.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self):
        response_data = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = response_data
            mock_resp.text = ""
            mock_ctx.get.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            await client.get_supported()
            await client.get_supported(force_refresh=True)

        # Two HTTP calls despite cache
        assert mock_ctx.get.call_count == 2

    @pytest.mark.asyncio
    async def test_handles_empty_kinds_list(self):
        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"kinds": []}
            mock_resp.text = ""
            mock_ctx.get.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            kinds = await client.get_supported()

        assert kinds == []

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_ctx.get.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(GatewayAPIError) as exc_info:
                await client.get_supported()
            assert exc_info.value.status_code == 500


# =============================================================================
# GET_VERIFYING_CONTRACT / GET_USDC_ADDRESS TESTS
# =============================================================================


class TestGetVerifyingContract:
    @pytest.mark.asyncio
    async def test_returns_contract_for_known_network(self):
        response_data = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = response_data
            mock_resp.text = ""
            mock_ctx.get.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            addr = await client.get_verifying_contract("eip155:5042002")

        assert addr == "0xVerifyingContractArcTestnet"

    @pytest.mark.asyncio
    async def test_raises_for_unknown_network(self):
        response_data = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = response_data
            mock_resp.text = ""
            mock_ctx.get.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(UnsupportedNetworkError) as exc_info:
                await client.get_verifying_contract("eip155:99999999")
            assert exc_info.value.network == "eip155:99999999"


class TestGetUsdcAddress:
    @pytest.mark.asyncio
    async def test_returns_usdc_for_known_network(self):
        response_data = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = response_data
            mock_resp.text = ""
            mock_ctx.get.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            addr = await client.get_usdc_address("eip155:1")

        assert addr == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

    @pytest.mark.asyncio
    async def test_raises_for_unknown_network(self):
        response_data = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = response_data
            mock_resp.text = ""
            mock_ctx.get.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(UnsupportedNetworkError):
                await client.get_usdc_address("eip155:99999999")


# =============================================================================
# VERIFY TESTS
# =============================================================================


class TestVerify:
    @pytest.mark.asyncio
    async def test_returns_verify_response_valid(self):
        payload = _make_payload()
        requirements = _make_requirements()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "isValid": True,
                "payer": "0x" + "a" * 40,
                "invalidReason": None,
            }
            mock_resp.text = ""
            mock_ctx.post.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            result = await client.verify(payload, requirements)

        assert isinstance(result, VerifyResponse)
        assert result.is_valid is True
        assert result.payer == "0x" + "a" * 40
        assert result.invalid_reason is None

    @pytest.mark.asyncio
    async def test_returns_verify_response_invalid(self):
        payload = _make_payload()
        requirements = _make_requirements()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "isValid": False,
                "payer": None,
                "invalidReason": "invalid_signature",
            }
            mock_resp.text = ""
            mock_ctx.post.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            result = await client.verify(payload, requirements)

        assert result.is_valid is False
        assert result.invalid_reason == "invalid_signature"

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        payload = _make_payload()
        requirements = _make_requirements()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.text = "Unauthorized"
            mock_ctx.post.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(GatewayAPIError) as exc_info:
                await client.verify(payload, requirements)
            assert exc_info.value.status_code == 401


# =============================================================================
# SETTLE TESTS
# =============================================================================


class TestSettle:
    @pytest.mark.asyncio
    async def test_returns_settle_response_on_success(self):
        payload = _make_payload()
        requirements = _make_requirements()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "success": True,
                "transaction": "batch-ref-123",
                "payer": "0x" + "a" * 40,
                "errorReason": None,
            }
            mock_resp.text = ""
            mock_ctx.post.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            result = await client.settle(payload, requirements)

        assert isinstance(result, SettleResponse)
        assert result.success is True
        assert result.transaction == "batch-ref-123"
        assert result.payer == "0x" + "a" * 40

    @pytest.mark.asyncio
    async def test_raises_settlement_error_on_failure(self):
        payload = _make_payload()
        requirements = _make_requirements()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "success": False,
                "transaction": None,
                "payer": "0x" + "a" * 40,
                "errorReason": "insufficient_balance",
            }
            mock_resp.text = ""
            mock_ctx.post.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(InsufficientBalanceError):
                await client.settle(payload, requirements)

    @pytest.mark.asyncio
    async def test_raises_on_http_402_with_body_error(self):
        payload = _make_payload()
        requirements = _make_requirements()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 402
            mock_resp.json.return_value = {
                "errorReason": "nonce_already_used",
                "payer": "0x" + "a" * 40,
            }
            mock_resp.text = ""
            mock_ctx.post.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(NonceReusedError):
                await client.settle(payload, requirements)

    @pytest.mark.asyncio
    async def test_raises_gateway_api_error_on_http_failure(self):
        payload = _make_payload()
        requirements = _make_requirements()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_resp.text = "Forbidden"
            mock_ctx.post.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(GatewayAPIError) as exc_info:
                await client.settle(payload, requirements)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_maps_unknown_error_reason_to_settlement_error(self):
        payload = _make_payload()
        requirements = _make_requirements()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "success": False,
                "transaction": "tx-999",
                "errorReason": "unknown_gateway_error",
            }
            mock_resp.text = ""
            mock_ctx.post.return_value = mock_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(SettlementError) as exc_info:
                await client.settle(payload, requirements)
            assert exc_info.value.reason == "unknown_gateway_error"
            assert exc_info.value.transaction == "tx-999"


# =============================================================================
# CHECK_BALANCE TESTS
# =============================================================================


class TestCheckBalance:
    @pytest.mark.asyncio
    async def test_returns_gateway_balance(self):
        supported_response = _make_supported_response()
        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            supported_resp = MagicMock()
            supported_resp.status_code = 200
            supported_resp.json.return_value = supported_response
            supported_resp.text = ""
            balance_resp = MagicMock()
            balance_resp.status_code = 200
            balance_resp.json.return_value = {
                "balances": [{"balance": "5000000"}],
            }
            balance_resp.text = ""
            mock_ctx.get.return_value = supported_resp
            mock_ctx.post.return_value = balance_resp
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            balance = await client.check_balance(
                address="0x" + "a" * 40,
                network="eip155:5042002",
            )

        assert balance.total == 5_000_000
        assert balance.available == 5_000_000
        assert balance.formatted_total == "5.000000 USDC"
        assert balance.formatted_available == "5.000000 USDC"
        assert balance.total_decimal == "5.000000"
        assert balance.available_decimal == "5.000000"

    @pytest.mark.asyncio
    async def test_raises_unsupported_network_on_404(self):
        supported_response = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            supported_resp = MagicMock(status_code=200, text="")
            supported_resp.json.return_value = supported_response
            mock_ctx.get.return_value = supported_resp
            mock_ctx.post.return_value = MagicMock(status_code=404, text="Not Found")
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(UnsupportedNetworkError):
                await client.check_balance(
                    address="0x" + "a" * 40,
                    network="eip155:5042002",
                )

    @pytest.mark.asyncio
    async def test_raises_gateway_api_error_on_http_failure(self):
        supported_response = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            supported_resp = MagicMock(status_code=200, text="")
            supported_resp.json.return_value = supported_response
            mock_ctx.get.return_value = supported_resp
            mock_ctx.post.return_value = MagicMock(status_code=500, text="Internal Server Error")
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            with pytest.raises(GatewayAPIError) as exc_info:
                await client.check_balance(
                    address="0x" + "a" * 40,
                    network="eip155:5042002",
                )
            assert exc_info.value.status_code == 500


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestNanopaymentClientEdgeCases:
    @pytest.mark.asyncio
    async def test_get_supported_after_insufficient_balance_error(self):
        """Cache is still populated after a settle failure."""
        response_data = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_ctx.get.return_value = MagicMock(
                status_code=200,
                json=lambda: response_data,
                text="",
            )
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")

            # get_supported populates cache
            kinds = await client.get_supported()
            assert len(kinds) == 2

            # Cache hit
            kinds2 = await client.get_supported()
            assert kinds2 == kinds
            mock_ctx.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_networks_pick_first_match(self):
        """get_verifying_contract returns first matching network."""
        response_data = _make_supported_response()

        with patch("omniclaw.protocols.nanopayments.client.NanopaymentHTTPClient") as MockHTTP:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__.return_value = mock_ctx
            mock_ctx.__aexit__.return_value = None
            mock_ctx.get.return_value = MagicMock(
                status_code=200,
                json=lambda: response_data,
                text="",
            )
            MockHTTP.return_value = mock_ctx

            client = NanopaymentClient(api_key="key")
            addr = await client.get_verifying_contract("eip155:5042002")

        assert addr == "0xVerifyingContractArcTestnet"
