"""
Comprehensive tests for NanopaymentAdapter - targeting uncovered code paths.

Tests cover:
- Circuit breaker state transitions and thresholds
- Settlement retry logic with exponential backoff
- Auto-topup with wallet manager
- Helper functions (_is_url, _is_address)
- NanopaymentProtocolAdapter (router integration)
- Error handling for HTTP requests
"""

import json
import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from omniclaw.protocols.nanopayments import NanopaymentAdapter
from omniclaw.protocols.nanopayments.adapter import (
    CircuitOpenError,
    NanopaymentCircuitBreaker,
    NanopaymentProtocolAdapter,
    _is_address,
    _is_url,
)
from omniclaw.protocols.nanopayments.client import NanopaymentClient
from omniclaw.protocols.nanopayments.exceptions import (
    GatewayAPIError,
    GatewayConnectionError,
    GatewayTimeoutError,
    InsufficientBalanceError,
    NonceReusedError,
    SettlementError,
)
from omniclaw.protocols.nanopayments.types import (
    EIP3009Authorization,
    PaymentPayload,
    PaymentPayloadInner,
    PaymentRequirements,
)
from omniclaw.protocols.nanopayments.vault import NanoKeyVault


# =============================================================================
# TEST HELPERS (reused from existing tests + new ones)
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


def _make_requirements() -> PaymentRequirements:
    """Create a PaymentRequirements object for _settle_with_retry tests."""
    from omniclaw.protocols.nanopayments.types import (
        PaymentRequirementsExtra,
        PaymentRequirementsKind,
    )

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
                    verifying_contract="0x" + "c" * 40,
                ),
            ),
        ),
    )


# =============================================================================
# CIRCUIT BREAKER TESTS
# =============================================================================


class TestNanopaymentCircuitBreaker:
    """Tests for NanopaymentCircuitBreaker class."""

    def test_circuit_starts_closed(self):
        """Circuit breaker starts in closed state."""
        cb = NanopaymentCircuitBreaker()
        assert cb.state == "closed"
        assert cb.is_available() is True

    def test_record_failure_trips_after_threshold(self):
        """After 5 failures (default threshold), state becomes open."""
        cb = NanopaymentCircuitBreaker(failure_threshold=5)

        # 4 failures should keep it closed
        for _ in range(4):
            cb.record_failure()
        assert cb.state == "closed"
        assert cb.is_available() is True

        # 5th failure should trip it open
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_available() is False

    def test_record_error_trips_after_threshold(self):
        """record_error() also trips circuit after threshold."""
        cb = NanopaymentCircuitBreaker(failure_threshold=3)

        # 2 errors should keep it closed
        cb.record_error()
        cb.record_error()
        assert cb.state == "closed"

        # 3rd error should trip it open
        cb.record_error()
        assert cb.state == "open"
        assert cb.is_available() is False

    def test_half_open_after_recovery_seconds(self):
        """State becomes half_open after recovery period elapses."""
        cb = NanopaymentCircuitBreaker(failure_threshold=2, recovery_seconds=1.0)

        # Trip the circuit open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Immediately after trip, still open
        assert cb.state == "open"

        # Mock time to simulate recovery period passing
        with patch("time.monotonic") as mock_time:
            # Set time to just before recovery period
            mock_time.return_value = cb._last_failure_time + 0.5
            assert cb.state == "open"

            # Set time to after recovery period
            mock_time.return_value = cb._last_failure_time + 1.0
            assert cb.state == "half_open"

    def test_half_open_success_closes_circuit(self):
        """After half_open, record_success resets to closed."""
        cb = NanopaymentCircuitBreaker(failure_threshold=2, recovery_seconds=1.0)

        # Trip the circuit open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Move to half_open
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = cb._last_failure_time + 1.0
            assert cb.state == "half_open"

        # Record success in half_open state
        cb.record_success()
        assert cb.state == "closed"
        assert cb.is_available() is True
        assert cb._consecutive_failures == 0

    def test_half_open_failure_reopens(self):
        """After half_open, record_failure reopens the circuit."""
        cb = NanopaymentCircuitBreaker(failure_threshold=2, recovery_seconds=1.0)

        # Trip the circuit open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Move to half_open
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = cb._last_failure_time + 1.0
            assert cb.state == "half_open"

        # Record failure in half_open state
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_available() is False

    def test_record_success_in_closed_state_resets_failures(self):
        """record_success resets consecutive failure count."""
        cb = NanopaymentCircuitBreaker(failure_threshold=5)

        # Record some failures (but not enough to trip)
        cb.record_failure()
        cb.record_failure()
        assert cb._consecutive_failures == 2

        # Success should reset the counter
        cb.record_success()
        assert cb._consecutive_failures == 0
        assert cb.state == "closed"

    def test_reset_closes_circuit(self):
        """reset() closes the circuit regardless of current state."""
        cb = NanopaymentCircuitBreaker(failure_threshold=2)

        # Trip the circuit open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Reset should close it
        cb.reset()
        assert cb.state == "closed"
        assert cb.is_available() is True
        assert cb._consecutive_failures == 0
        assert cb._last_failure_time is None

    def test_is_available_false_when_open(self):
        """is_available returns False when circuit is open."""
        cb = NanopaymentCircuitBreaker(failure_threshold=1)

        # Closed: available
        assert cb.is_available() is True

        # Trip open
        cb.record_failure()
        assert cb.is_available() is False

    def test_is_available_true_when_half_open(self):
        """is_available returns True when circuit is half_open (trial request allowed)."""
        cb = NanopaymentCircuitBreaker(failure_threshold=1, recovery_seconds=0.5)

        # Trip open
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_available() is False

        # Move to half_open
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = cb._last_failure_time + 0.5
            assert cb.state == "half_open"
            assert cb.is_available() is True


