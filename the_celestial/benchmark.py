from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .capture import data_root, verify_frozen_case
from .io import atomic_write_json, atomic_write_text, digest_json, digest_text, read_json_object
from .models import (
    AgentRole,
    BenchmarkSpec,
    ContentMessage,
    ConversationEnvelope,
    Coverage,
    EnvelopeStatus,
    EvaluationResult,
    PairwiseResult,
)
from .profiles import load_profile, load_rubric
from .prompting import (
    BASELINE_INSTRUCTION,
    compile_baseline_prompt,
    compile_evaluation_prompt,
    compile_pairwise_prompt,
    compile_repair_prompt,
    compile_verified_prompt,
    evaluation_schema,
)
from .provider import ProviderError, run_prompt, validate_exact_model
from .verification import available_source_ids, collect_frozen_excerpts


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _verify_ledger(root: Path) -> None:
    path = root / "ledger.jsonl"
    if not path.exists():
        return
    previous_line: str | None = None
    for sequence, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("Invalid Celestial ledger event")
        event_digest = value.pop("event_sha256", None)
        if value.get("sequence") != sequence:
            raise ValueError("Celestial ledger sequence mismatch")
        expected_previous = digest_text(previous_line) if previous_line is not None else None
        if value.get("previous_event_sha256") != expected_previous:
            raise ValueError("Celestial ledger chain mismatch")
        if event_digest != digest_json(value):
            raise ValueError("Celestial ledger event digest mismatch")
        previous_line = line


def _append_ledger(root: Path, event: dict[str, Any]) -> None:
    path = root / "ledger.jsonl"
    _verify_ledger(root)
    previous = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [line for line in previous.splitlines() if line.strip()]
    previous_digest = digest_text(lines[-1]) if lines else None
    body = {
        "sequence": len(lines) + 1,
        "timestamp": utc_now(),
        "previous_event_sha256": previous_digest,
        **event,
    }
    body["event_sha256"] = digest_json(body)
    atomic_write_text(path, previous + json.dumps(body, sort_keys=True) + "\n")


def _next_attempt(directory: Path, repetition: int, kind: str) -> int:
    prefix = f"{repetition:02d}-attempt-"
    attempts = []
    for path in directory.glob(f"{prefix}*-{kind}.txt"):
        try:
            attempts.append(int(path.name.removeprefix(prefix).split("-", 1)[0]))
        except ValueError:
            continue
    return max(attempts, default=0) + 1


def _validate_result_citations(result: EvaluationResult, message_ids: set[str]) -> None:
    cited = [
        message_id
        for panel in (result.instruction_design, result.execution_and_output)
        for dimension in panel.dimensions.values()
        for message_id in dimension.message_ids
    ] + [message_id for claim in result.claims for message_id in claim.message_ids]
    invalid = sorted(set(cited) - message_ids)
    if invalid:
        raise ValueError(f"Result cites unknown message IDs: {invalid}")


def _parse_result(
    raw: str,
    expected: dict[str, object],
    message_ids: set[str],
) -> EvaluationResult:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("The Celestial response must be a JSON object")
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"The Celestial response has invalid {key}")
    result = EvaluationResult.model_validate(value)
    _validate_result_citations(result, message_ids)
    return result


