from __future__ import annotations

import warnings

# Suppress deprecation warnings from downstream dependencies (e.g. web3 using pkg_resources)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")
warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")

import argparse
import json
import os
import sys
from collections.abc import Sequence

from omniclaw.onboarding import (
    print_backup_info,
    print_doctor_status,
    run_export_env_cli,
    run_import_secret_cli,
    run_setup_cli,
)


BANNER = r"""
   ____  __  __ _   _ ___ ____ _        ___        __
  / __ \|  \/  | \ | |_ _/ ___| |      / \ \      / /
 | |  | | |\/| |  \| || | |   | |     / _ \ \ /\ / /
 | |__| | |  | | |\  || | |___| |___ / ___ \ V  V /
  \____/|_|  |_|_| \_|___\____|_____/_/   \_\_/\_/

  OmniClaw is the economy and control layer for AI agent payments.
  Economic Execution and Control Layer for Agentic Systems
"""


def print_banner():
    """Print the OmniClaw CLI banner."""
    print(f"\033[1;36m{BANNER}\033[0m")
    print("\033[90mOmniClaw Financial Infrastructure - v2.0 Production-Ready\033[0m\n")


ENV_VARS = {
    "required": {
        "CIRCLE_API_KEY": "Circle API key for wallet/payment operations",
        "OMNICLAW_PRIVATE_KEY": "Private key for nanopayment signing",
    },
    "optional": {
        "ENTITY_SECRET": "Auto-generated entity secret (advanced/manual setup only)",
        "OMNICLAW_RPC_URL": "RPC endpoint for trust gate (ERC-8004)",
        "OMNICLAW_STORAGE_BACKEND": "Storage backend: memory or redis",
        "OMNICLAW_REDIS_URL": "Redis connection URL (when using redis)",
        "OMNICLAW_LOG_LEVEL": "Logging: DEBUG, INFO, WARNING, ERROR",
    },
    "production": {
        "OMNICLAW_ENV": "Set to production for mainnet/strict mode",
        "OMNICLAW_STRICT_SETTLEMENT": "Enable strict settlement validation",
        "OMNICLAW_WEBHOOK_VERIFICATION_KEY": "Public key for webhook signatures",
        "OMNICLAW_SELLER_NONCE_REDIS_URL": "Redis for distributed nonce (multi-instance)",
    },
}


def print_env_vars():
    """Print all available environment variables."""
    print("\n=== OmniClaw Environment Variables ===\n")

    print("Required:")
    for var, desc in ENV_VARS["required"].items():
        value = os.environ.get(var, "")
        status = f"✓ {value[:20]}..." if value else "✗ not set"
        print(f"  {var}")
        print(f"    {desc}")
        print(f"    {status}\n")

    print("\nOptional:")
    for var, desc in ENV_VARS["optional"].items():
        value = os.environ.get(var, "")
        status = f"✓ {value[:30]}..." if value else "○ default"
        print(f"  {var}")
        print(f"    {desc}")
        print(f"    {status}\n")

    print("\nProduction:")
    for var, desc in ENV_VARS["production"].items():
        value = os.environ.get(var, "")
        status = f"✓ {value[:30]}..." if value else "○ not set"
        print(f"  {var}")
        print(f"    {desc}")
        print(f"    {status}\n")


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

    # --- env ---
    subparsers.add_parser(
        "env",
        help="List all available environment variables",
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

    # --- backup-info ---
    backup_info_parser = subparsers.add_parser(
        "backup-info",
        help="Show location and status of backup-critical files (recovery file, managed credentials, .env)",
    )
    backup_info_parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )

    # --- export-env ---
    export_env_parser = subparsers.add_parser(
        "export-env",
        help="Print active credentials as shell export statements or dotenv format",
    )
    export_env_parser.add_argument(
        "--format",
        choices=["shell", "dotenv"],
        default="shell",
        help="Output format (default: shell)",
    )
    export_env_parser.add_argument(
        "--output",
        default=None,
        help="Write to file instead of stdout",
    )
    export_env_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it exists",
    )
    export_env_parser.add_argument(
        "--api-key",
        default=None,
        help="Circle API key (falls back to CIRCLE_API_KEY env var)",
    )

    # --- import-secret ---
    import_secret_parser = subparsers.add_parser(
        "import-secret",
        help="Import an existing entity secret into the managed config store",
    )
    import_secret_parser.add_argument(
        "--api-key",
        default=None,
        help="Circle API key (falls back to CIRCLE_API_KEY env var)",
    )
    import_secret_parser.add_argument(
        "--entity-secret",
        required=True,
        help="64-character hex entity secret to import",
    )
    import_secret_parser.add_argument(
        "--recovery-file",
        default=None,
        help="Path to the associated Circle recovery file",
    )

    # --- server ---
    server_parser = subparsers.add_parser(
        "server",
        help="Start the OmniClaw Control Plane (Financial Firewall) server",
    )
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    server_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # --- policy ---
    policy_parser = subparsers.add_parser(
        "policy",
        help="Policy utilities (lint/validate)",
    )
    policy_sub = policy_parser.add_subparsers(dest="policy_command")
    lint_parser = policy_sub.add_parser("lint", help="Validate policy.json")
    lint_parser.add_argument(
        "--path",
        default=os.environ.get("OMNICLAW_AGENT_POLICY_PATH", "/config/policy.json"),
        help="Path to policy.json",
    )

    return parser


