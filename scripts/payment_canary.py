#!/usr/bin/env python3
"""
Sandbox payment canary with settlement SLA monitoring.

Usage:
  python scripts/payment_canary.py \
    --wallet-id <wallet_id> \
    --recipient <recipient> \
    --amount 0.10 \
    --network ARC-TESTNET
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from decimal import Decimal

from omniclaw.client import OmniClaw
from omniclaw.core.types import Network, PaymentStatus


FINAL_SUCCESS = {PaymentStatus.SETTLED, PaymentStatus.COMPLETED}
FINAL_FAILURE = {PaymentStatus.FAILED, PaymentStatus.FAILED_FINAL, PaymentStatus.CANCELLED, PaymentStatus.BLOCKED}


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run a payment canary with settlement SLA checks.")
    parser.add_argument("--wallet-id", required=True, help="Source wallet ID.")
    parser.add_argument("--recipient", required=True, help="Destination address or URL.")
    parser.add_argument("--amount", required=True, help="USDC amount, e.g. 0.10.")
    parser.add_argument("--network", default="ARC-TESTNET", help="OmniClaw network (default: ARC-TESTNET).")
    parser.add_argument("--sla-seconds", type=int, default=300, help="Max seconds to reach final state.")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Polling interval in seconds.")
    args = parser.parse_args()

    network = Network.from_string(args.network)
    amount = Decimal(args.amount)

    client = OmniClaw(network=network)

    started = time.time()
    result = await client.pay(
        wallet_id=args.wallet_id,
        recipient=args.recipient,
        amount=amount,
        wait_for_completion=False,
        timeout_seconds=float(args.sla_seconds),
    )

    print(
        f"[canary] submitted status={result.status.value} success={result.success} "
        f"tx_id={result.transaction_id} tx_hash={result.blockchain_tx}"
    )

    if result.status in FINAL_SUCCESS:
        print("[canary] already final-success at submission")
        return 0
    if result.status in FINAL_FAILURE:
        print("[canary] final failure at submission")
        return 2
    if not result.transaction_id:
        print("[canary] no transaction_id returned; cannot monitor lifecycle")
        return 3

    tx_id = result.transaction_id
    last_state = None
    while True:
        elapsed = time.time() - started
        if elapsed > args.sla_seconds:
            print(f"[canary] SLA breached ({elapsed:.1f}s > {args.sla_seconds}s)")
            return 4

        tx = client._wallet_service._circle.get_transaction(tx_id)
        if tx.state != last_state:
            print(f"[canary] tx={tx_id} state={tx.state.value} elapsed={elapsed:.1f}s")
            last_state = tx.state

        if tx.state.value in {"COMPLETE", "CLEARED"}:
            print("[canary] final-success")
            return 0
        if tx.state.value in {"FAILED", "CANCELLED"}:
            print("[canary] final-failure")
            return 2

        await asyncio.sleep(args.poll_interval)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

