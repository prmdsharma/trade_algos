"""
Pytest configuration: ensures the project root is on sys.path so that
bare imports like `from execution.trade_manager import ...` work when
running `pytest tests` directly.
"""

import sys
from pathlib import Path

# Add the project root (sensex_scalping_algo/) to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
