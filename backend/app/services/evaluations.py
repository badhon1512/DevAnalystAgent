from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db.models import EvaluationCaseResult, EvaluationRun
from app.schemas.evaluations import (
    EvaluationCaseSummary,
    EvaluationCategorySummary,
    EvaluationDashboardResponse,
    EvaluationRunDetail,
    EvaluationRunSummary,
    RagEvaluationSummary,
)


AGENT_SUITE = "productai-agent-evals"
RAG_SUITE = "productai-rag-evals"


def _number(value: Decimal | float | int | None) -> float | None:
    return float(value) if value is not None else None


def run_summary(run: EvaluationRun) -> EvaluationRunSummary:
    return EvaluationRunSummary(
        run_id=run.run_id,
        status=run.status,
        suite_name=run.suite_name,
        suite_version=run.suite_version,
        model=run.model,
        analysis_depth=run.analysis_depth,
        answer_detail=run.answer_detail,
        trigger_source=run.trigger_source,
        environment=run.environment,
        selected_case_count=run.selected_case_count,
        attempted_case_count=run.attempted_case_count,
        completed_case_count=run.completed_case_count,
        passed_case_count=run.passed_case_count,
        failed_case_count=run.failed_case_count,
        error_case_count=run.error_case_count,
        pass_rate_percent=_number(run.pass_rate_percent),
        average_score_percent=_number(run.average_score_percent),
        actual_cost_usd=_number(run.actual_cost_usd),
        average_latency_ms=run.average_latency_ms,
        p95_latency_ms=run.p95_latency_ms,
        total_tokens=run.total_tokens,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at,
    )


def case_summary(result: EvaluationCaseResult) -> EvaluationCaseSummary:
    return EvaluationCaseSummary(
        case_id=result.case_id,
        category=result.category,
        attempt_number=result.attempt_number,
        status=result.status,
        passed=result.passed,
        score_percent=_number(result.score_percent),
        tools_used=result.tools_used or [],
        tool_call_count=result.tool_call_count,
        guardrail_status=result.guardrail_status,
        latency_ms=result.latency_ms,
        cost_usd=_number(result.cost_usd),
        failed_checks=result.failed_checks or [],
        error_stage=result.error_stage,
        error_type=result.error_type,
        error_message=result.error_message,
    )


def rag_summary(run: EvaluationRun | None) -> RagEvaluationSummary | None:
    if run is None:
        return None
    metrics = (run.run_metadata or {}).get("rag_metrics", {})
    return RagEvaluationSummary(
        run_id=run.run_id,
        status=run.status,
        retrieval_mode=metrics.get(
            "retrieval_mode",
            (run.configuration or {}).get("retrieval_mode", "hybrid"),
        ),
        embedding_model=run.model,
        embedding_provider=(
            run.model_provider
            or (run.configuration or {}).get("embedding_provider", "unknown")
        ),
        embedding_dimensions=int(
            (run.configuration or {}).get("embedding_dimensions", 0)
        ),
        selected_case_count=run.selected_case_count,
        completed_case_count=run.completed_case_count,
        pass_rate_percent=float(metrics.get("pass_rate_percent", 0)),
        quality_gate_status=str(metrics.get("quality_gate_status", "PENDING")),
        hit_at_1_percent=float(metrics.get("hit_at_1_percent", 0)),
        hit_at_3_percent=float(metrics.get("hit_at_3_percent", 0)),
        hit_at_k_percent=float(metrics.get("hit_at_k_percent", 0)),
        mean_precision_at_k_percent=float(
            metrics.get("mean_precision_at_k_percent", 0)
        ),
        mean_passage_recall_percent=float(
            metrics.get("mean_passage_recall_percent", 0)
        ),
        mean_source_recall_percent=float(
            metrics.get("mean_source_recall_percent", 0)
        ),
        mean_retrieval_f1_percent=float(
            metrics.get("mean_retrieval_f1_percent", 0)
        ),
        mean_reciprocal_rank=float(metrics.get("mean_reciprocal_rank", 0)),
        mean_average_precision=float(metrics.get("mean_average_precision", 0)),
        mean_ndcg_at_k=float(metrics.get("mean_ndcg_at_k", 0)),
        mean_content_term_recall_percent=float(
            metrics.get("mean_content_term_recall_percent", 0)
        ),
        mean_unique_chunk_ratio_percent=float(
            metrics.get("mean_unique_chunk_ratio_percent", 0)
        ),
        mean_redundancy_percent=float(
            metrics.get("mean_redundancy_percent", 0)
        ),
        mean_similarity_score=float(metrics.get("mean_similarity_score", 0)),
        mean_context_character_count=int(
            metrics.get("mean_context_character_count", 0)
        ),
        error_free_rate_percent=float(metrics.get("error_free_rate_percent", 0)),
        average_latency_ms=int(metrics.get("average_latency_ms", 0)),
        p50_latency_ms=int(metrics.get("p50_latency_ms", 0)),
        p95_latency_ms=int(metrics.get("p95_latency_ms", 0)),
        p99_latency_ms=int(metrics.get("p99_latency_ms", 0)),
        throughput_cases_per_second=float(
            metrics.get("throughput_cases_per_second", 0)
        ),
        quality_gates=metrics.get("quality_gates", {}),
        generation_evaluation=metrics.get("generation_evaluation", {}),
        metrics_by_k=metrics.get("metrics_by_k", {}),
        finished_at=run.finished_at,
    )


