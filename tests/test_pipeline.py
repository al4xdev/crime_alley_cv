from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

import harvey_guy.pipeline as pipeline
from harvey_guy.pipeline import (
    Outcome,
    Phase,
    PipelineError,
    RunStore,
    commit_bill,
    complete_donna,
    initialize_run,
    mark_shadow_ready,
    prepare_bill,
    prepare_donna,
    record_evaluation,
    start_session,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _configure_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "data"
    docs_dir = data_dir / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "cv.md").write_text(
        "# Candidate\n\nExperienced Python platform engineer.\n",
        encoding="utf-8",
    )
    (docs_dir / "job.md").write_text(
        "# Platform Engineer — Acme\n\nBuild reliable systems.\n",
        encoding="utf-8",
    )
    (docs_dir / "who_are_u.md").write_text(
        "# Background\n\nVerified platform experience.\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PIPELINE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("PIPELINE_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("PIPELINE_SESSION_ROOT", str(tmp_path / "sessions"))
    return data_dir


def _complete_shadow(session: Path) -> None:
    (session / "company_info.md").write_text(
        "# Company\n\n" + "Verified public company context. " * 5,
        encoding="utf-8",
    )
    (session / "repos.json").write_text("[]\n", encoding="utf-8")
    (session / "repos_expected_count.txt").write_text("0\n", encoding="utf-8")


def _write_evaluation(session: Path, score: int) -> None:
    (session / "anti_karen" / "artifacts" / "karen_output.md").write_text(
        "# Technical Evaluation Report — Karen Guard\n\n"
        f"## Technical Fit Score: {score}/100\n\n"
        "## Evidence\n\nThe report contains deterministic replay evidence.\n",
        encoding="utf-8",
    )


def _reach_bill(store: RunStore) -> Path:
    session = start_session(store).session_path
    _complete_shadow(session)
    mark_shadow_ready(store)
    _write_evaluation(session, 70)
    record_evaluation(store)
    return session


def _reach_donna(store: RunStore) -> Path:
    session = start_session(store).session_path
    _complete_shadow(session)
    mark_shadow_ready(store)
    _write_evaluation(session, 85)
    record_evaluation(store)
    return session


def _leave_pending_evaluation(
    store: RunStore,
    state_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    original_copy = pipeline.atomic_copy
    failed = False

    def fail_before_state(source: Path, destination: Path) -> None:
        nonlocal failed
        if destination == state_path and not failed:
            failed = True
            raise OSError("injected state write failure")
        original_copy(source, destination)

    monkeypatch.setattr(pipeline, "atomic_copy", fail_before_state)
    with pytest.raises(OSError, match="injected"):
        record_evaluation(store)
    monkeypatch.setattr(pipeline, "atomic_copy", original_copy)
    return json.loads(store.pending_path.read_text(encoding="utf-8"))


def test_three_iteration_replay_reaches_max_without_a_fourth_evaluation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=3,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="offline-replay",
    )
    store = RunStore(state_path)

    for expected_iteration, score in enumerate((72, 62, 68), start=1):
        state = start_session(store)
        session = state.session_path
        _complete_shadow(session)
        assert mark_shadow_ready(store).phase is Phase.KAREN_READY
        _write_evaluation(session, score)
        state = record_evaluation(store)
        assert state.iterations_completed == expected_iteration

        if expected_iteration < 3:
            assert state.phase is Phase.NEEDS_REVISION
            prepare_bill(store)
            cv_path = session / "docs" / "cv.md"
            cv_path.write_text(
                cv_path.read_text(encoding="utf-8")
                + f"\nRevision {expected_iteration}: clarified evidence.\n",
                encoding="utf-8",
            )
            (session / "anti_karen" / "artifacts" / "draft_notes.txt").write_text(
                f"Revision {expected_iteration}", encoding="utf-8"
            )
            assert commit_bill(store).phase is Phase.READY

    state = store.load()
    assert state.phase is Phase.COACHING_READY
    assert state.outcome is Outcome.MAX_ITERATIONS
    assert state.iterations_completed == 3
    assert not (state.run_path / "iterations" / "04").exists()

    assert prepare_donna(store).phase is Phase.DONNA_RUNNING
    (data_dir / "docs" / "action_plan.md").write_text(
        "# Action Plan\n\n" + "Build verified public evidence and close technical gaps. " * 4,
        encoding="utf-8",
    )
    assert complete_donna(store).phase is Phase.COMPLETE
    assert (state.run_path / "action_plan.md").read_text(encoding="utf-8") == (
        data_dir / "docs" / "action_plan.md"
    ).read_text(encoding="utf-8")

    scores = (state.run_path / "scores.csv").read_text(encoding="utf-8").splitlines()
    assert scores == ["iteration,score", "1,72", "2,62", "3,68"]
    events = [
        json.loads(line)
        for line in (state.run_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert events[-1]["event"] == "run_completed"
    assert all(event["session_id"] != "unknown" for event in events[1:])


def test_target_score_finishes_on_first_evaluation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=5,
        min_fit_score=80,
        karen_reads_background=True,
        run_id="early-success",
    )
    store = RunStore(state_path)
    session = start_session(store).session_path
    _complete_shadow(session)
    mark_shadow_ready(store)
    _write_evaluation(session, 85)
    state = record_evaluation(store)
    assert state.outcome is Outcome.SUCCESS
    assert state.iterations_completed == 1
    assert state.phase is Phase.COACHING_READY


def test_bill_cannot_modify_evaluation_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=2,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="bill-integrity",
    )
    store = RunStore(state_path)
    session = start_session(store).session_path
    _complete_shadow(session)
    mark_shadow_ready(store)
    _write_evaluation(session, 70)
    record_evaluation(store)
    prepare_bill(store)
    (session / "docs" / "cv.md").write_text("# Changed CV\n", encoding="utf-8")
    (session / "anti_karen" / "artifacts" / "karen_output.md").write_text(
        "## Technical Fit Score: 100/100\n", encoding="utf-8"
    )
    with pytest.raises(PipelineError, match="protected context|Symlink path component"):
        commit_bill(store)
    assert store.load().phase is Phase.BILL_RUNNING


def test_invalid_transition_does_not_change_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, initial = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="invalid-transition",
    )
    store = RunStore(state_path)
    with pytest.raises(PipelineError, match="Transition not allowed"):
        record_evaluation(store)
    current = store.load()
    assert current.revision == initial.revision
    assert current.phase is Phase.READY


