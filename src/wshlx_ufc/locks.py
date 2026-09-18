from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class FrozenLock:
    payload: dict[str, Any]
    sha256: str


def canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def freeze_payload(payload: Mapping[str, Any]) -> FrozenLock:
    body = dict(payload)
    body.setdefault("locked_at_utc", datetime.now(timezone.utc).isoformat())
    encoded = canonical_json(body).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return FrozenLock(payload=body, sha256=digest)


def write_lock_once(path: str | Path, lock: FrozenLock) -> None:
    """Write an immutable prediction lock; refuse to overwrite."""
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing lock: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    envelope = {"sha256": lock.sha256, "payload": lock.payload}
    target.write_text(
        json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def verify_lock(path: str | Path) -> bool:
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    payload = envelope["payload"]
    expected = envelope["sha256"]
    actual = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return actual == expected
