"""
Tests for GatewayWalletManager (Phase 5: on-chain operations).

Tests verify:
- Deposit: approval (if needed) + deposit transaction
- Withdraw: withdrawal transaction
- Balance queries via NanopaymentClient
- Error handling for failed transactions

All web3 calls are mocked.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omniclaw.protocols.nanopayments import GatewayWalletManager
from omniclaw.protocols.nanopayments.client import NanopaymentClient
from omniclaw.protocols.nanopayments.exceptions import (
    DepositError,
    ERC20ApprovalError,
    WithdrawError,
)
from omniclaw.protocols.nanopayments.signing import generate_eoa_keypair


# =============================================================================
# TEST HELPERS
# =============================================================================


def _mock_web3(address: str, chain_id: int = 5042002):
    """Create a mock web3 instance."""
    mock_w3 = MagicMock()
    mock_w3.eth.get_transaction_count.return_value = 42
    mock_w3.eth.send_raw_transaction.return_value = b"\x01" * 32
    mock_w3.eth.wait_for_transaction_receipt.return_value = {
        "status": 1,
        "transactionHash": b"\x02" * 32,
    }
    # Gas reserve check mocks
    mock_w3.eth.get_balance.return_value = 10**18  # 1 ETH in wei
    mock_w3.eth.gas_price = MagicMock(return_value=30_000_000_000)  # 30 gwei
    mock_w3.from_wei = lambda v, unit: v / 1e18 if unit == "ether" else v
    mock_account = MagicMock()
    mock_account.sign_transaction.return_value = MagicMock(raw_transaction=b"\x03" * 32)
    mock_w3.eth.account = mock_account
    return mock_w3


def _make_client_mock(
    gateway_addr: str = "0x" + "c" * 40,
    usdc_addr: str = "0x" + "d" * 40,
) -> MagicMock:
    """Mock NanopaymentClient."""
    from omniclaw.protocols.nanopayments.types import GatewayBalance, SettleResponse

    mock = MagicMock(spec=NanopaymentClient)
    mock.get_verifying_contract = AsyncMock(return_value=gateway_addr)
    mock.get_usdc_address = AsyncMock(return_value=usdc_addr)
    mock.check_balance = AsyncMock(
        return_value=GatewayBalance(
            total=5000000,
            available=4500000,
            formatted_total="5.000000 USDC",
            formatted_available="4.500000 USDC",
        )
    )
    mock.settle = AsyncMock(
        return_value=SettleResponse(
            success=True,
            transaction="batch_tx_123",
            payer="0x" + "1" * 40,
            error_reason=None,
        )
    )
    return mock


# =============================================================================
# INIT TESTS
# =============================================================================


class TestGatewayWalletManagerInit:
    def test_derives_address_from_key(self):
        private_key, expected_address = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = _mock_web3(expected_address)
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

        assert manager.address.lower() == expected_address.lower()

    def test_stores_network(self):
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = _mock_web3("")
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:1",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

        assert manager._network == "eip155:1"

    def test_uses_provided_gateway_address(self):
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = _mock_web3("")
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
                gateway_address="0xPreSetGateway000000000000000001",
            )

        assert manager._gateway_address == "0xPreSetGateway000000000000000001"


# =============================================================================
# DEPOSIT TESTS
# =============================================================================


class TestDeposit:
    @pytest.mark.asyncio
    async def test_deposit_approval_not_needed(self):
        """If allowance is sufficient, skip approval."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()
        mock_w3 = _mock_web3("")
        mock_w3.eth.contract = MagicMock()

        # Mock contract: allowance returns large value
        mock_contract = MagicMock()
        mock_contract.functions.allowance.return_value.call.return_value = 100_000_000
        mock_contract.encode_abi.return_value = "0x"
        mock_w3.eth.contract.return_value = mock_contract

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            result = await manager.deposit("10.00")

        assert result.approval_tx_hash is None
        assert result.deposit_tx_hash is not None
        assert result.amount == 10_000_000
        assert "10.00 USDC" in result.formatted_amount

    @pytest.mark.asyncio
    async def test_deposit_approval_needed(self):
        """If allowance is insufficient, approve first."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()
        mock_w3 = _mock_web3("")
        mock_w3.eth.contract = MagicMock()

        mock_contract = MagicMock()
        # Allowance is 0 (insufficient)
        mock_contract.functions.allowance.return_value.call.return_value = 0
        mock_contract.encode_abi.return_value = "0xabcd"
        mock_w3.eth.contract.return_value = mock_contract

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            result = await manager.deposit("5.00")

        assert result.approval_tx_hash is not None
        assert result.deposit_tx_hash is not None
        assert result.amount == 5_000_000

    @pytest.mark.asyncio
    async def test_deposit_transaction_failure(self):
        """Transaction failure raises DepositError."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()
        mock_w3 = _mock_web3("")
        mock_w3.eth.contract = MagicMock()
        mock_w3.eth.wait_for_transaction_receipt.return_value = {"status": 0}

        mock_contract = MagicMock()
        mock_contract.functions.allowance.return_value.call.return_value = 100_000_000
        mock_contract.encode_abi.return_value = "0x"
        mock_w3.eth.contract.return_value = mock_contract

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            with pytest.raises(DepositError):
                await manager.deposit("10.00")

    @pytest.mark.asyncio
    async def test_deposit_catches_other_exceptions(self):
        """Non-transaction exceptions are wrapped as DepositError."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()
        mock_w3 = _mock_web3("")
        mock_w3.eth.contract.side_effect = RuntimeError("RPC error")

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            with pytest.raises(DepositError) as exc_info:
                await manager.deposit("10.00")
            assert "RPC error" in str(exc_info.value)


# =============================================================================
# WITHDRAW TESTS
# =============================================================================


class TestWithdraw:
    @pytest.mark.asyncio
    async def test_withdraw_same_chain(self):
        """Same-chain withdrawal delegates to Gateway settle flow."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()
        mock_w3 = _mock_web3("")
        mock_w3.eth.contract = MagicMock()

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            result = await manager.withdraw("2.50", recipient="0x" + "b" * 40)
            assert result.amount == 2_500_000
            assert result.destination_chain == "eip155:5042002"
            assert result.mint_tx_hash == "batch_tx_123"

    @pytest.mark.asyncio
    async def test_withdraw_cross_chain(self):
        """Cross-chain withdrawal delegates to Gateway settle flow."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()
        mock_w3 = _mock_web3("")

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            result = await manager.withdraw(
                "1.00",
                destination_chain="eip155:1",
                recipient="0x" + "c" * 40,
            )
            assert result.amount == 1_000_000
            assert result.destination_chain == "eip155:1"
            assert result.recipient == "0x" + "c" * 40

    @pytest.mark.asyncio
    async def test_withdraw_same_chain_returns_result(self):
        """Same-chain withdraw returns a structured result."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        manager = GatewayWalletManager(
            private_key=private_key,
            network="eip155:5042002",
            rpc_url="https://rpc.example.com",
            nanopayment_client=client,
        )
        result = await manager.withdraw(
            "1.00",
            destination_chain="eip155:5042002",  # Same chain
            recipient="0x" + "a" * 40,
        )
        assert result.amount == 1_000_000
        assert result.destination_chain == "eip155:5042002"
        assert result.recipient == "0x" + "a" * 40