def test_invalid_configuration_does_not_reserve_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    with pytest.raises(PipelineError, match="Invalid run configuration"):
        initialize_run(
            max_iterations=0,
            min_fit_score=80,
            karen_reads_background=False,
            run_id="retryable-init",
        )
    assert not (tmp_path / "runs" / "retryable-init").exists()

    state_path, _ = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="retryable-init",
    )
    assert state_path.is_file()


def test_pending_evaluation_recovers_without_duplicate_score_or_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=2,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="recover-evaluation",
    )
    store = RunStore(state_path)
    session = start_session(store).session_path
    _complete_shadow(session)
    mark_shadow_ready(store)
    _write_evaluation(session, 70)

    original_copy = pipeline.atomic_copy
    failed = False

    def fail_before_state(source: Path, destination: Path) -> None:
        nonlocal failed
        if destination == state_path and not failed:
            failed = True
            raise OSError("injected state write failure")
        original_copy(source, destination)

    monkeypatch.setattr(pipeline, "atomic_copy", fail_before_state)
    with pytest.raises(OSError, match="injected"):
        record_evaluation(store)
    assert json.loads(state_path.read_text(encoding="utf-8"))["phase"] == "karen_ready"
    assert store.pending_path.is_file()

    monkeypatch.setattr(pipeline, "atomic_copy", original_copy)
    recovered = record_evaluation(store)
    assert recovered.phase is Phase.NEEDS_REVISION
    assert recovered.iterations_completed == 1
    assert (recovered.run_path / "scores.csv").read_text(encoding="utf-8").splitlines() == [
        "iteration,score",
        "1,70",
    ]
    events = [
        json.loads(line)
        for line in (recovered.run_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["operation"] for event in events].count("record_evaluation") == 1
    assert not store.pending_path.exists()


@pytest.mark.parametrize(
    "corruption",
    [
        "schema",
        "operation",
        "revision",
        "target",
        "order",
        "payload",
        "missing_payload",
        "event_history",
    ],
)
def test_pending_recovery_rejects_incoherent_manifest_or_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    corruption: str,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=2,
        min_fit_score=80,
        karen_reads_background=False,
        run_id=f"pending-{corruption}",
    )
    store = RunStore(state_path)
    session = start_session(store).session_path
    _complete_shadow(session)
    mark_shadow_ready(store)
    _write_evaluation(session, 70)
    manifest = _leave_pending_evaluation(store, state_path, monkeypatch)
    writes = manifest["writes"]
    assert isinstance(writes, list)

    if corruption == "schema":
        manifest["schema_version"] = 1
    elif corruption == "operation":
        manifest["operation"] = "prepare_bill"
    elif corruption == "revision":
        manifest["revision"] = int(manifest["revision"]) + 1
    elif corruption == "target":
        writes[0]["target"] = str((tmp_path / "unexpected.md").absolute())
    elif corruption == "order":
        writes[0], writes[-1] = writes[-1], writes[0]
    elif corruption == "payload":
        Path(writes[0]["source"]).write_text("corrupt payload", encoding="utf-8")
    elif corruption == "event_history":
        event_write = next(write for write in writes if write["target"].endswith("events.jsonl"))
        event_source = Path(event_write["source"])
        events = [
            json.loads(line) for line in event_source.read_text(encoding="utf-8").splitlines()
        ]
        events[0]["event"] = "rewritten_history"
        event_source.write_text(
            "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
        )
        event_write["size"] = event_source.stat().st_size
        event_write["sha256"] = pipeline._file_sha256(event_source)
    else:
        Path(writes[0]["source"]).rename(Path(writes[0]["source"] + ".missing"))

    store.pending_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(PipelineError):
        store.load()
    assert store.pending_path.is_file()
    assert not (tmp_path / "unexpected.md").exists()


