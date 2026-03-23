# OmniClaw Nanopayments Implementation Plan

> **Status:** Ready to Implement
> **Version:** 1.0
> **Last Updated:** March 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Phase 1: Foundation](#phase-1-foundation)
4. [Phase 2: EIP-3009 Signing](#phase-2-eip-3009-signing)
5. [Phase 3: NanopaymentClient](#phase-3-nanopaymentclient)
6. [Phase 4: NanoKeyVault](#phase-4-nanokeyvault)
7. [Phase 5: GatewayWalletManager](#phase-5-gatewaywalletmanager)
8. [Phase 6: NanopaymentAdapter](#phase-6-nanopaymentadapter)
9. [Phase 7: GatewayMiddleware](#phase-7-gatewaymiddleware)
10. [Phase 8: SDK Integration](#phase-8-sdk-integration)
11. [Testing Requirements](#testing-requirements)

---

## 1. Overview

### Vision

> **"OmniClaw enables autonomous agents to pay, get paid, and operate independently."**

OmniClaw provides the economic infrastructure layer for AI agents. After implementation, agents can:

- **Pay** for resources via `agent.pay()` — now with gasless micro-payments
- **Get paid** via `@agent.sell()` — agents can now monetize their capabilities
- **Operate independently** — full financial autonomy with spending guards and safety layers

### Key Design Principles

1. **Operator controls keys, agents use infrastructure**
   - Keys live on SDK instance, not agent objects
   - Agent holds only `nano_key_alias` (string reference)
   - Raw key never exposed to agent

2. **Graceful degradation at every level**
   - No EOA key → fall back to standard Circle transfer
   - No GatewayWalletBatched → fall back to existing x402 (onchain)
   - Agent code never changes

3. **Security boundary is absolute**
   - Compromised agent can spend (up to guard limits)
   - Compromised agent CANNOT exfiltrate keys

---

## 2. Architecture

### Two Separate Wallet Systems

```
CIRCLE MPC WALLET (existing)
  Managed by: Circle + entity_secret (MPC share)
  Signing: Circle's infrastructure (2-of-2 MPC)
  Used for: Standard USDC transfers, CCTP cross-chain
  Key: entity_secret (NOT raw private key)

GATEWAY WALLET (nanopayments)
  Managed by: Operator via NanoKeyVault
  Signing: LOCAL EIP-3009 with raw EOA private key
  Used for: Gasless micro-payments, x402 Gateway payments
  Key: raw EOA private key (encrypted in vault)
```

### Implementation Phases

| Phase | Name | Files | Dependencies |
|-------|------|-------|--------------|
| 1 | Foundation | `types.py`, `constants.py`, `exceptions.py` | None |
| 2 | EIP-3009 Signing | `signing.py` + tests | Phase 1 |
| 3 | NanopaymentClient | `client.py` + tests | Phase 1 |
| 4 | NanoKeyVault | `keys.py`, `vault.py` + tests | Phase 2 |
| 5 | GatewayWalletManager | `wallet.py` + tests | Phase 2, 3 |
| 6 | NanopaymentAdapter | `adapter.py` + tests | Phase 2, 3, 4 |
| 7 | GatewayMiddleware | `middleware.py` + tests | Phase 3, 4 |
| 8 | SDK Integration | `agent.py`, `sdk.py`, `router.py`, config | Phase 6, 7 |

---

## Phase 1: Foundation

### Files to Create

1. `src/omniclaw/protocols/nanopayments/__init__.py`
2. `src/omniclaw/protocols/nanopayments/constants.py`
3. `src/omniclaw/protocols/nanopayments/types.py`
4. `src/omniclaw/protocols/nanopayments/exceptions.py`

### What to Build

**constants.py:**
- `GATEWAY_API_TESTNET` = `"https://api-sandbox.circle.com/gateway"`
- `GATEWAY_API_MAINNET` = `"https://api.circle.com/gateway"`
- API paths: `/x402/v1/verify`, `/x402/v1/settle`, `/x402/v1/supported`, `/v1/balances`
- `CIRCLE_BATCHING_NAME` = `"GatewayWalletBatched"` (CRITICAL: this is the EIP-712 domain name)
- `CIRCLE_BATCHING_VERSION` = `"1"`
- `CIRCLE_BATCHING_SCHEME` = `"exact"`
- `MAX_TIMEOUT_SECONDS` = `345600` (4 days, required by Gateway)
- `MIN_VALID_BEFORE_SECONDS` = `259200` (3 days minimum)
- `DEFAULT_VALID_BEFORE_SECONDS` = `345600` (4 days)
- `DEFAULT_MICRO_PAYMENT_THRESHOLD_USDC` = `"1.00"`
- `DEFAULT_GATEWAY_AUTO_TOPUP_THRESHOLD` = `"1.00"`
- `DEFAULT_GATEWAY_AUTO_TOPUP_AMOUNT` = `"10.00"`
- `SUPPORTED_NETWORKS_CACHE_TTL_SECONDS` = `3600`

**types.py:**
```python
@dataclass(frozen=True)
class PaymentRequirementsExtra:
    name: str                    # Must be 'GatewayWalletBatched'
    version: str                 # Typically '1'
    verifying_contract: str       # Gateway Wallet contract address (NOT USDC address)

@dataclass(frozen=True)
class PaymentRequirementsKind:
    scheme: str                  # 'exact'
    network: str                 # CAIP-2 e.g. 'eip155:5042002'
    asset: str                   # USDC contract address
    amount: str                 # Atomic units as string (e.g. '1000' = $0.001)
    max_timeout_seconds: int     # Must be 345600
    pay_to: str                  # Seller address
    extra: PaymentRequirementsExtra

@dataclass(frozen=True)
class PaymentRequirements:
    x402_version: int
    accepts: tuple[PaymentRequirementsKind, ...]

@dataclass(frozen=True)
class EIP3009Authorization:
    from_address: str
    to: str
    value: str                   # Atomic units as string
    valid_after: str             # '0' = immediately valid
    valid_before: str            # Unix timestamp string
    nonce: str                   # '0x' + 64 hex chars

@dataclass(frozen=True)
class PaymentPayloadInner:
    signature: str                # '0x' + hex (65 bytes)
    authorization: EIP3009Authorization

@dataclass(frozen=True)
class PaymentPayload:
    x402_version: int           # 2
    scheme: str                  # 'exact'
    network: str                 # CAIP-2
    payload: PaymentPayloadInner

    def to_dict(self) -> dict: ...
    @classmethod
    def from_dict(cls, data: dict) -> PaymentPayload: ...

@dataclass(frozen=True)
class VerifyResponse:
    is_valid: bool
    payer: str | None
    invalid_reason: str | None

@dataclass(frozen=True)
class SettleResponse:
    success: bool
    transaction: str | None
    payer: str | None
    error_reason: str | None

@dataclass(frozen=True)
class SupportedKind:
    x402_version: int
    scheme: str
    network: str
    extra: dict | None

    @property
    def verifying_contract(self) -> str | None: ...
    @property
    def usdc_address(self) -> str | None: ...

@dataclass(frozen=True)
class GatewayBalance:
    total: int
    available: int
    formatted_total: str         # e.g. '1.000000 USDC'
    formatted_available: str

    @property
    def total_decimal(self) -> str: ...
    @property
    def available_decimal(self) -> str: ...

@dataclass(frozen=True)
class NanopaymentResult:
    success: bool
    payer: str
    seller: str
    transaction: str
    amount_usdc: str             # Decimal string e.g. '0.001'
    amount_atomic: str
    network: str
    response_data: Any | None
    is_nanopayment: bool = True

@dataclass(frozen=True)
class PaymentInfo:
    verified: bool
    payer: str
    amount: str                 # Atomic units
    network: str
    transaction: str | None

    @property
    def amount_decimal(self) -> str: ...
```

**exceptions.py:**
```
All exceptions inherit from NanopaymentError

Category 1: Signing (SigningError base)
  - InvalidPrivateKeyError
  - SignatureVerificationError

Category 2: Gateway API (GatewayAPIError base)
  - GatewayTimeoutError
  - GatewayConnectionError

Category 3: Verification (VerificationError base)
  - InvalidSignatureError
  - AuthorizationExpiredError
  - AuthorizationNotYetValidError
  - NonceReusedError
  - InsufficientBalanceError

Category 4: Settlement (SettlementError base)
  - InsufficientGatewayBalanceError

Category 5: Network (NanopaymentError base)
  - UnsupportedNetworkError
  - NetworkMismatchError
  - UnsupportedSchemeError
  - MissingVerifyingContractError

Category 6: Key Management (KeyManagementError base)
  - KeyNotFoundError
  - KeyEncryptionError
  - DuplicateKeyAliasError
  - NoDefaultKeyError

Category 7: Wallet Operations (GatewayWalletError base)
  - DepositError
  - WithdrawError
  - ERC20ApprovalError

Category 8: Middleware (MiddlewareError base)
  - InvalidPriceError
  - PaymentRequiredError
  - NoNetworksAvailableError
```

### Phase 1 Acceptance Criteria

- [ ] All types defined and importable from `omniclaw.protocols.nanopayments`
- [ ] All exceptions defined with correct hierarchy (all inherit from NanopaymentError)
- [ ] `PaymentPayload.to_dict()` and `PaymentPayload.from_dict()` roundtrip correctly
- [ ] All exception types can be caught as `NanopaymentError`
- [ ] `GatewayBalance.total_decimal` and `available_decimal` work correctly
- [ ] `PaymentInfo.amount_decimal` works correctly
- [ ] Constants match Circle Gateway requirements (4-day timeout, GatewayWalletBatched name)
- [ ] All tests pass

---

## Phase 2: EIP-3009 Signing

### Files to Create

1. `src/omniclaw/protocols/nanopayments/signing.py`

### What to Build

The core cryptographic module. Uses `eth-account>=0.13` for signing.

**EIP-712 Domain Construction:**
```python
def build_eip712_domain(
    chain_id: int,           # e.g. 5042002 (NOT CAIP-2 string)
    verifying_contract: str,  # Gateway Wallet contract address
    name: str = "GatewayWalletBatched",   # CRITICAL: NOT "USD Coin"
    version: str = "1",
) -> dict
```

**EIP-712 Message Construction:**
```python
def build_eip712_message(
    from_address: str,
    to_address: str,
    value: int,              # Atomic units
    valid_after: int = 0,
    valid_before: int | None = None,  # Defaults to now + 4 days
    nonce: str | None = None,          # Defaults to os.urandom(32)
) -> dict
```

**EIP3009Signer Class:**
```python
class EIP3009Signer:
    def __init__(self, private_key: str) -> None:
        # Validates key format (64 hex chars)
        # Derives address from key
        # Raises InvalidPrivateKeyError if invalid

    @property
    def address(self) -> str:
        # Returns EOA address derived from private key

    def sign_transfer_with_authorization(
        self,
        requirements: PaymentRequirementsKind,
        amount_atomic: int | None = None,
        valid_before: int | None = None,
        nonce: str | None = None,
    ) -> PaymentPayload:
        # 1. Validates requirements.extra.name == "GatewayWalletBatched"
        # 2. Gets verifying_contract from requirements.extra
        # 3. Parses chain_id from requirements.network (e.g. 'eip155:5042002' -> 5042002)
        # 4. Builds EIP-712 domain with name="GatewayWalletBatched"
        # 5. Builds EIP-712 message
        # 6. Signs with eth_account
        # 7. Returns PaymentPayload

    def verify_signature(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirementsKind,
    ) -> bool:
        # Verifies signature locally using eth_account.Account.recover_message
        # Used for testing, NOT production (use NanopaymentClient.verify instead)
```

**Utility Functions:**
```python
def parse_caip2_chain_id(network: str) -> int:
    # "eip155:5042002" -> 5042002

def generate_nonce() -> str:
    # Returns "0x" + os.urandom(32).hex()

def compute_valid_before(seconds_from_now: int = 345600) -> int:
    # Returns unix timestamp

def generate_eoa_keypair() -> tuple[str, str]:
    # Returns (private_key_hex, address)
    # For testing/setup only
```

### Critical Security Notes

1. **Domain name MUST be "GatewayWalletBatched"** — NOT "USD Coin". This is the most common bug.
2. **verifyingContract MUST be Gateway Wallet address** — NOT USDC token address.
3. **validBefore MUST be >= 3 days from now** — Gateway rejects shorter.
4. **Nonce MUST be cryptographically random** — use `os.urandom`, not `random` module.
5. **Private key MUST be 64 hex chars (32 bytes)** — validated on init.

### Phase 2 Acceptance Criteria

- [ ] `EIP3009Signer` initializes correctly with valid private keys
- [ ] `EIP3009Signer` rejects invalid private keys (wrong length, invalid hex)
- [ ] `sign_transfer_with_authorization()` produces valid `PaymentPayload`
- [ ] Signature is recoverable using `Account.recover_message()` from eth_account
- [ ] Local `verify_signature()` returns `True` for correctly signed payloads
- [ ] `verify_signature()` returns `False` for wrong keys
- [ ] **Domain name is "GatewayWalletBatched"** (NOT "USD Coin") — TEST THIS SPECIFICALLY
- [ ] `validBefore` is enforced to be at least 3 days in the future
- [ ] Nonces are unique across multiple sign calls
- [ ] Self-transfer is rejected
- [ ] Amount exceeding requirement is rejected
- [ ] Non-GatewayWalletBatched schemes are rejected
- [ ] Missing verifyingContract is rejected
- [ ] Works with different chain IDs
- [ ] Signature format is correct (0x + 130 hex chars = 65 bytes)
- [ ] All tests pass with 90%+ line coverage

---

## Phase 3: NanopaymentClient

### Files to Create

1. `src/omniclaw/protocols/nanopayments/client.py`

### What to Build

Wraps Circle Gateway REST API endpoints.

**NanopaymentHTTPClient (internal):**
```python
class NanopaymentHTTPClient:
    async def __aenter__(self) -> NanopaymentHTTPClient: ...
    async def __aexit__(self, ...) -> None: ...
    async def get(self, path: str, **kwargs) -> httpx.Response: ...
    async def post(self, path: str, **kwargs) -> httpx.Response: ...
    # Handles timeouts and connection errors
```

**NanopaymentClient:**
```python
class NanopaymentClient:
    def __init__(
        self,
        environment: str = "testnet",   # 'testnet' or 'mainnet'
        api_key: str | None = None,       # If None, read from CIRCLE_API_KEY env
        base_url: str | None = None,      # Override for testing
        timeout: float = 30.0,
    ) -> None:

    async def get_supported(self, force_refresh: bool = False) -> list[SupportedKind]:
        # GET /x402/v1/supported
        # Caches for 60 minutes (SUPPORTED_NETWORKS_CACHE_TTL_SECONDS)
        # Returns list of SupportedKind with verifyingContract and usdcAddress

    async def get_verifying_contract(self, network: str) -> str:
        # Gets verifyingContract for a given CAIP-2 network
        # Raises UnsupportedNetworkError if not found

    async def get_usdc_address(self, network: str) -> str:
        # Gets USDC contract address for a given CAIP-2 network
        # Raises UnsupportedNetworkError if not found

    async def verify(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> VerifyResponse:
        # POST /x402/v1/verify
        # WARNING: For debugging only. Use settle() in production.

    async def settle(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> SettleResponse:
        # POST /x402/v1/settle
        # PRIMARY production method
        # Returns SettleResponse on success
        # Raises SettlementError on failure

    async def check_balance(
        self,
        address: str,
        network: str,
    ) -> GatewayBalance:
        # GET /v1/balances?address=...&network=...
        # Returns GatewayBalance with total, available, formatted amounts
```

### Important Notes

1. **Always use `settle()` in production** — never `verify()` then `settle()`. Settle is optimized for low latency.
2. **Cache supported networks for 60 minutes** — Circle may deploy contract upgrades.
3. **Handle HTTP 402 responses** from settle endpoint (payment-specific errors in body).
4. **Raise `SettlementError`** when `success=false` in settle response.

### Phase 3 Acceptance Criteria

- [ ] `get_supported()` fetches and parses supported networks correctly
- [ ] `get_supported()` uses cache on second call within TTL
- [ ] `get_supported()` re-fetches after cache expiry (force_refresh=True)
- [ ] `get_verifying_contract()` returns correct address for known network
- [ ] `get_verifying_contract()` raises `UnsupportedNetworkError` for unknown network
- [ ] `settle()` returns `SettleResponse` on success
- [ ] `settle()` raises `SettlementError` on failure (e.g. insufficient_balance)
- [ ] `settle()` raises `GatewayAPIError` on HTTP errors
- [ ] `verify()` returns `VerifyResponse` correctly
- [ ] `check_balance()` returns `GatewayBalance` with correct fields
- [ ] All HTTP errors are caught and wrapped in appropriate exceptions
- [ ] All tests pass with mocked HTTP responses

---

## Phase 4: NanoKeyVault

### Files to Create

1. `src/omniclaw/protocols/nanopayments/keys.py` (internal encryption/decryption)
2. `src/omniclaw/vault.py` (public vault API for SDK)

### What to Build

**keys.py (internal, NOT exposed to agents):**
```python
class NanoKeyStore:
    """
    Internal key storage and decryption.
    This is NOT exposed to agents.
    """

    def __init__(
        self,
        entity_secret: str,    # Circle's entity secret (master key)
        storage_backend: StorageBackend,
    ) -> None:

    def encrypt_key(self, private_key: str) -> str:
        # Encrypts EOA private key using entity_secret as AES-256-GCM key
        # Returns base64-encoded ciphertext

    def decrypt_key(self, encrypted_key: str) -> str:
        # Decrypts encrypted key using entity_secret
        # Returns raw private key hex

    def _get_master_key(self) -> bytes:
        # Derives AES key from entity_secret using PBKDF2
        # Returns 32-byte key for AES-256

    def create_signer(self, encrypted_key: str) -> EIP3009Signer:
        # Decrypts key and creates EIP3009Signer
        # Returns signer (NEVER returns raw key)
```

**vault.py (SDK-level vault):**
```python
class NanoKeyVault:
    """
    The secure key vault for EOA private keys.
    Lives on the SDK instance, NOT on agents.
    Agents hold only nano_key_alias (string reference).
    """

    def __init__(
        self,
        entity_secret: str,
        storage_backend: StorageBackend,
        circle_api_key: str,
        nanopayments_environment: str = "testnet",
    ) -> None:

    def add_key(self, alias: str, private_key: str) -> str:
        # Import an existing EOA key
        # Encrypts and stores in vault
        # Returns the EOA address
        # Raises DuplicateKeyAliasError if alias exists

    def generate_key(self, alias: str) -> str:
        # Generate new EOA keypair
        # Stores encrypted key in vault
        # Returns the EOA address (operator must fund this)
        # Raises DuplicateKeyAliasError if alias exists

    def set_default_key(self, alias: str) -> None:
        # Sets the default key for agents that don't specify one
        # Raises KeyNotFoundError if alias doesn't exist

    def get_address(self, alias: str | None = None) -> str:
        # Get EOA address for a key alias
        # Uses default if alias is None
        # Raises KeyNotFoundError or NoDefaultKeyError

    def sign(
        self,
        requirements: PaymentRequirementsKind,
        amount_atomic: int | None = None,
        alias: str | None = None,
    ) -> PaymentPayload:
        # 1. Gets key (by alias or default)
        # 2. Decrypts key using entity_secret
        # 3. Creates EIP3009Signer
        # 4. Signs the authorization
        # 5. Returns PaymentPayload
        # NEVER exposes raw key
        # Raises KeyNotFoundError, NoDefaultKeyError

    def rotate_key(self, alias: str) -> str:
        # Generate new key, replace old one
        # Returns new address
        # Old key remains usable for pending payments

    def list_keys(self) -> list[str]:
        # Returns list of key aliases (NOT the keys themselves)
        # Safe to expose to operator

    def has_key(self, alias: str | None = None) -> bool:
        # Check if key exists (by alias or default)

    async def get_balance(self, alias: str | None = None) -> GatewayBalance:
        # Get Gateway balance for a key's address
        # Uses NanopaymentClient internally
```

### Key Security Design

```
KEY FLOW:

Operator adds/generates key:
  private_key -> encrypt_key(entity_secret) -> encrypted_blob -> storage

Signing happens:
  encrypted_blob <- storage
  encrypted_blob -> decrypt_key(entity_secret) -> raw_key
  raw_key -> EIP3009Signer -> sign() -> PaymentPayload
  (raw_key NEVER leaves the vault)

Agent object holds:
  nano_key_alias = "alice-nano"  # Just a string
  (NOT the actual key)
```

### Phase 4 Acceptance Criteria

- [ ] `add_key()` encrypts and stores key correctly
- [ ] `add_key()` raises `DuplicateKeyAliasError` for existing alias
- [ ] `generate_key()` creates valid keypair and stores encrypted
- [ ] `generate_key()` returns address that can receive funds
- [ ] `set_default_key()` sets default without error
- [ ] `sign()` decrypts key, creates signer, returns `PaymentPayload`
- [ ] `sign()` NEVER exposes raw private key (test this)
- [ ] `sign()` with non-existent alias raises `KeyNotFoundError`
- [ ] `sign()` with no alias and no default raises `NoDefaultKeyError`
- [ ] `get_address()` returns correct address for alias
- [ ] `get_address()` uses default when alias is None
- [ ] `list_keys()` returns aliases (not keys)
- [ ] `has_key()` returns True/False correctly
- [ ] `rotate_key()` generates new key and returns new address
- [ ] `get_balance()` returns correct `GatewayBalance`
- [ ] All tests pass, encrypted keys are NOT decryptable without correct entity_secret
- [ ] 90%+ line coverage

---

## Phase 5: GatewayWalletManager

### Files to Create

1. `src/omniclaw/protocols/nanopayments/wallet.py`

### What to Build

Handles on-chain operations for depositing to and withdrawing from the Gateway Wallet contract.

```python
class GatewayWalletManager:
    """
    Manages Gateway Wallet contract interactions.
    Handles deposit (Circle wallet -> Gateway) and withdraw (Gateway -> wallet).
    """

    def __init__(
        self,
        private_key: str,                    # EOA private key for signing
        network: str,                        # CAIP-2 network
        rpc_url: str,                        # RPC endpoint
        gateway_client: NanopaymentClient,   # For balance queries
        entity_secret: str,                  # For approving USDC
    ) -> None:

    async def deposit(
        self,
        amount_usdc: str,    # Decimal string e.g. "10.00"
    ) -> DepositResult:
        """
        Deposit USDC from Circle wallet (or any address) to Gateway contract.
        
        Flow:
        1. If USDC allowance insufficient, approve Gateway contract
        2. Call depositWithAuthorization() on Gateway Wallet contract
        3. Wait for transaction receipt
        4. Return tx_hash and amount
        
        Raises:
            DepositError: If deposit fails
            ERC20ApprovalError: If approval fails
        """

    async def withdraw(
        self,
        amount_usdc: str,
        destination_chain: str | None = None,   # None = same chain
        recipient: str | None = None,           # None = own address
    ) -> WithdrawResult:
        """
        Withdraw USDC from Gateway to a wallet.
        
        Same-chain: Instant via internal transfer
        Cross-chain: Burn on source, mint on destination
        
        Raises:
            WithdrawError: If withdrawal fails
        """

    async def get_balance(self) -> GatewayBalance:
        """Get Gateway balance for this wallet's address."""

    def get_address(self) -> str:
        """Get the EOA address (derived from private key)."""
```

**Result Types:**
```python
@dataclass
class DepositResult:
    approval_tx_hash: str | None   # None if no approval needed
    deposit_tx_hash: str
    amount: int                    # Atomic units
    formatted_amount: str           # e.g. "10.000000 USDC"

@dataclass
class WithdrawResult:
    mint_tx_hash: str | None      # For cross-chain
    amount: int
    formatted_amount: str
    source_chain: str
    destination_chain: str
    recipient: str
```

### Important Notes

1. **Deposit is an ONCHAIN transaction** — it costs gas. This is the only time gas is paid.
2. **Use `depositWithAuthorization()`** (EIP-3009 permit) when available — single tx, no separate approve.
3. **Fallback to approve() + deposit()** if permit not available.
4. **Wait for transaction confirmation** before returning.
5. **Get RPC URL from config** or use defaults for known chains.

### Phase 5 Acceptance Criteria

- [ ] `deposit()` approves USDC if allowance insufficient
- [ ] `deposit()` calls Gateway contract deposit function
- [ ] `deposit()` waits for transaction confirmation
- [ ] `deposit()` returns `DepositResult` with tx hashes
- [ ] `deposit()` raises `DepositError` on failure
- [ ] `withdraw()` handles same-chain withdrawal
- [ ] `withdraw()` handles cross-chain withdrawal
- [ ] `withdraw()` returns `WithdrawResult` with correct fields
- [ ] `get_balance()` returns `GatewayBalance` from NanopaymentClient
- [ ] `get_address()` returns correct EOA address
- [ ] All operations use correct contract addresses from NanopaymentClient
- [ ] All tests pass with mocked web3 calls
- [ ] 90%+ line coverage

---

## Phase 6: NanopaymentAdapter

### Files to Create

1. `src/omniclaw/protocols/nanopayments/adapter.py`

### What to Build

Buyer-side execution engine. Plugs into OmniClaw's existing PaymentRouter.

```python
class NanopaymentAdapter:
    """
    Buyer-side adapter for Circle Gateway nanopayments.
    
    Handles two scenarios:
    1. x402 URL recipient: detects GatewayWalletBatched, signs, retries
    2. Direct address recipient (micro-payment): routes through Gateway directly
    """

    def __init__(
        self,
        vault: NanoKeyVault,
        nanopayment_client: NanopaymentClient,
        http_client: httpx.AsyncClient,
    ) -> None:

    async def pay_x402_url(
        self,
        url: str,
        method: str = "GET",
        headers: dict | None = None,
        body: bytes | None = None,
        nano_key_alias: str | None = None,
    ) -> NanopaymentResult:
        """
        Pay for a URL-based resource via x402 with Gateway batching.
        
        Flow:
        1. Send initial HTTP request
        2. If not 402, return response directly (free resource)
        3. Parse 402 response (PAYMENT-REQUIRED header + JSON body)
        4. Check for GatewayWalletBatched in accepts array
        5. If not found: raise UnsupportedSchemeError (router will fallback)
        6. Get verifying_contract from NanopaymentClient
        7. Call vault.sign() to create signed PaymentPayload
        8. Retry request with PAYMENT-SIGNATURE header
        9. Return NanopaymentResult
        """

    async def pay_direct(
        self,
        seller_address: str,
        amount_usdc: str,           # Decimal string e.g. "0.001"
        network: str,               # CAIP-2
        nano_key_alias: str | None = None,
    ) -> NanopaymentResult:
        """
        Pay a direct address via Gateway nanopayment.
        
        Used when:
        - Recipient is a 0x address
        - Amount is below micro_payment_threshold
        
        Flow:
        1. Get supported networks and find matching network
        2. Build PaymentRequirements from scratch
        3. Call vault.sign() to create signed PaymentPayload
        4. Call NanopaymentClient.settle()
        5. Return NanopaymentResult
        """

    async def check_and_topup(
        self,
        nano_key_alias: str | None = None,
        threshold: str | None = None,
        topup_amount: str | None = None,
    ) -> bool:
        """
        Check gateway balance and auto-topup if needed.
        Called internally before each pay_x402_url or pay_direct.
        
        Returns True if topup was performed.
        """
```

### Important Notes

1. **Graceful fallback**: If no GatewayWalletBatched scheme found, raise error so router can fallback to existing x402.
2. **Auto-topup**: Check gateway balance before payment, deposit if below threshold.
3. **Base64 encoding**: PAYMENT-SIGNATURE header must be base64-encoded JSON.
4. **PAYMENT-RESPONSE**: Parse from successful response headers.

### Phase 6 Acceptance Criteria

- [ ] `pay_x402_url()` sends initial request and parses 402 response
- [ ] `pay_x402_url()` detects GatewayWalletBatched in accepts array
- [ ] `pay_x402_url()` raises error if no GatewayWalletBatched (for router fallback)
- [ ] `pay_x402_url()` calls vault.sign() with correct requirements
- [ ] `pay_x402_url()` retries with PAYMENT-SIGNATURE header (base64 encoded)
- [ ] `pay_x402_url()` returns `NanopaymentResult` with response_data
- [ ] `pay_direct()` builds requirements and settles without HTTP
- [ ] `pay_direct()` converts decimal amount to atomic units correctly
- [ ] `check_and_topup()` deposits when balance < threshold
- [ ] `check_and_topup()` returns False if no topup needed
- [ ] All error paths handled correctly
- [ ] All tests pass with mocked HTTP and vault
- [ ] 90%+ line coverage

---

## Phase 7: GatewayMiddleware

### Files to Create

1. `src/omniclaw/protocols/nanopayments/middleware.py`

### What to Build

Seller-side FastAPI/Starlette middleware. The Python equivalent of Circle's `createGatewayMiddleware()`.

```python
class GatewayMiddleware:
    """
    FastAPI/Starlette middleware for x402 payment gating.
    
    Sellers use this to protect their endpoints.
    When a buyer requests without payment: returns 402.
    When a buyer requests with valid payment: settles and serves content.
    """

    def __init__(
        self,
        seller_address: str,                    # EOA address (from vault)
        nanopayment_client: NanopaymentClient,
        supported_kinds: list[SupportedKind] | None = None,  # Fetched if None
    ) -> None:

    async def handle(
        self,
        request: Request,
        price_usd: str,      # e.g. "$0.001" or "0.001"
    ) -> PaymentInfo:
        """
        Handle payment for a request.
        
        Called by route handlers.
        
        Returns PaymentInfo if payment verified.
        Raises HTTPException(402) with requirements if payment missing.
        Raises HTTPException(402) with error if payment invalid.
        """

    def _build_402_response(
        self,
        price_usd: str,
        request: Request,
    ) -> HTTPException:
        """
        Build 402 response with correct x402 v2 body structure.
        
        Returns HTTPException(402) with:
        - status_code: 402
        - detail: {"x402Version": 2, "accepts": [...]} 
        - headers: {"PAYMENT-REQUIRED": base64(requirements)}
        """

    def _build_accepts_array(
        self,
        price_usd: str,
    ) -> list[dict]:
        """
        Build the accepts array for 402 response.
        
        For each supported kind:
        - scheme: "exact"
        - network: CAIP-2
        - asset: USDC address
        - amount: price in atomic units
        - maxTimeoutSeconds: 345600
        - payTo: seller_address
        - extra.name: "GatewayWalletBatched"
        - extra.version: "1"
        - extra.verifyingContract: from supported kinds
        """

    async def require(self, price: str):
        """
        Returns a FastAPI dependency for route protection.
        
        Usage:
            @app.get("/premium")
            async def premium(payment=Depends(gateway.require("$0.001"))):
                return {"data": "paid content", "paid_by": payment.payer}
        """
```

**Price Parsing:**
```python
def parse_price(price_str: str) -> int:
    """
    Parse price string to USDC atomic units.
    
    Accepts:
        "$0.001" -> 1000
        "0.001" -> 1000
        "$1" -> 1000000
        "1000" -> 1000000 (assumed atomic)
    
    Returns atomic units (int).
    Raises InvalidPriceError if unparseable.
    """
```

### Important Notes

1. **PAYMENT-REQUIRED header**: Must be base64-encoded requirements JSON.
2. **maxTimeoutSeconds**: Must be exactly 345600 (4 days).
3. **extra.verifyingContract**: Must be fetched from NanopaymentClient.get_supported().
4. **Always call settle()**: Not verify() then settle(). Settle is atomic and faster.
5. **PAYMENT-RESPONSE header**: Set on successful responses with transaction info.

### Phase 7 Acceptance Criteria

- [ ] `require()` returns 402 when PAYMENT-SIGNATURE header absent
- [ ] 402 body has correct x402Version (2), scheme ("exact"), accepts array
- [ ] 402 body contains extra.name = "GatewayWalletBatched"
- [ ] 402 body contains correct verifyingContract from supported kinds
- [ ] 402 body has correct amount (atomic units) for price
- [ ] `handle()` verifies and settles when PAYMENT-SIGNATURE present
- [ ] `handle()` returns PaymentInfo on success
- [ ] `handle()` returns 402 with error on invalid payment
- [ ] `parse_price()` handles "$0.001", "0.001", "$1", "1000" formats
- [ ] `parse_price()` raises InvalidPriceError for invalid formats
- [ ] PAYMENT-RESPONSE header set on successful responses
- [ ] All tests pass
- [ ] 90%+ line coverage

---

## Phase 8: SDK Integration

### Files to Modify/Create

1. `src/omniclaw/core/config.py` — Add nanopayments config fields
2. `src/omniclaw/agent.py` — Enhance OmniClawAgent with nanopayments
3. `src/omniclaw/sdk.py` — Create OmniClaw (operator entry point)
4. `src/omniclaw/payment/router.py` — Update routing logic

### Config Changes

Add to `Config` dataclass:
```python
# Nanopayments configuration
nanopayments_enabled: bool = True
nanopayments_environment: str = "testnet"
nanopayments_auto_topup: bool = True
nanopayments_topup_threshold: str = "1.00"
nanopayments_topup_amount: str = "10.00"
nanopayments_micro_threshold: str = "1.00"
nanopayments_default_key_alias: str | None = None
```

### OmniClawAgent Changes

```python
class OmniClawAgent:
    # Existing: pay(), simulate(), add_budget_guard(), etc.
    # Existing: _wallet_id, _agent_name, _client, etc.
    
    # NEW: Nanopayments
    _nano_key_alias: str | None = None
    _nanopayment_adapter: NanopaymentAdapter | None = None
    
    @property
    def nano_address(self) -> str | None:
        """Get the EOA address for nanopayments. Read-only."""
        if self._nano_key_alias and self._sdk:
            return self._sdk.vault.get_address(self._nano_key_alias)
        return None
    
    @property
    def gateway_balance(self) -> GatewayBalance | None:
        """Get Gateway balance. Read-only."""
        if self._nano_key_alias and self._sdk:
            return await self._sdk.vault.get_balance(self._nano_key_alias)
        return None
    
    def sell(self, price: str, **kwargs) -> Callable:
        """
        Decorator to mark a function as a paid endpoint.
        
        Usage:
            @agent.sell(price="$0.001")
            async def get_data():
                return {"data": "..."}
        """
        # Registers with GatewayMiddleware
        # Attaches to agent's paid_routes list
    
    def current_payment(self) -> PaymentInfo | None:
        """
        Get current payment context within a @sell() decorated function.
        
        Usage:
            @agent.sell(price="$0.001")
            async def get_data():
                payer = agent.current_payment().payer
                return {"data": "...", "paid_by": payer}
        """
        # Returns PaymentInfo from the current request context
        # Only valid within a @sell() decorated function
```

### OmniClaw (Operator SDK)

```python
class OmniClaw:
    """
    The operator's SDK entry point.
    
    Operator uses this to:
    - Add/generate EOA keys
    - Create agents
    - Configure gateway
    - Manage finances
    """
    
    def __init__(
        self,
        circle_api_key: str,
        entity_secret: str,
        storage_backend: StorageBackend | None = None,
        **config_overrides,
    ) -> None:
        self._vault = NanoKeyVault(...)
        self._nanopayment_client = NanopaymentClient(...)
        self._agents: dict[str, OmniClawAgent] = {}
    
    @property
    def vault(self) -> NanoKeyVault:
        """Access the NanoKeyVault for key management."""
        return self._vault
    
    # Key management
    def add_key(self, alias: str, private_key: str) -> str: ...
    def generate_key(self, alias: str) -> str: ...
    def set_default_key(self, alias: str) -> None: ...
    def list_keys(self) -> list[str]: ...
    
    # Gateway management
    async def deposit_to_gateway(
        self,
        amount: str,
        alias: str | None = None,
    ) -> DepositResult: ...
    async def withdraw_from_gateway(
        self,
        amount: str,
        alias: str | None = None,
        chain: str | None = None,
    ) -> WithdrawResult: ...
    def configure_gateway(
        self,
        alias: str | None = None,
        auto_topup: bool | None = None,
        threshold: str | None = None,
        topup_amount: str | None = None,
    ): ...
    
    # Agent management
    def create_agent(
        self,
        name: str,
        nano_key_alias: str | None = None,
        **agent_config,
    ) -> OmniClawAgent:
        """
        Create a new agent.
        
        Args:
            name: Unique agent name
            nano_key_alias: Which vault key to use. Uses default if None.
        
        Returns:
            Configured OmniClawAgent instance.
        """
        agent = OmniClawAgent(...)
        agent._nano_key_alias = nano_key_alias or self._vault._default_key_alias
        self._agents[name] = agent
        return agent
    
    def list_agents(self) -> list[str]: ...
    def get_agent(self, name: str) -> OmniClawAgent | None: ...
```

### Router Integration

Update `payment/router.py`:

```python
async def _route_payment(self, recipient, amount, ...) -> PaymentResult:
    # URL routing
    if self._is_url(recipient):
        response, reqs = await self._x402_check(recipient)
        if response.status_code == 402:
            if reqs and self._has_gateway_option(reqs):
                # NEW: Gateway nanopayments path
                return await self._nanopay_x402(recipient, reqs, nano_key_alias)
            else:
                # Existing x402 flow (onchain)
                return await self._existing_x402(recipient, reqs)
        return result
    
    # Address routing
    if self._is_below_threshold(amount) and self._nanopay_available():
        # NEW: Use EIP-3009 for micro-payments
        return await self._nanopay_direct(recipient, amount, nano_key_alias)
    else:
        # Existing Circle transfer
        return await self._standard_transfer(recipient, amount)

def _has_gateway_option(self, requirements: PaymentRequirements) -> bool:
    """Check if any accepted kind is GatewayWalletBatched."""
    for kind in requirements.accepts:
        if kind.extra.name == "GatewayWalletBatched":
            return True
    return False

def _is_below_threshold(self, amount: str) -> bool:
    """Check if amount is below micro_payment_threshold."""
    from decimal import Decimal
    return Decimal(amount) < Decimal(self._config.nanopayments_micro_threshold)

async def _nanopay_x402(self, url, requirements, key_alias): ...
async def _nanopay_direct(self, address, amount, key_alias): ...
```

### Phase 8 Acceptance Criteria

- [ ] Config accepts all nanopayments fields
- [ ] `OmniClaw` creates vault and NanopaymentClient on init
- [ ] `OmniClaw.add_key()` and `generate_key()` work correctly
- [ ] `OmniClaw.create_agent()` creates agent with correct `nano_key_alias`
- [ ] Agent's `pay()` routes through NanopaymentAdapter when GatewayWalletBatched detected
- [ ] Agent's `pay()` falls back to existing x402 when no GatewayWalletBatched
- [ ] Agent's `pay()` falls back to standard transfer for >= $1.00 amounts
- [ ] `@agent.sell()` registers routes with GatewayMiddleware
- [ ] Seller endpoint returns 402 without payment
- [ ] Seller endpoint serves content with valid payment
- [ ] `current_payment()` returns correct PaymentInfo within decorated functions
- [ ] All existing tests still pass (no regressions)
- [ ] Full integration tests pass

---

## Testing Requirements

### Test File Structure

```
tests/
├── test_nanopayments_types.py
├── test_nanopayments_exceptions.py
├── test_nanopayments_signing.py
├── test_nanopayments_client.py
├── test_nanopayments_vault.py
├── test_nanopayments_wallet.py
├── test_nanopayments_adapter.py
├── test_nanopayments_middleware.py
└── test_nanopayments_integration.py
```

### Coverage Requirements

- [ ] Minimum 90% line coverage on all new modules
- [ ] 100% coverage on signing.py (critical crypto)
- [ ] All error paths tested
- [ ] All edge cases documented in tests

### Critical Test Cases

**Phase 2 (Signing):**
- Domain name is "GatewayWalletBatched" (NOT "USD Coin")
- validBefore >= 3 days enforced
- Nonce is cryptographically random and unique
- Signature recoverable with eth_account.Account.recover_message
- Wrong key fails verification
- Self-transfer rejected
- Amount exceeding requirement rejected

**Phase 3 (Client):**
- Cache works correctly (no extra HTTP calls within TTL)
- force_refresh bypasses cache
- All error codes from Gateway mapped correctly
- Settlement errors raise appropriate exceptions

**Phase 4 (Vault):**
- Raw key NEVER exposed (encrypted storage verified)
- Wrong entity_secret cannot decrypt key
- Duplicate alias rejected
- Default key used when no alias specified

**Phase 6 (Adapter):**
- Falls back gracefully when no GatewayWalletBatched
- Auto-topup triggers when balance low
- PAYMENT-SIGNATURE header is valid base64
- Response data returned correctly

**Phase 7 (Middleware):**
- 402 response structure matches x402 v2 spec exactly
- maxTimeoutSeconds is 345600
- Invalid price formats rejected
- Expired authorization rejected by Gateway

**Phase 8 (Integration):**
- End-to-end: agent.pay() -> Gateway settle -> resource returned
- End-to-end: @agent.sell() -> 402 -> valid payment -> content served
- Guard chain still blocks payments before routing
- 2PC lock prevents double-spend
- No regressions in existing functionality

---

## Edge Cases to Handle

1. **Gateway returns new network**: Don't hardcode contract addresses
2. **Nonce collision**: Use os.urandom(32), never reuse
3. **Gateway balance at exactly threshold**: Topup should trigger
4. **Payment during topup**: 2PC lock prevents double-spend
5. **Expired authorization in flight**: validBefore = 4 days gives buffer
6. **Network mismatch**: Route to CCTP or fail gracefully
7. **No EOA key configured**: Fall back to standard transfer
8. **Invalid base64 in PAYMENT-SIGNATURE**: Return 400, not 402
9. **Gateway API down**: Circuit breaker handles, guard limits prevent drain
10. **Multiple agents share key**: Each has own nano_key_alias but same address

---

## Security Checklist

- [ ] Raw private key never logged
- [ ] Raw private key never returned from any method
- [ ] Key encrypted at rest with AES-256-GCM
- [ ] Key decrypted only inside vault.sign()
- [ ] Entity secret used as master key (not stored separately)
- [ ] Signature uses cryptographically random nonce (os.urandom)
- [ ] validBefore enforces 3-day minimum
- [ ] No hardcoded contract addresses
- [ ] All exceptions have appropriate error codes
- [ ] Agent can only spend up to guard limits

---

## Acceptance Criteria Summary

### Phase 1 (Foundation)
- All types and exceptions defined and importable
- Correct inheritance hierarchy
- Roundtrip serialization works

### Phase 2 (Signing)
- Signatures verifiable with eth_account
- Domain name is GatewayWalletBatched
- 90%+ coverage

### Phase 3 (Client)
- All Gateway endpoints wrapped
- Caching works
- Errors mapped correctly

### Phase 4 (Vault)
- Keys encrypted and never exposed
- All key operations work
- 90%+ coverage

### Phase 5 (Wallet)
- Deposit/withdraw operations work
- On-chain tx handling correct

### Phase 6 (Adapter)
- Both pay paths work
- Auto-topup works
- Graceful fallback

### Phase 7 (Middleware)
- 402 structure correct
- Settlement works
- Price parsing works

### Phase 8 (Integration)
- Full end-to-end works
- No regressions
- All tests pass
