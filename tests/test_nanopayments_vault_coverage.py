"""
Additional tests for NanoKeyVault to cover uncovered lines.

Covers:
- default_network property (lines 96-99)
- environment property (lines 101-104)
- get_network() (lines 226-248)
- update_key_network() (lines 250-268)
- list_keys() (lines 297-310)
- get_balance() (lines 429-445)
- get_raw_key() (lines 447-474)
- create_wallet_manager() (lines 480-543)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from omniclaw.protocols.nanopayments.client import NanopaymentClient
from omniclaw.protocols.nanopayments.exceptions import (
    InvalidPrivateKeyError,
    KeyNotFoundError,
    NoDefaultKeyError,
)
from omniclaw.protocols.nanopayments.keys import NanoKeyStore
from omniclaw.protocols.nanopayments.vault import NanoKeyVault


# =============================================================================
# MOCK STORAGE BACKEND
# =============================================================================


class MockStorageBackend:
    """In-memory mock for StorageBackend."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, dict]] = {}

    async def save(
        self,
        collection: str,
        key: str,
        data: dict,
    ) -> None:
        if collection not in self._data:
            self._data[collection] = {}
        self._data[collection][key] = data

    async def get(
        self,
        collection: str,
        key: str,
    ) -> dict | None:
        return self._data.get(collection, {}).get(key)

    async def delete(
        self,
        collection: str,
        key: str,
    ) -> None:
        if collection in self._data and key in self._data[collection]:
            del self._data[collection][key]

    async def query(
        self,
        collection: str,
        limit: int = 100,
    ) -> list[dict]:
        """Query returns list of records for list_keys()."""
        return list(self._data.get(collection, {}).values())

    async def list_keys(self, collection: str) -> list[str]:
        return list(self._data.get(collection, {}).keys())


# =============================================================================
# HARDCODED VALID KEYS (avoid session scope issues with generate_eoa_keypair)
# =============================================================================


PRIVATE_KEY = "0x250716a653d2155d15bfb1e1ded08b6764937ca6ab3cdd7e2f0510c975fb5652"
ADDRESS = "0xb9Ee214552fF51AB41955b3DAfD7A340b5459629"


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def store():
    """A NanoKeyStore for testing."""
    return NanoKeyStore(entity_secret="test-entity-secret-for-vault!")


@pytest.fixture
def storage():
    """A mock storage backend."""
    return MockStorageBackend()


@pytest.fixture
def vault(store, storage):
    """A NanoKeyVault with mocked dependencies."""
    return NanoKeyVault(
        entity_secret="test-entity-secret-for-vault!",
        storage_backend=storage,
        circle_api_key="test-api-key",
        nanopayments_environment="testnet",
    )


@pytest.fixture
def vault_mainnet(store, storage):
    """A NanoKeyVault for mainnet environment."""
    return NanoKeyVault(
        entity_secret="test-entity-secret-for-vault!",
        storage_backend=storage,
        circle_api_key="test-api-key",
        nanopayments_environment="mainnet",
    )


@pytest.fixture
def vault_with_explicit_network(store, storage):
    """A NanoKeyVault with explicit default network."""
    return NanoKeyVault(
        entity_secret="test-entity-secret-for-vault!",
        storage_backend=storage,
        circle_api_key="test-api-key",
        nanopayments_environment="testnet",
        default_network="eip155:421614",  # Arbitrum testnet
    )


# =============================================================================
# DEFAULT_NETWORK PROPERTY TESTS
# =============================================================================


class TestDefaultNetworkProperty:
    def test_default_network_returns_set_value(self, vault_with_explicit_network):
        """Lines 96-99: default_network property returns _default_network."""
        assert vault_with_explicit_network.default_network == "eip155:421614"

    def test_default_network_from_environment_testnet(self, vault):
        """Default network is determined from environment."""
        assert vault.default_network == "eip155:11155111"  # Sepolia

    def test_default_network_from_environment_mainnet(self, vault_mainnet):
        """Mainnet environment gives Ethereum mainnet."""
        assert vault_mainnet.default_network == "eip155:1"


# =============================================================================
# ENVIRONMENT PROPERTY TESTS
# =============================================================================


class TestEnvironmentProperty:
    def test_environment_returns_set_value(self, vault):
        """Lines 101-104: environment property returns _environment."""
        assert vault.environment == "testnet"

    def test_environment_mainnet(self, vault_mainnet):
        assert vault_mainnet.environment == "mainnet"


# =============================================================================
# GET_NETWORK TESTS
# =============================================================================