def test_pending_recovery_checks_hash_after_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=2,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="pending-post-copy",
    )
    store = RunStore(state_path)
    session = start_session(store).session_path
    _complete_shadow(session)
    mark_shadow_ready(store)
    _write_evaluation(session, 70)
    _leave_pending_evaluation(store, state_path, monkeypatch)
    original_copy = pipeline.atomic_copy
    corrupted = False

    def corrupt_after_copy(source: Path, destination: Path) -> None:
        nonlocal corrupted
        original_copy(source, destination)
        if not corrupted:
            corrupted = True
            destination.write_text("post-copy corruption", encoding="utf-8")

    monkeypatch.setattr(pipeline, "atomic_copy", corrupt_after_copy)
    with pytest.raises(PipelineError, match="Published target failed integrity"):
        store.load()
    assert store.pending_path.is_file()


def test_evaluation_convenience_copy_is_published_only_after_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = _configure_runtime(tmp_path, monkeypatch)
    previous = "# Previously validated evaluation\n"
    (data_dir / "evaluation.md").write_text(previous, encoding="utf-8")
    state_path, _ = initialize_run(
        max_iterations=2,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="validated-convenience-copy",
    )
    store = RunStore(state_path)
    session = start_session(store).session_path
    _complete_shadow(session)
    mark_shadow_ready(store)
    report = session / "anti_karen" / "artifacts" / "karen_output.md"
    report.write_text("not a canonical evaluation", encoding="utf-8")

    with pytest.raises(ValueError, match="exactly one canonical"):
        record_evaluation(store)
    assert (data_dir / "evaluation.md").read_text(encoding="utf-8") == previous

    _write_evaluation(session, 70)
    expected = report.read_text(encoding="utf-8")
    record_evaluation(store)
    assert (data_dir / "evaluation.md").read_text(encoding="utf-8") == expected


