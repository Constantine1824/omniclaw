"""
Pytest configuration for nanopayments integration tests.

IMPORTANT: This conftest must mock 'circle' BEFORE any imports of omniclaw
or its submodules. This overrides the parent conftest.py for these tests.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# CRITICAL: Mock circle BEFORE any omniclaw imports
if "circle" not in sys.modules:
    sys.modules["circle"] = MagicMock()
    sys.modules["circle.web3"] = MagicMock()
    sys.modules["circle.web3.developer_controlled_wallets"] = MagicMock()
