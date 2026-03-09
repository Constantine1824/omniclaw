import asyncio
import os
import random
from decimal import Decimal

from omniclaw.client import OmniClaw
from omniclaw.core.types import Network, PaymentStrategy
from omniclaw.guards.single_tx import SingleTxGuard
from omniclaw.core.logging import get_logger

logger = get_logger("live_simulation")

async def run_live_simulation():
    print("🚀 Initializing OmniClaw SDK for Live Dashboard Simulation...")
    # Initialize client 
    # (Using dummy keys if real ones aren't in env since we just want to hit the local Redis event bus)
    os.environ["CIRCLE_API_KEY"] = os.environ.get("CIRCLE_API_KEY", "TEST_API_KEY_12345")
    os.environ["ENTITY_SECRET"] = os.environ.get("ENTITY_SECRET", "00" * 32)
    os.environ["OMNICLAW_EVENTS_ENABLED"] = "true"
    
    client = OmniClaw(network=Network.ARC_TESTNET)

    wallet_id = "sim-wallet-001"
    recipient = "0x742d35Cc6634C0532925a3b844Bc9e7595f5e4a0"

    print(f"\n🛡️ Configuring Guard: Max $50.00 per TX on {wallet_id}...")
    await client.guards.add_guard(wallet_id, SingleTxGuard(max_amount=Decimal("50.00"), name="TxLimitGuard"))

    print("\n--- 🟢 Generating Successful Payment ---")
    try:
        await client.pay(
            wallet_id=wallet_id,
            recipient=recipient,
            amount=Decimal("12.50"),
            purpose="Monthly Subscription",
            check_trust=False, # Skip TrustGate for local sim
        )
        print("✅ Payment succeeded (Check Live Ledger)")
    except Exception as e:
        print(f"Payment failed as expected in mock mode: {e}, but event was emitted!")

    await asyncio.sleep(2)

    print("\n--- 🔴 Generating Blocked Payment (Hits Guard) ---")
    try:
        await client.pay(
            wallet_id=wallet_id,
            recipient=recipient,
            amount=Decimal("5000.00"),
            purpose="Buying a car",
            check_trust=False,
        )
    except Exception as e:
        print(f"🚫 Blocked by Guard (Expected): {e}")

    await asyncio.sleep(2)

    print("\n--- 🟡 Generating Pending Approval (Intent) ---")
    try:
        # QUEUE_BACKGROUND creates a pending intent
        await client.pay(
            wallet_id=wallet_id,
            recipient=recipient,
            amount=Decimal("45.00"),
            purpose="Requires HITL Review",
            strategy=PaymentStrategy.QUEUE_BACKGROUND,
            check_trust=False,
        )
        print("⏳ Intent Queued (Check Command Center -> Pending Approvals)")
    except Exception as e:
        print(f"Exception: {e}")
    # Give background event tasks time to flush to Redis before exit
    print("\n⏳ Flushing events to Redis...")
    await asyncio.sleep(3)

    print("✨ Simulation Complete. Check the Dashboard UI!")

if __name__ == "__main__":
    asyncio.run(run_live_simulation())
