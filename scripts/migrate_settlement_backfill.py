#!/usr/bin/env python3
"""
Backfill settlement metadata on ledger entries.

Default mode is dry-run; no writes happen unless --apply is set.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Ensure local src/ is importable when running from repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from omniclaw.core.migrations import normalize_ledger_entry
from omniclaw.storage import get_storage


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Backfill settlement metadata for ledger entries",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. If omitted, runs in dry-run mode.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Query batch size (default: 500).",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=None,
        help="Optional cap on number of entries processed.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="How many changed keys to include in sample output.",
    )
    return parser


def _diff_update(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Build a shallow update payload for changed top-level fields."""
    updates: dict[str, Any] = {}
    for key in ("status", "metadata", "tx_hash", "method", "purpose"):
        if key in new and old.get(key) != new.get(key):
            updates[key] = new[key]
    return updates


async def _run(apply: bool, batch_size: int, max_entries: int | None, sample_limit: int) -> int:
    storage = get_storage()
    collection = "ledger_entries"

    processed = 0
    changed = 0
    updated = 0
    failed = 0
    offset = 0
    changed_samples: list[dict[str, Any]] = []

    while True:
        limit = batch_size
        if max_entries is not None:
            remaining = max_entries - processed
            if remaining <= 0:
                break
            limit = min(limit, remaining)

        rows = await storage.query(collection, limit=limit, offset=offset)
        if not rows:
            break

        for row in rows:
            processed += 1
            key = str(row.get("_key") or row.get("id") or "")
            normalized, row_changed = normalize_ledger_entry(row)
            if not row_changed:
                continue

            changed += 1
            if len(changed_samples) < sample_limit:
                changed_samples.append(
                    {
                        "key": key,
                        "before_status": row.get("status"),
                        "after_status": normalized.get("status"),
                        "before_settlement_final": (row.get("metadata") or {}).get(
                            "settlement_final"
                        ),
                        "after_settlement_final": (normalized.get("metadata") or {}).get(
                            "settlement_final"
                        ),
                    }
                )

            if apply:
                update_payload = _diff_update(row, normalized)
                if not update_payload:
                    continue
                try:
                    ok = await storage.update(collection, key, update_payload)
                    if ok:
                        updated += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1

        offset += len(rows)

    mode = "APPLY" if apply else "DRY_RUN"
    summary = {
        "mode": mode,
        "collection": collection,
        "processed": processed,
        "changed": changed,
        "updated": updated,
        "failed": failed,
        "sample_changes": changed_samples,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if apply and failed:
        return 2
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return asyncio.run(
        _run(
            apply=bool(args.apply),
            batch_size=int(args.batch_size),
            max_entries=args.max_entries,
            sample_limit=int(args.sample_limit),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())

