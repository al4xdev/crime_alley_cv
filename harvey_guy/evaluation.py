from __future__ import annotations

import re
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

SCORE_LINE = re.compile(
    r"^## Technical Fit Score: (?P<score>[0-9]{1,3})/100$",
    re.MULTILINE,
)


class Evaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    fit_score: int = Field(ge=0, le=100)
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def parse_evaluation(content: str) -> Evaluation:
    matches = list(SCORE_LINE.finditer(content))
    if len(matches) != 1:
        raise ValueError(
            "Evaluation must contain exactly one canonical "
            "'## Technical Fit Score: N/100' line."
        )
    score = int(matches[0].group("score"))
    digest = sha256(content.encode("utf-8")).hexdigest()
    return Evaluation(fit_score=score, report_sha256=digest)


def read_evaluation(path: Path) -> Evaluation:
    if not path.is_file():
        raise FileNotFoundError(path)
    return parse_evaluation(path.read_text(encoding="utf-8"))
