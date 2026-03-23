"""
NanoKeyStore: Internal key encryption/decryption for NanoKeyVault.

This module is NOT exposed to agents. It lives inside NanoKeyVault and
provides the cryptographic primitives for encrypting/decrypting EOA private keys.

Security Design:
    - Master key derived from entity_secret via PBKDF2 (32-byte AES key)
    - EOA private keys encrypted with AES-256-GCM
    - Each encryption uses a random 12-byte nonce
    - Encrypted blobs are base64-encoded for safe storage
    - Raw private key is NEVER stored unencrypted
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from omniclaw.protocols.nanopayments.exceptions import (
    KeyEncryptionError,
)
from omniclaw.protocols.nanopayments.signing import (
    EIP3009Signer,
    generate_eoa_keypair,
)

# PBKDF2 parameters
_PBKDF2_ITERATIONS: int = 480000
"""OWASP recommended minimum for PBKDF2-SHA256 (2023)."""

_PBKDF2_SALT: bytes = b"OmniClaw-NanoKeyVault-v1"
"""Static salt — acceptable since entity_secret is already high-entropy."""


class NanoKeyStore:
    """
    Internal key storage and decryption engine.

    Lives inside NanoKeyVault. NOT exposed to agents.

    Args:
        entity_secret: Circle's entity secret (high-entropy master key).
            Must be at least 32 bytes of entropy.
    """

    def __init__(
        self,
        entity_secret: str,
    ) -> None:
        if not entity_secret or len(entity_secret) < 16:
            raise KeyEncryptionError(
                operation="init",
                reason="entity_secret too short (minimum 16 characters required)",
            )
        self._entity_secret = entity_secret

    def _get_master_key(self) -> bytes:
        """
        Derive a 32-byte AES key from the entity secret using PBKDF2.

        The entity secret is high-entropy (Circle generates it), so a static
        salt is acceptable per OWASP guidance.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_PBKDF2_SALT,
            iterations=_PBKDF2_ITERATIONS,
        )
        return kdf.derive(self._entity_secret.encode("utf-8"))

    def encrypt_key(self, private_key: str) -> str:
        """
        Encrypt an EOA private key using AES-256-GCM.

        Args:
            private_key: Raw EOA private key hex (with or without 0x prefix).

        Returns:
            Base64-encoded ciphertext: 12-byte nonce + ciphertext + 16-byte tag.

        Raises:
            KeyEncryptionError: If encryption fails.
        """
        try:
            # Normalize: remove 0x prefix if present
            key_hex = private_key
            if key_hex.startswith("0x"):
                key_hex = key_hex[2:]
            key_bytes = bytes.fromhex(key_hex)

            master_key = self._get_master_key()
            aesgcm = AESGCM(master_key)
            nonce = os.urandom(12)  # 96-bit nonce for GCM

            # Prepend nonce to ciphertext so it can be extracted during decryption
            encrypted = aesgcm.encrypt(nonce, key_bytes, None)  # None = no associated data
            return base64.b64encode(nonce + encrypted).decode("ascii")
        except Exception as exc:
            raise KeyEncryptionError(
                operation="encrypt",
                reason=str(exc),
            ) from exc

    def decrypt_key(self, encrypted_key: str) -> str:
        """
        Decrypt an encrypted EOA private key.

        Args:
            encrypted_key: Base64-encoded ciphertext from encrypt_key().

        Returns:
            Raw private key hex (with 0x prefix).

        Raises:
            KeyEncryptionError: If decryption fails.
        """
        try:
            ciphertext = base64.b64decode(encrypted_key)
            nonce = ciphertext[:12]
            actual_ciphertext = ciphertext[12:]

            master_key = self._get_master_key()
            aesgcm = AESGCM(master_key)

            key_bytes = aesgcm.decrypt(nonce, actual_ciphertext, None)  # no associated data
            return "0x" + key_bytes.hex()
        except Exception as exc:
            raise KeyEncryptionError(
                operation="decrypt",
                reason=str(exc),
            ) from exc

    def create_signer(self, encrypted_key: str) -> EIP3009Signer:
        """
        Decrypt a key and create an EIP3009Signer.

        The raw private key is held only within the EIP3009Signer instance
        and is never exposed to the caller.

        Args:
            encrypted_key: Encrypted private key blob.

        Returns:
            EIP3009Signer instance ready to sign.

        Raises:
            KeyEncryptionError: If decryption fails.
        """
        raw_key = self.decrypt_key(encrypted_key)
        return EIP3009Signer(raw_key)

    # -------------------------------------------------------------------------
    # Key generation helpers
    # -------------------------------------------------------------------------

    def generate_and_encrypt_key(self) -> tuple[str, str]:
        """
        Generate a new EOA keypair and encrypt the private key.

        Returns:
            Tuple of (encrypted_key, address).
            The operator must fund the address before use.
        """
        private_key, address = generate_eoa_keypair()
        encrypted = self.encrypt_key(private_key)
        return encrypted, address