# =============================================================================
# BALANCE TESTS
# =============================================================================


class TestGetBalance:
    @pytest.mark.asyncio
    async def test_get_balance_delegates_to_client(self):
        """get_balance should delegate to NanopaymentClient.check_balance."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            MockWeb3.return_value = _mock_web3("")
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            balance = await manager.get_balance()

        client.check_balance.assert_called_once_with(
            address=manager.address,
            network="eip155:5042002",
        )
        assert balance.total == 5_000_000
        assert balance.available == 4_500_000
        assert balance.total_decimal == "5.000000"
        assert balance.available_decimal == "4.500000"


# =============================================================================
# GAS RESERVE TESTS
# =============================================================================


class TestGasReserve:
    """Tests for gas reserve checking and management."""

    @pytest.mark.asyncio
    async def test_get_gas_balance_wei(self):
        """get_gas_balance_wei returns ETH balance in wei."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = _mock_web3("")
            mock_w3.eth.get_balance.return_value = 5_000_000_000_000_000_000  # 5 ETH
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            balance = manager.get_gas_balance_wei()

        assert balance == 5_000_000_000_000_000_000

    @pytest.mark.asyncio
    async def test_check_gas_reserve_sufficient(self):
        """check_gas_reserve returns True when ETH balance is sufficient."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = _mock_web3("")
            # 1 ETH = enough for ~5 deposits at 0.2M gas * 30 gwei = 0.006 ETH per deposit
            mock_w3.eth.get_balance.return_value = 10**18  # 1 ETH
            mock_w3.eth.gas_price = 30_000_000_000  # 30 gwei (direct value)
            mock_w3.from_wei = lambda v, unit: v / 1e18 if unit == "ether" else v
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            has_sufficient, message = manager.check_gas_reserve()

        assert has_sufficient is True
        assert "ETH balance:" in message

    @pytest.mark.asyncio
    async def test_check_gas_reserve_insufficient(self):
        """check_gas_reserve returns False when ETH balance is too low."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            # Very low ETH balance - below required reserve
            # gas_cost = 30e9 * 200000 * 1.2 = 7.2e15 wei = 0.0072 ETH
            # required = 2 * 0.0072 = 0.0144 ETH
            # balance = 0.001 ETH = 1e15 wei < 1.44e16 wei (required)
            mock_w3.eth.get_balance.return_value = 1_000_000_000_000_000  # 0.001 ETH
            mock_w3.eth.gas_price = 30_000_000_000  # 30 gwei (attribute)
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.account = MagicMock()

            # Use a real conversion function
            def from_wei(value, unit):
                if unit == "ether":
                    return value / 10**18
                return value

            mock_w3.from_wei = from_wei
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )
            has_sufficient, message = manager.check_gas_reserve()

        assert has_sufficient is False
        assert "ETH balance:" in message

    @pytest.mark.asyncio
    async def test_deposit_skips_gas_check_when_check_gas_false(self):
        """deposit() with check_gas=False skips gas reserve check."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = _mock_web3("")
            MockWeb3.return_value = mock_w3
            mock_w3.eth.contract = MagicMock()

            mock_contract = MagicMock()
            mock_contract.functions.allowance.return_value.call.return_value = 100_000_000
            mock_contract.encode_abi.return_value = "0x"
            mock_w3.eth.contract.return_value = mock_contract

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            # Should NOT raise even without gas balance mock
            result = await manager.deposit("10.00", check_gas=False)

        assert result.amount == 10_000_000

    @pytest.mark.asyncio
    async def test_ensure_gas_reserve_raises_on_insufficient(self):
        """ensure_gas_reserve raises InsufficientGasError when gas is low."""
        from omniclaw.protocols.nanopayments.exceptions import InsufficientGasError

        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            # Very low ETH balance
            mock_w3.eth.get_balance.return_value = 1_000_000_000_000_000  # 0.001 ETH
            mock_w3.eth.gas_price = 30_000_000_000  # 30 gwei (attribute)
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.account = MagicMock()

            def from_wei(value, unit):
                if unit == "ether":
                    return value / 10**18
                return value

            mock_w3.from_wei = from_wei

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            with pytest.raises(InsufficientGasError):
                manager.ensure_gas_reserve()

    @pytest.mark.asyncio
    async def test_deposit_skip_if_insufficient_gas(self):
        """deposit() with skip_if_insufficient_gas=True returns empty result."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            # Very low ETH balance
            mock_w3.eth.get_balance.return_value = 1_000_000_000_000_000  # 0.001 ETH
            mock_w3.eth.gas_price = 30_000_000_000  # 30 gwei (attribute)
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.send_raw_transaction.return_value = b"\x01" * 32
            mock_w3.eth.wait_for_transaction_receipt.return_value = {
                "status": 1,
                "transactionHash": b"\x02" * 32,
            }
            mock_w3.eth.account = MagicMock()
            mock_w3.eth.account.sign_transaction.return_value = MagicMock(
                raw_transaction=b"\x03" * 32
            )

            def from_wei(value, unit):
                if unit == "ether":
                    return value / 10**18
                return value

            mock_w3.from_wei = from_wei

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            result = await manager.deposit(
                "10.00",
                skip_if_insufficient_gas=True,
            )

        assert result.approval_tx_hash is None
        assert result.deposit_tx_hash is None


