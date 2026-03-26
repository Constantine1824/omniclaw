"""Command-line interface for OmniClaw operator utilities."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from omniclaw.onboarding import print_doctor_status


def build_parser() -> argparse.ArgumentParser:
    """Build the OmniClaw CLI parser."""
    parser = argparse.ArgumentParser(prog="omniclaw")
    subparsers = parser.add_subparsers(dest="command")

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Inspect OmniClaw setup, managed credentials, and recovery state",
    )
    doctor_parser.add_argument("--api-key", help="Override CIRCLE_API_KEY for diagnostics")
    doctor_parser.add_argument(
        "--entity-secret",
        help="Override ENTITY_SECRET for diagnostics",
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the OmniClaw CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        print_doctor_status(
            api_key=args.api_key,
            entity_secret=args.entity_secret,
            as_json=args.json,
        )
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
