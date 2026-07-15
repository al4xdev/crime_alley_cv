from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from .models import AgentProfile, AgentRole

ROOT = Path(__file__).resolve().parent
PROFILES_ROOT = ROOT / "profiles"
RUBRIC_PATH = ROOT / "rubric.json"


def load_profile(role: AgentRole | str) -> tuple[AgentProfile, str]:
    parsed_role = AgentRole(role)
    path = PROFILES_ROOT / parsed_role.value / "profile.json"
    content = path.read_bytes()
    profile = AgentProfile.model_validate_json(content)
    if profile.role is not parsed_role:
        raise ValueError(f"Profile role mismatch: {path}")
    return profile, sha256(content).hexdigest()


def load_rubric() -> tuple[dict[str, object], str]:
    content = RUBRIC_PATH.read_bytes()
    value = json.loads(content)
    if not isinstance(value, dict):
        raise ValueError("The Celestial rubric must be a JSON object")
    return value, sha256(content).hexdigest()
