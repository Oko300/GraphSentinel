"""
Gemini API Key Rotator
──────────────────────
Cycles through available Gemini keys in round-robin order.
Accepts either:
  - GEMINI_API_KEY          (single key)
  - GEMINI_API_KEY_1 … _N   (rotation pool)
  - GOOGLE_API_KEY          (alias)
"""

import os
import threading
from dotenv import load_dotenv

load_dotenv()


def _load_keys() -> list[str]:
    keys: list[str] = []

    # Numbered keys first (rotation pool)
    i = 1
    while True:
        key = os.getenv(f"GEMINI_API_KEY_{i}")
        if not key:
            break
        key = key.strip()
        if key:
            keys.append(key)
        i += 1

    # Single-key fallbacks
    for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        key = os.getenv(env_name)
        if key and key.strip() and key.strip() not in keys:
            keys.append(key.strip())

    if not keys:
        raise EnvironmentError(
            "No Gemini API keys found. "
            "Set GEMINI_API_KEY or GEMINI_API_KEY_1 … GEMINI_API_KEY_N "
            "in your environment / Render secrets."
        )
    return keys


class KeyRotator:
    """Thread-safe round-robin key rotator with rate-limit fallback."""

    def __init__(self):
        self._keys = _load_keys()
        self._index = 0
        self._lock = threading.Lock()
        print(f"[KeyRotator] Loaded {len(self._keys)} Gemini API key(s).")

    @property
    def current(self) -> str:
        with self._lock:
            return self._keys[self._index]

    def next_key(self) -> str:
        """Advance to the next key and return it."""
        with self._lock:
            self._index = (self._index + 1) % len(self._keys)
            new_key = self._keys[self._index]
            print(
                f"[KeyRotator] Rotated to key index {self._index + 1} "
                f"of {len(self._keys)}"
            )
            return new_key

    def __len__(self):
        return len(self._keys)


_rotator: KeyRotator | None = None


def get_rotator() -> KeyRotator:
    global _rotator
    if _rotator is None:
        _rotator = KeyRotator()
    return _rotator


def current_key() -> str:
    return get_rotator().current


def rotate_key() -> str:
    return get_rotator().next_key()