def _evaluate_once(
    *,
    spec: BenchmarkSpec,
    envelope_path: Path,
    case_root: Path,
    item_id: str,
    repetition: int,
    item_root: Path,
) -> tuple[EvaluationResult | None, dict[str, Any]]:
    source_ids = available_source_ids(case_root)
    prompt, expected, message_ids = compile_evaluation_prompt(
        envelope_path,
        item_id=item_id,
        repetition=repetition,
        verification_source_ids=source_ids,
    )
    raw_dir = item_root / "raw"
    attempt = _next_attempt(raw_dir, repetition, "initial")
    raw_prefix = raw_dir / f"{repetition:02d}-attempt-{attempt:02d}"
    calls = 0
    repair_used = False
    try:
        raw = run_prompt(
            spec.judge_provider,
            spec.judge_model,
            prompt,
            schema=evaluation_schema(),
        )
        calls += 1
    except ProviderError as exc:
        return None, {"status": "provider_error", "calls": 1, "error": str(exc)}
    atomic_write_text(raw_prefix.with_name(raw_prefix.name + "-initial.txt"), raw, exclusive=True)
    try:
        result = _parse_result(raw, expected, message_ids)
    except (json.JSONDecodeError, ValueError, ValidationError) as exc:
        repair_used = True
        try:
            raw = run_prompt(
                spec.judge_provider,
                spec.judge_model,
                compile_repair_prompt(prompt, raw, str(exc)),
                schema=evaluation_schema(),
            )
            calls += 1
            atomic_write_text(
                raw_prefix.with_name(raw_prefix.name + "-repair.txt"), raw, exclusive=True
            )
            result = _parse_result(raw, expected, message_ids)
        except (ProviderError, json.JSONDecodeError, ValueError, ValidationError) as repair_exc:
            return None, {
                "status": "invalid",
                "calls": calls,
                "repair_used": True,
                "error": str(repair_exc),
            }
    if result.verification_requests:
        evidence = collect_frozen_excerpts(case_root, result.verification_requests)
        verified_prompt = compile_verified_prompt(prompt, result.model_dump(mode="json"), evidence)
        try:
            raw = run_prompt(
                spec.judge_provider,
                spec.judge_model,
                verified_prompt,
                schema=evaluation_schema(),
            )
            calls += 1
            atomic_write_text(
                raw_prefix.with_name(raw_prefix.name + "-verified.txt"), raw, exclusive=True
            )
            result = _parse_result(raw, expected, message_ids)
            if result.verification_requests:
                raise ValueError("Final verified result must not request more verification")
        except (ProviderError, json.JSONDecodeError, ValueError, ValidationError) as exc:
            if repair_used:
                return None, {
                    "status": "invalid_verified_result",
                    "calls": calls,
                    "repair_used": True,
                    "error": str(exc),
                }
            try:
                raw = run_prompt(
                    spec.judge_provider,
                    spec.judge_model,
                    compile_repair_prompt(verified_prompt, raw, str(exc)),
                    schema=evaluation_schema(),
                )
                calls += 1
                repair_used = True
                atomic_write_text(
                    raw_prefix.with_name(raw_prefix.name + "-verified-repair.txt"),
                    raw,
                    exclusive=True,
                )
                result = _parse_result(raw, expected, message_ids)
                if result.verification_requests:
                    raise ValueError("Repaired result must not request verification")
            except (ProviderError, json.JSONDecodeError, ValueError, ValidationError) as repair_exc:
                return None, {
                    "status": "invalid_verified_result",
                    "calls": calls,
                    "repair_used": True,
                    "error": str(repair_exc),
                }
    return result, {"status": "complete", "calls": calls, "repair_used": repair_used}


def _case_for_request(capture_id: str) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    request = read_json_object(data_root() / "captures" / capture_id / "request.json")
    if request.get("schema_version") not in {2, 3}:
        raise ValueError("Celestial v1 captures are audit-only")
    if request.get("status") not in {"ready", "captured_disabled"}:
        raise ValueError("Capture is not ready for benchmarking")
    if request.get("last_capture_error"):
        raise ValueError("Capture contains errors and cannot be benchmarked")
    case_id = str(request.get("case_id", ""))
    verification = verify_frozen_case(case_id)
    case_root = data_root() / "cases" / case_id
    manifest = read_json_object(case_root / "manifest.json")
    if verification["digest"] != manifest["content_digest"]:
        raise ValueError("Case verification mismatch")
    return case_root, request, manifest


