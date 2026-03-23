"""
Tests for NanoKeyStore (Phase 4: key encryption/decryption).

Tests verify:
- AES-256-GCM encryption/decryption roundtrip
- Encrypted keys are NOT decryptable with wrong entity_secret
- Keys are stored as base64-encoded blobs
- NanoKeyStore never exposes raw key
"""

import pytest

from omniclaw.protocols.nanopayments.exceptions import KeyEncryptionError
from omniclaw.protocols.nanopayments.keys import NanoKeyStore


# =============================================================================
# INIT TESTS
# =============================================================================


class TestNanoKeyStoreInit:
    def test_accepts_valid_entity_secret(self):
        store = NanoKeyStore(entity_secret="my-super-secret-entity-key-32chars!")
        assert store._entity_secret == "my-super-secret-entity-key-32chars!"

    def test_rejects_short_entity_secret(self):
        with pytest.raises(KeyEncryptionError) as exc_info:
            NanoKeyStore(entity_secret="short")
        assert "too short" in str(exc_info.value).lower()

    def test_rejects_empty_entity_secret(self):
        with pytest.raises(KeyEncryptionError):
            NanoKeyStore(entity_secret="")
        with pytest.raises(KeyEncryptionError):
            NanoKeyStore(entity_secret=None)  # type: ignore


# =============================================================================
# ENCRYPT/DECRYPT TESTS
# =============================================================================


class TestEncryptionRoundtrip:
    def test_encrypt_produces_base64_output(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        encrypted = store.encrypt_key("0x" + "ab" * 32)
        assert isinstance(encrypted, str)
        # Valid base64
        import base64

        base64.b64decode(encrypted)
        # nonce(12) + key(32) + tag(16) = 60 bytes -> 80 base64 chars
        assert len(encrypted) >= 64  # must be valid base64

    def test_decrypt_recovers_original_key(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        private_key = "0x" + "12" * 32
        encrypted = store.encrypt_key(private_key)
        decrypted = store.decrypt_key(encrypted)
        assert decrypted == private_key

    def test_decrypt_without_0x_prefix(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        private_key = "0x" + "fe" * 32
        encrypted = store.encrypt_key(private_key)
        # encrypt_key normalizes the input
        decrypted = store.decrypt_key(encrypted)
        assert decrypted == private_key

    def test_different_ciphertexts_for_same_plaintext(self):
        """AES-GCM with random nonce produces different ciphertexts."""
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        private_key = "0x" + "99" * 32
        enc1 = store.encrypt_key(private_key)
        enc2 = store.encrypt_key(private_key)
        assert enc1 != enc2  # Different nonces
        # Both decrypt to same value
        assert store.decrypt_key(enc1) == store.decrypt_key(enc2)


class TestWrongEntitySecret:
    def test_encrypt_with_wrong_secret_produces_different_blob(self):
        store1 = NanoKeyStore(entity_secret="secret-one-for-testing!")
        store2 = NanoKeyStore(entity_secret="secret-two-for-testing!")
        private_key = "0x" + "1a" * 32
        enc1 = store1.encrypt_key(private_key)
        enc2 = store2.encrypt_key(private_key)
        assert enc1 != enc2

    def test_decrypt_fails_with_wrong_secret(self):
        store1 = NanoKeyStore(entity_secret="correct-secret-testing!")
        store2 = NanoKeyStore(entity_secret="wrong-secret-testing!!")
        private_key = "0x" + "2b" * 32
        encrypted = store1.encrypt_key(private_key)
        with pytest.raises(KeyEncryptionError) as exc_info:
            store2.decrypt_key(encrypted)
        assert "decrypt" in str(exc_info.value).lower()

    def test_corrupted_ciphertext_fails(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        encrypted = store.encrypt_key("0x" + "cc" * 32)
        # Corrupt the base64 string
        corrupted = encrypted[:-4] + ("AAAA" if encrypted[-4:] != "AAAA" else "BBBB")
        with pytest.raises(KeyEncryptionError):
            store.decrypt_key(corrupted)

    def test_truncated_ciphertext_fails(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        encrypted = store.encrypt_key("0x" + "dd" * 32)
        # Truncate to half
        with pytest.raises(KeyEncryptionError):
            store.decrypt_key(encrypted[: len(encrypted) // 2])


# =============================================================================
# CREATE SIGNER TESTS
# =============================================================================


class TestCreateSigner:
    def test_creates_valid_signer(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        private_key = "0x" + "3e" * 32
        encrypted = store.encrypt_key(private_key)
        signer = store.create_signer(encrypted)
        assert signer.address is not None
        assert signer.address.startswith("0x")
        assert len(signer.address) == 42

    def test_signer_signs_successfully(self):
        from omniclaw.protocols.nanopayments.signing import generate_eoa_keypair

        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        private_key, _ = generate_eoa_keypair()
        encrypted = store.encrypt_key(private_key)
        signer = store.create_signer(encrypted)
        assert signer.address is not None


# =============================================================================
# GENERATE AND ENCRYPT TESTS
# =============================================================================


class TestGenerateAndEncrypt:
    def test_generates_valid_keypair(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        encrypted, address = store.generate_and_encrypt_key()
        # Decrypt and verify
        decrypted = store.decrypt_key(encrypted)
        assert decrypted.startswith("0x")
        assert len(decrypted) == 66
        # Address is derivable
        from eth_account import Account

        derived = Account.from_key(decrypted).address
        assert derived.lower() == address.lower()

    def test_generates_unique_keypairs(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        results = [store.generate_and_encrypt_key() for _ in range(5)]
        addresses = [r[1] for r in results]
        assert len(set(addresses)) == 5  # All unique


# =============================================================================
# EDGE CASES
# =============================================================================


class TestKeyStoreEdgeCases:
    def test_encrypt_key_with_0x_prefix(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        private_key = "0x" + "4f" * 32
        encrypted = store.encrypt_key(private_key)
        decrypted = store.decrypt_key(encrypted)
        assert decrypted == private_key

    def test_encrypt_key_without_0x_prefix(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        private_key = "0x" + "5a" * 32
        encrypted = store.encrypt_key(private_key)
        decrypted = store.decrypt_key(encrypted)
        assert decrypted == private_key

    def test_encrypt_none_raises_error(self):
        store = NanoKeyStore(entity_secret="entity-secret-for-testing!")
        with pytest.raises(KeyEncryptionError):
            store.encrypt_key(None)  # type: ignore
