from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def validate_session_id(session_id: str) -> str:
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError(f"Invalid session ID: {session_id!r}")
    return session_id


@dataclass(frozen=True, slots=True)
class SessionLayout:
    root: Path

    @classmethod
    def from_id(cls, session_id: str, *, tmp_root: Path = Path("/tmp")) -> SessionLayout:
        return cls(tmp_root / f"karen_guard_{validate_session_id(session_id)}")

    @property
    def docs(self) -> Path:
        return self.root / "docs"

    @property
    def repos(self) -> Path:
        return self.root / "repos"

    @property
    def out(self) -> Path:
        return self.root / "out"

    @property
    def private(self) -> Path:
        return self.root / "anti_karen"

    @property
    def artifacts(self) -> Path:
        return self.private / "artifacts"

    @property
    def contracts(self) -> Path:
        return self.private / "contracts"

    @property
    def logs(self) -> Path:
        return self.private / "logs"

    def create(self) -> None:
        for directory in (
            self.root,
            self.docs,
            self.repos,
            self.out,
            self.private,
            self.artifacts,
            self.contracts,
            self.logs,
        ):
            directory.mkdir(parents=True, exist_ok=True)