def handle_setup(args: argparse.Namespace) -> int:
    """Handle the setup command."""
    from omniclaw.onboarding import resolve_entity_secret, create_env_file

    api_key = args.api_key or os.getenv("CIRCLE_API_KEY")
    if not api_key:
        api_key = input("Enter your Circle API Key: ").strip()

    if not api_key:
        print("❌ Error: Circle API Key is required.")
        return 1

    entity_secret = resolve_entity_secret(api_key)
    if entity_secret:
        print("✅ Found existing Entity Secret in managed store.")
    else:
        print("💡 No Entity Secret found for this API key.")
        entity_secret = input(
            "Enter your 64-char Entity Secret (or press Enter to generate): "
        ).strip()
        if not entity_secret:
            from omniclaw.onboarding import auto_setup_entity_secret

            print("🚀 Generating and registering new Entity Secret...")
            entity_secret = auto_setup_entity_secret(api_key)

    env_path = ".env.agent"
    create_env_file(api_key, entity_secret, env_path=env_path, network=args.network, overwrite=True)
    print(f"✨ Successfully configured {env_path}!")
    print("To start the server locally, run: omniclaw server")
    print("To start via Docker, run: docker compose -f docker-compose.agent.yml up -d")
    return 0


def handle_server(args: argparse.Namespace) -> int:
    """Handle the server command."""
    import uvicorn
    from dotenv import load_dotenv
    from omniclaw.onboarding import resolve_entity_secret, auto_setup_entity_secret

    # Load .env.agent if it exists
    if os.path.exists(".env.agent"):
        load_dotenv(".env.agent")
        print("📄 Loaded configuration from .env.agent")
    elif os.path.exists(".env"):
        load_dotenv(".env")
        print("📄 Loaded configuration from .env")

    # Auto-Setup Logic: Check if we have an API key but no Entity Secret
    api_key = os.getenv("CIRCLE_API_KEY")
    entity_secret = os.getenv("ENTITY_SECRET")

    if api_key and not entity_secret:
        print("💡 Found API Key but no Entity Secret. Attempting auto-setup...")
        entity_secret = resolve_entity_secret(api_key)
        if not entity_secret:
            print("🚀 Generating new Entity Secret for this machine...")
            entity_secret = auto_setup_entity_secret(api_key)

        if entity_secret:
            os.environ["ENTITY_SECRET"] = entity_secret
            print("✅ Credentials verified and injected.")
        else:
            print("❌ Error: Failed to resolve or generate Entity Secret.")
            return 1

    print(f"🚀 Starting OmniClaw Control Plane on {args.host}:{args.port}...")
    uvicorn.run(
        "omniclaw.agent.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=os.getenv("OMNICLAW_LOG_LEVEL", "info").lower(),
    )
    return 0


def handle_policy_lint(args: argparse.Namespace) -> int:
    """Validate policy.json against strict schema."""
    from omniclaw.agent.policy_schema import validate_policy

    path = args.path
    try:
        with open(path) as f:
            data = json.load(f)
        validate_policy(data)
        print(f"✅ policy.json is valid: {path}")
        return 0
    except Exception as e:
        print(f"❌ Invalid policy.json: {e}")
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the OmniClaw CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    print_banner()

    if args.command == "doctor":
        print_doctor_status(
            api_key=args.api_key,
            entity_secret=args.entity_secret,
            as_json=args.json,
        )
        return 0

    if args.command == "env":
        print_env_vars()
        return 0

    if args.command == "setup":
        return handle_setup(args)

    if args.command == "backup-info":
        print_backup_info(as_json=args.json)
        return 0

    if args.command == "export-env":
        return run_export_env_cli(
            api_key=args.api_key,
            fmt=args.format,
            output=args.output,
            force=args.force,
        )

    if args.command == "import-secret":
        api_key = args.api_key or os.environ.get("CIRCLE_API_KEY")
        if not api_key:
            print(
                "Error: Circle API key is required.\n"
                "Pass --api-key or set the CIRCLE_API_KEY environment variable.",
                file=sys.stderr,
            )
            return 1
        return run_import_secret_cli(
            api_key=api_key,
            entity_secret=args.entity_secret,
            recovery_file=args.recovery_file,
        )

    if args.command == "server":
        return handle_server(args)

    if args.command == "policy" and args.policy_command == "lint":
        return handle_policy_lint(args)

    parser.print_help()
    print("\nCommands:")
    print("  setup        - Quick credentials configuration")
    print("  server       - Start the Financial Firewall server")
    print("  doctor       - Inspect setup and credentials")
    print("  env          - List all environment variables")
    print("  backup-info  - Show backup file locations")
    print("  export-env   - Export credentials to shell/dotenv")
    print("  import-secret - Import an entity secret")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
