"""
NanoKeyVault: Secure EOA key management for OmniClaw nanopayments.

This is the SDK-level vault that lives on the OmniClaw instance (not on agents).
Agents hold only `nano_key_alias` (a string reference) — never the raw key.

Key Security Flow:
    Operator adds/generates key:
        private_key -> NanoKeyStore.encrypt_key(entity_secret) -> encrypted_blob
        encrypted_blob -> StorageBackend.save()

    Signing happens:
        StorageBackend.get() -> encrypted_blob
        NanoKeyStore.decrypt_key(entity_secret) -> raw_key
        raw_key -> EIP3009Signer -> sign() -> PaymentPayload
        (raw_key NEVER leaves the vault)

Usage:
    vault = NanoKeyVault(entity_secret="...", storage_backend=..., circle_api_key="...")
    vault.generate_key("alice-nano")
    payload = vault.sign(requirements=req, amount_atomic=1000, alias="alice-nano")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from omniclaw.protocols.nanopayments.client import NanopaymentClient
from omniclaw.protocols.nanopayments.exceptions import (
    DuplicateKeyAliasError,
    KeyNotFoundError,
    NoDefaultKeyError,
)
from omniclaw.protocols.nanopayments.keys import NanoKeyStore

if TYPE_CHECKING:
    from omniclaw.protocols.nanopayments.types import (
        GatewayBalance,
        PaymentPayload,
        PaymentRequirementsKind,
        ResourceInfo,
    )
    from omniclaw.protocols.nanopayments.wallet import GatewayWalletManager
    from omniclaw.storage.base import StorageBackend

logger = logging.getLogger(__name__)

# Storage collection name for encrypted keys
_NANO_KEYS_COLLECTION: str = "nano_keys"
"""StorageBackend collection name for encrypted EOA keys."""

# Default networks by environment
_DEFAULT_NETWORKS = {
    "mainnet": "eip155:1",  # Ethereum mainnet
    "testnet": "eip155:5042002",  # Arc testnet (Circle Gateway default)
}


class NanoKeyVault:
    """
    Secure EOA key vault for Circle Gateway nanopayments.

    Lives on the SDK instance (not on agents). Manages encryption,
    storage, and signing of EOA private keys.

    Args:
        entity_secret: Circle's entity secret (master encryption key).
        storage_backend: Pluggable storage backend for encrypted blobs.
        circle_api_key: Circle API key for Gateway balance queries.
        nanopayments_environment: 'testnet' or 'mainnet'.
        default_network: Default CAIP-2 network (e.g., 'eip155:1').
            If None, determined from environment.
    """

    def __init__(
        self,
        entity_secret: str,
        storage_backend: StorageBackend,
        circle_api_key: str,
        nanopayments_environment: str = "testnet",
        default_network: str | None = None,
    ) -> None:
        self._keystore = NanoKeyStore(entity_secret=entity_secret)
        self._storage = storage_backend
        self._environment = nanopayments_environment
        self._client = NanopaymentClient(
            environment=nanopayments_environment,
            api_key=circle_api_key,
        )
        # Key metadata: alias -> {encrypted_key, address, created_at, network}
        self._default_key_alias: str | None = None

        # Default network - determined from environment or explicitly set
        if default_network:
            self._default_network = default_network
        else:
            self._default_network = _DEFAULT_NETWORKS.get(
                nanopayments_environment, _DEFAULT_NETWORKS["testnet"]
            )

    @property
    def default_network(self) -> str:
        """Get the default CAIP-2 network."""
        return self._default_network

    @property
    def environment(self) -> str:
        """Get the nanopayments environment (testnet/mainnet)."""
        return self._environment

    # -------------------------------------------------------------------------
    # Key management
    # -------------------------------------------------------------------------

    async def add_key(
        self,
        alias: str,
        private_key: str,
        network: str | None = None,
    ) -> str:
        """
        Import an existing EOA private key into the vault.

        Encrypts the key and stores it under the given alias.

        Args:
            alias: Unique identifier for this key (e.g. "alice-nano").
            private_key: EOA private key hex (with or without 0x prefix).
            network: CAIP-2 network for this key. If None, uses default network.

        Returns:
            The EOA address derived from the key.

        Raises:
            DuplicateKeyAliasError: If a key with this alias already exists.
        """
        from eth_account import Account

        # Derive address from private key directly (no need for full EIP3009Signer)
        try:
            # Normalize key: add 0x if missing
            key_hex = private_key if private_key.startswith("0x") else f"0x{private_key}"
            account = Account.from_key(key_hex)
            address = account.address
        except Exception as exc:
            from omniclaw.protocols.nanopayments.exceptions import InvalidPrivateKeyError

            raise InvalidPrivateKeyError(reason=str(exc)) from exc

        existing = await self._storage.get(_NANO_KEYS_COLLECTION, alias)
        if existing is not None:
            raise DuplicateKeyAliasError(alias=alias)

        encrypted = self._keystore.encrypt_key(private_key)

        # Use provided network or default
        key_network = network or self._default_network

        await self._storage.save(
            _NANO_KEYS_COLLECTION,
            alias,
            {
                "encrypted_key": encrypted,
                "address": address,
                "network": key_network,
            },
        )

        logger.info(f"Added key '{alias}' for address {address} on network {key_network}")

        return address

    async def generate_key(
        self,
        alias: str,
        network: str | None = None,
    ) -> str:
        """
        Generate a new EOA keypair and store it encrypted in the vault.

        Args:
            alias: Unique identifier for this key.
            network: CAIP-2 network for this key. If None, uses default network.

        Returns:
            The new EOA address. The operator must fund this address
            before it can be used for payments.

        Raises:
            DuplicateKeyAliasError: If a key with this alias already exists.
        """
        existing = await self._storage.get(_NANO_KEYS_COLLECTION, alias)
        if existing is not None:
            raise DuplicateKeyAliasError(alias=alias)

        encrypted, address = self._keystore.generate_and_encrypt_key()

        # Use provided network or default
        key_network = network or self._default_network

        await self._storage.save(
            _NANO_KEYS_COLLECTION,
            alias,
            {
                "encrypted_key": encrypted,
                "address": address,
                "network": key_network,
            },
        )

        logger.info(f"Generated key '{alias}' for address {address} on network {key_network}")

        return address

    async def set_default_key(self, alias: str) -> None:
        """
        Set the default key for agents that don't specify a nano_key_alias.

        Args:
            alias: The key alias to set as default.

        Raises:
            KeyNotFoundError: If no key with this alias exists.
        """
        record = await self._storage.get(_NANO_KEYS_COLLECTION, alias)
        if record is None:
            raise KeyNotFoundError(alias=alias)
        self._default_key_alias = alias

    async def get_network(self, alias: str | None = None) -> str:
        """
        Get the CAIP-2 network for a key.

        Args:
            alias: Key alias. If None, uses the default key.

        Returns:
            The CAIP-2 network (e.g., 'eip155:1').

        Raises:
            KeyNotFoundError: If the alias doesn't exist.
            NoDefaultKeyError: If alias is None and no default key is set.
        """
        resolved_alias = alias or self._default_key_alias
        if resolved_alias is None:
            raise NoDefaultKeyError()

        record = await self._storage.get(_NANO_KEYS_COLLECTION, resolved_alias)
        if record is None:
            raise KeyNotFoundError(alias=resolved_alias)

        # Return stored network or fall back to default
        return record.get("network") or self._default_network

    async def update_key_network(self, alias: str, network: str) -> None:
        """
        Update the network for an existing key.

        Args:
            alias: The key alias.
            network: The new CAIP-2 network.

        Raises:
            KeyNotFoundError: If no key with this alias exists.
        """
        record = await self._storage.get(_NANO_KEYS_COLLECTION, alias)
        if record is None:
            raise KeyNotFoundError(alias=alias)

        record["network"] = network
        await self._storage.save(_NANO_KEYS_COLLECTION, alias, record)

        logger.info(f"Updated network for key '{alias}' to {network}")

    # -------------------------------------------------------------------------
    # Address lookups
    # -------------------------------------------------------------------------

    async def get_address(self, alias: str | None = None) -> str:
        """
        Get the EOA address for a key alias.

        Args:
            alias: Key alias. If None, uses the default key.

        Returns:
            The EOA address (checksummed).

        Raises:
            KeyNotFoundError: If the alias doesn't exist.
            NoDefaultKeyError: If alias is None and no default key is set.
        """
        resolved_alias = alias or self._default_key_alias
        if resolved_alias is None:
            raise NoDefaultKeyError()

        record = await self._storage.get(_NANO_KEYS_COLLECTION, resolved_alias)
        if record is None:
            raise KeyNotFoundError(alias=resolved_alias)
        return record["address"]

    async def list_keys(self) -> list[str]:
        """
        List all key aliases in the vault.

        Returns:
            List of key aliases (safe to expose to operators).
            Does NOT return the actual keys.
        """
        records = await self._storage.query(_NANO_KEYS_COLLECTION, limit=1000)
        aliases: list[str] = []
        for record in records:
            alias = record.get("_key") or record.get("key") or record.get("alias")
            if alias:
                aliases.append(str(alias))
        return aliases

    async def has_key(self, alias: str | None = None) -> bool:
        """
        Check whether a key exists in the vault.

        Args:
            alias: Key alias. If None, checks for a default key.

        Returns:
            True if the key exists, False otherwise.
        """
        try:
            await self.get_address(alias)
            return True
        except (KeyNotFoundError, NoDefaultKeyError):
            return False

    # -------------------------------------------------------------------------
    # Signing (raw key never exposed)
    # -------------------------------------------------------------------------

    async def sign(
        self,
        requirements: PaymentRequirementsKind,
        amount_atomic: int | None = None,
        alias: str | None = None,
        network: str | None = None,
        resource: ResourceInfo | None = None,
    ) -> PaymentPayload:
        """
        Sign an EIP-3009 payment authorization.

        Decrypts the key internally, creates a signer, signs the authorization,
        and returns the PaymentPayload. The raw private key is held only within
        the signer and is never exposed.

        Args:
            requirements: The PaymentRequirementsKind from the seller's 402 response.
            amount_atomic: Payment amount in USDC atomic units.
                If None, uses requirements.amount.
            alias: Key alias. If None, uses the default key.
            network: Override the network for this payment.
                If None, uses the key's stored network.
            resource: ResourceInfo for the payment. Required by Circle Gateway.

        Returns:
            Signed PaymentPayload ready for Gateway settlement.

        Raises:
            KeyNotFoundError: If the alias doesn't exist.
            NoDefaultKeyError: If alias is None and no default key is set.
        """
        resolved_alias = alias or self._default_key_alias
        if resolved_alias is None:
            raise NoDefaultKeyError()

        record = await self._storage.get(_NANO_KEYS_COLLECTION, resolved_alias)
        if record is None:
            raise KeyNotFoundError(alias=resolved_alias)

        encrypted_key = record["encrypted_key"]
        signer = self._keystore.create_signer(encrypted_key)
        key_network = network or record.get("network") or self._default_network
        if key_network != requirements.network:
            raise ValueError(
                f"Network mismatch for key '{resolved_alias}': key={key_network}, "
                f"requirements={requirements.network}"
            )

        # Amount: use provided value or fall back to requirements.amount
        if amount_atomic is None:
            amount_atomic = int(requirements.amount)

        payload = signer.sign_transfer_with_authorization(
            requirements=requirements,
            amount_atomic=amount_atomic,
        )

        # Attach resource info (required by Circle Gateway)
        if resource is not None:
            # PaymentPayload is frozen, so we need to recreate it
            from omniclaw.protocols.nanopayments.types import PaymentPayload

            payload = PaymentPayload(
                x402_version=payload.x402_version,
                scheme=payload.scheme,
                network=payload.network,
                payload=payload.payload,
                resource=resource,
            )

        return payload

    # -------------------------------------------------------------------------
    # Key rotation
    # -------------------------------------------------------------------------

    async def rotate_key(self, alias: str, network: str | None = None) -> str:
        """
        Generate a new key and replace the existing one.

        The old key remains stored (for pending payment finalization).
        The new key is returned; the operator must fund the new address.

        Args:
            alias: The key to rotate.
            network: New network for the rotated key. If None, keeps old network.

        Returns:
            The new EOA address.

        Raises:
            KeyNotFoundError: If no key with this alias exists.
        """
        existing = await self._storage.get(_NANO_KEYS_COLLECTION, alias)
        if existing is None:
            raise KeyNotFoundError(alias=alias)

        # Keep old network unless explicitly changed
        key_network = network or existing.get("network") or self._default_network

        new_encrypted, new_address = self._keystore.generate_and_encrypt_key()

        await self._storage.save(
            _NANO_KEYS_COLLECTION,
            alias,
            {
                "encrypted_key": new_encrypted,
                "address": new_address,
                "network": key_network,
            },
        )

        logger.info(f"Rotated key '{alias}' to new address {new_address}")

        return new_address

    # -------------------------------------------------------------------------
    # Balance queries
    # -------------------------------------------------------------------------

    async def get_balance(self, alias: str | None = None) -> GatewayBalance:
        """
        Get the Gateway wallet balance for a key's address.

        Args:
            alias: Key alias. If None, uses the default key.

        Returns:
            GatewayBalance with total, available, and formatted amounts.

        Raises:
            KeyNotFoundError: If the alias doesn't exist.
            NoDefaultKeyError: If alias is None and no default key is set.
        """
        address = await self.get_address(alias)
        network = await self.get_network(alias)
        return await self._client.check_balance(address=address, network=network)

    async def get_raw_key(self, alias: str | None = None) -> str:
        """
        Get the raw (decrypted) private key for gateway operations.

        WARNING: This exposes the raw private key in memory. Only use this
        for gateway on-chain operations (deposit/withdraw). The raw key
        never leaves the server/process.

        Args:
            alias: Key alias. If None, uses the default key.

        Returns:
            The raw EOA private key hex (with 0x prefix).

        Raises:
            KeyNotFoundError: If the alias doesn't exist.
            NoDefaultKeyError: If alias is None and no default key is set.
        """
        resolved_alias = alias or self._default_key_alias
        if resolved_alias is None:
            raise NoDefaultKeyError()

        record = await self._storage.get(_NANO_KEYS_COLLECTION, resolved_alias)
        if record is None:
            raise KeyNotFoundError(alias=resolved_alias)

        encrypted_key = record["encrypted_key"]
        return self._keystore.decrypt_key(encrypted_key)

    # -------------------------------------------------------------------------
    # Gateway Wallet Manager integration
    # -------------------------------------------------------------------------

    async def create_wallet_manager(
        self,
        alias: str | None = None,
        rpc_url: str | None = None,
        gateway_address: str | None = None,
        usdc_address: str | None = None,
        cctp_gateway_address: str | None = None,
    ) -> GatewayWalletManager:
        """
        Create a GatewayWalletManager for on-chain operations.

        This creates a wallet manager bound to a specific key, using
        the key's stored network.

        Args:
            alias: Key alias. If None, uses the default key.
            rpc_url: RPC endpoint for the key's network.
            gateway_address: Gateway contract address (fetched from API if None).
            usdc_address: USDC contract address (fetched from API if None).
            cctp_gateway_address: CCTP gateway for cross-chain withdrawals.

        Returns:
            GatewayWalletManager configured for this key.

        Raises:
            RuntimeError: If RPC URL is not provided and no default is configured.
            KeyNotFoundError: If the alias doesn't exist.
            NoDefaultKeyError: If alias is None and no default key is set.
        """
        import os

        from omniclaw.protocols.nanopayments.wallet import GatewayWalletManager

        # Get the real private key from the vault
        private_key = await self.get_raw_key(alias)

        if rpc_url is None:
            # Try to get from environment
            key_network = await self.get_network(alias)

            # Check for network-specific RPC URLs in environment
            env_rpc = os.environ.get(f"RPC_URL_{key_network.replace(':', '_').upper()}")
            if env_rpc:
                rpc_url = env_rpc
            else:
                # Try generic RPC_URL
                rpc_url = os.environ.get("RPC_URL")

            if rpc_url is None:
                raise ValueError(
                    "rpc_url is required. Provide it explicitly or set "
                    "RPC_URL or RPC_URL_EIP155_CHAINID environment variable."
                )

        return GatewayWalletManager(
            private_key=private_key,
            network=await self.get_network(alias),
            rpc_url=rpc_url,
            nanopayment_client=self._client,
            gateway_address=gateway_address,
            usdc_address=usdc_address,
            cctp_gateway_address=cctp_gateway_address,
        )
