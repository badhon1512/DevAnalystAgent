import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    EvaluationArtifact,
    EvaluationCaseResult,
    EvaluationRun,
)
from evals.models import EvalOptions
from evals.persistence import EvaluationPersistence
from evals.run_case import find_case
from evals.score_result import score_result_file


def test_persistence_records_completed_run_case_and_artifacts(tmp_path) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[
            EvaluationRun.__table__,
            EvaluationCaseResult.__table__,
            EvaluationArtifact.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)
    persistence = EvaluationPersistence(session_factory)
    case = find_case("rag-return-window-001")
    options = EvalOptions(model="gpt-4.1")

    run_id = persistence.create_run(
        [case],
        options,
        estimated_cost_usd=0.05,
        configuration={"api_base": "http://benchmark.test"},
        selection_filters={"case_ids": [case.id]},
        context={
            "trigger_source": "test",
            "triggered_by": "pytest",
            "environment": "test",
        },
    )
    persistence.mark_run_running(run_id)
    case_result_id = persistence.start_case(
        run_id,
        case,
        sequence_number=1,
    )

    result_path = tmp_path / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "case": case.model_dump(),
                "response": {
                    "answer": "Our return window is 30 days.",
                    "final_answer": "Our return window is 30 days.",
                    "trace": {
                        "trace_id": "trace-001",
                        "latency_ms": 25,
                        "guardrail_status": "allowed",
                        "model": "gpt-4.1",
                        "token_usage": {
                            "input_tokens": 20,
                            "output_tokens": 10,
                            "total_tokens": 30,
                            "estimated_total_cost_usd": 0.001,
                        },
                        "tools_used": ["search_company_documents"],
                        "tool_calls": [
                            {"name": "search_company_documents"}
                        ],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    score, score_path = score_result_file(result_path)
    persistence.complete_case(
        run_id,
        case_result_id,
        result_path=result_path,
        score_path=score_path,
        score=score,
    )

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    report_path = tmp_path / "report.md"
    report_path.write_text("# Report", encoding="utf-8")
    persistence.finalize_run(
        run_id,
        summary={
            "attempted": 1,
            "completed": 1,
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "pass_rate_percent": 100,
            "average_score_percent": 100,
            "known_actual_cost_usd": 0.001,
            "average_agent_latency_ms": 25,
            "minimum_agent_latency_ms": 25,
            "maximum_agent_latency_ms": 25,
            "p95_agent_latency_ms": 25,
            "total_input_tokens": 20,
            "total_output_tokens": 10,
            "total_tokens": 30,
        },
        manifest_path=manifest_path,
        report_path=report_path,
    )

    with session_factory() as session:
        run = session.get(EvaluationRun, run_id)
        case_result = session.get(EvaluationCaseResult, case_result_id)
        artifacts = session.query(EvaluationArtifact).all()

        assert run is not None
        assert run.status == "completed"
        assert run.suite_version
        assert run.passed_case_count == 1
        assert float(run.actual_cost_usd) == 0.001
        assert run.total_tokens == 30

        assert case_result is not None
        assert case_result.status == "completed"
        assert case_result.passed is True
        assert case_result.case_version
        assert case_result.tools_used == ["search_company_documents"]
        assert case_result.raw_result_uri == str(result_path)

        assert {artifact.artifact_type for artifact in artifacts} == {
            "raw_result",
            "score",
            "manifest",
            "report",
        }
        assert all(artifact.checksum_sha256 for artifact in artifacts)