def plan_capture(capture_id: str) -> dict[str, Any]:
    case_root, request, manifest = _case_for_request(capture_id)
    if not request.get("celestial_requested"):
        raise ValueError("The Celestial was not enabled for this capture")
    subject_provider = str(request["subject_provider"])
    subject_model_value = request.get("subject_model")
    subject_model = str(subject_model_value) if subject_model_value is not None else None
    baseline_provider = str(request.get("baseline_provider") or subject_provider)
    baseline_model_value = request.get("baseline_model") or subject_model
    baseline_model = str(baseline_model_value) if baseline_model_value is not None else ""
    judge_provider = str(request["judge_provider"])
    judge_model = str(request["judge_model"])
    validate_exact_model(baseline_provider, baseline_model)
    validate_exact_model(judge_provider, judge_model)
    envelopes = sorted((case_root / "envelopes").glob("*/*.json"))
    observed = [path for path in envelopes if read_json_object(path).get("status") == "observed"]
    roles = {str(read_json_object(path)["role"]) for path in observed} | {"baseline"}
    profile_sha256 = {role: load_profile(role)[1] for role in sorted(roles)}
    _, rubric_sha256 = load_rubric()
    plan_body = {
        "schema_version": 3,
        "capture_id": capture_id,
        "case_id": case_root.name,
        "case_digest": manifest["content_digest"],
        "subject_provider": subject_provider,
        "subject_model": subject_model,
        "baseline_provider": baseline_provider,
        "baseline_model": baseline_model,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "rubric_sha256": rubric_sha256,
        "profile_sha256": profile_sha256,
        "repetitions": 3,
    }
    plan_digest = digest_json(plan_body)
    benchmark_id = f"{capture_id}-{plan_digest[:12]}"
    spec = BenchmarkSpec(
        benchmark_id=benchmark_id,
        **plan_body,
        plan_digest=plan_digest,
        created_at=utc_now(),
    )
    output_root = data_root() / "benchmarks" / benchmark_id
    spec_path = output_root / "spec.json"
    if spec_path.exists():
        existing_spec = BenchmarkSpec.model_validate_json(spec_path.read_text())
        if existing_spec.model_dump(exclude={"created_at"}) != spec.model_dump(
            exclude={"created_at"}
        ):
            raise ValueError("Benchmark spec conflicts with existing plan")
        spec = existing_spec
    else:
        atomic_write_json(spec_path, spec.model_dump(mode="json"), exclusive=True)
        _append_ledger(output_root, {"event": "planned", "plan_digest": plan_digest})
    items = len(observed) + 1
    return {
        "benchmark_id": benchmark_id,
        "capture_id": capture_id,
        "case_id": case_root.name,
        "plan_digest": plan_digest,
        "observed_items": len(observed),
        "repetitions": 3,
        "baseline_calls": 1,
        "pairwise_calls": 3,
        "expected_provider_calls": items * 3 + 4,
        "maximum_provider_calls": items * 9 + 8,
    }


def _load_spec(capture_id: str, plan_digest: str) -> tuple[BenchmarkSpec, Path, Path]:
    existing_root = data_root() / "benchmarks" / f"{capture_id}-{plan_digest[:12]}"
    existing_spec_path = existing_root / "spec.json"
    if existing_spec_path.is_file():
        existing_spec = BenchmarkSpec.model_validate_json(existing_spec_path.read_text())
        if existing_spec.capture_id != capture_id or existing_spec.plan_digest != plan_digest:
            raise ValueError("Existing benchmark spec conflicts with the accepted plan")
        existing_case_root = data_root() / "cases" / existing_spec.case_id
        verify_frozen_case(existing_spec.case_id)
        return existing_spec, existing_root, existing_case_root
    plan = plan_capture(capture_id)
    if plan["plan_digest"] != plan_digest:
        raise ValueError("Quota confirmation digest does not match the current benchmark plan")
    root = data_root() / "benchmarks" / str(plan["benchmark_id"])
    spec = BenchmarkSpec.model_validate_json((root / "spec.json").read_text())
    case_root = data_root() / "cases" / spec.case_id
    verify_frozen_case(spec.case_id)
    return spec, root, case_root


def _baseline_envelope(spec: BenchmarkSpec, case_root: Path, baseline: str) -> dict[str, Any]:
    initial_cv = (case_root / "inputs" / "initial_cv.md").read_text(encoding="utf-8")
    job = (case_root / "inputs" / "job_description.md").read_text(encoding="utf-8")
    messages = [
        ContentMessage(
            message_id="instruction",
            kind="instruction",
            source_label="baseline_instruction",
            content=BASELINE_INSTRUCTION,
            sha256=digest_text(BASELINE_INSTRUCTION),
        ),
        ContentMessage(
            message_id="input-1",
            kind="input",
            source_label="initial_cv",
            content=initial_cv,
            sha256=digest_text(initial_cv),
        ),
        ContentMessage(
            message_id="input-2",
            kind="input",
            source_label="job_description",
            content=job,
            sha256=digest_text(job),
        ),
        ContentMessage(
            message_id="output-1",
            kind="output",
            source_label="baseline_cv",
            content=baseline,
            sha256=digest_text(baseline),
        ),
    ]
    envelope = ConversationEnvelope(
        capture_id=spec.capture_id,
        run_id=read_json_object(case_root / "manifest.json")["run_id"],
        case_key=digest_json({"initial_cv": initial_cv, "job": job})[:20],
        role=AgentRole.BASELINE,
        invocation=1,
        coverage=Coverage.PROMPT_OUTPUT_ONLY,
        status=EnvelopeStatus.OBSERVED,
        input_fingerprint=digest_json({"initial_cv": initial_cv, "job": job}),
        messages=messages,
        created_at=utc_now(),
    )
    return envelope.model_dump(mode="json")