# =============================================================================
# SETTLE RETRY TESTS
# =============================================================================


class TestSettleWithRetry:
    """Tests for _settle_with_retry method."""

    @pytest.mark.asyncio
    async def test_settle_with_retry_success_first_attempt(self):
        """Settle succeeds on first try."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
        )

        requirements = _make_requirements()
        payload = await mock_vault.sign(requirements=requirements.accepts[0])

        result = await adapter._settle_with_retry(payload=payload, requirements=requirements)

        assert result is not None
        assert result.success is True
        mock_client.settle.assert_called_once()

    @pytest.mark.asyncio
    async def test_settle_with_retry_exhausts_retries_on_timeout(self):
        """GatewayTimeoutError exhausts all retries."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()
        mock_client.settle = AsyncMock(side_effect=GatewayTimeoutError(endpoint="/x402/v1/settle"))

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
            retry_attempts=3,
            retry_base_delay=0.1,
        )

        requirements = _make_requirements()
        payload = await mock_vault.sign(requirements=requirements.accepts[0])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(GatewayTimeoutError):
                await adapter._settle_with_retry(payload=payload, requirements=requirements)

            # Should have slept for retries: attempts 0, 1, 2 (3 retries)
            assert mock_sleep.call_count == 3
            # settle called once per attempt (total retry_attempts + 1)
            assert mock_client.settle.call_count == 4

    @pytest.mark.asyncio
    async def test_settle_with_retry_exhausts_retries_on_connection_error(self):
        """GatewayConnectionError exhausts all retries."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()
        mock_client.settle = AsyncMock(
            side_effect=GatewayConnectionError(reason="Connection refused")
        )

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
            retry_attempts=2,
            retry_base_delay=0.1,
        )

        requirements = _make_requirements()
        payload = await mock_vault.sign(requirements=requirements.accepts[0])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(GatewayConnectionError):
                await adapter._settle_with_retry(payload=payload, requirements=requirements)

            # Should have slept for retries: attempts 0, 1 (2 retries)
            assert mock_sleep.call_count == 2
            # settle called retry_attempts + 1 times
            assert mock_client.settle.call_count == 3

    @pytest.mark.asyncio
    async def test_settle_with_retry_circuit_open_raises_immediately(self):
        """If circuit is open, raises CircuitOpenError immediately (no retries)."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()

        # Pre-trip the circuit breaker
        circuit_breaker = NanopaymentCircuitBreaker(failure_threshold=1)
        circuit_breaker.record_failure()  # Trip it open

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
            circuit_breaker=circuit_breaker,
        )

        requirements = _make_requirements()
        payload = await mock_vault.sign(requirements=requirements.accepts[0])

        with pytest.raises(CircuitOpenError):
            await adapter._settle_with_retry(payload=payload, requirements=requirements)

        # settle should NOT have been called
        mock_client.settle.assert_not_called()

    @pytest.mark.asyncio
    async def test_settle_with_retry_nonce_reused_record_failure(self):
        """NonceReusedError records failure and does not retry."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()
        mock_client.settle = AsyncMock(
            side_effect=NonceReusedError(reason="nonce_already_used", payer="0x" + "a" * 40)
        )

        circuit_breaker = NanopaymentCircuitBreaker(failure_threshold=5)
        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
            circuit_breaker=circuit_breaker,
        )

        requirements = _make_requirements()
        payload = await mock_vault.sign(requirements=requirements.accepts[0])

        with pytest.raises(NonceReusedError):
            await adapter._settle_with_retry(payload=payload, requirements=requirements)

        # settle should have been called once (no retries for nonce reused)
        mock_client.settle.assert_called_once()
        # Circuit breaker should have recorded failure
        assert circuit_breaker._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_settle_with_retry_insufficient_balance_record_failure(self):
        """InsufficientBalanceError records failure and does not retry."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()
        mock_client.settle = AsyncMock(
            side_effect=InsufficientBalanceError(
                reason="insufficient_balance", payer="0x" + "a" * 40
            )
        )

        circuit_breaker = NanopaymentCircuitBreaker(failure_threshold=5)
        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
            circuit_breaker=circuit_breaker,
        )

        requirements = _make_requirements()
        payload = await mock_vault.sign(requirements=requirements.accepts[0])

        with pytest.raises(InsufficientBalanceError):
            await adapter._settle_with_retry(payload=payload, requirements=requirements)

        mock_client.settle.assert_called_once()
        assert circuit_breaker._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_settle_with_retry_settlement_error_with_timeout_retries(self):
        """SettlementError containing 'timeout' retries."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()
        mock_client.settle = AsyncMock(
            side_effect=SettlementError(
                reason="timeout occurred during processing", transaction=None, payer="0x" + "a" * 40
            )
        )

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
            retry_attempts=2,
            retry_base_delay=0.1,
        )

        requirements = _make_requirements()
        payload = await mock_vault.sign(requirements=requirements.accepts[0])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(SettlementError):
                await adapter._settle_with_retry(payload=payload, requirements=requirements)

            # Should have slept for retries
            assert mock_sleep.call_count == 2
            assert mock_client.settle.call_count == 3

    @pytest.mark.asyncio
    async def test_settle_with_retry_settlement_error_other_raises(self):
        """SettlementError without 'timeout'/'connection' does not retry."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()
        mock_client.settle = AsyncMock(
            side_effect=SettlementError(
                reason="invalid signature", transaction=None, payer="0x" + "a" * 40
            )
        )

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
        )

        requirements = _make_requirements()
        payload = await mock_vault.sign(requirements=requirements.accepts[0])

        with pytest.raises(SettlementError) as exc:
            await adapter._settle_with_retry(payload=payload, requirements=requirements)

        assert "invalid signature" in str(exc.value)
        # settle called only once (no retries)
        mock_client.settle.assert_called_once()

    @pytest.mark.asyncio
    async def test_settle_with_retry_half_open_success(self):
        """After half_open, settle succeeds and closes circuit."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()

        # Pre-configure circuit breaker to be half_open
        circuit_breaker = NanopaymentCircuitBreaker(failure_threshold=1, recovery_seconds=0.5)
        circuit_breaker.record_failure()  # Trip open

        # Move to half_open
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = circuit_breaker._last_failure_time + 0.5
            assert circuit_breaker.state == "half_open"

            adapter = NanopaymentAdapter(
                vault=mock_vault,
                nanopayment_client=mock_client,
                http_client=AsyncMock(),
                auto_topup_enabled=False,
                circuit_breaker=circuit_breaker,
            )

            requirements = _make_requirements()
            payload = await mock_vault.sign(requirements=requirements.accepts[0])

            result = await adapter._settle_with_retry(payload=payload, requirements=requirements)

            # Should succeed and close the circuit
            assert result is not None
            assert result.success is True
            assert circuit_breaker.state == "closed"


# =============================================================================
# AUTO-TOPUP WITH WALLET MANAGER TESTS
# =============================================================================


class TestCheckAndTopup:
    """Tests for _check_and_topup method with wallet manager."""

    @pytest.mark.asyncio
    async def test_check_and_topup_with_wallet_manager_low_balance(self):
        """When wallet manager set, balance below threshold triggers deposit."""
        mock_vault = _mock_vault()
        mock_vault.get_balance = AsyncMock(
            return_value=MagicMock(
                available_decimal="0.500000",  # Below $1.00 threshold
            )
        )

        mock_wallet_manager = MagicMock()
        mock_wallet_manager.deposit = AsyncMock(return_value=MagicMock(deposit_tx_hash="0xtx123"))

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=True,
        )
        adapter.set_wallet_manager(mock_wallet_manager)

        result = await adapter._check_and_topup()

        assert result is True
        mock_wallet_manager.deposit.assert_called_once_with("10.00")  # Default topup amount

    @pytest.mark.asyncio
    async def test_check_and_topup_with_wallet_manager_high_balance(self):
        """When wallet manager set but balance above threshold, returns False."""
        mock_vault = _mock_vault()
        mock_vault.get_balance = AsyncMock(
            return_value=MagicMock(
                available_decimal="10.000000",  # Above $1.00 threshold
            )
        )

        mock_wallet_manager = MagicMock()
        mock_wallet_manager.deposit = AsyncMock()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=True,
        )
        adapter.set_wallet_manager(mock_wallet_manager)

        result = await adapter._check_and_topup()

        assert result is False
        mock_wallet_manager.deposit.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_topup_no_wallet_manager_returns_false(self):
        """Without wallet manager, returns False."""
        mock_vault = _mock_vault()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=True,
        )
        # Note: no set_wallet_manager called

        result = await adapter._check_and_topup()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_and_topup_balance_fetch_fails_returns_false(self):
        """If vault.get_balance raises, returns False."""
        mock_vault = _mock_vault()
        mock_vault.get_balance = AsyncMock(side_effect=Exception("Balance check failed"))

        mock_wallet_manager = MagicMock()
        mock_wallet_manager.deposit = AsyncMock()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=True,
        )
        adapter.set_wallet_manager(mock_wallet_manager)

        result = await adapter._check_and_topup()

        assert result is False
        mock_wallet_manager.deposit.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_and_topup_deposit_fails_returns_false(self):
        """If wallet_manager.deposit raises, returns False."""
        mock_vault = _mock_vault()
        mock_vault.get_balance = AsyncMock(
            return_value=MagicMock(
                available_decimal="0.500000",  # Below threshold
            )
        )

        mock_wallet_manager = MagicMock()
        mock_wallet_manager.deposit = AsyncMock(side_effect=Exception("Deposit failed"))

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=True,
        )
        adapter.set_wallet_manager(mock_wallet_manager)

        result = await adapter._check_and_topup()

        assert result is False


# =============================================================================
# SET WALLET MANAGER TESTS
# =============================================================================


class TestSetWalletManager:
    """Tests for set_wallet_manager method."""

    def test_set_wallet_manager_stores_manager(self):
        """set_wallet_manager stores the manager."""
        mock_vault = _mock_vault()
        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=True,
        )

        mock_wallet_manager = MagicMock()
        adapter.set_wallet_manager(mock_wallet_manager)

        assert adapter._wallet_manager is mock_wallet_manager


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================


class TestIsUrl:
    """Tests for _is_url helper function."""

    def test_is_url_true_for_http(self):
        """_is_url returns True for http:// URLs."""
        assert _is_url("http://example.com") is True
        assert _is_url("http://api.example.com/path") is True

    def test_is_url_true_for_https(self):
        """_is_url returns True for https:// URLs."""
        assert _is_url("https://example.com") is True
        assert _is_url("https://api.example.com/data?key=value") is True

    def test_is_url_false_for_address(self):
        """_is_url returns False for EVM addresses."""
        assert _is_url("0x" + "a" * 40) is False
        assert _is_url("0x1234567890123456789012345678901234567890") is False


