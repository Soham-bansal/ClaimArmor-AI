from __future__ import annotations

import os
from pathlib import Path


def load_local_env(path: Path = Path(".env")) -> None:
    """Load a simple local .env without overwriting process environment values."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key.replace("_", "").isalnum() or not key[0].isalpha():
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
