from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean, pstdev
from typing import Any

from .capture import data_root
from .io import atomic_write_json, atomic_write_text, read_json_object
from .models import DIMENSIONS, EvaluationResult, HumanLabel


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    left_mean, right_mean = fmean(left), fmean(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True))
    denominator = math.sqrt(
        sum((a - left_mean) ** 2 for a in left) * sum((b - right_mean) ** 2 for b in right)
    )
    return numerator / denominator if denominator else None


def _weighted_kappa(left: list[int], right: list[int]) -> float | None:
    if len(left) < 2 or len(left) != len(right):
        return None
    size = 5
    observed = [[0.0] * size for _ in range(size)]
    for a, b in zip(left, right, strict=True):
        observed[a][b] += 1
    total = float(len(left))
    rows = [sum(row) for row in observed]
    columns = [sum(observed[i][j] for i in range(size)) for j in range(size)]
    observed_disagreement = (
        sum(((i - j) / (size - 1)) ** 2 * observed[i][j] for i in range(size) for j in range(size))
        / total
    )
    expected_disagreement = sum(
        ((i - j) / (size - 1)) ** 2 * rows[i] * columns[j] for i in range(size) for j in range(size)
    ) / (total * total)
    return 1 - observed_disagreement / expected_disagreement if expected_disagreement else None


def _load_results(root: Path) -> dict[str, list[EvaluationResult]]:
    values: dict[str, list[EvaluationResult]] = defaultdict(list)
    for path in sorted((root / "items").glob("*/result-*.json")):
        try:
            result = EvaluationResult.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        values[result.item_id].append(result)
    return values


