"""Utilities for common error handlers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_common_handlers(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    with file_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return []
    if isinstance(data, dict):
        handlers = data.get("error_handlers", [])
    else:
        handlers = data
    if not isinstance(handlers, list):
        return []
    return [handler for handler in handlers if isinstance(handler, dict)]
