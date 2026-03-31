"""Test configuration for pytest."""
import sys
from pathlib import Path

# Add project root to path so imports work
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
