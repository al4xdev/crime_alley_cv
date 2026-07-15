from __future__ import annotations

import json
from pathlib import Path

from .io import read_json_object
from .models import ConversationEnvelope, VerificationRequest

MAX_EXCERPT_CHARACTERS = 4000


def collect_frozen_excerpts(
    case_root: Path,
    requests: list[VerificationRequest],
) -> list[dict[str, str]]:
    if len(requests) > 5:
        raise ValueError("A verification batch may contain at most five requests")
    messages: dict[str, list[tuple[str, str]]] = {}
    for path in sorted((case_root / "envelopes").glob("*/*.json")):
        envelope = ConversationEnvelope.model_validate_json(json.dumps(read_json_object(path)))
        for message in envelope.messages:
            messages.setdefault(message.source_label, []).append(
                (message.message_id, message.content)
            )
    results: list[dict[str, str]] = []
    for request in requests:
        candidates = messages.get(request.source_label, [])
        query = request.query.casefold()
        selected = next(
            (
                (message_id, content)
                for message_id, content in candidates
                if query in content.casefold()
            ),
            candidates[0] if candidates else None,
        )
        if selected is None:
            results.append(
                {
                    "claim_id": request.claim_id,
                    "source_label": request.source_label,
                    "status": "unavailable",
                    "excerpt": "",
                }
            )
            continue
        message_id, content = selected
        results.append(
            {
                "claim_id": request.claim_id,
                "source_label": request.source_label,
                "status": "available",
                "message_id": message_id,
                "excerpt": content[:MAX_EXCERPT_CHARACTERS],
            }
        )
    return results