class TestGetNetwork:
    @pytest.mark.asyncio
    async def test_get_network_returns_stored_network(self, vault, storage):
        """Lines 226-248: get_network returns stored network."""
        await storage.save(
            "nano_keys",
            "test-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:421614",
            },
        )
        network = await vault.get_network("test-key")
        assert network == "eip155:421614"

    @pytest.mark.asyncio
    async def test_get_network_falls_back_to_default(self, vault, storage):
        """If record has no network, falls back to default."""
        await storage.save(
            "nano_keys",
            "test-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": None,
            },
        )
        network = await vault.get_network("test-key")
        assert network == vault.default_network

    @pytest.mark.asyncio
    async def test_get_network_with_alias_none_uses_default(self, vault, storage):
        """Lines 239-241: alias=None uses default key."""
        await storage.save(
            "nano_keys",
            "default-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:421614",
            },
        )
        vault._default_key_alias = "default-key"
        network = await vault.get_network(alias=None)
        assert network == "eip155:421614"

    @pytest.mark.asyncio
    async def test_get_network_no_default_raises(self, vault):
        """Lines 240-241: No default key raises NoDefaultKeyError."""
        vault._default_key_alias = None
        with pytest.raises(NoDefaultKeyError):
            await vault.get_network(alias=None)

    @pytest.mark.asyncio
    async def test_get_network_key_not_found(self, vault, storage):
        """Lines 243-245: Key doesn't exist raises KeyNotFoundError."""
        with pytest.raises(KeyNotFoundError) as exc_info:
            await vault.get_network("nonexistent")
        assert exc_info.value.alias == "nonexistent"


# =============================================================================
# UPDATE_KEY_NETWORK TESTS
# =============================================================================


class TestUpdateKeyNetwork:
    @pytest.mark.asyncio
    async def test_update_key_network_success(self, vault, storage):
        """Lines 250-268: update_key_network updates storage."""
        await storage.save(
            "nano_keys",
            "test-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:421614",
            },
        )
        await vault.update_key_network("test-key", "eip155:1")

        record = await storage.get("nano_keys", "test-key")
        assert record["network"] == "eip155:1"

    @pytest.mark.asyncio
    async def test_update_key_network_not_found(self, vault):
        """Lines 261-263: Key doesn't exist raises KeyNotFoundError."""
        with pytest.raises(KeyNotFoundError) as exc_info:
            await vault.update_key_network("nonexistent", "eip155:1")
        assert exc_info.value.alias == "nonexistent"


# =============================================================================
# LIST_KEYS TESTS
# =============================================================================


class TestListKeys:
    @pytest.mark.asyncio
    async def test_list_keys_returns_aliases(self, vault, storage):
        """Lines 297-310: list_keys queries storage and returns aliases."""
        # Storage query returns records with "key" field
        await storage.save("nano_keys", "key1", {"key": "alias1", "address": ADDRESS})
        await storage.save("nano_keys", "key2", {"key": "alias2", "address": ADDRESS})

        aliases = await vault.list_keys()
        assert "alias1" in aliases
        assert "alias2" in aliases

    @pytest.mark.asyncio
    async def test_list_keys_returns_alias_from_record(self, vault, storage):
        """Uses record.get('key') or record.get('alias')."""
        await storage.save("nano_keys", "entry1", {"alias": "my-alias", "address": ADDRESS})

        aliases = await vault.list_keys()
        assert "my-alias" in aliases

    @pytest.mark.asyncio
    async def test_list_keys_empty_returns_empty_list(self, vault, storage):
        """No keys returns empty list."""
        aliases = await vault.list_keys()
        assert aliases == []


# =============================================================================
# GET_BALANCE TESTS
# =============================================================================


class TestGetBalance:
    @pytest.mark.asyncio
    async def test_get_balance_returns_balance(self, vault, storage):
        """Lines 429-445: get_balance calls get_address, get_network, client.check_balance."""
        await storage.save(
            "nano_keys",
            "test-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:5042002",
            },
        )

        # Mock client.check_balance
        mock_balance = MagicMock()
        mock_balance.total = 5_000_000
        mock_balance.available = 5_000_000
        mock_balance.formatted_total = "5.000000 USDC"
        mock_balance.formatted_available = "5.000000 USDC"
        mock_balance.available_decimal = "5.000000"

        vault._client.check_balance = AsyncMock(return_value=mock_balance)

        balance = await vault.get_balance("test-key")

        assert balance.total == 5_000_000
        assert balance.available == 5_000_000

    @pytest.mark.asyncio
    async def test_get_balance_uses_default_key(self, vault, storage):
        """Uses default key when alias is None."""
        await storage.save(
            "nano_keys",
            "default-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:5042002",
            },
        )
        vault._default_key_alias = "default-key"

        mock_balance = MagicMock()
        mock_balance.total = 1_000_000
        mock_balance.available = 1_000_000
        mock_balance.formatted_total = "1.000000 USDC"
        mock_balance.formatted_available = "1.000000 USDC"
        mock_balance.available_decimal = "1.000000"

        vault._client.check_balance = AsyncMock(return_value=mock_balance)

        balance = await vault.get_balance(alias=None)
        assert balance.total == 1_000_000


# =============================================================================
# GET_RAW_KEY TESTS
# =============================================================================


