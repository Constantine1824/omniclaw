"""Command-line interface for OmniClaw operator utilities."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from omniclaw.onboarding import print_doctor_status, run_setup_cli


def build_parser() -> argparse.ArgumentParser:
    """Build the OmniClaw CLI parser."""
    parser = argparse.ArgumentParser(prog="omniclaw")
    subparsers = parser.add_subparsers(dest="command")

    # --- doctor ---
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

    # --- setup ---
    setup_parser = subparsers.add_parser(
        "setup",
        help="Run first-time OmniClaw setup (generate entity secret, register with Circle, create .env)",
    )
    setup_parser.add_argument(
        "--api-key",
        default=None,
        help="Circle API key (falls back to CIRCLE_API_KEY env var)",
    )
    setup_parser.add_argument(
        "--network",
        default="ARC-TESTNET",
        help="Target network (default: ARC-TESTNET)",
    )
    setup_parser.add_argument(
        "--env-path",
        default=".env",
        help="Path for .env file (default: .env in current directory)",
    )
    setup_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing .env and credentials without prompting",
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

    if args.command == "setup":
        api_key = args.api_key or os.environ.get("CIRCLE_API_KEY")
        if not api_key:
            print(
                "Error: Circle API key is required.\n"
                "Pass --api-key or set the CIRCLE_API_KEY environment variable.",
                file=sys.stderr,
            )
            return 1
        return run_setup_cli(
            api_key=api_key,
            network=args.network,
            env_path=args.env_path,
            force=args.force,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
