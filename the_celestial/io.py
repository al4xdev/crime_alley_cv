from __future__ import annotations

import json
import os
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import Any


def digest_text(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_json(value: Any) -> str:
    return digest_text(canonical_json(value))


def atomic_write_text(path: Path, content: str, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if exclusive and path.exists():
        raise FileExistsError(path)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive and path.exists():
            raise FileExistsError(path)
        temporary.replace(path)
        path.chmod(0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_json(path: Path, value: Any, *, exclusive: bool = False) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        exclusive=exclusive,
    )


def read_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value
