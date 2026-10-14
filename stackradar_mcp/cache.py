"""Small JSON cache so a demo does not hammer public APIs on every question."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def cache_dir() -> Path:
    path = Path(os.environ.get("STACKRADAR_CACHE_DIR", ".cache/stackradar"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_ttl_seconds() -> int:
    raw = os.environ.get("STACKRADAR_CACHE_TTL_SECONDS", str(6 * 3600))
    try:
        return max(1, int(raw))
    except ValueError:
        return 6 * 3600


def _path_for(key: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in key)[:180]
    return cache_dir() / f"{safe}.json"


def cache_get(key: str) -> Any | None:
    path = _path_for(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("expires_at", 0) < time.time():
        return None
    return payload.get("value")


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    path = _path_for(key)
    payload = {"expires_at": time.time() + (ttl if ttl is not None else cache_ttl_seconds()), "value": value}
    path.write_text(json.dumps(payload), encoding="utf-8")
