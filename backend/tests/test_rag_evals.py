import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import EvaluationArtifact, EvaluationCaseResult, EvaluationRun
from app.rag.passage_ids import stable_passage_key
from evals.build_rag_qrels import contains_term
from evals.load_rag_cases import find_rag_case, load_rag_cases
from evals.load_rag_qrels import load_rag_qrels, qrels_for_case
from evals.rag_persistence import RagEvaluationPersistence
from evals.run_rag import (
    execute_rag_batch,
    execute_rag_comparison,
    run_rag_case,
    select_rag_cases,
)
from evals.score_rag import score_rag_result


def retrieval_match(
    *,
    chunk_id: str = "chunk-1",
    title: str = "Return and Refund Policy 2026",
    source_path: str = "app/knowledge/return_and_refund_policy_2026.pdf",
    content: str = "The standard return window is 30 calendar days.",
    passage_key: str | None = None,
) -> dict:
    return {
        "document_id": "document-1",
        "chunk_id": chunk_id,
        "passage_key": passage_key or qrels_for_case("retrieval-return-window-001")[0].passage_key,
        "title": title,
        "content": content,
        "score": 0.91,
        "source_type": "pdf",
        "source_path": source_path,
        "department": "Customer Support",
        "version": "2026",
        "chunk_index": 0,
    }


def test_load_rag_cases() -> None:
    cases = load_rag_cases()

    assert len(cases) >= 64
    assert len({case.id for case in cases}) == len(cases)
    categories = {case.category for case in cases}
    assert len(categories) >= 10
    assert "multi_source_retrieval" in categories
    assert {
        "paraphrase_conversational",
        "paraphrase_implicit",
        "paraphrase_noisy",
    }.issubset(categories)
    assert find_rag_case("retrieval-return-window-001").top_k == 5
    styles = [case.query_style for case in cases]
    assert styles.count("direct") == 19
    assert len(styles) - styles.count("direct") == 45


def test_load_rag_qrels_covers_every_case() -> None:
    cases = load_rag_cases()
    qrels = load_rag_qrels()
    cases_by_id = {case.id: case for case in cases}

    assert len(qrels) >= len(cases)
    assert {qrel.case_id for qrel in qrels} == {case.id for case in cases}
    assert all(qrel.relevance in {1, 2} for qrel in qrels)
    assert all(qrel.chunk_text.strip() for qrel in qrels)
    for qrel in qrels:
        source = qrel.passage_key.split(":", maxsplit=1)[0]
        assert source in cases_by_id[qrel.case_id].expected_sources


def test_qrel_term_matching_does_not_match_inside_words() -> None:
    assert contains_term("No purchase order may be raised.", "may") is True
    assert contains_term("CUSTOMER OPERATIONS\nMANAGER", "customer operations manager") is True
    assert contains_term("Supplier payment records are retained.", "may") is False
    assert contains_term("Onboarding is not complete.", "not") is True
    assert contains_term("The annotation is complete.", "not") is False


def test_reviewed_qrel_overrides_exclude_false_onboarding_passages() -> None:
    for case_id in (
        "retrieval-supplier-onboarding-001",
        "paraphrase-noisy-onboarding-001",
    ):
        qrels = qrels_for_case(case_id)

        assert len(qrels) == 1
        assert "No purchase order may be raised" in qrels[0].chunk_text


def test_reviewed_multi_policy_qrels_are_partial_relevance() -> None:
    qrels = qrels_for_case("retrieval-multi-policy-customer-delay-001")

    assert len(qrels) == 2
    assert {qrel.relevance for qrel in qrels} == {1}


def test_full_relevance_qrels_have_term_evidence_or_reviewed_override() -> None:
    cases = {case.id: case for case in load_rag_cases()}
    reviewed_exceptions = {
        (
            "retrieval-promotion-readiness-001",
            "pricing_discount_and_promotion_policy:2026.1:b1740322f5c51bf67363d38d",
        ),
        (
            "paraphrase-noisy-promotion-001",
            "pricing_discount_and_promotion_policy:2026.1:b1740322f5c51bf67363d38d",
        ),
    }
    observed_exceptions: set[tuple[str, str]] = set()

    for qrel in load_rag_qrels():
        if qrel.relevance != 2:
            continue
        case = cases[qrel.case_id]
        has_all_term_groups = all(
            any(contains_term(qrel.chunk_text, term) for term in alternatives)
            for alternatives in case.expected_content_term_groups
        )
        if not has_all_term_groups:
            observed_exceptions.add((qrel.case_id, qrel.passage_key))

    assert observed_exceptions == reviewed_exceptions


