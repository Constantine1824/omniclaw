"""
Tests for NanoKeyVault (Phase 4: SDK-level key management).

Tests verify:
- Keys are encrypted before storage
- Raw key never exposed
- Default key management
- Signing with correct alias routing
"""

import pytest

from omniclaw.protocols.nanopayments.client import NanopaymentClient
from omniclaw.protocols.nanopayments.exceptions import (
    DuplicateKeyAliasError,
    KeyNotFoundError,
    NoDefaultKeyError,
)
from omniclaw.protocols.nanopayments.keys import NanoKeyStore
from omniclaw.protocols.nanopayments.signing import EIP3009Signer, generate_eoa_keypair
from omniclaw.protocols.nanopayments.types import (
    PaymentRequirementsExtra,
    PaymentRequirementsKind,
)
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

    async def list_keys(self, collection: str) -> list[str]:
        return list(self._data.get(collection, {}).keys())


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
def buyer_keypair():
    return generate_eoa_keypair()


@pytest.fixture
def gateway_keypair():
    """Real gateway contract keypair for requirements."""
    return generate_eoa_keypair()


@pytest.fixture
def valid_requirements(buyer_keypair, gateway_keypair):
    return PaymentRequirementsKind(
        scheme="exact",
        network="eip155:5042002",
        asset="0xAbc1234567890aBcD1234567890aBcD12345678",  # Fake USDC address
        amount="1000000",
        max_timeout_seconds=345600,
        pay_to="0x" + "b" * 40,  # Fake seller (doesn't need to be real)
        extra=PaymentRequirementsExtra(
            name="GatewayWalletBatched",
            version="1",
            verifying_contract=gateway_keypair[1],  # Real checksummed address
        ),
    )


# =============================================================================
# ADD KEY TESTS
# =============================================================================


class TestAddKey:
    @pytest.mark.asyncio
    async def test_add_key_stores_encrypted_blob(self, vault, storage, buyer_keypair):
        private_key, address = buyer_keypair
        stored_address = await vault.add_key("alice", private_key)

        assert stored_address == address
        record = await storage.get("nano_keys", "alice")
        assert record is not None
        assert "encrypted_key" in record
        assert record["address"] == address
        # Raw key should NOT be stored
        assert "private_key" not in record
        assert private_key not in str(record)

    @pytest.mark.asyncio
    async def test_add_key_without_0x_prefix(self, vault, storage):
        """Should work with or without 0x prefix."""
        private_key, address = generate_eoa_keypair()
        stored_address = await vault.add_key("bob", private_key)
        assert stored_address == address

    @pytest.mark.asyncio
    async def test_add_key_rejects_duplicate_alias(self, vault, buyer_keypair):
        private_key, _ = buyer_keypair
        await vault.add_key("alice", private_key)
        with pytest.raises(DuplicateKeyAliasError) as exc_info:
            await vault.add_key("alice", private_key)
        assert exc_info.value.alias == "alice"


# =============================================================================
# GENERATE KEY TESTS
# =============================================================================


class TestGenerateKey:
    @pytest.mark.asyncio
    async def test_generate_key_stores_encrypted_blob(self, vault, storage):
        address = await vault.generate_key("charlie")

        assert address.startswith("0x")
        assert len(address) == 42
        record = await storage.get("nano_keys", "charlie")
        assert record is not None
        assert "encrypted_key" in record
        assert record["address"] == address

    @pytest.mark.asyncio
    async def test_generate_key_rejects_duplicate_alias(self, vault):
        await vault.generate_key("dave")
        with pytest.raises(DuplicateKeyAliasError):
            await vault.generate_key("dave")

    @pytest.mark.asyncio
    async def test_generated_key_can_sign(self, vault, valid_requirements):
        address = await vault.generate_key("eve")
        payload = await vault.sign(
            requirements=valid_requirements,
            amount_atomic=1000000,
            alias="eve",
        )
        assert payload.payload.authorization.from_address.lower() == address.lower()
        assert payload.payload.authorization.value == "1000000"


