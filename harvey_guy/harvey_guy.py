from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from .libs import Log


class Harvey:
    def __init__(self) -> None:
        if TYPE_CHECKING:
            self.root_dir: Path
            self.data_dir: Path
            self.docs_dir: Path
            self.repos_dir: Path
            self.session_docs_dir: Path
            self.session_dir: Path
            self.session_id: str
            self.log: Log

    def _setup(self) -> Harvey:
        self._get_paths()
        self.session_id, self.session_dir, self.log = self._init_session()
        self.session_docs_dir = self.session_dir / "docs"
        self.repos_dir = self.session_dir / "repos"
        return self

    @classmethod
    def setup(cls) -> Harvey:
        _instance = cls()
        return _instance._setup()

    def _get_root_dir(self, root_dir: str | None) -> Path:
        if root_dir is None:
            return Path(__file__).resolve().parent.parent
        return Path(root_dir).resolve()

    def _init_session(self) -> tuple[str, Path, Log]:
        session_id = str(uuid.uuid4())
        session_dir = Path("/tmp") / f"karen_guard_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        anti_karen_dir = session_dir / "anti_karen"
        anti_karen_dir.mkdir(parents=True, exist_ok=True)

        # Check for previous session state and copy history files into anti_karen
        import os

        checkpoint_path = Path(
            os.environ.get("LOOP_STATE_PATH", "/tmp/karen_guard_loop_state.json")
        )
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path) as f:
                    state = json.load(f)
                prev_session_id = state.get("session_id")
                if prev_session_id and prev_session_id != "previous_or_null":
                    prev_anti_karen = Path("/tmp") / f"karen_guard_{prev_session_id}" / "anti_karen"
                    if prev_anti_karen.exists() and prev_anti_karen.is_dir():
                        for item in prev_anti_karen.iterdir():
                            if item.is_file():
                                if item.name == "karen_guard_core.log":
                                    shutil.copy2(item, anti_karen_dir / "karen_guard_core_prev.log")
                                elif item.name == "karen_run.log":
                                    shutil.copy2(item, anti_karen_dir / "karen_run_prev.log")
                                else:
                                    shutil.copy2(item, anti_karen_dir / item.name)
            except Exception:
                pass

        log = Log.config(anti_karen_dir / "karen_guard_core.log", tool="harvey")
        log.info(f"Session initialized with ID: {session_id}")
        log.info(f"Session directory created: {session_dir}")
        return session_id, session_dir, log

    def _get_paths(self, root_dir: str | None = None) -> Harvey:
        self.root_dir = self._get_root_dir(root_dir)
        self.data_dir = self.root_dir / ".data"
        self.docs_dir = self.data_dir / "docs"
        return self

    def setup_paths(self) -> Harvey:
        self.data_dir.mkdir(exist_ok=True)
        self.docs_dir.mkdir(exist_ok=True)
        self.repos_dir.mkdir(exist_ok=True)
        self.log.info(f"Directories initialized under {self.data_dir}")
        return self

    def ingest_documents(self) -> Harvey:
        import os

        self.session_docs_dir.mkdir(parents=True, exist_ok=True)
        anti_karen_dir = self.session_dir / "anti_karen"
        anti_karen_dir.mkdir(exist_ok=True)

        required = {"cv.md", "job.md"}
        present = {item.name for item in self.docs_dir.iterdir() if item.is_file()}
        missing = required - present
        if missing:
            raise FileNotFoundError(
                f"Missing required documents in .data/docs/: {', '.join(sorted(missing))}"
            )

        karen_reads = os.environ.get("KAREN_READS_BACKGROUND", "yes").lower() == "yes"

        for item in self.docs_dir.iterdir():
            if item.is_file():
                if item.name.startswith('.'):
                    continue
                if item.name == "who_are_u.md" and not karen_reads:
                    shutil.copy2(item, anti_karen_dir / item.name)
                    self.log.info(
                        f"Ingested document {item.name} exclusively for Bill (anti_karen)"
                    )
                else:
                    shutil.copy2(item, self.session_docs_dir / item.name)
                    self.log.info(f"Ingested document {item.name} to session docs")
        return self

    def check_dependencies(self) -> Harvey:
        try:
            result = subprocess.run(["which", "at"], capture_output=True, text=True)
            if result.returncode != 0:
                self.log.warning(
                    "'at' utility not found. Long-running task watchdog will not function."
                )
            else:
                self.log.info("'at' utility is available.")
        except Exception as e:
            self.log.warning(f"Could not verify 'at' utility: {e}")
        return self

    def print_session_id(self) -> Harvey:
        print(self.session_id)
        return self
