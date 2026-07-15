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


def build_report(benchmark_root: Path) -> dict[str, Any]:
    manifest = read_json_object(benchmark_root / "manifest.json")
    results: list[EvaluationResult] = []
    by_item: dict[str, list[EvaluationResult]] = defaultdict(list)
    for path in sorted((benchmark_root / "items").glob("*/result-*.json")):
        try:
            result = EvaluationResult.model_validate(read_json_object(path))
        except ValueError:
            continue
        results.append(result)
        by_item[result.item_id].append(result)

    dimension_ranges: list[float] = []
    exact_pairs = 0
    total_pairs = 0
    for repetitions in by_item.values():
        for panel_name in ("instruction_design", "execution_and_output"):
            for dimension in DIMENSIONS:
                scores = [
                    getattr(result, panel_name).dimensions[dimension].score
                    for result in repetitions
                ]
                if scores:
                    dimension_ranges.append(max(scores) - min(scores))
                for index, score in enumerate(scores):
                    for other in scores[index + 1 :]:
                        total_pairs += 1
                        exact_pairs += int(score == other)

    checked_claims = [
        claim for result in results for claim in result.claims if claim.status != "not_checked"
    ]
    cited_claims = [claim for claim in checked_claims if claim.message_ids]
    unsupported = [claim for claim in checked_claims if claim.status == "unsupported"]
    high_unsupported = [claim for claim in unsupported if claim.severity == "high"]

    def unsupported_rate(item_prefix: str) -> float | None:
        claims = [
            claim
            for item_id, item_results in by_item.items()
            if item_id.startswith(item_prefix)
            for result in item_results
            for claim in result.claims
            if claim.status != "not_checked"
        ]
        if not claims:
            return None
        return sum(claim.status == "unsupported" for claim in claims) / len(claims)

    baseline_unsupported = unsupported_rate("baseline-")
    bill_unsupported = unsupported_rate("bill-")
    pairwise = list(manifest.get("pairwise_records", []))
    decisive = [record for record in pairwise if record.get("pipeline_preferred") is not None]

    labels: list[HumanLabel] = []
    label_root = data_root() / "labels" / str(manifest["benchmark_id"])
    for path in sorted(label_root.glob("*.json")):
        labels.append(HumanLabel.model_validate(read_json_object(path)))
    model_by_item = {item: values for item, values in by_item.items() if values}
    human_values: list[float] = []
    model_values: list[float] = []
    for label in labels:
        if label.instruction_scores is None or label.execution_scores is None:
            continue
        model_repetitions = model_by_item.get(label.blind_item_id)
        if not model_repetitions:
            continue
        for panel_name, human_scores in (
            ("instruction_design", label.instruction_scores),
            ("execution_and_output", label.execution_scores),
        ):
            for dimension in DIMENSIONS:
                human_values.append(float(human_scores[dimension]))
                model_values.append(
                    fmean(
                        getattr(result, panel_name).dimensions[dimension].score
                        for result in model_repetitions
                    )
                )

    model_means: dict[str, float] = {}
    case_id = manifest["case_id"]
    for other_manifest_path in (data_root() / "benchmarks").glob("*/manifest.json"):
        other = read_json_object(other_manifest_path)
        if other.get("case_id") != case_id:
            continue
        values: list[float] = []
        for result_path in other_manifest_path.parent.glob("items/*/result-*.json"):
            try:
                values.append(
                    EvaluationResult.model_validate(read_json_object(result_path)).global_index_100
                )
            except ValueError:
                continue
        if values:
            model_means[f"{other.get('judge_provider')}:{other.get('judge_model')}"] = fmean(values)

    pairwise_labels = [label for label in labels if label.pairwise_preference is not None]
    accepted_revisions = [label for label in pairwise_labels if label.pairwise_preference == "b"]
    report: dict[str, Any] = {
        "schema_version": 1,
        "benchmark_id": manifest["benchmark_id"],
        "observed_items": len(by_item),
        "valid_evaluations": len(results),
        "failed_evaluations": sum(
            record.get("status") != "complete" for record in manifest["records"]
        ),
        "judge_consistency": {
            "exact_dimension_agreement": exact_pairs / total_pairs if total_pairs else None,
            "mean_dimension_range_0_4": fmean(dimension_ranges) if dimension_ranges else None,
            "global_score_stddev": pstdev([result.global_index_100 for result in results])
            if len(results) > 1
            else 0.0,
        },
        "evidence": {
            "checked_claims": len(checked_claims),
            "citation_presence_rate": len(cited_claims) / len(checked_claims)
            if checked_claims
            else None,
            "unsupported_claim_rate": len(unsupported) / len(checked_claims)
            if checked_claims
            else None,
            "high_severity_unsupported_claims": len(high_unsupported),
        },
        "hallucination_reduction_proxy": {
            "baseline_unsupported_rate": baseline_unsupported,
            "bill_unsupported_rate": bill_unsupported,
            "absolute_reduction": baseline_unsupported - bill_unsupported
            if baseline_unsupported is not None and bill_unsupported is not None
            else None,
            "note": "This is a judge claim-grounding proxy, not observed hallucination truth.",
        },
        "simple_pipeline_comparison": {
            "comparisons": len(pairwise),
            "decisive_pipeline_preference_rate": sum(
                bool(record["pipeline_preferred"]) for record in decisive
            )
            / len(decisive)
            if decisive
            else None,
        },
        "human_model_agreement": {
            "labels": len(labels),
            "score_mae_0_4": fmean(
                abs(a - b) for a, b in zip(human_values, model_values, strict=True)
            )
            if human_values
            else None,
            "score_correlation": _correlation(human_values, model_values),
        },
        "revision_acceptance": {
            "status": "available" if pairwise_labels else "needs_pairwise_human_labels",
            "labeled_pairs": len(pairwise_labels),
            "acceptance_rate": len(accepted_revisions) / len(pairwise_labels)
            if pairwise_labels
            else None,
        },
        "real_cv_improvement": {
            "status": "judge_proxy_only" if pairwise else "unavailable",
            "note": "Real improvement requires blinded human labels or downstream hiring outcomes.",
        },
        "model_sensitivity": {
            "model_count": len(model_means),
            "global_mean_by_judge": model_means,
            "range_0_100": max(model_means.values()) - min(model_means.values())
            if len(model_means) > 1
            else None,
        },
        "self_judge_conflict": manifest["self_judge_conflict"],
        "observational_only": True,
    }
    atomic_write_json(benchmark_root / "report.json", report)
    lines = [
        "# The Celestial report",
        "",
        f"- Benchmark: `{manifest['benchmark_id']}`",
        f"- Valid evaluations: {len(results)}",
        f"- Observed items: {len(by_item)}",
        f"- Human labels: {len(labels)}",
        f"- Self-judge conflict: {manifest['self_judge_conflict']}",
        "- This report is observational and cannot block or alter the pipeline.",
        "",
        "See `report.json` for machine-readable metrics and unavailable-data markers.",
    ]
    atomic_write_text(benchmark_root / "report.md", "\n".join(lines) + "\n")
    return report
