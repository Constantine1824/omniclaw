from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AbstractPaymentClient(ABC):
    """Abstract interface for Omniclaw MCP payment operations."""

    @abstractmethod
    async def create_agent_wallet(
        self, agent_name: str, blockchain: str | None = None, apply_default_guards: bool = True
    ) -> Dict[str, Any]:
        pass


    @abstractmethod
    async def create_wallet_set(self, name: str | None = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_wallet(
        self,
        wallet_set_id: str | None = None,
        blockchain: str | None = None,
        account_type: str = "EOA",
        name: str | None = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def list_wallet_sets(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def list_wallets(self, wallet_set_id: str | None = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_wallet(self, wallet_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def simulate_payment(
        self,
        wallet_id: str,
        recipient: str,
        amount: str,
        check_trust: bool | None = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def execute_payment(
        self,
        wallet_id: str,
        recipient: str,
        amount: str,
        purpose: str | None = None,
        idempotency_key: str | None = None,
        check_trust: bool | None = None,
        wait_for_completion: bool = False,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_payment_intent(
        self,
        wallet_id: str,
        recipient: str,
        amount: str,
        purpose: str | None = None,
        expires_in: int | None = None,
        idempotency_key: str | None = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_payment_intent(self, intent_id: str) -> Dict[str, Any] | None:
        pass

    @abstractmethod
    async def confirm_intent(self, intent_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_intent(self, intent_id: str, reason: str | None = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_wallet_usdc_balance(self, wallet_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def list_guards(self, wallet_id: str) -> Dict[str, Any]:
        pass


    @abstractmethod
    async def can_pay(self, recipient: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def detect_method(self, recipient: str) -> Dict[str, Any]:
        pass