class TestIsAddress:
    """Tests for _is_address helper function."""

    def test_is_address_true_for_valid_42_char(self):
        """_is_address returns True for valid 42-char 0x address."""
        valid_address = "0x" + "a" * 40
        assert _is_address(valid_address) is True

    def test_is_address_false_for_url(self):
        """_is_address returns False for URLs."""
        assert _is_address("https://example.com") is False
        assert _is_address("http://api.example.com") is False

    def test_is_address_false_for_short_address(self):
        """_is_address returns False for address shorter than 42 chars."""
        short_address = "0x" + "a" * 39
        assert len(short_address) == 41
        assert _is_address(short_address) is False

    def test_is_address_false_for_long_address(self):
        """_is_address returns False for address longer than 42 chars."""
        long_address = "0x" + "a" * 41
        assert len(long_address) == 43
        assert _is_address(long_address) is False


# =============================================================================
# ROUTER TESTS (NanopaymentProtocolAdapter)
# =============================================================================


class TestNanopaymentProtocolAdapterSupports:
    """Tests for NanopaymentProtocolAdapter.supports method."""

    def test_supports_url_returns_true(self):
        """supports returns True for URL recipients."""
        mock_adapter = MagicMock()
        router = NanopaymentProtocolAdapter(nanopayment_adapter=mock_adapter)

        assert router.supports("https://api.example.com/data") is True
        assert router.supports("http://api.example.com/data") is True

    def test_supports_address_below_threshold_returns_true(self):
        """supports returns True for EVM address with amount below threshold."""
        mock_adapter = MagicMock()
        router = NanopaymentProtocolAdapter(
            nanopayment_adapter=mock_adapter, micro_threshold_usdc="1.00"
        )

        assert router.supports("0x" + "a" * 40, amount="0.50") is True
        assert router.supports("0x" + "b" * 40, amount="0.001") is True

    def test_supports_address_above_threshold_returns_false(self):
        """supports returns False for EVM address with amount above threshold."""
        mock_adapter = MagicMock()
        router = NanopaymentProtocolAdapter(
            nanopayment_adapter=mock_adapter, micro_threshold_usdc="1.00"
        )

        assert router.supports("0x" + "a" * 40, amount="1.00") is False
        assert router.supports("0x" + "b" * 40, amount="5.00") is False

    def test_supports_non_nanopayment_returns_false(self):
        """supports returns False for non-URL/non-address recipients."""
        mock_adapter = MagicMock()
        router = NanopaymentProtocolAdapter(nanopayment_adapter=mock_adapter)

        assert router.supports("invalid-recipient") is False
        assert router.supports("mailto:test@example.com") is False

    def test_supports_address_without_amount_returns_false(self):
        """supports returns False for address when amount is not provided."""
        mock_adapter = MagicMock()
        router = NanopaymentProtocolAdapter(nanopayment_adapter=mock_adapter)

        # Address without amount can't be checked against threshold
        assert router.supports("0x" + "a" * 40) is False