# =============================================================================
# DEFAULT KEY TESTS
# =============================================================================


class TestDefaultKey:
    @pytest.mark.asyncio
    async def test_set_default_key(self, vault, buyer_keypair):
        private_key, _ = buyer_keypair
        await vault.add_key("alice", private_key)
        await vault.set_default_key("alice")

        # Default alias is set correctly
        assert vault._default_key_alias == "alice"
        # Can get address without specifying alias
        address = await vault.get_address(alias=None)
        assert address.startswith("0x")

    @pytest.mark.asyncio
    async def test_set_default_key_unknown_alias(self, vault):
        with pytest.raises(KeyNotFoundError):
            await vault.set_default_key("nonexistent")

    @pytest.mark.asyncio
    async def test_sign_without_alias_uses_default(self, vault, buyer_keypair, valid_requirements):
        private_key, _ = buyer_keypair
        await vault.add_key("frank", private_key)
        await vault.set_default_key("frank")
        # Sign without specifying alias
        payload = await vault.sign(
            requirements=valid_requirements,
            amount_atomic=1000000,
            alias=None,
        )
        assert payload is not None


# =============================================================================
# GET ADDRESS TESTS
# =============================================================================


class TestGetAddress:
    @pytest.mark.asyncio
    async def test_get_address_returns_stored_address(self, vault, buyer_keypair):
        private_key, address = buyer_keypair
        await vault.add_key("grace", private_key)
        retrieved = await vault.get_address("grace")
        assert retrieved == address

    @pytest.mark.asyncio
    async def test_get_address_unknown_alias_raises(self, vault):
        with pytest.raises(KeyNotFoundError) as exc_info:
            await vault.get_address("nonexistent")
        assert exc_info.value.alias == "nonexistent"

    @pytest.mark.asyncio
    async def test_get_address_no_default_raises(self, vault):
        with pytest.raises(NoDefaultKeyError):
            await vault.get_address(alias=None)


# =============================================================================
# HAS KEY TESTS
# =============================================================================


class TestHasKey:
    @pytest.mark.asyncio
    async def test_has_key_returns_true_for_existing(self, vault, buyer_keypair):
        private_key, _ = buyer_keypair
        await vault.add_key("heidi", private_key)
        assert await vault.has_key("heidi") is True

    @pytest.mark.asyncio
    async def test_has_key_returns_false_for_nonexistent(self, vault):
        assert await vault.has_key("nonexistent") is False

    @pytest.mark.asyncio
    async def test_has_key_with_default(self, vault, buyer_keypair):
        private_key, _ = buyer_keypair
        await vault.add_key("ivan", private_key)
        await vault.set_default_key("ivan")
        assert await vault.has_key(alias=None) is True


# =============================================================================
# SIGN TESTS (CORE SECURITY TEST)
# =============================================================================


