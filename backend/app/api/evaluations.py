from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.admin import require_admin
from app.deps import get_db
from app.schemas.evaluations import (
    EvaluationDashboardResponse,
    EvaluationRunDetail,
    EvaluationRunQueued,
    EvaluationRunRequest,
)
from app.services.evaluations import (
    get_evaluation_dashboard,
    get_evaluation_run,
)
from evals.load_cases import load_cases
from evals.models import EvalOptions
from evals.persistence import EvaluationPersistence
from evals.run_batch import (
    DEFAULT_API_BASE,
    build_batch_configuration,
    estimate_batch_cost,
    execute_batch,
    select_cases,
)


router = APIRouter(tags=["evaluations"])


@router.get(
    "/evaluations/dashboard",
    response_model=EvaluationDashboardResponse,
)
def evaluation_dashboard(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return get_evaluation_dashboard(db, limit=limit)


@router.get(
    "/evaluations/runs/{run_id}",
    response_model=EvaluationRunDetail,
)
def evaluation_run_detail(
    run_id: UUID,
    db: Session = Depends(get_db),
):
    run = get_evaluation_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")
    return run


@router.post(
    "/admin/evaluations",
    response_model=EvaluationRunQueued,
    status_code=202,
)
def queue_evaluation_run(
    payload: EvaluationRunRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_admin),
):
    try:
        selected = select_cases(
            load_cases(),
            categories=payload.categories or None,
            case_ids=payload.case_ids or None,
            limit=payload.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not selected:
        raise HTTPException(status_code=400, detail="No evaluation cases selected.")

    estimated_cost = estimate_batch_cost(
        len(selected),
        payload.estimated_cost_per_case,
    )
    if estimated_cost > payload.budget_usd:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Estimated cost ${estimated_cost:.4f} exceeds "
                f"budget ${payload.budget_usd:.4f}."
            ),
        )

    options = EvalOptions(
        model=payload.model,
        analysis_depth=payload.analysis_depth,
        answer_detail=payload.answer_detail,
    )
    selection_filters = {
        "categories": payload.categories,
        "case_ids": payload.case_ids,
        "limit": payload.limit,
    }
    configuration = build_batch_configuration(
        api_base=DEFAULT_API_BASE,
        options=options,
        budget_usd=payload.budget_usd,
        estimated_cost_per_case=payload.estimated_cost_per_case,
        fail_fast=payload.fail_fast,
    )
    configuration["estimated_batch_cost_usd"] = estimated_cost
    persistence = EvaluationPersistence()
    run_id = persistence.create_run(
        selected,
        options,
        estimated_cost_usd=estimated_cost,
        configuration=configuration,
        selection_filters=selection_filters,
        context={
            "trigger_source": "admin",
            "triggered_by": "productai-admin",
        },
    )
    background_tasks.add_task(
        execute_batch,
        selected,
        api_base=DEFAULT_API_BASE,
        options=options,
        budget_usd=payload.budget_usd,
        estimated_cost_per_case=payload.estimated_cost_per_case,
        fail_fast=payload.fail_fast,
        persistence=persistence,
        persistence_context={
            "trigger_source": "admin",
            "triggered_by": "productai-admin",
        },
        selection_filters=selection_filters,
        existing_database_run_id=run_id,
    )
    return EvaluationRunQueued(
        run_id=run_id,
        status="queued",
        selected_case_count=len(selected),
        estimated_cost_usd=estimated_cost,
    )
