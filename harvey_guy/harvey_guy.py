from __future__ import annotations
from typing import TYPE_CHECKING
import re
import json
import uuid
import shutil
import urllib.request
import urllib.parse
import subprocess
from pathlib import Path
from .libs import Log

class Harvey:
    def __init__(self) -> None:
        if TYPE_CHECKING:
            self.root_dir: Path
            self.data_dir: Path
            self.documentation_dir: Path
            self.docs_dir: Path
            self.repos_dir: Path
            self.session_docs_dir: Path
            self.session_dir: Path 
            self.session_id: str
            self.github_username: str
            self.repos: list[dict[str, str]]
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

        log = Log.config(session_dir / "karen_guard_core.log", tool="harvey")
        log.info(f"Session initialized with ID: {session_id}")
        log.info(f"Session directory created: {session_dir}")
        return session_id, session_dir, log

    def _get_paths(self, root_dir: str | None = None):
        self.root_dir = self._get_root_dir(root_dir)
        self.data_dir = self.root_dir / "data"
        self.documentation_dir = self.data_dir / "documentation"
        self.docs_dir = self.data_dir / "docs"
        self.repos = []

    def setup_paths(self) -> Harvey:
        self.data_dir.mkdir(exist_ok=True)
        self.documentation_dir.mkdir(exist_ok=True)
        self.docs_dir.mkdir(exist_ok=True)
        self.repos_dir.mkdir(exist_ok=True)
        
        self.log.info(f"Directories initialized under {self.data_dir}")
        return self

    def ingest_documents(self) -> Harvey:
        self.session_docs_dir.mkdir(parents=True, exist_ok=True)
        for item in self.docs_dir.iterdir():
            if item.is_file():
                shutil.copy2(item, self.session_docs_dir / item.name)
                self.log.info(f"Ingested document {item.name} to session")
        return self

    def fetch_github_username(self) -> Harvey:
        try:
            result = subprocess.run(
                ["git", "config", "remote.origin.url"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.root_dir
            )
            url = result.stdout.strip()
            match = re.search(r"github\.com[:/]([^/]+)/", url)
            if match:
                self.github_username = match.group(1)
                self.log.info(f"Detected GitHub username from origin URL: {self.github_username}")
            else:
                self.log.warning(f"Could not parse username from URL: {url}")
        except Exception as e:
            self.log.error(f"Failed to get git origin URL: {e}")

        if not self.github_username:
            try:
                result = subprocess.run(
                    ["git", "config", "github.user"],
                    capture_output=True,
                    text=True,
                    cwd=self.root_dir
                )
                user = result.stdout.strip()
                if user:
                    self.github_username = user
                    self.log.info(f"Detected GitHub username from config: {self.github_username}")
            except Exception:
                pass

        if not self.github_username:
            self.log.warning("GitHub username could not be determined.")
            
        return self

    def ingest_repositories(self) -> Harvey:
        if not self.github_username:
            self.log.error("No GitHub username detected. Run fetch_github_username first.")
            return self

        url = f"https://api.github.com/users/{self.github_username}/repos?per_page=100"
        self.log.info(f"Ingesting repositories from GitHub API: {url}")
        
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Antigravity-JobStack-Harvey"}
            )

            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                self.repos = [
                    {
                        "name": repo["name"],
                        "clone_url": repo["clone_url"],
                        "ssh_url": repo["ssh_url"]
                    }
                    for repo in data
                ]
                
            repos_file = self.session_dir / "repos.json"
            with open(repos_file, "w", encoding="utf-8") as f:
                json.dump(self.repos, f, indent=4)
                
            self.log.info(f"Ingested {len(self.repos)} repositories nomenclature to {repos_file}")

            for repo in self.repos:
                try:
                    clone_url = repo["clone_url"]
                    target_path = self.repos_dir / repo["name"]
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    subprocess.run(
                        ["git", "clone", clone_url, str(target_path)],
                        capture_output=True,
                        check=True
                    )
                    self.log.info(f"Cloned repository {repo['name']} to {target_path}")
                except Exception as clone_error:
                    self.log.error(f"Failed to clone repository {repo['name']}: {clone_error}")
        except Exception as e:
            self.log.error(f"Failed to ingest repositories from GitHub API: {e}")
            
        return self

    def research_company(self) -> Harvey:
        company_name = "Unknown"
        job_path = self.docs_dir / "job.md"
        if job_path.exists():
            with open(job_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                match = re.search(r"—\s*([A-Za-z0-9\s]+)", first_line)
                if match:
                    company_name = match.group(1).strip()

        info_text = ""
        try:
            query = f"{company_name} empresa"
            url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode())
                info_text = res_data.get("AbstractText", "")
        except Exception as e:
            self.log.error(f"Search failed: {e}")

        if not info_text:
            try:
                wiki_url = f"https://pt.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(company_name)}&format=json"
                req = urllib.request.Request(wiki_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req) as response:
                    wiki_data = json.loads(response.read().decode())
                    search_results = wiki_data.get("query", {}).get("search", [])
                    if search_results:
                        snippet = search_results[0].get("snippet", "")
                        info_text = re.sub(r"<[^>]+>", "", snippet)
            except Exception as e:
                self.log.error(f"Wiki search failed: {e}")

        info_file = self.session_dir / "company_info.md"
        with open(info_file, "w", encoding="utf-8") as f:
            f.write(f"# Company Information: {company_name}\n\n")
            f.write(f"{info_text}\n")
        self.log.info(f"Company information saved to {info_file}")

        anti_karen_dir = self.session_dir / "anti_karen"
        anti_karen_dir.mkdir(exist_ok=True)
        self.log.info(f"Directory {anti_karen_dir} created successfully")
        
        return self

    def print_session_id(self) -> Harvey:
        print(self.session_id)
        return self