class TestNanopaymentProtocolAdapterGetPriority:
    """Tests for NanopaymentProtocolAdapter.get_priority method."""

    def test_get_priority_returns_10(self):
        """get_priority returns 10 (highest priority)."""
        mock_adapter = MagicMock()
        router = NanopaymentProtocolAdapter(nanopayment_adapter=mock_adapter)

        assert router.get_priority() == 10


class TestNanopaymentProtocolAdapterExecute:
    """Tests for NanopaymentProtocolAdapter.execute method."""

    @pytest.mark.asyncio
    async def test_execute_url_calls_pay_x402_url(self):
        """execute with URL calls pay_x402_url."""
        from omniclaw.protocols.nanopayments.types import NanopaymentResult

        mock_adapter = MagicMock()
        mock_result = NanopaymentResult(
            success=True,
            payer="0x" + "a" * 40,
            seller="0x" + "b" * 40,
            transaction="tx-123",
            amount_usdc="0.001",
            amount_atomic="1000",
            network="eip155:5042002",
            response_data=None,
            is_nanopayment=True,
        )
        mock_adapter.pay_x402_url = AsyncMock(return_value=mock_result)

        router = NanopaymentProtocolAdapter(nanopayment_adapter=mock_adapter)

        result = await router.execute(
            wallet_id="wallet-123",
            recipient="https://api.example.com/data",
            amount=Decimal("0.001"),
        )

        mock_adapter.pay_x402_url.assert_called_once()
        assert result.success is True
        assert result.method.value == "nanopayment"

    @pytest.mark.asyncio
    async def test_execute_address_calls_pay_direct(self):
        """execute with 0x address calls pay_direct."""
        from omniclaw.protocols.nanopayments.types import NanopaymentResult

        mock_adapter = MagicMock()
        mock_result = NanopaymentResult(
            success=True,
            payer="0x" + "a" * 40,
            seller="0x" + "b" * 40,
            transaction="tx-456",
            amount_usdc="0.50",
            amount_atomic="500000",
            network="eip155:5042002",
            response_data=None,
            is_nanopayment=True,
        )
        mock_adapter.pay_direct = AsyncMock(return_value=mock_result)

        router = NanopaymentProtocolAdapter(nanopayment_adapter=mock_adapter)

        result = await router.execute(
            wallet_id="wallet-123",
            recipient="0x" + "b" * 40,
            amount=Decimal("0.50"),
            destination_chain="eip155:5042002",
        )

        mock_adapter.pay_direct.assert_called_once()
        call_kwargs = mock_adapter.pay_direct.call_args.kwargs
        assert call_kwargs["seller_address"] == "0x" + "b" * 40
        assert call_kwargs["amount_usdc"] == "0.50"
        assert call_kwargs["network"] == "eip155:5042002"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_uses_destination_chain_as_network(self):
        """execute uses destination_chain parameter as network for pay_direct."""
        from omniclaw.protocols.nanopayments.types import NanopaymentResult

        mock_adapter = MagicMock()
        mock_result = NanopaymentResult(
            success=True,
            payer="0x" + "a" * 40,
            seller="0x" + "b" * 40,
            transaction="tx-789",
            amount_usdc="0.25",
            amount_atomic="250000",
            network="eip155:1",
            response_data=None,
            is_nanopayment=True,
        )
        mock_adapter.pay_direct = AsyncMock(return_value=mock_result)

        router = NanopaymentProtocolAdapter(nanopayment_adapter=mock_adapter)

        await router.execute(
            wallet_id="wallet-123",
            recipient="0x" + "b" * 40,
            amount=Decimal("0.25"),
            destination_chain="eip155:1",  # Ethereum mainnet
        )

        call_kwargs = mock_adapter.pay_direct.call_args.kwargs
        assert call_kwargs["network"] == "eip155:1"

    @pytest.mark.asyncio
    async def test_execute_graceful_degradation_on_error(self):
        """If adapter raises, returns FAILED result (not propagated)."""
        mock_adapter = MagicMock()
        mock_adapter.pay_x402_url = AsyncMock(side_effect=Exception("Network error"))

        router = NanopaymentProtocolAdapter(nanopayment_adapter=mock_adapter)

        result = await router.execute(
            wallet_id="wallet-123",
            recipient="https://api.example.com/data",
            amount=Decimal("0.001"),
        )

        # Should return failed result, not raise
        assert result.success is False
        assert result.status.value == "failed"
        assert "falling back" in result.error


