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


def seed_rag_run(session_factory: sessionmaker):
    with session_factory() as session:
        run = EvaluationRun(
            suite_name="productai-rag-evals",
            status="completed",
            model="text-embedding-3-small",
            trigger_source="cli",
            selected_case_count=40,
            attempted_case_count=40,
            completed_case_count=40,
            passed_case_count=36,
            failed_case_count=4,
            pass_rate_percent=90,
            average_latency_ms=250,
            p95_latency_ms=450,
            run_metadata={
                "benchmark_type": "rag_retrieval",
                "rag_metrics": {
                    "pass_rate_percent": 90,
                    "quality_gate_status": "PASS",
                    "hit_at_1_percent": 87.5,
                    "hit_at_3_percent": 92.5,
                    "hit_at_k_percent": 95,
                    "mean_precision_at_k_percent": 42,
                    "mean_source_recall_percent": 95,
                    "mean_retrieval_f1_percent": 58.2,
                    "mean_reciprocal_rank": 0.8812,
                    "mean_average_precision": 0.87,
                    "mean_ndcg_at_k": 0.91,
                    "mean_content_term_recall_percent": 94.58,
                    "mean_unique_chunk_ratio_percent": 100,
                    "mean_redundancy_percent": 0,
                    "mean_similarity_score": 0.61,
                    "mean_context_character_count": 4200,
                    "error_free_rate_percent": 100,
                    "average_latency_ms": 250,
                    "p50_latency_ms": 230,
                    "p95_latency_ms": 450,
                    "p99_latency_ms": 520,
                    "throughput_cases_per_second": 2.1,
                    "quality_gates": {"hit_at_k": True},
                    "generation_evaluation": {
                        "faithfulness": "not_measured"
                    },
                },
            },
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        session.add(run)
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


def test_dashboard_exposes_rag_suite_without_mixing_agent_runs() -> None:
    client, session_factory = evaluation_client()
    agent_run_id = seed_completed_run(session_factory)
    rag_run_id = seed_rag_run(session_factory)

    response = client.get("/evaluations/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["latest_run"]["run_id"] == str(agent_run_id)
    assert body["rag_latest"]["run_id"] == str(rag_run_id)
    assert body["rag_latest"]["hit_at_k_percent"] == 95
    assert body["rag_latest"]["generation_evaluation"]["faithfulness"] == (
        "not_measured"
    )


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

    rag_response = client.post("/admin/evaluations/rag", json={})
    assert rag_response.status_code == 401
    assert rag_response.json()["detail"] == "Admin token required."