def generate_baseline(capture_id: str, plan_digest: str) -> Path:
    spec, root, case_root = _load_spec(capture_id, plan_digest)
    output = root / "baseline" / "cv.md"
    metadata_path = root / "baseline" / "metadata.json"
    envelope_path = root / "items" / "baseline-001" / "envelope.json"
    if output.exists() and metadata_path.exists() and envelope_path.exists():
        metadata = read_json_object(metadata_path)
        if metadata.get("sha256") != digest_text(output.read_text(encoding="utf-8")):
            raise ValueError("Existing baseline failed integrity validation")
        return output
    prompt = compile_baseline_prompt(case_root)
    assert spec.baseline_provider is not None
    assert spec.baseline_model is not None
    raw = run_prompt(spec.baseline_provider, spec.baseline_model, prompt)
    calls = 1
    if len(raw.strip()) < 100 or not raw.lstrip().startswith("#"):
        raw = run_prompt(
            spec.baseline_provider,
            spec.baseline_model,
            prompt + "\nReturn only a complete Markdown CV; the previous output was invalid.",
        )
        calls += 1
    if len(raw.strip()) < 100 or not raw.lstrip().startswith("#"):
        raise ValueError("Baseline provider did not produce a usable Markdown CV")
    atomic_write_text(output, raw, exclusive=True)
    atomic_write_json(
        metadata_path,
        {"schema_version": 2, "sha256": digest_text(raw), "calls": calls},
        exclusive=True,
    )
    atomic_write_json(envelope_path, _baseline_envelope(spec, case_root, raw), exclusive=True)
    _append_ledger(root, {"event": "baseline_completed", "calls": calls})
    return output


def _pairwise_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "preference": {"enum": ["a", "b", "tie"]},
            "rationale": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["preference", "rationale", "confidence"],
        "additionalProperties": False,
    }


def _pairwise_compare(spec: BenchmarkSpec, root: Path, case_root: Path) -> list[PairwiseResult]:
    baseline = (root / "baseline" / "cv.md").read_text(encoding="utf-8")
    final_cv = (case_root / "inputs" / "final_cv.md").read_text(encoding="utf-8")
    records: list[PairwiseResult] = []
    start_pipeline_a = int(spec.plan_digest[0], 16) % 2 == 0
    for repetition in range(1, 4):
        result_path = root / "pairwise" / f"result-{repetition:02d}.json"
        if result_path.exists():
            records.append(PairwiseResult.model_validate_json(result_path.read_text()))
            continue
        pipeline_a = start_pipeline_a if repetition % 2 else not start_pipeline_a
        candidate_a, candidate_b = (final_cv, baseline) if pipeline_a else (baseline, final_cv)
        prompt = compile_pairwise_prompt(case_root, candidate_a, candidate_b)
        raw_dir = root / "pairwise" / "raw"
        attempt = _next_attempt(raw_dir, repetition, "initial")
        raw_prefix = raw_dir / f"{repetition:02d}-attempt-{attempt:02d}"
        raw = run_prompt(
            spec.judge_provider,
            spec.judge_model,
            prompt,
            schema=_pairwise_response_schema(),
        )
        atomic_write_text(
            raw_prefix.with_name(raw_prefix.name + "-initial.txt"), raw, exclusive=True
        )
        calls = 1
        try:
            value = json.loads(raw)
            preference = value["preference"]
            rationale = value["rationale"]
            confidence = value["confidence"]
            if (
                preference not in {"a", "b", "tie"}
                or not isinstance(rationale, str)
                or not rationale.strip()
                or not isinstance(confidence, (int, float))
                or not 0 <= confidence <= 1
            ):
                raise ValueError("Invalid pairwise response")
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            repaired = run_prompt(
                spec.judge_provider,
                spec.judge_model,
                prompt + "\nRepair this invalid JSON response once:\n" + raw[:8000],
                schema=_pairwise_response_schema(),
            )
            calls += 1
            atomic_write_text(
                raw_prefix.with_name(raw_prefix.name + "-repair.txt"),
                repaired,
                exclusive=True,
            )
            try:
                value = json.loads(repaired)
                preference = value["preference"]
                rationale = value["rationale"]
                confidence = value["confidence"]
                if (
                    preference not in {"a", "b", "tie"}
                    or not isinstance(rationale, str)
                    or not rationale.strip()
                    or not isinstance(confidence, (int, float))
                    or not 0 <= confidence <= 1
                ):
                    raise ValueError("Invalid repaired pairwise response")
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as repair_exc:
                raise ValueError("Pairwise response failed its one repair") from repair_exc
        record = PairwiseResult(
            repetition=repetition,
            blind_order="pipeline_a" if pipeline_a else "baseline_a",
            preference=preference,
            pipeline_preferred=(preference == ("a" if pipeline_a else "b"))
            if preference != "tie"
            else None,
            rationale=rationale,
            confidence=float(confidence),
        )
        atomic_write_json(result_path, record.model_dump(mode="json"), exclusive=True)
        _append_ledger(
            root, {"event": "pairwise_completed", "repetition": repetition, "calls": calls}
        )
        records.append(record)
    return records