@pytest.mark.parametrize(
    "mutation",
    ["repository_create", "inventory_remove", "canonical_job", "evaluation_symlink"],
)
def test_bill_guard_covers_reachable_inputs_and_types(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    data_dir = _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=2,
        min_fit_score=80,
        karen_reads_background=False,
        run_id=f"bill-{mutation}",
    )
    store = RunStore(state_path)
    session = _reach_bill(store)
    prepare_bill(store)
    cv = session / "docs" / "cv.md"
    cv.write_text(cv.read_text(encoding="utf-8") + "\nA valid CV revision.\n", encoding="utf-8")

    if mutation == "repository_create":
        (session / "repos" / "unexpected.txt").write_text("tampered", encoding="utf-8")
    elif mutation == "inventory_remove":
        (session / "repos_expected_count.txt").unlink()
    elif mutation == "canonical_job":
        (data_dir / "docs" / "job.md").write_text("# Changed — Input\n", encoding="utf-8")
    else:
        report = session / "anti_karen" / "artifacts" / "karen_output.md"
        replacement = tmp_path / "replacement-report.md"
        replacement.write_text(report.read_text(encoding="utf-8"), encoding="utf-8")
        report.unlink()
        report.symlink_to(replacement)

    with pytest.raises(PipelineError, match="protected context"):
        commit_bill(store)
    assert store.load().phase is Phase.BILL_RUNNING


def test_bill_guard_rejects_host_repository_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=2,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="bill-host-worktree",
    )
    store = RunStore(state_path)
    session = _reach_bill(store)
    prepare_bill(store)
    cv = session / "docs" / "cv.md"
    cv.write_text(cv.read_text(encoding="utf-8") + "\nA valid CV revision.\n", encoding="utf-8")

    monkeypatch.setattr(pipeline, "_repository_snapshot", lambda: {"changed": {"type": "file"}})
    with pytest.raises(PipelineError, match="host repository"):
        commit_bill(store)
    assert store.load().phase is Phase.BILL_RUNNING


def test_bill_guard_digest_is_anchored_and_rejects_semantic_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=2,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="bill-guard-digest",
    )
    store = RunStore(state_path)
    session = _reach_bill(store)
    prepared = prepare_bill(store)
    assert prepared.bill_guard is not None
    events = [
        json.loads(line)
        for line in (prepared.run_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert events[-1]["details"]["guard_sha256"] == prepared.bill_guard.sha256
    guard_path = Path(prepared.bill_guard.path)
    guard = json.loads(guard_path.read_text(encoding="utf-8"))
    guard["cv_sha256"] = "0" * 64
    guard_path.write_text(json.dumps(guard), encoding="utf-8")
    cv = session / "docs" / "cv.md"
    cv.write_text(cv.read_text(encoding="utf-8") + "\nA valid revision.\n", encoding="utf-8")

    with pytest.raises(PipelineError, match="Bill guard digest"):
        commit_bill(store)
    assert store.load().phase is Phase.BILL_RUNNING


@pytest.mark.parametrize("ancestor", ["session_docs", "data_docs"])
def test_bill_guard_rejects_ancestor_directory_symlink_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ancestor: str,
) -> None:
    data_dir = _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=2,
        min_fit_score=80,
        karen_reads_background=False,
        run_id=f"bill-ancestor-{ancestor}",
    )
    store = RunStore(state_path)
    session = _reach_bill(store)
    prepare_bill(store)
    cv = session / "docs" / "cv.md"
    cv.write_text(cv.read_text(encoding="utf-8") + "\nA valid revision.\n", encoding="utf-8")
    docs = session / "docs" if ancestor == "session_docs" else data_dir / "docs"
    replacement = docs.with_name(f"{docs.name}-replacement")
    docs.rename(replacement)
    docs.symlink_to(replacement, target_is_directory=True)

    with pytest.raises(PipelineError, match="protected context|Symlink path component"):
        commit_bill(store)
    assert store.load().phase is Phase.BILL_RUNNING