def test_rag_qrel_chunk_text_matches_its_stable_passage_key() -> None:
    for qrel in load_rag_qrels():
        source, version, _ = qrel.passage_key.rsplit(":", maxsplit=2)
        expected_key = stable_passage_key(
            source_path=source,
            title=source,
            version=version,
            content=qrel.chunk_text,
        )

        assert qrel.passage_key == expected_key


def test_select_rag_cases_by_category_and_limit() -> None:
    selected = select_rag_cases(
        load_rag_cases(),
        categories=["inventory_retrieval"],
        limit=2,
    )

    assert len(selected) == 2
    assert all(case.category == "inventory_retrieval" for case in selected)


def test_rag_score_passes_for_expected_source_terms_and_rank() -> None:
    case = find_rag_case("retrieval-return-window-001")
    result = {
        "response": {"matches": [retrieval_match()]},
        "run": {"elapsed_ms": 25},
    }

    score = score_rag_result(case, result)

    assert score.passed is True
    assert score.score_percent == 100
    assert score.metrics.hit_at_k is True
    assert score.metrics.hit_at_1 is True
    assert score.metrics.hit_at_3 is True
    assert score.metrics.precision_at_k_percent == 100
    assert score.metrics.passage_recall_percent > 0
    assert score.metrics.source_recall_percent == 100
    assert score.metrics.retrieval_f1_percent == 100
    assert score.metrics.reciprocal_rank == 1.0
    assert score.metrics.mean_average_precision == 1.0
    assert score.metrics.ndcg_at_k == 1.0
    assert score.metrics.unique_chunk_ratio_percent == 100
    assert score.metrics.redundancy_percent == 0
    assert score.metrics.mean_similarity_score == 0.91
    assert score.metrics.content_term_recall_percent == 100
    assert score.metrics.metrics_by_k["1"].hit is True
    assert score.metrics.metrics_by_k["5"].source_recall_percent == 100


def test_rag_score_detects_wrong_source_and_duplicate_chunks() -> None:
    case = find_rag_case("retrieval-return-window-001")
    wrong_match = retrieval_match(
        title="Product Quality and Recall Policy",
        source_path="app/knowledge/product_quality_and_recall_policy.pdf",
        passage_key="wrong-passage",
    )
    result = {
        "response": {"matches": [wrong_match, wrong_match]},
        "run": {"elapsed_ms": 25},
    }

    score = score_rag_result(case, result)

    assert score.passed is False
    assert score.metrics.hit_at_k is False
    assert score.metrics.duplicate_chunk_count == 1
    assert next(check for check in score.checks if check.name == "expected_sources").passed is False
    assert next(check for check in score.checks if check.name == "unique_chunks").passed is False