class TestSign:
    @pytest.mark.asyncio
    async def test_sign_returns_payment_payload(self, vault, buyer_keypair, valid_requirements):
        private_key, _ = buyer_keypair
        await vault.add_key("judith", private_key)
        payload = await vault.sign(
            requirements=valid_requirements,
            amount_atomic=1000000,
            alias="judith",
        )
        assert payload.x402_version == 2
        assert payload.scheme == "exact"
        assert payload.network == "eip155:5042002"
        assert payload.payload.signature.startswith("0x")

    @pytest.mark.asyncio
    async def test_sign_uses_requirements_amount_when_not_specified(
        self, vault, buyer_keypair, valid_requirements
    ):
        """If amount_atomic is None, should use requirements.amount."""
        private_key, _ = buyer_keypair
        await vault.add_key("klaus", private_key)
        payload = await vault.sign(
            requirements=valid_requirements,
            alias="klaus",
        )
        assert payload.payload.authorization.value == "1000000"

    @pytest.mark.asyncio
    async def test_sign_unknown_alias_raises(self, vault, valid_requirements):
        with pytest.raises(KeyNotFoundError):
            await vault.sign(requirements=valid_requirements, alias="nonexistent")

    @pytest.mark.asyncio
    async def test_sign_no_default_raises(self, vault, valid_requirements):
        with pytest.raises(NoDefaultKeyError):
            await vault.sign(requirements=valid_requirements, alias=None)

    @pytest.mark.asyncio
    async def test_sign_signature_is_valid(self, vault, buyer_keypair, valid_requirements):
        """Verify the signature can be recovered with eth_account."""
        private_key, _ = buyer_keypair
        await vault.add_key("laura", private_key)
        payload = await vault.sign(
            requirements=valid_requirements,
            amount_atomic=500000,
            alias="laura",
        )
        # Verify locally
        from omniclaw.protocols.nanopayments.signing import (
            build_eip712_domain,
            build_eip712_structured_data,
        )
        from eth_account.messages import encode_typed_data
        from eth_account import Account

        chain_id = 5042002
        domain = build_eip712_domain(
            chain_id=chain_id,
            verifying_contract=valid_requirements.extra.verifying_contract,
        )
        auth = payload.payload.authorization
        message_dict = {
            "from": auth.from_address,
            "to": auth.to,
            "value": int(auth.value),
            "validAfter": int(auth.valid_after),
            "validBefore": int(auth.valid_before),
            "nonce": auth.nonce,
        }
        structured_data = build_eip712_structured_data(domain, message_dict)
        signable = encode_typed_data(full_message=structured_data)
        recovered = Account.recover_message(signable, signature=payload.payload.signature)
        assert recovered.lower() == payload.payload.authorization.from_address.lower()


# =============================================================================
# RAW KEY SECURITY TESTS
# =============================================================================


class TestRawKeySecurity:
    @pytest.mark.asyncio
    async def test_raw_key_never_in_storage(self, vault, storage, buyer_keypair):
        """Encrypted blob in storage must NOT contain raw private key."""
        private_key, _ = buyer_keypair
        await vault.add_key("mallory", private_key)
        record = await storage.get("nano_keys", "mallory")
        # Raw key hex characters must NOT appear in storage
        raw_hex = private_key.lstrip("0x")
        assert raw_hex not in str(record)

    @pytest.mark.asyncio
    async def test_vault_sign_never_returns_raw_key(self, vault, buyer_keypair, valid_requirements):
        """vault.sign() must return PaymentPayload, never a raw key."""
        private_key, _ = buyer_keypair
        await vault.add_key("nancy", private_key)
        payload = await vault.sign(
            requirements=valid_requirements,
            alias="nancy",
        )
        # Must not contain raw key
        raw_hex = private_key.lstrip("0x")
        assert raw_hex not in payload.to_dict().__repr__()
        # Must be a PaymentPayload
        from omniclaw.protocols.nanopayments.types import PaymentPayload

        assert isinstance(payload, PaymentPayload)


# =============================================================================
# KEY ROTATION TESTS
# =============================================================================


class TestRotateKey:
    @pytest.mark.asyncio
    async def test_rotate_key_returns_new_address(self, vault, buyer_keypair):
        """Rotated key must have a different address."""
        private_key, _ = buyer_keypair
        await vault.add_key("olivia", private_key)
        original_address = await vault.get_address("olivia")
        new_address = await vault.rotate_key("olivia")
        assert new_address != original_address
        assert new_address.startswith("0x")

    @pytest.mark.asyncio
    async def test_rotate_key_unknown_alias_raises(self, vault):
        with pytest.raises(KeyNotFoundError):
            await vault.rotate_key("nonexistent")

    @pytest.mark.asyncio
    async def test_new_key_can_sign_after_rotation(self, vault, buyer_keypair, valid_requirements):
        private_key, _ = buyer_keypair
        await vault.add_key("peter", private_key)
        new_address = await vault.rotate_key("peter")
        # Sign with new key
        payload = await vault.sign(
            requirements=valid_requirements,
            amount_atomic=500000,
            alias="peter",
        )
        assert payload.payload.authorization.from_address.lower() == new_address.lower()