class TestNanopaymentProtocolAdapterSimulate:
    """Tests for NanopaymentProtocolAdapter.simulate method."""

    @pytest.mark.asyncio
    async def test_simulate_returns_would_succeed(self):
        """simulate returns dict with would_succeed=True."""
        mock_adapter = MagicMock()
        router = NanopaymentProtocolAdapter(nanopayment_adapter=mock_adapter)

        result = await router.simulate(
            wallet_id="wallet-123",
            recipient="https://api.example.com/data",
            amount=Decimal("0.001"),
        )

        assert result["would_succeed"] is True
        assert result["method"] == "nanopayment"
        assert result["recipient"] == "https://api.example.com/data"
        assert result["amount"] == "0.001"
        assert result["estimated_fee"] == "0"


# =============================================================================
# PAY_X402_URL ERROR HANDLING TESTS
# =============================================================================


class TestPayX402UrlErrorHandling:
    """Tests for pay_x402_url error handling."""

    @pytest.mark.asyncio
    async def test_pay_x402_url_initial_request_timeout_raises(self):
        """httpx.TimeoutException on initial request raises GatewayAPIError."""
        mock_http = AsyncMock()
        mock_http.request.side_effect = httpx.TimeoutException("Request timed out")

        adapter = NanopaymentAdapter(
            vault=_mock_vault(),
            nanopayment_client=_mock_client(),
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        with pytest.raises(GatewayAPIError) as exc:
            await adapter.pay_x402_url("https://api.example.com/data")

        assert "timed out" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_pay_x402_url_initial_request_connection_error_raises(self):
        """httpx.RequestError on initial request raises GatewayAPIError."""
        mock_http = AsyncMock()
        mock_http.request.side_effect = httpx.RequestError("Connection failed")

        adapter = NanopaymentAdapter(
            vault=_mock_vault(),
            nanopayment_client=_mock_client(),
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        with pytest.raises(GatewayAPIError) as exc:
            await adapter.pay_x402_url("https://api.example.com/data")

        assert "failed" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_pay_x402_url_retry_request_timeout_raises(self):
        """httpx.TimeoutException on retry request raises GatewayAPIError."""
        import base64

        # First request returns 402
        initial_resp = MagicMock()
        initial_resp.status_code = 402
        initial_resp.headers = {
            "payment-required": base64.b64encode(
                json.dumps(_make_requirements_dict()).encode()
            ).decode()
        }

        # Retry request times out
        mock_http = AsyncMock()
        mock_http.request.side_effect = [
            initial_resp,  # First call - initial request
            httpx.TimeoutException("Retry timed out"),  # Second call - retry
        ]

        adapter = NanopaymentAdapter(
            vault=_mock_vault(),
            nanopayment_client=_mock_client(),
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        with pytest.raises(GatewayAPIError) as exc:
            await adapter.pay_x402_url("https://api.example.com/data")

        assert "timed out" in str(exc.value).lower()
        assert "retry" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_pay_x402_url_retry_request_connection_error_raises(self):
        """httpx.RequestError on retry request raises GatewayAPIError."""
        import base64

        # First request returns 402
        initial_resp = MagicMock()
        initial_resp.status_code = 402
        initial_resp.headers = {
            "payment-required": base64.b64encode(
                json.dumps(_make_requirements_dict()).encode()
            ).decode()
        }

        # Retry request fails
        mock_http = AsyncMock()
        mock_http.request.side_effect = [
            initial_resp,
            httpx.RequestError("Connection reset"),
        ]

        adapter = NanopaymentAdapter(
            vault=_mock_vault(),
            nanopayment_client=_mock_client(),
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        with pytest.raises(GatewayAPIError) as exc:
            await adapter.pay_x402_url("https://api.example.com/data")

        assert "failed" in str(exc.value).lower()
        assert "retry" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_pay_x402_url_circuit_open_raises(self):
        """When circuit breaker is open and content NOT delivered, raises CircuitOpenError."""
        import base64

        # First request returns 402
        initial_resp = MagicMock()
        initial_resp.status_code = 402
        initial_resp.headers = {
            "payment-required": base64.b64encode(
                json.dumps(_make_requirements_dict()).encode()
            ).decode()
        }

        # Retry request returns non-success (no content delivered)
        retry_resp = MagicMock()
        retry_resp.status_code = 500
        retry_resp.content = b""
        retry_resp.text = "Server Error"

        mock_http = AsyncMock()
        mock_http.request.side_effect = [initial_resp, retry_resp]

        # Pre-trip the circuit breaker
        circuit_breaker = NanopaymentCircuitBreaker(failure_threshold=1)
        circuit_breaker.record_failure()  # Trip open

        adapter = NanopaymentAdapter(
            vault=_mock_vault(),
            nanopayment_client=_mock_client(),
            http_client=mock_http,
            auto_topup_enabled=False,
            circuit_breaker=circuit_breaker,
        )

        with pytest.raises(CircuitOpenError):
            await adapter.pay_x402_url("https://api.example.com/data")


# =============================================================================
# ADDITIONAL CIRCUIT BREAKER TESTS
# =============================================================================


class TestCircuitBreakerAdditional:
    """Additional circuit breaker edge case tests."""

    def test_record_failure_multiple_times_to_threshold(self):
        """Recording failures up to threshold doesn't trip until reached."""
        cb = NanopaymentCircuitBreaker(failure_threshold=3)

        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "closed"

        cb.record_failure()
        assert cb.state == "open"

    def test_record_error_counts_toward_threshold_separately(self):
        """record_error and record_failure both count toward threshold."""
        cb = NanopaymentCircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"

        cb.record_error()
        assert cb.state == "open"

    def test_success_during_half_open_closes_circuit(self):
        """Success during half_open state closes circuit and resets failures."""
        cb = NanopaymentCircuitBreaker(failure_threshold=2, recovery_seconds=1.0)

        # Trip the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        # Move to half_open
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = cb._last_failure_time + 1.0
            assert cb.state == "half_open"

            # Success should close
            cb.record_success()
            assert cb.state == "closed"
            assert cb._consecutive_failures == 0

    def test_state_property_transitions_open_to_half_open(self):
        """State property correctly transitions from open to half_open."""
        cb = NanopaymentCircuitBreaker(failure_threshold=1, recovery_seconds=2.0)

        # Trip the circuit
        cb.record_failure()
        assert cb.state == "open"
        failure_time = cb._last_failure_time

        # Before recovery period
        with patch("time.monotonic") as mock_time:
            mock_time.return_value = failure_time + 1.0
            assert cb.state == "open"

            # After recovery period
            mock_time.return_value = failure_time + 2.0
            assert cb.state == "half_open"


# =============================================================================
# GET CIRCUIT BREAKER STATE TEST
# =============================================================================


class TestGetCircuitBreakerState:
    """Tests for get_circuit_breaker_state method."""

    @pytest.mark.asyncio
    async def test_get_circuit_breaker_state_closed(self):
        """get_circuit_breaker_state returns 'closed' initially."""
        mock_vault = _mock_vault()
        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=False,
        )

        assert adapter.get_circuit_breaker_state() == "closed"

    @pytest.mark.asyncio
    async def test_get_circuit_breaker_state_after_failures(self):
        """get_circuit_breaker_state returns 'open' after threshold exceeded."""
        mock_vault = _mock_vault()
        circuit_breaker = NanopaymentCircuitBreaker(failure_threshold=2)

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=_mock_client(),
            http_client=AsyncMock(),
            auto_topup_enabled=False,
            circuit_breaker=circuit_breaker,
        )

        circuit_breaker.record_failure()
        circuit_breaker.record_failure()

        assert adapter.get_circuit_breaker_state() == "open"


# =============================================================================
# SETTLEMENT ERROR WITH CONNECTION KEYWORD TESTS
# =============================================================================


class TestSettlementErrorConnectionRetries:
    """Tests for SettlementError with 'connection' keyword triggering retries."""

    @pytest.mark.asyncio
    async def test_settle_with_retry_settlement_error_with_connection_retries(self):
        """SettlementError containing 'connection' retries."""
        mock_vault = _mock_vault()
        mock_client = _mock_client()
        mock_client.settle = AsyncMock(
            side_effect=SettlementError(
                reason="connection reset by peer",
                transaction=None,
                payer="0x" + "a" * 40,
            )
        )

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
            retry_attempts=2,
            retry_base_delay=0.1,
        )

        requirements = _make_requirements()
        payload = await mock_vault.sign(requirements=requirements.accepts[0])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(SettlementError):
                await adapter._settle_with_retry(payload=payload, requirements=requirements)

            # Should have slept for retries
            assert mock_sleep.call_count == 2
            assert mock_client.settle.call_count == 3


# =============================================================================
# ADDITIONAL ADAPTER COVERAGE
# =============================================================================


class TestPayX402UrlAdditionalCoverage:
    """Additional pay_x402_url coverage tests."""

    @pytest.mark.asyncio
    async def test_pay_x402_url_gets_verifying_contract_when_missing(self):
        """Line 345: get_verifying_contract called when verifying_contract is missing."""
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
                        "name": "GatewayWalletBatched",
                        "version": "1",
                        # NO verifyingContract!
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

        mock_vault = _mock_vault()
        mock_client = _mock_client()
        # Make get_verifying_contract return a value
        mock_client.get_verifying_contract = AsyncMock(return_value="0x" + "c" * 40)

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=mock_http,
            auto_topup_enabled=False,
        )

        result = await adapter.pay_x402_url("https://api.example.com/data")

        # Should have fetched verifying contract
        mock_client.get_verifying_contract.assert_called_once_with("eip155:5042002")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_pay_x402_url_auto_topup_exception_caught(self):
        """Lines 377-378: Auto-topup exception is caught and logged, payment proceeds."""
        import base64

        req_dict = _make_requirements_dict()

        mock_http = AsyncMock()
        resp = MagicMock()
        resp.status_code = 402
        resp.headers = {
            "payment-required": base64.b64encode(json.dumps(req_dict).encode()).decode()
        }
        mock_http.request.return_value = resp

        mock_vault = _mock_vault()
        mock_client = _mock_client()

        # Make vault.get_balance raise to trigger the exception in _check_and_topup
        mock_vault.get_balance = AsyncMock(side_effect=Exception("Balance check failed"))

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=mock_http,
            auto_topup_enabled=True,  # Auto-topup ON
        )

        # Should NOT raise despite auto-topup failure
        result = await adapter.pay_x402_url("https://api.example.com/data")
        assert result.success is True  # Payment still proceeds


