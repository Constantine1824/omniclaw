from typing import Any, Dict, Optional, Protocol

class BaseEventEmitter(Protocol):
    async def emit(
        self,
        event_type: str,
        wallet_id: str,
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        severity: str = "info",
        agent_id: Optional[str] = None,
    ) -> str:
        ...

    def emit_background(
        self,
        event_type: str,
        wallet_id: str,
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        severity: str = "info",
        agent_id: Optional[str] = None,
    ) -> None:
        ...

class NullEventEmitter:
    async def emit(
        self,
        event_type: str,
        wallet_id: str,
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        severity: str = "info",
        agent_id: Optional[str] = None,
    ) -> str:
        return ""

    def emit_background(
        self,
        event_type: str,
        wallet_id: str,
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        severity: str = "info",
        agent_id: Optional[str] = None,
    ) -> None:
        pass

_emitter: BaseEventEmitter = NullEventEmitter()

def set_emitter(emitter: BaseEventEmitter) -> None:
    global _emitter
    _emitter = emitter

def get_emitter() -> BaseEventEmitter:
    return _emitter

class ProxyEventEmitter:
    async def emit(
        self,
        event_type: str,
        wallet_id: str,
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        severity: str = "info",
        agent_id: Optional[str] = None,
    ) -> str:
        return await get_emitter().emit(
            event_type, wallet_id, payload, correlation_id, severity, agent_id
        )

    def emit_background(
        self,
        event_type: str,
        wallet_id: str,
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        severity: str = "info",
        agent_id: Optional[str] = None,
    ) -> None:
        get_emitter().emit_background(
            event_type, wallet_id, payload, correlation_id, severity, agent_id
        )

event_emitter = ProxyEventEmitter()