def rag_api(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/health":
        return httpx.Response(200, json={"status": "ok"})
    if request.url.path == "/documents/search":
        payload = json.loads(request.content)
        assert request.headers["cache-control"] == "no-store, no-cache, max-age=0"
        assert request.headers["pragma"] == "no-cache"
        assert payload["top_k"] in {1, 10}
        assert payload["retrieval_mode"] in {"keyword", "vector", "hybrid"}
        assert payload["use_embedding_cache"] is False
        assert payload["embedding_model"] in {
            "BAAI/bge-small-en-v1.5",
            "text-embedding-3-small",
        }
        return httpx.Response(
            200,
            headers={
                "Cache-Control": "no-store, no-cache, max-age=0, must-revalidate",
                "Pragma": "no-cache",
            },
            json={
                "query": payload["query"],
                "retrieval_mode": payload["retrieval_mode"],
                "embedding_cache_policy": (
                    "not_applicable"
                    if payload["retrieval_mode"] == "keyword"
                    else "bypassed"
                ),
                "matches": [retrieval_match()],
            },
        )
    return httpx.Response(404)


def test_run_rag_case_captures_retrieval_result(tmp_path) -> None:
    case = find_rag_case("retrieval-return-window-001")
    result_path = run_rag_case(
        case,
        "http://benchmark.test",
        results_dir=tmp_path,
        transport=httpx.MockTransport(rag_api),
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["case"]["id"] == case.id
    assert result["request"] == {
        "query": case.query,
        "top_k": 10,
        "retrieval_mode": "hybrid",
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "use_embedding_cache": False,
    }
    assert result["response"]["matches"][0]["chunk_id"] == "chunk-1"
    assert result["run"]["http_status"] == 200
    assert result["run"]["cache_policy"] == {
        "http_request": "no-store",
        "http_response": "no-store, no-cache, max-age=0, must-revalidate",
        "query_embedding": "bypassed",
        "saved_result_reused": False,
        "warmup_request": False,
    }


def test_run_rag_case_refuses_cache_enabled_response(tmp_path) -> None:
    def cached_api(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Cache-Control": "no-store"},
            json={
                "query": "cached",
                "retrieval_mode": "hybrid",
                "embedding_cache_policy": "enabled",
                "matches": [retrieval_match()],
            },
        )

    with pytest.raises(RuntimeError, match="cache-enabled response"):
        run_rag_case(
            find_rag_case("retrieval-return-window-001"),
            "http://benchmark.test",
            results_dir=tmp_path,
            transport=httpx.MockTransport(cached_api),
        )

    assert list(tmp_path.glob("*.json")) == []


def test_execute_rag_batch_writes_metrics_and_report(tmp_path) -> None:
    case = find_rag_case("retrieval-return-window-001")
    manifest_path, report_path = execute_rag_batch(
        [case],
        api_base="http://benchmark.test",
        results_dir=tmp_path / "cases",
        batch_results_dir=tmp_path / "batches",
        transport=httpx.MockTransport(rag_api),
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert manifest["benchmark_type"] == "rag_retrieval"
    assert manifest["summary"]["passed"] == 1
    assert manifest["summary"]["hit_at_k_percent"] == 100
    assert manifest["summary"]["hit_at_1_percent"] == 100
    assert manifest["summary"]["mean_ndcg_at_k"] == 1
    assert manifest["summary"]["retrieval_mode"] == "hybrid"
    assert manifest["summary"]["query_embedding_cache"] == "bypassed"
    assert manifest["summary"]["saved_result_reuse"] is False
    assert manifest["summary"]["warmup_request"] is False
    assert manifest["summary"]["metrics_by_k"]["1"]["hit_percent"] == 100
    assert manifest["summary"]["metrics_by_k"]["5"]["mean_passage_recall_percent"] > 0
    assert manifest["summary"]["quality_gate_status"] == "PASS"
    assert manifest["summary"]["generation_evaluation"]["faithfulness"] == ("not_measured")
    assert manifest["categories"][0]["category"] == "policy_retrieval"
    assert manifest["categories"][0]["hit_at_k_percent"] == 100
    assert manifest["summary"]["mean_reciprocal_rank"] == 1.0
    assert Path(manifest["runs"][0]["result_path"]).exists()
    assert Path(manifest["runs"][0]["score_path"]).exists()
    assert "# ProductAI RAG Evaluation" in report
    assert "## Category slices" in report
    assert "## Failure diagnostics" in report
    assert "### Retrieval depth" in report
    assert "retrieval-return-window-001" in report


def test_rag_batch_persists_production_metrics(tmp_path) -> None:
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
    persistence = RagEvaluationPersistence(session_factory)
    case = find_rag_case("retrieval-return-window-001")

    execute_rag_batch(
        [case],
        api_base="http://benchmark.test",
        results_dir=tmp_path / "cases",
        batch_results_dir=tmp_path / "batches",
        transport=httpx.MockTransport(rag_api),
        persistence=persistence,
        persistence_context={"environment": "test"},
    )

    with session_factory() as session:
        run = session.query(EvaluationRun).one()
        case_result = session.query(EvaluationCaseResult).one()
        assert run.suite_name == "productai-rag-evals"
        assert run.model == "BAAI/bge-small-en-v1.5"
        assert run.model_provider == "baai"
        assert run.status == "completed"
        assert run.run_metadata["rag_metrics"]["mean_ndcg_at_k"] == 1
        assert case_result.result_metadata["rag_metrics"]["hit_at_1"] is True


def test_rag_comparison_runs_all_retrieval_modes(tmp_path) -> None:
    case = find_rag_case("retrieval-return-window-001")
    manifest_path, report_path = execute_rag_comparison(
        [case],
        api_base="http://benchmark.test",
        comparison_results_dir=tmp_path / "comparisons",
        transport=httpx.MockTransport(rag_api),
    )
    comparison = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert comparison["benchmark_type"] == "rag_retrieval_comparison"
    assert comparison["retrieval_modes"] == ["keyword", "vector", "hybrid"]
    assert comparison["query_embedding_cache"] == "bypassed"
    assert comparison["saved_result_reuse"] is False
    assert comparison["warmup_request"] is False
    assert [run["retrieval_mode"] for run in comparison["runs"]] == [
        "keyword",
        "vector",
        "hybrid",
    ]
    assert all(
        run["summary"]["metrics_by_k"]["5"]["hit_percent"] == 100 for run in comparison["runs"]
    )
    assert "# ProductAI Retrieval Mode Comparison" in report
    assert "| hybrid |" in report