def run_benchmark(capture_id: str, *, plan_digest: str) -> Path:
    spec, root, case_root = _load_spec(capture_id, plan_digest)
    completed_manifest = root / "manifest.json"
    if completed_manifest.exists():
        _verify_ledger(root)
        manifest = read_json_object(completed_manifest)
        if (
            manifest.get("schema_version") not in {2, 3}
            or manifest.get("plan_digest") != plan_digest
        ):
            raise ValueError("Existing benchmark manifest conflicts with the accepted plan")
        completed_records = [
            record for record in manifest.get("records", []) if record.get("status") == "complete"
        ]
        if len(completed_records) != len(manifest.get("records", [])):
            raise ValueError("Completed benchmark contains failed evaluation records")
        for record in completed_records:
            path = (
                root
                / "items"
                / str(record["item_id"])
                / f"result-{int(record['repetition']):02d}.json"
            )
            result = EvaluationResult.model_validate_json(path.read_text(encoding="utf-8"))
            if result.item_id != record["item_id"] or result.repetition != record["repetition"]:
                raise ValueError("Completed benchmark result identity mismatch")
        pairwise_paths = sorted((root / "pairwise").glob("result-*.json"))
        if len(pairwise_paths) != 3:
            raise ValueError("Completed benchmark is missing pairwise repetitions")
        for path in pairwise_paths:
            PairwiseResult.model_validate_json(path.read_text(encoding="utf-8"))
        return root
    if not (root / "baseline" / "cv.md").is_file():
        raise ValueError("Generate the baseline before judging")
    envelopes = sorted((case_root / "envelopes").glob("*/*.json")) + [
        root / "items" / "baseline-001" / "envelope.json"
    ]
    records: list[dict[str, Any]] = []
    has_failures = False
    for envelope_path in envelopes:
        value = read_json_object(envelope_path)
        if value.get("status") != "observed":
            continue
        item_id = f"{value['role']}-{int(value['invocation']):03d}"
        item_root = root / "items" / item_id
        for repetition in range(1, 4):
            result_path = item_root / f"result-{repetition:02d}.json"
            if result_path.exists():
                resumed_result = EvaluationResult.model_validate_json(result_path.read_text())
                records.append(
                    {
                        "item_id": item_id,
                        "repetition": repetition,
                        "status": "complete",
                        "resumed": True,
                    }
                )
                if resumed_result.item_id != item_id or resumed_result.repetition != repetition:
                    raise ValueError("Existing result identity mismatch")
                continue
            evaluated_result, status = _evaluate_once(
                spec=spec,
                envelope_path=envelope_path,
                case_root=case_root,
                item_id=item_id,
                repetition=repetition,
                item_root=item_root,
            )
            record = {"item_id": item_id, "repetition": repetition, **status}
            records.append(record)
            if evaluated_result is not None:
                atomic_write_json(
                    result_path, evaluated_result.model_dump(mode="json"), exclusive=True
                )
            else:
                has_failures = True
                atomic_write_json(item_root / f"failure-{repetition:02d}.json", record)
            _append_ledger(root, {"event": "evaluation_attempted", **record})
    if has_failures:
        atomic_write_json(
            root / "progress.json",
            {"schema_version": 2, "plan_digest": plan_digest, "records": records},
        )
        raise RuntimeError("Benchmark remains incomplete; rerun the same accepted plan to resume")
    pairwise = _pairwise_compare(spec, root, case_root)
    manifest = {
        "schema_version": 3,
        **spec.model_dump(mode="json"),
        "self_judge_conflict": (
            spec.subject_provider == spec.judge_provider and spec.subject_model == spec.judge_model
        ),
        "baseline_judge_conflict": (
            spec.baseline_provider == spec.judge_provider
            and spec.baseline_model == spec.judge_model
        ),
        "records": records,
        "pairwise_records": [record.model_dump(mode="json") for record in pairwise],
        "completed_at": utc_now(),
    }
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        existing = read_json_object(manifest_path)
        if existing != manifest:
            raise ValueError("Completed benchmark manifest is immutable")
    else:
        atomic_write_json(manifest_path, manifest, exclusive=True)
        _append_ledger(root, {"event": "benchmark_completed"})
    return root
