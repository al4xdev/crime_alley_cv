from __future__ import annotations

import pytest

from harvey_guy.evaluation import parse_evaluation


def test_canonical_score_is_parsed() -> None:
    evaluation = parse_evaluation(
        "# Report\n\nCoverage: 99/100\n\n"
        "## Technical Fit Score: 72/100\n\n## Evidence\nUseful details.\n"
    )
    assert evaluation.fit_score == 72


@pytest.mark.parametrize(
    "content",
    [
        "## Technical Fit Score: 140/100\n",
        "## Technical Fit Score: 72/100\n## Technical Fit Score: 73/100\n",
        "Technical Fit Score: 72/100\n",
        "## Technical Fit Score: ٧٢/100\n",
    ],
)
def test_ambiguous_noncanonical_or_out_of_range_scores_fail(content: str) -> None:
    with pytest.raises(ValueError):
        parse_evaluation(content)
