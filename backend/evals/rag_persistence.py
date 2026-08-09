import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.db.models import EvaluationCaseResult, EvaluationRun
from evals.models import RagBenchmarkCase, RagBenchmarkScore
from evals.persistence import (
    EvaluationPersistence,
    _case_version,
    _suite_version,
    default_run_context,
)
from app.rag.embeddings import get_embedding_profile


def _utcnow() -> datetime:
    return datetime.utcnow()


class RagEvaluationPersistence(EvaluationPersistence):
    def create_rag_run(
        self,
        cases: list[RagBenchmarkCase],
        *,
        configuration: dict,
        selection_filters: dict | None = None,
        context: dict | None = None,
    ) -> UUID:
        run_context = {**default_run_context(), **(context or {})}
        profile = get_embedding_profile(configuration.get("embedding_model"))
        run_context["model_provider"] = profile.provider
        run = EvaluationRun(
            baseline_run_id=run_context.pop("baseline_run_id", None),
            idempotency_key=run_context.pop("idempotency_key", None),
            suite_name="productai-rag-evals",
            suite_version=_suite_version(cases),
            status="queued",
            model=profile.model,
            configuration=configuration,
            selection_filters=selection_filters,
            selected_case_count=len(cases),
            estimated_cost_usd=0,
            **run_context,
        )
        with self._session_factory() as session:
            session.add(run)
            session.commit()
            session.refresh(run)
            return run.run_id

    def start_rag_case(
        self,
        run_id: UUID,
        case: RagBenchmarkCase,
        *,
        sequence_number: int,
    ) -> UUID:
        case_result = EvaluationCaseResult(
            run_id=run_id,
            case_id=case.id,
            case_version=_case_version(case),
            category=case.category,
            sequence_number=sequence_number,
            attempt_number=1,
            status="running",
            query=case.query,
            reference_source=", ".join(case.expected_sources),
            expected_tools=[],
            forbidden_tools=[],
            expected_answer_contains=[],
            expected_answer_terms=case.expected_content_term_groups,
            started_at=_utcnow(),
        )
        with self._session_factory() as session:
            session.add(case_result)
            session.commit()
            session.refresh(case_result)
            return case_result.case_result_id

    def complete_rag_case(
        self,
        run_id: UUID,
        case_result_id: UUID,
        *,
        result_path: Path,
        score_path: Path,
        score: RagBenchmarkScore,
    ) -> None:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        failed_checks = [
            check.model_dump() for check in score.checks if not check.passed
        ]
        metrics = score.metrics.model_dump()
        with self._session_factory() as session:
            case_result = self._get_case_result(session, case_result_id)
            case_result.status = "completed"
            case_result.passed = score.passed
            case_result.score_percent = score.score_percent
            case_result.answer = None
            case_result.final_answer = None
            case_result.tools_used = []
            case_result.tool_call_count = 0
            case_result.checks = [check.model_dump() for check in score.checks]
            case_result.failed_checks = failed_checks
            case_result.latency_ms = score.metrics.latency_ms
            case_result.raw_result_uri = str(result_path)
            case_result.score_result_uri = str(score_path)
            case_result.result_metadata = {
                "benchmark_type": "rag_retrieval",
                "rag_metrics": metrics,
                "retrieved_sources": [
                    match.get("source_path") or match.get("title")
                    for match in result.get("response", {}).get("matches", [])
                ],
            }
            case_result.finished_at = _utcnow()
            self._add_artifact(
                session,
                run_id,
                result_path,
                artifact_type="rag_raw_result",
                case_result_id=case_result_id,
                is_sensitive=True,
            )
            self._add_artifact(
                session,
                run_id,
                score_path,
                artifact_type="rag_score",
                case_result_id=case_result_id,
                is_sensitive=False,
            )
            session.commit()

    def finalize_rag_run(
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
                "completed_with_errors" if summary["errors"] else "completed"
            )
            run.attempted_case_count = summary["completed"] + summary["errors"]
            run.completed_case_count = summary["completed"]
            run.passed_case_count = summary["passed"]
            run.failed_case_count = summary["failed"]
            run.error_case_count = summary["errors"]
            run.pass_rate_percent = summary["pass_rate_percent"]
            run.average_score_percent = summary["pass_rate_percent"]
            run.actual_cost_usd = 0
            run.average_latency_ms = summary["average_latency_ms"]
            run.minimum_latency_ms = summary.get("minimum_latency_ms")
            run.maximum_latency_ms = summary.get("maximum_latency_ms")
            run.p95_latency_ms = summary["p95_latency_ms"]
            run.manifest_uri = str(manifest_path)
            run.report_uri = str(report_path)
            run.run_metadata = {
                "benchmark_type": "rag_retrieval",
                "rag_metrics": summary,
            }
            run.finished_at = _utcnow()
            run.updated_at = _utcnow()
            self._add_artifact(
                session,
                run_id,
                manifest_path,
                artifact_type="rag_manifest",
                is_sensitive=True,
            )
            self._add_artifact(
                session,
                run_id,
                report_path,
                artifact_type="rag_report",
                is_sensitive=False,
            )
            session.commit()
