from app.db.models import (
    EvaluationArtifact,
    EvaluationCaseResult,
    EvaluationRun,
)


def column_names(model: type) -> set[str]:
    return {column.name for column in model.__table__.columns}


def test_evaluation_run_has_dashboard_and_audit_fields() -> None:
    assert {
        "run_id",
        "baseline_run_id",
        "idempotency_key",
        "suite_name",
        "suite_version",
        "status",
        "trigger_source",
        "triggered_by",
        "environment",
        "git_commit_sha",
        "git_branch",
        "deployment_id",
        "ci_provider",
        "ci_run_id",
        "model_provider",
        "model",
        "prompt_version",
        "agent_version",
        "configuration",
        "selection_filters",
        "selected_case_count",
        "passed_case_count",
        "failed_case_count",
        "error_case_count",
        "pass_rate_percent",
        "actual_cost_usd",
        "p95_latency_ms",
        "total_tokens",
        "manifest_uri",
        "report_uri",
        "cancellation_requested",
        "started_at",
        "finished_at",
    } <= column_names(EvaluationRun)


def test_evaluation_case_result_preserves_case_and_execution_snapshots() -> None:
    assert {
        "case_result_id",
        "run_id",
        "case_id",
        "case_version",
        "attempt_number",
        "query",
        "answer",
        "final_answer",
        "expected_tools",
        "forbidden_tools",
        "expected_answer_contains",
        "expected_answer_terms",
        "tools_used",
        "checks",
        "failed_checks",
        "trace_id",
        "guardrail_status",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "error_stage",
        "error_type",
        "error_message",
        "raw_result_uri",
        "score_result_uri",
    } <= column_names(EvaluationCaseResult)

    unique_constraints = {
        constraint.name for constraint in EvaluationCaseResult.__table__.constraints
    }
    assert "uq_evaluation_case_results_run_case_attempt" in unique_constraints


def test_evaluation_artifact_supports_external_storage_and_retention() -> None:
    assert {
        "artifact_id",
        "run_id",
        "case_result_id",
        "artifact_type",
        "storage_provider",
        "uri",
        "content_type",
        "size_bytes",
        "checksum_sha256",
        "is_sensitive",
        "retention_expires_at",
    } <= column_names(EvaluationArtifact)

    foreign_keys = {
        (foreign_key.target_fullname, foreign_key.ondelete)
        for foreign_key in EvaluationArtifact.__table__.foreign_keys
    }
    assert ("evaluation_runs.run_id", "CASCADE") in foreign_keys
    assert (
        "evaluation_case_results.case_result_id",
        "CASCADE",
    ) in foreign_keys
