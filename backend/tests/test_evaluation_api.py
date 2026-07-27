from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.evaluations import router
from app.db.base import Base
from app.db.models import (
    EvaluationArtifact,
    EvaluationCaseResult,
    EvaluationRun,
)
from app.deps import get_db


def evaluation_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            EvaluationRun.__table__,
            EvaluationCaseResult.__table__,
            EvaluationArtifact.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), session_factory


def seed_completed_run(session_factory: sessionmaker):
    with session_factory() as session:
        run = EvaluationRun(
            status="completed",
            model="gpt-5.4-nano",
            trigger_source="cli",
            selected_case_count=2,
            attempted_case_count=2,
            completed_case_count=2,
            passed_case_count=1,
            failed_case_count=1,
            pass_rate_percent=50,
            average_score_percent=75,
            actual_cost_usd=0.02,
            average_latency_ms=120,
            p95_latency_ms=150,
            total_tokens=400,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        session.add(run)
        session.flush()
        session.add_all(
            [
                EvaluationCaseResult(
                    run_id=run.run_id,
                    case_id="rag-policy-001",
                    category="rag",
                    sequence_number=1,
                    status="completed",
                    passed=True,
                    score_percent=100,
                    query="Secret benchmark input",
                    answer="Secret raw model answer",
                    final_answer="Secret final answer",
                    tools_used=["search_company_documents"],
                    tool_call_count=1,
                    guardrail_status="allowed",
                    latency_ms=100,
                    cost_usd=0.01,
                    raw_result_uri="/private/results/result.json",
                    score_result_uri="/private/results/score.json",
                ),
                EvaluationCaseResult(
                    run_id=run.run_id,
                    case_id="guardrail-001",
                    category="guardrails",
                    sequence_number=2,
                    status="completed",
                    passed=False,
                    score_percent=50,
                    query="Another secret input",
                    answer="Another raw answer",
                    failed_checks=[{"name": "guardrail_status"}],
                ),
                EvaluationCaseResult(
                    run_id=run.run_id,
                    case_id="queued-001",
                    category="rag",
                    sequence_number=3,
                    status="queued",
                    query="Not yet evaluated",
                ),
            ]
        )
        session.commit()
        return run.run_id


def test_dashboard_is_visible_and_excludes_unfinished_category_cases() -> None:
    client, session_factory = evaluation_client()
    run_id = seed_completed_run(session_factory)

    response = client.get("/evaluations/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_run"]["run_id"] == str(run_id)
    assert body["latest_run"]["pass_rate_percent"] == 50
    categories = {item["category"]: item for item in body["categories"]}
    assert categories["rag"]["total"] == 1
    assert categories["rag"]["pass_rate_percent"] == 100
    assert categories["guardrails"]["pass_rate_percent"] == 0


def test_run_detail_exposes_scores_but_not_raw_prompts_or_artifacts() -> None:
    client, session_factory = evaluation_client()
    run_id = seed_completed_run(session_factory)

    response = client.get(f"/evaluations/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["cases"][0]["tools_used"] == ["search_company_documents"]
    serialized = response.text
    for private_value in (
        "Secret benchmark input",
        "Secret raw model answer",
        "Secret final answer",
        "/private/results/result.json",
        "/private/results/score.json",
    ):
        assert private_value not in serialized


def test_missing_run_returns_not_found() -> None:
    client, _ = evaluation_client()

    response = client.get(
        "/evaluations/runs/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404


def test_running_evaluations_requires_admin_mode() -> None:
    client, _ = evaluation_client()

    response = client.post("/admin/evaluations", json={})

    assert response.status_code == 401
    assert response.json()["detail"] == "Admin token required."