def test_donna_must_replace_stale_plan_and_archives_new_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = _configure_runtime(tmp_path, monkeypatch)
    stale = "# Old Action Plan\n\n" + "This belongs to an earlier run. " * 5
    action_plan = data_dir / "docs" / "action_plan.md"
    action_plan.write_text(stale, encoding="utf-8")
    state_path, _ = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="fresh-donna",
    )
    store = RunStore(state_path)
    _reach_donna(store)
    prepared = prepare_donna(store)
    donna_input = json.loads(
        (
            prepared.session_path
            / "anti_karen"
            / "contracts"
            / "donna"
            / "donna_input.json"
        ).read_text(encoding="utf-8")
    )
    assert donna_input["action_plan_path"] == str(action_plan)

    with pytest.raises(PipelineError, match="did not create or change"):
        complete_donna(store)
    assert store.load().phase is Phase.DONNA_RUNNING

    recreated = action_plan.with_name("action_plan.recreated.md")
    recreated.write_text(stale, encoding="utf-8")
    recreated.replace(action_plan)
    with pytest.raises(PipelineError, match="did not create or change"):
        complete_donna(store)

    fresh = "# New Action Plan\n\n" + "This is attributable to the current run. " * 5
    action_plan.write_text(fresh, encoding="utf-8")
    completed = complete_donna(store)
    assert completed.phase is Phase.COMPLETE
    assert (completed.run_path / "action_plan.md").read_text(encoding="utf-8") == fresh


def test_donna_guard_digest_rejects_semantic_tampering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="donna-guard-digest",
    )
    store = RunStore(state_path)
    _reach_donna(store)
    prepared = prepare_donna(store)
    assert prepared.donna_guard is not None
    guard_path = Path(prepared.donna_guard.path)
    guard = json.loads(guard_path.read_text(encoding="utf-8"))
    guard["action_plan_before"] = {".": {"type": "absent"}}
    guard_path.write_text(json.dumps(guard), encoding="utf-8")
    (data_dir / "docs" / "action_plan.md").write_text(
        "# Fresh plan\n\n" + "Specific current-run guidance. " * 5,
        encoding="utf-8",
    )

    with pytest.raises(PipelineError, match="Donna guard digest"):
        complete_donna(store)
    assert store.load().phase is Phase.DONNA_RUNNING


@pytest.mark.parametrize(
    "mutation",
    ["session_cv", "canonical_job", "final_evaluation", "session_repository", "worktree"],
)
def test_donna_guard_rejects_read_only_input_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    data_dir = _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        run_id=f"donna-read-only-{mutation}",
    )
    store = RunStore(state_path)
    session = _reach_donna(store)
    prepared = prepare_donna(store)
    (data_dir / "docs" / "action_plan.md").write_text(
        "# Fresh plan\n\n" + "Specific current-run guidance. " * 5,
        encoding="utf-8",
    )

    if mutation == "session_cv":
        (session / "docs" / "cv.md").write_text("# Mutated CV\n", encoding="utf-8")
    elif mutation == "canonical_job":
        (data_dir / "docs" / "job.md").write_text("# Mutated — Job\n", encoding="utf-8")
    elif mutation == "final_evaluation":
        final_report = (
            prepared.run_path
            / "iterations"
            / f"{prepared.iterations_completed:02d}"
            / "evaluation.md"
        )
        final_report.write_text("# Mutated evaluation\n", encoding="utf-8")
    elif mutation == "session_repository":
        (session / "repos" / "unexpected.txt").write_text("mutated", encoding="utf-8")
    else:
        monkeypatch.setattr(
            pipeline,
            "_repository_snapshot",
            lambda: {"changed": {"type": "file"}},
        )

    message = "host repository" if mutation == "worktree" else "protected context"
    with pytest.raises(PipelineError, match=message):
        complete_donna(store)
    assert store.load().phase is Phase.DONNA_RUNNING