# =============================================================================
# TRUSTLESS WITHDRAWAL TESTS
# =============================================================================


class TestTrustlessWithdrawal:
    """Tests for emergency trustless withdrawal (on-chain, 7-day delay)."""

    @pytest.mark.asyncio
    async def test_initiate_trustless_withdrawal(self):
        """initiate_trustless_withdrawal() initiates on-chain withdrawal."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_transaction_count.return_value = 10
            mock_w3.eth.send_raw_transaction.return_value = b"\x01" * 32
            mock_w3.eth.wait_for_transaction_receipt.return_value = {
                "status": 1,
                "transactionHash": b"\x02" * 32,
            }
            mock_w3.eth.account = MagicMock()
            mock_w3.eth.get_balance.return_value = 10**18  # 1 ETH
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            # Mock gateway contract
            mock_gateway = MagicMock()
            mock_gateway.functions.availableBalance.return_value.call.return_value = 5_000_000
            mock_gateway.functions.withdrawalDelay.return_value.call.return_value = 6300
            mock_gateway.functions.initiateWithdrawal.return_value = MagicMock()
            mock_gateway.functions.withdraw.return_value = MagicMock()
            mock_w3.eth.contract.return_value = mock_gateway

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            tx_hash = await manager.initiate_trustless_withdrawal("5.00")
            assert tx_hash is not None
            assert len(tx_hash) > 0

    @pytest.mark.asyncio
    async def test_initiate_trustless_withdrawal_insufficient_balance(self):
        """Insufficient balance raises WithdrawError."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_balance.return_value = 10**18
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.account = MagicMock()
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            mock_gateway = MagicMock()
            mock_gateway.functions.availableBalance.return_value.call.return_value = (
                100_000  # Only 0.1 USDC
            )
            mock_gateway.functions.withdrawalDelay.return_value.call.return_value = 6300
            mock_w3.eth.contract.return_value = mock_gateway

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            with pytest.raises(WithdrawError):
                await manager.initiate_trustless_withdrawal("100.00")

    @pytest.mark.asyncio
    async def test_complete_trustless_withdrawal_ready(self):
        """complete_trustless_withdrawal() succeeds when delay passed."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_transaction_count.return_value = 10
            mock_w3.eth.send_raw_transaction.return_value = b"\x03" * 32
            mock_w3.eth.wait_for_transaction_receipt.return_value = {
                "status": 1,
                "transactionHash": b"\x04" * 32,
            }
            mock_w3.eth.account = MagicMock()
            mock_w3.eth.get_balance.return_value = 10**18
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.block_number = 70000
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            mock_gateway = MagicMock()
            mock_gateway.functions.withdrawalBlock.return_value.call.return_value = 69000
            mock_gateway.functions.withdraw.return_value = MagicMock()
            mock_w3.eth.contract.return_value = mock_gateway

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            tx_hash = await manager.complete_trustless_withdrawal()
            assert tx_hash is not None

    @pytest.mark.asyncio
    async def test_complete_trustless_withdrawal_not_ready(self):
        """complete_trustless_withdrawal() raises when delay not passed."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_balance.return_value = 10**18
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.block_number = 69500
            mock_w3.eth.account = MagicMock()
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            mock_gateway = MagicMock()
            mock_gateway.functions.withdrawalBlock.return_value.call.return_value = 69000
            mock_w3.eth.contract.return_value = mock_gateway

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            with pytest.raises(WithdrawError):
                await manager.complete_trustless_withdrawal()

    @pytest.mark.asyncio
    async def test_complete_trustless_withdrawal_no_initiation(self):
        """complete_trustless_withdrawal() raises when no withdrawal initiated."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_balance.return_value = 10**18
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.block_number = 70000
            mock_w3.eth.account = MagicMock()
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            mock_gateway = MagicMock()
            mock_gateway.functions.withdrawalBlock.return_value.call.return_value = (
                0  # No withdrawal
            )
            mock_w3.eth.contract.return_value = mock_gateway

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            with pytest.raises(WithdrawError):
                await manager.complete_trustless_withdrawal()


# =============================================================================
# TRANSFER AND BALANCE TESTS (Additional Coverage)
# =============================================================================


class TestTransferMethods:
    """Tests for API-based transfer methods."""

    @pytest.mark.asyncio
    async def test_transfer_to_address_same_chain(self):
        """transfer_to_address() executes Gateway settlement transfer."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = _mock_web3("")
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            result = await manager.transfer_to_address(
                "10.00",
                recipient_address="0x" + "a" * 40,
            )
            assert result.amount == 10_000_000
            assert result.destination_chain == "eip155:5042002"

    @pytest.mark.asyncio
    async def test_transfer_crosschain(self):
        """transfer_crosschain() executes Gateway settlement transfer."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = _mock_web3("")
            MockWeb3.return_value = mock_w3
            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            result = await manager.transfer_crosschain(
                "5.00",
                destination_chain="eip155:8453",  # Base
                recipient_address="0x" + "b" * 40,
            )
            assert result.amount == 5_000_000
            assert result.destination_chain == "eip155:8453"

    @pytest.mark.asyncio
    async def test_get_onchain_balance(self):
        """get_onchain_balance() returns USDC balance in wallet."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_balance.return_value = 10**18
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.account = MagicMock()
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            mock_usdc = MagicMock()
            mock_usdc.functions.balanceOf.return_value.call.return_value = 1_000_000
            mock_w3.eth.contract.return_value = mock_usdc

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            balance = await manager.get_onchain_balance()
            assert balance == 1_000_000

    @pytest.mark.asyncio
    async def test_get_gateway_available_balance(self):
        """get_gateway_available_balance() queries contract."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_balance.return_value = 10**18
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.account = MagicMock()
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            mock_gateway = MagicMock()
            mock_gateway.functions.availableBalance.return_value.call.return_value = 2_000_000
            mock_w3.eth.contract.return_value = mock_gateway

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            balance = await manager.get_gateway_available_balance()
            assert balance == 2_000_000

    def test_get_gas_balance_eth(self):
        """get_gas_balance_eth() returns ETH balance as decimal string."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_balance.return_value = 10**18  # 1 ETH
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.account = MagicMock()
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            balance = manager.get_gas_balance_eth()
            assert "1" in balance

    def test_estimate_gas_cost_eth(self):
        """estimate_gas_cost_eth() returns ETH cost as decimal string."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_balance.return_value = 10**18
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.account = MagicMock()
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            cost = manager.estimate_gas_cost_eth()
            assert cost is not None
            # Should be > 0
            cost_float = float(cost)
            assert cost_float > 0

    def test_has_sufficient_gas_for_deposit(self):
        """has_sufficient_gas_for_deposit() returns bool."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_balance.return_value = 10**18  # 1 ETH
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.account = MagicMock()
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            assert manager.has_sufficient_gas_for_deposit() is True

    @pytest.mark.asyncio
    async def test_get_withdrawal_delay(self):
        """get_withdrawal_delay() returns delay in blocks."""
        private_key, _ = generate_eoa_keypair()
        client = _make_client_mock()

        with patch("web3.Web3") as MockWeb3:
            mock_w3 = MagicMock()
            MockWeb3.return_value = mock_w3
            mock_w3.eth.get_balance.return_value = 10**18
            mock_w3.eth.gas_price.return_value = 30_000_000_000
            mock_w3.eth.get_transaction_count.return_value = 0
            mock_w3.eth.account = MagicMock()
            mock_w3.from_wei = lambda v, unit: v / 10**18 if unit == "ether" else v

            mock_gateway = MagicMock()
            mock_gateway.functions.withdrawalDelay.return_value.call.return_value = 6300
            mock_w3.eth.contract.return_value = mock_gateway

            manager = GatewayWalletManager(
                private_key=private_key,
                network="eip155:5042002",
                rpc_url="https://rpc.example.com",
                nanopayment_client=client,
            )

            delay = await manager.get_withdrawal_delay()
            assert delay == 6300
