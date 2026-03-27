#!/usr/bin/env python3
"""
Payment canary - verify payment functionality before/after deploys.

Usage:
    python examples/payment_canary.py \
        --wallet-id <wallet_id> \
        --recipient <recipient> \
        --amount 0.10 \
        --network BASE_SEPOLIA \
        --sla-seconds 300
"""

import argparse
import asyncio
import sys
import time

from omniclaw import OmniClaw, Network


async def run_canary(
    wallet_id: str,
    recipient: str,
    amount: str,
    network: str,
    sla_seconds: int,
) -> int:
    """Run payment canary with SLA."""
    start_time = time.time()

    try:
        network_enum = Network.from_string(network)
    except ValueError:
        network_enum = Network.BASE_SEPOLIA

    client = OmniClaw(network=network_enum)

    print(f"Canary: testing payment of {amount} USDC to {recipient}")
    print(f"Network: {network_enum.value}")
    print(f"SLA: {sla_seconds}s")

    elapsed = time.time() - start_time
    if elapsed > sla_seconds:
        print(f"FAIL: Setup exceeded SLA ({elapsed:.1f}s > {sla_seconds}s)")
        return 1

    try:
        result = await client.pay(
            wallet_id=wallet_id,
            recipient=recipient,
            amount=amount,
        )

        elapsed = time.time() - start_time
        if elapsed > sla_seconds:
            print(f"FAIL: Payment exceeded SLA ({elapsed:.1f}s > {sla_seconds}s)")
            return 1

        if result.success:
            print(f"SUCCESS: Payment completed in {elapsed:.1f}s")
            print(f"Transaction: {result.transaction}")
            return 0
        else:
            print(f"FAIL: Payment failed: {result.error_message}")
            return 1

    except Exception as e:
        print(f"FAIL: Exception: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Payment canary")
    parser.add_argument("--wallet-id", required=True, help="Wallet ID to pay from")
    parser.add_argument("--recipient", required=True, help="Recipient address")
    parser.add_argument("--amount", default="0.10", help="Amount in USDC")
    parser.add_argument("--network", default="BASE_SEPOLIA", help="Network (BASE_SEPOLIA, etc)")
    parser.add_argument("--sla-seconds", type=int, default=300, help="SLA in seconds")

    args = parser.parse_args()

    return asyncio.run(
        run_canary(
            wallet_id=args.wallet_id,
            recipient=args.recipient,
            amount=args.amount,
            network=args.network,
            sla_seconds=args.sla_seconds,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