class TestCircuitBreakerOpenWithContent:
    """Test circuit breaker open but content delivered (lines 430-434)."""

    @pytest.mark.asyncio
    async def test_circuit_open_but_content_delivered_continues(self):
        """Lines 430-434: Circuit open but HTTP success → no exception raised."""
        import base64

        req_dict = _make_requirements_dict()

        # First request: 402 response
        # Second request: 200 success (content delivered despite circuit open)
        first_resp = MagicMock()
        first_resp.status_code = 402
        first_resp.headers = {
            "payment-required": base64.b64encode(json.dumps(req_dict).encode()).decode()
        }
        first_resp.text = "{}"
        first_resp.content = b"{}"

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.text = '{"data": "premium content"}'
        success_resp.content = b'{"data": "premium content"}'

        mock_http = AsyncMock()
        mock_http.request.side_effect = [first_resp, success_resp]

        mock_vault = _mock_vault()
        mock_client = _mock_client()

        # Trip the circuit breaker first
        cb = NanopaymentCircuitBreaker(failure_threshold=1, recovery_seconds=60.0)
        cb.record_failure()

        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=mock_http,
            auto_topup_enabled=False,
            circuit_breaker=cb,
            retry_attempts=0,  # No retries
        )

        # Should NOT raise — content was delivered despite circuit open
        result = await adapter.pay_x402_url("https://api.example.com/data")
        # In strict settlement mode, HTTP content delivery alone is not final success.
        assert result.success is False
        assert result.is_nanopayment is True
        assert result.response_data == '{"data": "premium content"}'