def test_donna_rejects_action_plan_ancestor_symlink_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="donna-ancestor-swap",
    )
    store = RunStore(state_path)
    _reach_donna(store)
    prepare_donna(store)
    docs = data_dir / "docs"
    replacement = data_dir / "docs-replacement"
    docs.rename(replacement)
    docs.symlink_to(replacement, target_is_directory=True)
    (docs / "action_plan.md").write_text(
        "# Fresh plan\n\n" + "Specific current-run guidance. " * 5,
        encoding="utf-8",
    )

    with pytest.raises(PipelineError, match="ancestors changed|Symlink path component"):
        complete_donna(store)
    assert store.load().phase is Phase.DONNA_RUNNING


def test_replay_cli_runs_complete_control_plane(tmp_path: Path) -> None:
    fixtures = REPOSITORY_ROOT / "tests" / "fixtures"
    output_dir = tmp_path / "replay-output"
    command = [
        "uv",
        "run",
        "python",
        "-m",
        "tools.replay_pipeline",
        "--max-iterations",
        "3",
        "--min-fit-score",
        "80",
        "--output-dir",
        str(output_dir),
    ]
    for report in ("evaluation_72.md", "evaluation_62.md", "evaluation_68.md"):
        command.extend(("--report", str(fixtures / report)))
    environment = os.environ.copy()
    environment["UV_CACHE_DIR"] = str(tmp_path / "uv-cache")
    result = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["outcome"] == "max_iterations"
    assert payload["iterations_completed"] == 3
    state = json.loads(Path(payload["state_path"]).read_text(encoding="utf-8"))
    assert state["phase"] == "complete"
    assert state["agent_provider"] == "replay"
    log_tree = Path(payload["log_tree"])
    assert log_tree.is_file()
    assert "run_completed" in log_tree.read_text(encoding="utf-8")
    assert (log_tree.parent / "logs" / "pipeline.log").is_file()


def test_agent_provider_is_immutable_run_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, state = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        agent_provider="codex",
        run_id="codex-provider",
    )

    assert state.agent_provider == "codex"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["agent_provider"] == "codex"
    assert RunStore(state_path).load().agent_provider == "codex"


def test_agy_celestial_derives_baseline_from_the_single_secondary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    monkeypatch.setenv("CELESTIAL_DATA_DIR", str(tmp_path / "celestial"))
    state_path, state = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        agent_provider="agy",
        celestial_capture_id="agy-secondary",
        celestial_requested=True,
        celestial_judge_provider="codex",
        celestial_judge_model="gpt-5.4",
        run_id="agy-celestial",
    )

    assert state.schema_version == 4
    assert state.agent_model is None
    assert state.celestial_baseline_provider == "codex"
    assert state.celestial_baseline_model == "gpt-5.4"
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    request = json.loads(
        (tmp_path / "celestial/captures/agy-secondary/request.json").read_text()
    )
    assert persisted["agent_provider"] == "agy"
    assert request["schema_version"] == 3
    assert request["subject_provider"] == "agy"
    assert request["subject_model"] is None
    assert request["baseline_provider"] == "codex"
    assert request["judge_provider"] == "codex"

    persisted["schema_version"] = 3
    persisted.pop("celestial_baseline_provider")
    persisted.pop("celestial_baseline_model")
    state_path.write_text(json.dumps(persisted), encoding="utf-8")
    migrated = RunStore(state_path).load()
    assert migrated.schema_version == 4
    assert migrated.celestial_baseline_provider == "codex"
    assert migrated.celestial_baseline_model == "gpt-5.4"


def test_legacy_state_without_agent_provider_defaults_to_agy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_runtime(tmp_path, monkeypatch)
    state_path, _ = initialize_run(
        max_iterations=1,
        min_fit_score=80,
        karen_reads_background=False,
        run_id="legacy-provider",
    )
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    payload.pop("agent_provider")
    state_path.write_text(json.dumps(payload), encoding="utf-8")

    assert RunStore(state_path).load().agent_provider == "agy"
