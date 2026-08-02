from __future__ import annotations

import secrets
import time
import uuid


def new_id(prefix: str) -> str:
    """Return a time-sortable UUIDv7 identifier with a domain prefix."""
    timestamp_ms = int(time.time() * 1000)
    value = timestamp_ms << 80
    value |= 0x7 << 76
    value |= secrets.randbits(12) << 64
    value |= 0b10 << 62
    value |= secrets.randbits(62)
    return f"{prefix}_{uuid.UUID(int=value)}"


def stable_id(prefix: str, namespace: str, value: str) -> str:
    return f"{prefix}_{uuid.uuid5(uuid.uuid5(uuid.NAMESPACE_URL, namespace), value)}"
