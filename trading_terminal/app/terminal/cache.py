"""Results of slow fetches, kept on disk and refreshed in the background.

get() returns the last saved value straight away, even if it is stale, and starts a refresh
when it is older than max_age, so a slow source only ever blocks the very first load.
"""
from __future__ import annotations

import pickle
import threading
import time
from pathlib import Path
from typing import Any, Callable

from . import config

DIR = config.DATA_DIR / ".cache"
_lock = threading.Lock()
_running: set[str] = set()
_errors: dict[str, str] = {}


def _path(key: str) -> Path:
    return DIR / f"{key}.pkl"


def _load(key: str):
    try:
        with open(_path(key), "rb") as f:
            return pickle.load(f)  # (saved_at, value)
    except Exception:
        return None


def _refresh(key: str, fn: Callable[[], Any]) -> None:
    try:
        value = fn()
        DIR.mkdir(exist_ok=True)
        tmp = _path(key).with_suffix(".tmp")
        with open(tmp, "wb") as f:
            pickle.dump((time.time(), value), f)
        tmp.replace(_path(key))
        _errors.pop(key, None)
    except Exception as e:
        _errors[key] = str(e)
    finally:
        with _lock:
            _running.discard(key)


def get(key: str, fn: Callable[[], Any], max_age: float):
    """(value or None, age in seconds or None, refreshing now?, last refresh error or None)."""
    saved = _load(key)
    age = time.time() - saved[0] if saved else None
    with _lock:
        if (saved is None or age > max_age) and key not in _running:
            _running.add(key)
            threading.Thread(target=_refresh, args=(key, fn), daemon=True, name=f"cache-{key}").start()
        refreshing = key in _running
    return (saved[1] if saved else None), age, refreshing, _errors.get(key)
