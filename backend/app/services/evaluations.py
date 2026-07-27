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
)


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


def get_evaluation_dashboard(
    db: Session,
    *,
    limit: int = 20,
) -> EvaluationDashboardResponse:
    runs = (
        db.query(EvaluationRun)
        .order_by(EvaluationRun.created_at.desc())
        .limit(limit)
        .all()
    )
    total_runs = db.query(func.count(EvaluationRun.run_id)).scalar() or 0
    completed_statuses = ("completed", "completed_with_errors")
    completed_runs = (
        db.query(func.count(EvaluationRun.run_id))
        .filter(EvaluationRun.status.in_(completed_statuses))
        .scalar()
        or 0
    )
    aggregate = (
        db.query(
            func.avg(EvaluationRun.pass_rate_percent),
            func.sum(EvaluationRun.actual_cost_usd),
        )
        .filter(EvaluationRun.status.in_(completed_statuses))
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
        .filter(EvaluationCaseResult.status.in_(("completed", "error")))
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

    return EvaluationDashboardResponse(
        generated_at=datetime.utcnow(),
        latest_run=run_summary(runs[0]) if runs else None,
        runs=[run_summary(run) for run in runs],
        categories=categories,
        total_runs=int(total_runs),
        completed_runs=int(completed_runs),
        average_pass_rate_percent=round(float(aggregate[0] or 0), 2),
        total_known_cost_usd=round(float(aggregate[1] or 0), 8),
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