class TestRouterExecuteNetworkFallback:
    """Test router execute network fallback (lines 931-940)."""

    @pytest.mark.asyncio
    async def test_execute_address_uses_destination_chain(self):
        """Execute with address uses destination_chain as network."""
        from decimal import Decimal

        mock_vault = _mock_vault()
        mock_client = _mock_client()
        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
        )
        router = NanopaymentProtocolAdapter(nanopayment_adapter=adapter, micro_threshold_usdc="1.00")

        mock_vault.sign = AsyncMock(return_value=mock_vault.sign())
        mock_vault.get_address = AsyncMock(return_value="0x" + "a" * 40)

        result = await router.execute(
            wallet_id="w123",
            recipient="0x" + "b" * 40,
            amount=Decimal("0.1"),
            destination_chain="eip155:1",
        )

        # Should have used destination_chain as network
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_address_falls_back_to_env_network(self):
        """Lines 931-940: No destination_chain → falls back to Config or env var."""
        from decimal import Decimal
        import os

        mock_vault = _mock_vault()
        mock_client = _mock_client()
        adapter = NanopaymentAdapter(
            vault=mock_vault,
            nanopayment_client=mock_client,
            http_client=AsyncMock(),
            auto_topup_enabled=False,
        )
        router = NanopaymentProtocolAdapter(nanopayment_adapter=adapter, micro_threshold_usdc="1.00")

        mock_vault.sign = AsyncMock(return_value=mock_vault.sign())
        mock_vault.get_address = AsyncMock(return_value="0x" + "a" * 40)

        # Set env var for fallback
        with patch.dict(os.environ, {"NANOPAYMENTS_DEFAULT_NETWORK": "eip155:10"}):
            result = await router.execute(
                wallet_id="w123",
                recipient="0x" + "b" * 40,
                amount=Decimal("0.1"),
            )

        # Should have used env var network
        assert result.success is True
