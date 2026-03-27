#!/usr/bin/env python3
"""
Setup script for facilitator integration testing.

This script helps you:
1. Check which facilitator API keys are configured
2. Provide instructions for getting API keys
3. Run integration tests with available keys
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header(text: str):
    print(f"\n{'=' * 60}")
    print(f" {text}")
    print("=" * 60)


def check_api_keys():
    """Check which API keys are configured."""
    print_header("Checking API Keys")

    keys = {
        "CIRCLE_API_KEY": "Circle Gateway",
        "COINBASE_API_KEY": "Coinbase CDP",
        "ORDERN_API_KEY": "OrderN",
        "RBX_API_KEY": "RBX",
        "THIRDWEB_API_KEY": "Thirdweb",
    }

    configured = []
    missing = []

    for env_var, name in keys.items():
        value = os.environ.get(env_var)
        if value and len(value) > 5:
            # Show masked version
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"  [{'✓'}] {name}: {masked}")
            configured.append(name)
        else:
            print(f"  [{' '}] {name}: Not configured")
            missing.append(name)

    return configured, missing


def print_setup_instructions():
    """Print instructions for getting API keys."""
    print_header("How to Get API Keys")

    instructions = """
    CIRCLE GATEWAY:
    1. Go to https://www.circle.com/en/gateway
    2. Sign up for an account
    3. Create API key in the dashboard
    4. Set: export CIRCLE_API_KEY="your_key"
    
    COINBASE CDP:
    1. Go to https://portal.cdp.coinbase.com/
    2. Sign up and create a project
    3. Generate API key with x402 permissions
    4. Set: export COINBASE_API_KEY="your_key"
    
    ORDERN:
    1. Go to https://ordern.ai
    2. Sign up for early access
    3. Get API key from dashboard
    4. Set: export ORDERN_API_KEY="your_key"
    
    RBX:
    1. Go to https://rbx.io
    2. Sign up for beta access
    3. Get API key
    4. Set: export RBX_API_KEY="your_key"
    
    THIRDWEB:
    1. Go to https://thirdweb.com/dashboard
    2. Create a project
    3. Get API key
    4. Set: export THIRDWEB_API_KEY="your_key"
    """
    print(instructions)


def run_tests(facilitators: list[str] | None = None):
    """Run integration tests."""
    print_header("Running Integration Tests")

    test_file = "tests/test_facilitator_live_integration.py"

    if not Path(test_file).exists():
        print(f"Error: Test file not found: {test_file}")
        return 1

    if facilitators:
        # Run specific tests
        for fac in facilitators:
            test_name = f"test_{fac}_verify"
            print(f"\n--- Testing {fac.upper()} ---")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", f"{test_file}::{test_name}", "-v", "-s"],
                cwd=Path(__file__).parent.parent,
            )
            if result.returncode != 0:
                print(f"Test failed for {fac}")
    else:
        # Run all tests
        print("\nRunning all facilitator tests...")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "-s"],
            cwd=Path(__file__).parent.parent,
        )
        return result.returncode

    return 0


def main():
    print("=" * 60)
    print(" OmniClaw Facilitator Integration Test Setup")
    print("=" * 60)

    # Check API keys
    configured, missing = check_api_keys()

    print(f"\n{len(configured)} facilitator(s) configured, {len(missing)} missing")

    if missing:
        print_setup_instructions()

    # Ask to run tests
    if configured:
        print("\n" + "=" * 60)
        response = input("Run integration tests? [y/N]: ").strip().lower()

        if response == "y" or response == "yes":
            # Allow selecting specific facilitators
            print("\nAvailable facilitators:", ", ".join(configured))
            fac_input = input("Enter facilitator(s) to test (or 'all'): ").strip().lower()

            if fac_input == "all" or not fac_input:
                return run_tests()
            else:
                facilitators = [f.strip() for f in fac_input.split(",")]
                return run_tests(facilitators)

    print("\nSetup complete. Configure API keys and run again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
