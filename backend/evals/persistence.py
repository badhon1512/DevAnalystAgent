import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import (
    EvaluationArtifact,
    EvaluationCaseResult,
    EvaluationRun,
)
from app.db.session import SessionLocal
from evals.models import BenchmarkCase, BenchmarkScore, EvalOptions


SessionFactory = Callable[[], Session]


def _utcnow() -> datetime:
    return datetime.utcnow()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact_file:
        for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _case_version(case: BenchmarkCase) -> str:
    canonical = json.dumps(
        case.model_dump(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _suite_version(cases: list[BenchmarkCase]) -> str:
    versions = "|".join(f"{case.id}:{_case_version(case)}" for case in cases)
    return hashlib.sha256(versions.encode("utf-8")).hexdigest()[:16]


def default_run_context() -> dict:
    return {
        "trigger_source": "cli",
        "triggered_by": os.getenv("USERNAME") or os.getenv("USER"),
        "environment": os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or "local",
        "git_commit_sha": (
            os.getenv("GITHUB_SHA")
            or os.getenv("RAILWAY_GIT_COMMIT_SHA")
            or os.getenv("COMMIT_SHA")
        ),
        "git_branch": (
            os.getenv("GITHUB_REF_NAME")
            or os.getenv("RAILWAY_GIT_BRANCH")
            or os.getenv("BRANCH_NAME")
        ),
        "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID"),
        "ci_provider": "github" if os.getenv("GITHUB_ACTIONS") else None,
        "ci_run_id": os.getenv("GITHUB_RUN_ID"),
        "model_provider": "openai",
        "prompt_version": os.getenv("PROMPT_VERSION"),
        "agent_version": os.getenv("AGENT_VERSION"),
    }


class EvaluationPersistence:
    def __init__(self, session_factory: SessionFactory = SessionLocal):
        self._session_factory = session_factory

    def create_run(
        self,
        cases: list[BenchmarkCase],
        options: EvalOptions,
        *,
        estimated_cost_usd: float,
        configuration: dict,
        selection_filters: dict | None = None,
        context: dict | None = None,
    ) -> UUID:
        run_context = {**default_run_context(), **(context or {})}
        baseline_run_id = run_context.pop("baseline_run_id", None)
        run = EvaluationRun(
            baseline_run_id=baseline_run_id,
            idempotency_key=run_context.pop("idempotency_key", None),
            suite_name=run_context.pop(
                "suite_name",
                "productai-agent-evals",
            ),
            suite_version=_suite_version(cases),
            status="queued",
            model=options.model,
            analysis_depth=options.analysis_depth,
            answer_detail=options.answer_detail,
            configuration=configuration,
            selection_filters=selection_filters,
            selected_case_count=len(cases),
            estimated_cost_usd=estimated_cost_usd,
            **run_context,
        )
        with self._session_factory() as session:
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.run_id

    def mark_run_running(self, run_id: UUID) -> None:
        with self._session_factory() as session:
            run = self._get_run(session, run_id)
            run.status = "running"
            run.started_at = _utcnow()
            run.updated_at = _utcnow()
            session.commit()

    def start_case(
        self,
        run_id: UUID,
        case: BenchmarkCase,
        *,
        sequence_number: int,
        attempt_number: int = 1,
    ) -> UUID:
        case_result = EvaluationCaseResult(
            run_id=run_id,
            case_id=case.id,
            case_version=_case_version(case),
            category=case.category,
            sequence_number=sequence_number,
            attempt_number=attempt_number,
            status="running",
            query=case.query,
            reference_source=case.reference_source,
            expected_tools=case.expected_tools,
            forbidden_tools=case.forbidden_tools,
            expected_answer_contains=case.expected_answer_contains,
            expected_answer_terms=case.expected_answer_terms,
            started_at=_utcnow(),
        )
        with self._session_factory() as session:
            session.add(case_result)
            session.commit()
            session.refresh(case_result)
            return case_result.case_result_id

    def complete_case(
        self,
        run_id: UUID,
        case_result_id: UUID,
        *,
        result_path: Path,
        score_path: Path,
        score: BenchmarkScore,
    ) -> None:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        response = result["response"]
        trace = response["trace"]
        usage = trace.get("token_usage", {})
        failed_checks = [
            check.model_dump() for check in score.checks if not check.passed
        ]

        with self._session_factory() as session:
            case_result = self._get_case_result(session, case_result_id)
            case_result.status = "completed"
            case_result.passed = score.passed
            case_result.score_percent = score.score_percent
            case_result.answer = response["answer"]
            case_result.final_answer = response.get("final_answer")
            case_result.tools_used = trace.get("tools_used", [])
            case_result.tool_call_count = len(trace.get("tool_calls", []))
            case_result.checks = [check.model_dump() for check in score.checks]
            case_result.failed_checks = failed_checks
            case_result.trace_id = trace.get("trace_id")
            case_result.guardrail_status = trace.get("guardrail_status")
            case_result.model = trace.get("model")
            case_result.latency_ms = trace.get("latency_ms")
            case_result.input_tokens = usage.get("input_tokens", 0)
            case_result.output_tokens = usage.get("output_tokens", 0)
            case_result.total_tokens = usage.get("total_tokens", 0)
            case_result.cost_usd = usage.get("estimated_total_cost_usd")
            case_result.raw_result_uri = str(result_path)
            case_result.score_result_uri = str(score_path)
            case_result.finished_at = _utcnow()
            self._add_artifact(
                session,
                run_id,
                result_path,
                artifact_type="raw_result",
                case_result_id=case_result_id,
                is_sensitive=True,
            )
            self._add_artifact(
                session,
                run_id,
                score_path,
                artifact_type="score",
                case_result_id=case_result_id,
                is_sensitive=False,
            )
            session.commit()

    def fail_case(
        self,
        case_result_id: UUID,
        *,
        stage: str,
        error: Exception,
    ) -> None:
        with self._session_factory() as session:
            case_result = self._get_case_result(session, case_result_id)
            case_result.status = "error"
            case_result.passed = False
            case_result.error_stage = stage
            case_result.error_type = type(error).__name__
            case_result.error_message = str(error)
            case_result.finished_at = _utcnow()
            session.commit()

    def finalize_run(
        self,
        run_id: UUID,
        *,
        summary: dict,
        manifest_path: Path,
        report_path: Path,
    ) -> None:
        with self._session_factory() as session:
            run = self._get_run(session, run_id)
            run.status = (
                "completed_with_errors"
                if summary["errors"]
                else "completed"
            )
            run.attempted_case_count = summary["attempted"]
            run.completed_case_count = summary["completed"]
            run.passed_case_count = summary["passed"]
            run.failed_case_count = summary["failed"]
            run.error_case_count = summary["errors"]
            run.pass_rate_percent = summary["pass_rate_percent"]
            run.average_score_percent = summary["average_score_percent"]
            run.actual_cost_usd = summary["known_actual_cost_usd"]
            run.average_latency_ms = summary["average_agent_latency_ms"]
            run.minimum_latency_ms = summary["minimum_agent_latency_ms"]
            run.maximum_latency_ms = summary["maximum_agent_latency_ms"]
            run.p95_latency_ms = summary["p95_agent_latency_ms"]
            run.total_input_tokens = summary["total_input_tokens"]
            run.total_output_tokens = summary["total_output_tokens"]
            run.total_tokens = summary["total_tokens"]
            run.manifest_uri = str(manifest_path)
            run.report_uri = str(report_path)
            run.finished_at = _utcnow()
            run.updated_at = _utcnow()
            self._add_artifact(
                session,
                run_id,
                manifest_path,
                artifact_type="manifest",
                is_sensitive=True,
            )
            self._add_artifact(
                session,
                run_id,
                report_path,
                artifact_type="report",
                is_sensitive=True,
            )
            session.commit()

    def fail_run(self, run_id: UUID, error: Exception) -> None:
        with self._session_factory() as session:
            run = self._get_run(session, run_id)
            run.status = "failed"
            run.error_summary = f"{type(error).__name__}: {error}"
            run.finished_at = _utcnow()
            run.updated_at = _utcnow()
            session.commit()

    @staticmethod
    def _get_run(session: Session, run_id: UUID) -> EvaluationRun:
        run = session.get(EvaluationRun, run_id)
        if run is None:
            raise ValueError(f"Evaluation run not found: {run_id}")
        return run

    @staticmethod
    def _get_case_result(
        session: Session,
        case_result_id: UUID,
    ) -> EvaluationCaseResult:
        case_result = session.get(EvaluationCaseResult, case_result_id)
        if case_result is None:
            raise ValueError(
                f"Evaluation case result not found: {case_result_id}"
            )
        return case_result

    @staticmethod
    def _add_artifact(
        session: Session,
        run_id: UUID,
        path: Path,
        *,
        artifact_type: str,
        case_result_id: UUID | None = None,
        is_sensitive: bool,
    ) -> None:
        resolved_path = path.resolve()
        session.add(
            EvaluationArtifact(
                run_id=run_id,
                case_result_id=case_result_id,
                artifact_type=artifact_type,
                name=path.name,
                storage_provider="local",
                uri=str(resolved_path),
                content_type=(
                    "application/json"
                    if path.suffix == ".json"
                    else "text/markdown"
                ),
                size_bytes=path.stat().st_size,
                checksum_sha256=_sha256(path),
                is_sensitive=is_sensitive,
            )
        )
