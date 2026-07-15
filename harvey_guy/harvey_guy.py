from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from .layout import SessionLayout
from .libs import Log


class Harvey:
    def __init__(
        self,
        *,
        root_dir: Path | None = None,
        data_dir: Path | None = None,
        session_root: Path | None = None,
        karen_reads_background: bool | None = None,
    ) -> None:
        self.root_dir = (root_dir or Path(__file__).resolve().parent.parent).resolve()
        configured_data = os.environ.get("PIPELINE_DATA_DIR")
        self.data_dir = (
            data_dir or (Path(configured_data) if configured_data else self.root_dir / ".data")
        ).resolve()
        self.docs_dir = self.data_dir / "docs"
        configured_sessions = os.environ.get("PIPELINE_SESSION_ROOT")
        self.session_root = (
            session_root
            or (Path(configured_sessions) if configured_sessions else Path("/tmp"))
        ).resolve()
        if karen_reads_background is None:
            raw_background = os.environ.get("KAREN_READS_BACKGROUND", "yes")
            if raw_background not in {"yes", "no"}:
                raise ValueError("KAREN_READS_BACKGROUND must be 'yes' or 'no'")
            karen_reads_background = raw_background == "yes"
        self.karen_reads_background = karen_reads_background

        self.session_id = ""
        self.session_dir = Path()
        self.session_docs_dir = Path()
        self.repos_dir = Path()
        self.log: Log
        self.layout: SessionLayout

    @classmethod
    def setup(
        cls,
        *,
        root_dir: Path | None = None,
        data_dir: Path | None = None,
        session_root: Path | None = None,
        karen_reads_background: bool | None = None,
    ) -> Harvey:
        return cls(
            root_dir=root_dir,
            data_dir=data_dir,
            session_root=session_root,
            karen_reads_background=karen_reads_background,
        )._setup()

    def _setup(self) -> Harvey:
        self.session_id, self.session_dir, self.log = self._init_session()
        self.layout = SessionLayout(self.session_dir)
        self.session_docs_dir = self.layout.docs
        self.repos_dir = self.layout.repos
        return self

    def _init_session(self) -> tuple[str, Path, Log]:
        session_id = str(uuid.uuid4())
        session_dir = self.session_root / f"karen_guard_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=False)
        layout = SessionLayout(session_dir)
        layout.create()

        log = Log.config(layout.logs / "harvey.log", tool="harvey")
        log.info(f"Session initialized with ID: {session_id}")
        return session_id, session_dir, log

    def setup_paths(self) -> Harvey:
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.layout.create()
        return self

    def ingest_documents(self) -> Harvey:
        required = ("cv.md", "job.md")
        for name in required:
            source = self.docs_dir / name
            if not source.is_file() or source.stat().st_size == 0:
                raise FileNotFoundError(f"Missing required document: {source}")
            shutil.copy2(source, self.session_docs_dir / name)
            self.log.info(f"Ingested {name} to session docs")

        background = self.docs_dir / "who_are_u.md"
        if background.is_file():
            destination_dir = (
                self.session_docs_dir
                if self.karen_reads_background
                else self.layout.artifacts
            )
            shutil.copy2(background, destination_dir / background.name)
            self.log.info(f"Ingested {background.name} to {destination_dir.name}")
        return self