class TestGetRawKey:
    @pytest.mark.asyncio
    async def test_get_raw_key_decrypts_and_returns(self, vault, storage):
        """Lines 447-474: get_raw_key decrypts and returns raw key."""
        # Add a key using the vault
        stored_address = await vault.add_key("test-key", PRIVATE_KEY)
        assert stored_address == ADDRESS

        # Get the raw key
        raw_key = await vault.get_raw_key("test-key")
        assert raw_key == PRIVATE_KEY

    @pytest.mark.asyncio
    async def test_get_raw_key_no_default_raises(self, vault):
        """Lines 465-467: No default key raises NoDefaultKeyError."""
        vault._default_key_alias = None
        with pytest.raises(NoDefaultKeyError):
            await vault.get_raw_key(alias=None)

    @pytest.mark.asyncio
    async def test_get_raw_key_not_found_raises(self, vault, storage):
        """Lines 469-471: Key not found raises KeyNotFoundError."""
        with pytest.raises(KeyNotFoundError) as exc_info:
            await vault.get_raw_key("nonexistent")
        assert exc_info.value.alias == "nonexistent"


# =============================================================================
# CREATE_WALLET_MANAGER TESTS
# =============================================================================


class TestCreateWalletManager:
    @pytest.mark.asyncio
    async def test_create_wallet_manager_requires_rpc_url(self, vault, storage):
        """Lines 527-531: Raises ValueError when rpc_url is None and no env vars."""
        await storage.save(
            "nano_keys",
            "test-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:1",
            },
        )

        # No RPC URL and no env vars set
        with pytest.raises(ValueError) as exc_info:
            vault.create_wallet_manager("test-key", rpc_url=None)

        assert "rpc_url is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_wallet_manager_with_rpc_url(self, vault, storage):
        """Lines 535-543: With explicit rpc_url, creates manager."""
        await storage.save(
            "nano_keys",
            "test-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:1",
            },
        )

        with patch("omniclaw.protocols.nanopayments.wallet.GatewayWalletManager") as MockManager:
            MockManager.return_value = MagicMock()

            manager = vault.create_wallet_manager(
                alias="test-key",
                rpc_url="https://rpc.example.com",
            )

            MockManager.assert_called_once()
            call_kwargs = MockManager.call_args.kwargs
            assert call_kwargs["rpc_url"] == "https://rpc.example.com"
            assert call_kwargs["network"] == vault.default_network

    @pytest.mark.asyncio
    async def test_create_wallet_manager_uses_env_rpc(self, vault, storage):
        """Lines 520-525: Uses RPC_URL from environment."""
        await storage.save(
            "nano_keys",
            "test-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:1",
            },
        )

        with patch.dict("os.environ", {"RPC_URL": "https://env-rpc.example.com"}):
            with patch(
                "omniclaw.protocols.nanopayments.wallet.GatewayWalletManager"
            ) as MockManager:
                MockManager.return_value = MagicMock()

                manager = vault.create_wallet_manager(
                    alias="test-key",
                    rpc_url=None,  # Not provided
                )

                call_kwargs = MockManager.call_args.kwargs
                assert call_kwargs["rpc_url"] == "https://env-rpc.example.com"

    @pytest.mark.asyncio
    async def test_create_wallet_manager_uses_network_specific_env(self, vault, storage):
        """Lines 520-522: Uses network-specific RPC_URL_EIP155_X env var."""
        await storage.save(
            "nano_keys",
            "test-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:1",
            },
        )

        # The default network for testnet is eip155:11155111
        with patch.dict(
            "os.environ", {"RPC_URL_EIP155_11155111": "https://network-rpc.example.com"}
        ):
            with patch(
                "omniclaw.protocols.nanopayments.wallet.GatewayWalletManager"
            ) as MockManager:
                MockManager.return_value = MagicMock()

                manager = vault.create_wallet_manager(
                    alias="test-key",
                    rpc_url=None,
                )

                call_kwargs = MockManager.call_args.kwargs
                assert call_kwargs["rpc_url"] == "https://network-rpc.example.com"

    @pytest.mark.asyncio
    async def test_create_wallet_manager_with_explicit_params(self, vault, storage):
        """Passes through gateway_address, usdc_address, cctp_gateway_address."""
        await storage.save(
            "nano_keys",
            "test-key",
            {
                "encrypted_key": "encrypted",
                "address": ADDRESS,
                "network": "eip155:1",
            },
        )

        with patch("omniclaw.protocols.nanopayments.wallet.GatewayWalletManager") as MockManager:
            MockManager.return_value = MagicMock()

            manager = vault.create_wallet_manager(
                alias="test-key",
                rpc_url="https://rpc.example.com",
                gateway_address="0xGateway123",
                usdc_address="0xUSDC456",
                cctp_gateway_address="0xCCTP789",
            )

            call_kwargs = MockManager.call_args.kwargs
            assert call_kwargs["gateway_address"] == "0xGateway123"
            assert call_kwargs["usdc_address"] == "0xUSDC456"
            assert call_kwargs["cctp_gateway_address"] == "0xCCTP789"


# =============================================================================
# ADD KEY ERROR HANDLING (line 140-143)
# =============================================================================


class TestAddKeyErrorHandling:
    """Test add_key error paths (lines 140-143)."""

    @pytest.mark.asyncio
    async def test_add_key_invalid_hex_raises(self, vault):
        """Line 140-143: Invalid private key hex raises InvalidPrivateKeyError."""
        with pytest.raises(InvalidPrivateKeyError):
            await vault.add_key(
                "bad-key", "0xZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ"
            )