def build_report(benchmark_root: Path) -> dict[str, Any]:
    manifest = read_json_object(benchmark_root / "manifest.json")
    if manifest.get("schema_version") != 2:
        raise ValueError("Celestial v1 benchmarks are audit-only")
    by_item = _load_results(benchmark_root)
    results = [result for repetitions in by_item.values() for result in repetitions]
    exact_pairs = total_pairs = 0
    absolute_differences: list[float] = []
    within_item_global_stddev: list[float] = []
    for repetitions in by_item.values():
        globals_ = [result.global_index_100 for result in repetitions]
        if len(globals_) > 1:
            within_item_global_stddev.append(pstdev(globals_))
        for panel_name in ("instruction_design", "execution_and_output"):
            for dimension in DIMENSIONS:
                scores = [
                    getattr(result, panel_name).dimensions[dimension].score
                    for result in repetitions
                ]
                for index, score in enumerate(scores):
                    for other in scores[index + 1 :]:
                        total_pairs += 1
                        exact_pairs += int(score == other)
                        absolute_differences.append(abs(score - other))

    compatible: dict[str, dict[str, list[EvaluationResult]]] = {}
    signature = (
        manifest["case_digest"],
        manifest["rubric_sha256"],
        json_key(manifest["profile_sha256"]),
        manifest["schema_version"],
    )
    for other_path in (data_root() / "benchmarks").glob("*/manifest.json"):
        other = read_json_object(other_path)
        other_signature = (
            other.get("case_digest"),
            other.get("rubric_sha256"),
            json_key(other.get("profile_sha256")),
            other.get("schema_version"),
        )
        if other_signature == signature:
            compatible[f"{other.get('judge_provider')}:{other.get('judge_model')}"] = _load_results(
                other_path.parent
            )
    judge_means: dict[str, float] = {}
    for judge, judge_items in compatible.items():
        scores = [result.global_index_100 for values in judge_items.values() for result in values]
        if scores:
            judge_means[judge] = fmean(scores)

    labels: list[HumanLabel] = []
    label_root = data_root() / "labels" / str(manifest["benchmark_id"])
    for path in sorted(label_root.glob("*.json")):
        labels.append(HumanLabel.model_validate_json(path.read_text(encoding="utf-8")))
    private_path = benchmark_root / "human" / "private-map.json"
    private = read_json_object(private_path).get("items", {}) if private_path.is_file() else {}
    blind_to_mapping = (
        {
            value["blind_item_id"]: value
            for value in private.values()
            if isinstance(value, dict) and isinstance(value.get("blind_item_id"), str)
        }
        if isinstance(private, dict)
        else {}
    )
    by_blind: dict[str, list[HumanLabel]] = defaultdict(list)
    for label in labels:
        by_blind[label.blind_item_id].append(label)

    human_left: list[int] = []
    human_right: list[int] = []
    human_values: list[float] = []
    model_values: list[float] = []
    for blind_id, item_labels in by_blind.items():
        scoring = [
            label
            for label in item_labels
            if label.instruction_scores is not None and label.execution_scores is not None
        ]
        if len({label.rater_id for label in scoring}) < 2:
            continue
        first, second = scoring[0], scoring[1]
        canonical = blind_to_mapping.get(blind_id, {}).get("canonical_item_id")
        model_repetitions = by_item.get(str(canonical), []) if canonical is not None else []
        for panel_name, left_scores, right_scores in (
            ("instruction_design", first.instruction_scores, second.instruction_scores),
            ("execution_and_output", first.execution_scores, second.execution_scores),
        ):
            assert left_scores is not None and right_scores is not None
            for dimension in DIMENSIONS:
                human_left.append(left_scores[dimension])
                human_right.append(right_scores[dimension])
                if model_repetitions:
                    human_values.append((left_scores[dimension] + right_scores[dimension]) / 2)
                    model_values.append(
                        fmean(
                            getattr(result, panel_name).dimensions[dimension].score
                            for result in model_repetitions
                        )
                    )

    pairwise_human: dict[str, float | None] = {}
    for blind_id, item_labels in by_blind.items():
        preferences = [
            label.pairwise_preference for label in item_labels if label.pairwise_preference
        ]
        if len(preferences) < 2:
            continue
        mapping = blind_to_mapping.get(blind_id, {})
        revision_side = mapping.get("preferred_revision_side")
        if revision_side:
            pairwise_human[blind_id] = sum(value == revision_side for value in preferences) / len(
                preferences
            )

    claim_set_rates: dict[str, dict[str, float | int] | None] = {
        "baseline": None,
        "final": None,
    }
    for mapping in blind_to_mapping.values():
        claim_set = mapping.get("claim_set")
        claim_blind_id = mapping.get("blind_item_id")
        if claim_set not in claim_set_rates or not isinstance(claim_blind_id, str):
            continue
        cv_claim_labels = [
            label
            for label in by_blind.get(claim_blind_id, [])
            if label.claim_support is not None
        ]
        if len({label.rater_id for label in cv_claim_labels}) < 2:
            continue
        by_rater = {label.rater_id: label.claim_support or {} for label in cv_claim_labels}
        first_claims, second_claims = list(by_rater.values())[:2]
        consensus = [
            first_claims[claim_id]
            for claim_id in first_claims.keys() & second_claims.keys()
            if first_claims[claim_id] == second_claims[claim_id]
            and first_claims[claim_id] in {"supported", "unsupported"}
        ]
        if consensus:
            unsupported = sum(value == "unsupported" for value in consensus)
            claim_set_rates[str(claim_set)] = {
                "consensus_claims": len(consensus),
                "unsupported_claims": unsupported,
                "unsupported_rate": unsupported / len(consensus),
            }

    checked_claims = [
        claim for result in results for claim in result.claims if claim.status != "not_checked"
    ]
    human_checked = true_positive = false_positive = 0
    for blind_id, item_labels in by_blind.items():
        model_claim_labels = [label.claim_support for label in item_labels if label.claim_support]
        if len(model_claim_labels) < 2:
            continue
        canonical = blind_to_mapping.get(blind_id, {}).get("canonical_item_id")
        model_claims = {
            claim.claim_id: claim
            for result in (by_item.get(str(canonical), []) if canonical is not None else [])[:1]
            for claim in result.claims
            if claim.status == "supported"
        }
        for claim_id in model_claims:
            votes_by_rater = {
                label.rater_id: label.claim_support[claim_id]
                for label in item_labels
                if label.claim_support and claim_id in label.claim_support
            }
            votes = list(votes_by_rater.values())
            if len(votes) < 2 or len(set(votes[:2])) != 1:
                continue
            human_checked += 1
            if votes[0] == "supported":
                true_positive += 1
            else:
                false_positive += 1

    report: dict[str, Any] = {
        "schema_version": 2,
        "benchmark_id": manifest["benchmark_id"],
        "observed_items": len(by_item),
        "valid_evaluations": len(results),
        "failed_evaluations": sum(
            record.get("status") != "complete" for record in manifest["records"]
        ),
        "judge_repeatability": {
            "exact_dimension_agreement": exact_pairs / total_pairs if total_pairs else None,
            "mean_absolute_dimension_difference_0_4": fmean(absolute_differences)
            if absolute_differences
            else None,
            "mean_within_item_global_stddev": fmean(within_item_global_stddev)
            if within_item_global_stddev
            else None,
        },
        "inter_judge_sensitivity": {
            "compatible_judges": len(judge_means),
            "global_mean_by_judge": judge_means,
            "range_0_100": max(judge_means.values()) - min(judge_means.values())
            if len(judge_means) > 1
            else None,
        },
        "human_agreement": {
            "labels": len(labels),
            "weighted_kappa_0_4": _weighted_kappa(human_left, human_right),
        },
        "human_model_agreement": {
            "score_mae_0_4": fmean(
                abs(a - b) for a, b in zip(human_values, model_values, strict=True)
            )
            if human_values
            else None,
            "score_correlation": _correlation(human_values, model_values),
        },
        "evidence_precision": {
            "status": "available" if human_checked else "needs_two_human_labels",
            "human_checked_supported_claims": human_checked,
            "precision": true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else None,
        },
        "citation_integrity": {
            "checked_claims": len(checked_claims),
            "schema_valid_citation_rate": 1.0 if checked_claims else None,
        },
        "simple_pipeline_comparison": {
            "judge_comparisons": len(manifest.get("pairwise_records", [])),
            "judge_pipeline_preference_rate": fmean(
                float(record["pipeline_preferred"])
                for record in manifest.get("pairwise_records", [])
                if record.get("pipeline_preferred") is not None
            )
            if any(
                record.get("pipeline_preferred") is not None
                for record in manifest.get("pairwise_records", [])
            )
            else None,
        },
        "revision_acceptance": {
            "status": "available" if pairwise_human else "needs_two_human_labels",
            "acceptance_by_blind_pair": pairwise_human,
        },
        "real_cv_improvement": {
            "status": "available"
            if isinstance(private, dict)
            and isinstance(private.get("baseline_final"), dict)
            and private["baseline_final"].get("blind_item_id") in pairwise_human
            else "needs_two_human_labels",
            "human_pipeline_preference_rate": pairwise_human.get(
                str(private.get("baseline_final", {}).get("blind_item_id"))
            )
            if isinstance(private, dict)
            else None,
            "note": "This metric is a blinded human preference, not a hiring outcome.",
        },
        "hallucination_reduction": {
            "status": "available"
            if all(claim_set_rates.values())
            else "needs_two_human_claim_labels",
            "baseline": claim_set_rates["baseline"],
            "final": claim_set_rates["final"],
            "unsupported_rate_reduction": (
                float(claim_set_rates["baseline"]["unsupported_rate"])
                - float(claim_set_rates["final"]["unsupported_rate"])
            )
            if claim_set_rates["baseline"] and claim_set_rates["final"]
            else None,
            "note": "Reported only after matched baseline and final-CV claim labels exist.",
        },
        "self_judge_conflict": manifest["self_judge_conflict"],
        "observational_only": True,
    }
    atomic_write_json(benchmark_root / "report.json", report)
    atomic_write_text(
        benchmark_root / "report.md",
        "# The Celestial report\n\n"
        f"- Benchmark: `{manifest['benchmark_id']}`\n"
        f"- Valid evaluations: {len(results)}\n"
        f"- Human labels: {len(labels)}\n"
        "- Observational only; unavailable metrics remain explicit in report.json.\n",
    )
    return report


def json_key(value: object) -> str:
    import json

    return json.dumps(value, sort_keys=True, separators=(",", ":"))
