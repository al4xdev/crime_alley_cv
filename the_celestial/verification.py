from __future__ import annotations

from pathlib import Path

from .models import FrozenCaseManifest, VerificationRequest

MAX_EXCERPT_CHARACTERS = 4000


def available_source_ids(case_root: Path) -> list[str]:
    manifest = FrozenCaseManifest.model_validate_json(
        (case_root / "manifest.json").read_text(encoding="utf-8")
    )
    return [entry.source_id for entry in manifest.evidence_entries]


def collect_frozen_excerpts(
    case_root: Path,
    requests: list[VerificationRequest],
) -> list[dict[str, str]]:
    if len(requests) > 5:
        raise ValueError("A verification batch may contain at most five requests")
    manifest = FrozenCaseManifest.model_validate_json(
        (case_root / "manifest.json").read_text(encoding="utf-8")
    )
    entries = {entry.source_id: entry for entry in manifest.evidence_entries}
    results: list[dict[str, str]] = []
    for request in requests:
        entry = entries.get(request.source_id)
        if entry is None:
            results.append(
                {
                    "claim_id": request.claim_id,
                    "source_id": request.source_id,
                    "status": "unavailable",
                    "excerpt": "",
                }
            )
            continue
        path = case_root / "evidence" / entry.repository / entry.relative_path
        content = path.read_text(encoding="utf-8", errors="replace")
        folded = content.casefold()
        index = folded.find(request.query.casefold())
        if index < 0:
            results.append(
                {
                    "claim_id": request.claim_id,
                    "source_id": request.source_id,
                    "status": "unavailable",
                    "excerpt": "",
                }
            )
            continue
        start = max(0, index - MAX_EXCERPT_CHARACTERS // 2)
        excerpt = content[start : start + MAX_EXCERPT_CHARACTERS]
        results.append(
            {
                "claim_id": request.claim_id,
                "source_id": request.source_id,
                "status": "available",
                "excerpt": excerpt,
            }
        )
    return results