def get_evaluation_dashboard(
    db: Session,
    *,
    limit: int = 20,
) -> EvaluationDashboardResponse:
    runs = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.suite_name == AGENT_SUITE)
        .order_by(EvaluationRun.created_at.desc())
        .limit(limit)
        .all()
    )
    total_runs = (
        db.query(func.count(EvaluationRun.run_id))
        .filter(EvaluationRun.suite_name == AGENT_SUITE)
        .scalar()
        or 0
    )
    completed_statuses = ("completed", "completed_with_errors")
    completed_runs = (
        db.query(func.count(EvaluationRun.run_id))
        .filter(
            EvaluationRun.suite_name == AGENT_SUITE,
            EvaluationRun.status.in_(completed_statuses),
        )
        .scalar()
        or 0
    )
    aggregate = (
        db.query(
            func.avg(EvaluationRun.pass_rate_percent),
            func.sum(EvaluationRun.actual_cost_usd),
        )
        .filter(
            EvaluationRun.suite_name == AGENT_SUITE,
            EvaluationRun.status.in_(completed_statuses),
        )
        .one()
    )
    category_rows = (
        db.query(
            EvaluationCaseResult.category,
            func.count(EvaluationCaseResult.case_result_id),
            func.sum(
                case(
                    (EvaluationCaseResult.passed.is_(True), 1),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (
                        (EvaluationCaseResult.status == "completed")
                        & EvaluationCaseResult.passed.is_(False),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(
                case(
                    (EvaluationCaseResult.status == "error", 1),
                    else_=0,
                )
            ),
            func.avg(EvaluationCaseResult.score_percent),
        )
        .join(EvaluationRun, EvaluationRun.run_id == EvaluationCaseResult.run_id)
        .filter(
            EvaluationRun.suite_name == AGENT_SUITE,
            EvaluationCaseResult.status.in_(("completed", "error")),
        )
        .group_by(EvaluationCaseResult.category)
        .order_by(EvaluationCaseResult.category)
        .all()
    )
    categories = []
    for category, total, passed, failed, errors, average_score in category_rows:
        passed_count = int(passed or 0)
        total_count = int(total or 0)
        categories.append(
            EvaluationCategorySummary(
                category=category,
                total=total_count,
                passed=passed_count,
                failed=int(failed or 0),
                errors=int(errors or 0),
                pass_rate_percent=(
                    round(passed_count / total_count * 100, 2)
                    if total_count
                    else 0
                ),
                average_score_percent=round(float(average_score or 0), 2),
            )
        )

    latest_rag_run = (
        db.query(EvaluationRun)
        .filter(EvaluationRun.suite_name == RAG_SUITE)
        .order_by(EvaluationRun.created_at.desc())
        .first()
    )

    return EvaluationDashboardResponse(
        generated_at=datetime.utcnow(),
        latest_run=run_summary(runs[0]) if runs else None,
        runs=[run_summary(run) for run in runs],
        categories=categories,
        total_runs=int(total_runs),
        completed_runs=int(completed_runs),
        average_pass_rate_percent=round(float(aggregate[0] or 0), 2),
        total_known_cost_usd=round(float(aggregate[1] or 0), 8),
        rag_latest=rag_summary(latest_rag_run),
    )


def get_evaluation_run(db: Session, run_id: UUID) -> EvaluationRunDetail | None:
    run = db.get(EvaluationRun, run_id)
    if run is None:
        return None
    results = (
        db.query(EvaluationCaseResult)
        .filter(EvaluationCaseResult.run_id == run_id)
        .order_by(
            EvaluationCaseResult.sequence_number,
            EvaluationCaseResult.attempt_number,
        )
        .all()
    )
    return EvaluationRunDetail(
        **run_summary(run).model_dump(),
        cases=[case_summary(result) for result in results],
    )
