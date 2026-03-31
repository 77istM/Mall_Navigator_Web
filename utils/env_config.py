"""Environment configuration helpers.

Loads key/value pairs from a local .env file without requiring third-party
packages. Existing process environment variables are never overwritten.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: str = ".env") -> dict[str, str]:
    """Load variables from a .env file into os.environ.

    Returns a dict of variables that were loaded from the file.
    """
    env_path = Path(path)
    if not env_path.exists() or not env_path.is_file():
        return {}

    loaded: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue

        if key not in os.environ:
            os.environ[key] = value
            loaded[key] = value
    return loaded
