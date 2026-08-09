import json
import math
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import httpx

from app.schemas.document import DocumentSearchResponse
from app.rag.embeddings import DEFAULT_EMBEDDING_MODEL, get_embedding_profile
from app.rag.retriever import RetrievalMode
from evals.models import RagBenchmarkCase
from evals.rag_persistence import RagEvaluationPersistence
from evals.run_case import DEFAULT_API_BASE, check_api_health
from evals.score_rag import score_rag_result_file


RAG_RESULTS_DIR = Path(__file__).with_name("results") / "rag"
RAG_BATCH_RESULTS_DIR = RAG_RESULTS_DIR / "batches"
RAG_COMPARISON_RESULTS_DIR = RAG_RESULTS_DIR / "comparisons"
RAG_EVALUATION_TOP_K = 10
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, max-age=0",
    "Pragma": "no-cache",
}
RETRIEVAL_MODES: tuple[RetrievalMode, ...] = (
    "keyword",
    "vector",
    "hybrid",
)


def select_rag_cases(
    cases: list[RagBenchmarkCase],
    *,
    categories: list[str] | None = None,
    case_ids: list[str] | None = None,
    limit: int | None = None,
) -> list[RagBenchmarkCase]:
    selected = cases
    if categories:
        category_set = set(categories)
        selected = [case for case in selected if case.category in category_set]
    if case_ids:
        case_id_set = set(case_ids)
        selected = [case for case in selected if case.id in case_id_set]
        missing_ids = sorted(case_id_set - {case.id for case in selected})
        if missing_ids:
            raise ValueError(f"Unknown RAG benchmark case IDs: {', '.join(missing_ids)}")
    if limit is not None:
        selected = selected[:limit]
    return selected


def run_rag_case(
    case: RagBenchmarkCase,
    api_base: str = DEFAULT_API_BASE,
    *,
    results_dir: Path = RAG_RESULTS_DIR,
    transport: httpx.BaseTransport | None = None,
    timeout_seconds: float = 30.0,
    retrieval_mode: RetrievalMode = "hybrid",
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    evaluation_top_k: int = RAG_EVALUATION_TOP_K,
) -> Path:
    payload = {
        "query": case.query,
        "top_k": min(12, max(case.top_k, evaluation_top_k)),
        "retrieval_mode": retrieval_mode,
        "embedding_model": get_embedding_profile(embedding_model).model,
        "use_embedding_cache": False,
    }
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    with httpx.Client(timeout=timeout_seconds, transport=transport) as client:
        response = client.post(
            f"{api_base.rstrip('/')}/documents/search",
            json=payload,
            headers=NO_CACHE_HEADERS,
        )
        response.raise_for_status()
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response_data = DocumentSearchResponse.model_validate(response.json()).model_dump(mode="json")
    expected_embedding_policy = (
        "not_applicable" if retrieval_mode == "keyword" else "bypassed"
    )
    if response_data["embedding_cache_policy"] != expected_embedding_policy:
        raise RuntimeError(
            "RAG evaluation refused a cache-enabled response: expected "
            f"{expected_embedding_policy}, received "
            f"{response_data['embedding_cache_policy']}."
        )
    response_cache_control = response.headers.get("cache-control", "")
    if "no-store" not in response_cache_control.lower():
        raise RuntimeError(
            "RAG evaluation refused a response without Cache-Control: no-store."
        )
    result = {
        "schema_version": 1,
        "case": case.model_dump(),
        "request": payload,
        "response": response_data,
        "run": {
            "run_id": str(uuid4()),
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": elapsed_ms,
            "api_base": api_base,
            "http_status": response.status_code,
            "cache_policy": {
                "http_request": "no-store",
                "http_response": response_cache_control,
                "query_embedding": response_data["embedding_cache_policy"],
                "saved_result_reused": False,
                "warmup_request": False,
            },
        },
    }
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    result_path = results_dir / f"{case.id}-{timestamp}.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result_path


def percentile(values: list[int], percentile_value: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile_value) - 1)]


def _write_markdown_report(manifest: dict, report_path: Path) -> None:
    summary = manifest["summary"]
    lines = [
        "# ProductAI RAG Evaluation",
        "",
        "## Production scorecard",
        "",
        "### Run health",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| Selected cases | {summary['selected']} |",
        f"| Completed | {summary['completed']} |",
        f"| Errors | {summary['errors']} |",
        f"| Error-free execution | {summary['error_free_rate_percent']}% |",
        f"| Pass rate | {summary['pass_rate_percent']}% |",
        f"| Retrieval mode | {summary['retrieval_mode']} |",
        f"| Embedding model | {summary['embedding_model']} |",
        f"| Embedding provider | {summary['embedding_provider']} |",
        f"| Embedding dimensions | {summary['embedding_dimensions']} |",
        f"| Query embedding cache | {summary['query_embedding_cache']} |",
        f"| Saved result reuse | {summary['saved_result_reuse']} |",
        f"| Warm-up request | {summary['warmup_request']} |",
        f"| Quality gate | {summary['quality_gate_status']} |",
        "",
        "### Retrieval and ranking",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| Hit@1 | {summary['hit_at_1_percent']}% |",
        f"| Hit@3 | {summary['hit_at_3_percent']}% |",
        f"| Hit@K | {summary['hit_at_k_percent']}% |",
        f"| Precision@K | {summary['mean_precision_at_k_percent']}% |",
        f"| Passage Recall@K | {summary['mean_passage_recall_percent']}% |",
        f"| Source Recall@K | {summary['mean_source_recall_percent']}% |",
        f"| Retrieval F1 | {summary['mean_retrieval_f1_percent']}% |",
        f"| MRR | {summary['mean_reciprocal_rank']:.4f} |",
        f"| MAP@K | {summary['mean_average_precision']:.4f} |",
        f"| nDCG@K | {summary['mean_ndcg_at_k']:.4f} |",
        "",
        "### Context quality",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| Content concept recall | {summary['mean_content_term_recall_percent']}% |",
        f"| Unique chunk ratio | {summary['mean_unique_chunk_ratio_percent']}% |",
        f"| Redundancy | {summary['mean_redundancy_percent']}% |",
        f"| Mean similarity | {summary['mean_similarity_score']:.4f} |",
        f"| Mean context size | {summary['mean_context_character_count']} characters |",
        "",
        "### Runtime reliability",
        "",
        "| Metric | Result |",
        "| --- | ---: |",
        f"| Average latency | {summary['average_latency_ms']} ms |",
        f"| P50 latency | {summary['p50_latency_ms']} ms |",
        f"| P95 latency | {summary['p95_latency_ms']} ms |",
        f"| P99 latency | {summary['p99_latency_ms']} ms |",
        f"| Throughput | {summary['throughput_cases_per_second']} cases/s |",
        "",
        "### Retrieval depth",
        "",
        "| K | Hit@K | Precision@K | Recall@K | F1@K | MRR | MAP@K | nDCG@K |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for k, metrics in summary["metrics_by_k"].items():
        lines.append(
            f"| {k} | {metrics['hit_percent']}% | "
            f"{metrics['mean_precision_percent']}% | "
            f"{metrics['mean_passage_recall_percent']}% | "
            f"{metrics['mean_retrieval_f1_percent']}% | "
            f"{metrics['mean_reciprocal_rank']:.4f} | "
            f"{metrics['mean_average_precision']:.4f} | "
            f"{metrics['mean_ndcg']:.4f} |"
        )
    lines.extend(
        [
            "",
            "### Answer-generation coverage",
            "",
            "| Metric | Status |",
            "| --- | --- |",
            "| Faithfulness / groundedness | Not measured by retrieval-only suite |",
            "| Answer relevance | Not measured by retrieval-only suite |",
            "| Citation precision and recall | Not measured by retrieval-only suite |",
            "| Abstention accuracy | Requires unanswerable-query cases |",
            "",
            "## Cases",
            "",
            "| Case | Category | Status | Score | Hit@K | P@K | nDCG | MRR | Latency |",
            "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for run in manifest["runs"]:
        if run["status"] == "completed":
            lines.append(
                f"| `{run['case_id']}` | {run['category']} | "
                f"{'PASS' if run['passed'] else 'FAIL'} | "
                f"{run['score_percent']}% | "
                f"{'yes' if run['hit_at_k'] else 'no'} | "
                f"{run['precision_at_k_percent']:.1f}% | "
                f"{run['ndcg_at_k']:.4f} | "
                f"{run['reciprocal_rank']:.4f} | {run['latency_ms']} ms |"
            )
        else:
            lines.append(
                f"| `{run['case_id']}` | {run['category']} | " "ERROR | - | - | - | - | - | - |"
            )
    lines.extend(
        [
            "",
            "## Category slices",
            "",
            "| Category | Cases | Pass rate | Hit@K | Passage Recall@K | Source Recall@K | MRR | P95 latency |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for category in manifest.get("categories", []):
        lines.append(
            f"| {category['category']} | {category['completed']} | "
            f"{category['pass_rate_percent']}% | "
            f"{category['hit_at_k_percent']}% | "
            f"{category['mean_passage_recall_percent']}% | "
            f"{category['mean_source_recall_percent']}% | "
            f"{category['mean_reciprocal_rank']:.4f} | "
            f"{category['p95_latency_ms']} ms |"
        )

    failed_runs = [
        run for run in manifest["runs"] if run["status"] == "error" or not run.get("passed", False)
    ]
    lines.extend(["", "## Failure diagnostics", ""])
    if not failed_runs:
        lines.append("No failed or errored cases.")
    for run in failed_runs:
        lines.append(f"### {run['case_id']}")
        if run["status"] == "error":
            lines.append(f"- Execution error: {run.get('error', 'Unknown error')}")
        else:
            for check in run.get("failed_checks", []):
                lines.append(f"- `{check['name']}`: {check['detail']}")
        lines.append("")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_comparison_report(comparison: dict, report_path: Path) -> None:
    lines = [
        "# ProductAI Retrieval Mode Comparison",
        "",
        "The same cases were run against keyword, vector, and hybrid retrieval.",
        "",
        "## Overall comparison",
        "",
        "| Mode | Pass | Hit@1 | Hit@3 | Hit@5 | Recall@5 | Precision@5 | nDCG@5 | MRR | P50 | P95 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in comparison["runs"]:
        summary = run["summary"]
        at_five = summary["metrics_by_k"]["5"]
        lines.append(
            f"| {run['retrieval_mode']} | {summary['pass_rate_percent']}% | "
            f"{summary['metrics_by_k']['1']['hit_percent']}% | "
            f"{summary['metrics_by_k']['3']['hit_percent']}% | "
            f"{at_five['hit_percent']}% | "
            f"{at_five['mean_passage_recall_percent']}% | "
            f"{at_five['mean_precision_percent']}% | "
            f"{at_five['mean_ndcg']:.4f} | "
            f"{at_five['mean_reciprocal_rank']:.4f} | "
            f"{summary['p50_latency_ms']} ms | {summary['p95_latency_ms']} ms |"
        )

    lines.extend(
        [
            "",
            "## K-depth curves",
            "",
            "| Mode | K | Hit@K | Precision@K | Recall@K | F1@K | MAP@K | nDCG@K |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for run in comparison["runs"]:
        for k, metrics in run["summary"]["metrics_by_k"].items():
            lines.append(
                f"| {run['retrieval_mode']} | {k} | {metrics['hit_percent']}% | "
                f"{metrics['mean_precision_percent']}% | "
                f"{metrics['mean_passage_recall_percent']}% | "
                f"{metrics['mean_retrieval_f1_percent']}% | "
                f"{metrics['mean_average_precision']:.4f} | "
                f"{metrics['mean_ndcg']:.4f} |"
            )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def execute_rag_batch(
    cases: list[RagBenchmarkCase],
    *,
    api_base: str = DEFAULT_API_BASE,
    results_dir: Path = RAG_RESULTS_DIR,
    batch_results_dir: Path = RAG_BATCH_RESULTS_DIR,
    transport: httpx.BaseTransport | None = None,
    fail_fast: bool = False,
    retrieval_mode: RetrievalMode = "hybrid",
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    persistence: RagEvaluationPersistence | None = None,
    persistence_context: dict | None = None,
    selection_filters: dict | None = None,
    existing_database_run_id: UUID | None = None,
) -> tuple[Path, Path]:
    embedding_profile = get_embedding_profile(embedding_model)
    check_api_health(api_base, transport=transport)
    started_at = datetime.now(timezone.utc)
    runs: list[dict] = []
    database_run_id = existing_database_run_id
    if persistence is not None:
        if database_run_id is None:
            database_run_id = persistence.create_rag_run(
                cases,
                configuration={
                    "api_base": api_base,
                    "embedding_model": embedding_profile.model,
                    "embedding_provider": embedding_profile.provider,
                    "embedding_dimensions": embedding_profile.dimensions,
                    "retrieval_mode": retrieval_mode,
                    "query_embedding_cache": "bypassed",
                    "saved_result_reuse": False,
                    "warmup_request": False,
                    "quality_gates": "production-defaults-v1",
                },
                selection_filters=selection_filters,
                context=persistence_context,
            )
        persistence.mark_run_running(database_run_id)

    for sequence_number, case in enumerate(cases, start=1):
        case_result_id = None
        try:
            if persistence is not None and database_run_id is not None:
                case_result_id = persistence.start_rag_case(
                    database_run_id,
                    case,
                    sequence_number=sequence_number,
                )
            result_path = run_rag_case(
                case,
                api_base,
                results_dir=results_dir,
                transport=transport,
                retrieval_mode=retrieval_mode,
                embedding_model=embedding_profile.model,
            )
            score, score_path = score_rag_result_file(result_path)
            if (
                persistence is not None
                and database_run_id is not None
                and case_result_id is not None
            ):
                persistence.complete_rag_case(
                    database_run_id,
                    case_result_id,
                    result_path=result_path,
                    score_path=score_path,
                    score=score,
                )
            runs.append(
                {
                    "case_id": case.id,
                    "category": case.category,
                    "query_style": case.query_style,
                    "query": case.query,
                    "status": "completed",
                    "passed": score.passed,
                    "score_percent": score.score_percent,
                    "failed_checks": [
                        check.model_dump() for check in score.checks if not check.passed
                    ],
                    **score.metrics.model_dump(),
                    "result_path": str(result_path),
                    "score_path": str(score_path),
                }
            )
        except Exception as exc:
            if persistence is not None and case_result_id is not None:
                persistence.fail_case(
                    case_result_id,
                    stage="rag_retrieval_or_scoring",
                    error=exc,
                )
            runs.append(
                {
                    "case_id": case.id,
                    "category": case.category,
                    "query_style": case.query_style,
                    "query": case.query,
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            if fail_fast:
                break

    completed = [run for run in runs if run["status"] == "completed"]
    passed = sum(bool(run["passed"]) for run in completed)
    latencies = [int(run["latency_ms"]) for run in completed]

    def mean(key: str, *, digits: int = 2) -> float:
        values = [float(run[key]) for run in completed]
        return round(sum(values) / len(values), digits) if values else 0.0

    finished_at = datetime.now(timezone.utc)
    elapsed_seconds = max((finished_at - started_at).total_seconds(), 0.001)
    error_count = len(runs) - len(completed)
    summary = {
        "retrieval_mode": retrieval_mode,
        "embedding_model": embedding_profile.model,
        "embedding_provider": embedding_profile.provider,
        "embedding_dimensions": embedding_profile.dimensions,
        "query_embedding_cache": "bypassed",
        "saved_result_reuse": False,
        "warmup_request": False,
        "selected": len(cases),
        "completed": len(completed),
        "errors": error_count,
        "passed": passed,
        "failed": len(completed) - passed,
        "pass_rate_percent": round(passed / len(completed) * 100, 2) if completed else 0,
        "error_free_rate_percent": round(
            (len(cases) - error_count) / len(cases) * 100,
            2,
        )
        if cases
        else 100,
        "hit_at_1_percent": round(
            sum(bool(run["hit_at_1"]) for run in completed) / len(completed) * 100,
            2,
        )
        if completed
        else 0,
        "hit_at_3_percent": round(
            sum(bool(run["hit_at_3"]) for run in completed) / len(completed) * 100,
            2,
        )
        if completed
        else 0,
        "hit_at_k_percent": round(
            sum(bool(run["hit_at_k"]) for run in completed) / len(completed) * 100,
            2,
        )
        if completed
        else 0,
        "mean_precision_at_k_percent": mean("precision_at_k_percent"),
        "mean_passage_recall_percent": mean("passage_recall_percent"),
        "mean_source_recall_percent": mean("source_recall_percent"),
        "mean_retrieval_f1_percent": mean("retrieval_f1_percent"),
        "mean_reciprocal_rank": mean("reciprocal_rank", digits=4),
        "mean_average_precision": mean("mean_average_precision", digits=4),
        "mean_ndcg_at_k": mean("ndcg_at_k", digits=4),
        "mean_content_term_recall_percent": mean("content_term_recall_percent"),
        "mean_unique_chunk_ratio_percent": mean("unique_chunk_ratio_percent"),
        "mean_redundancy_percent": mean("redundancy_percent"),
        "mean_similarity_score": mean("mean_similarity_score", digits=4),
        "mean_context_character_count": round(mean("context_character_count")),
        "average_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "minimum_latency_ms": min(latencies) if latencies else 0,
        "maximum_latency_ms": max(latencies) if latencies else 0,
        "p50_latency_ms": percentile(latencies, 0.50),
        "p95_latency_ms": percentile(latencies, 0.95),
        "p99_latency_ms": percentile(latencies, 0.99),
        "throughput_cases_per_second": round(len(completed) / elapsed_seconds, 2),
        "generation_evaluation": {
            "faithfulness": "not_measured",
            "answer_relevance": "not_measured",
            "citation_precision": "not_measured",
            "citation_recall": "not_measured",
            "abstention_accuracy": "not_measured",
        },
    }
    metrics_by_k: dict[str, dict] = {}
    for k in (1, 2, 3, 4, 5, 10):
        key = str(k)
        available = [run["metrics_by_k"][key] for run in completed]

        def k_mean(metric: str, *, digits: int = 2) -> float:
            values = [float(item[metric]) for item in available]
            return round(sum(values) / len(values), digits) if values else 0.0

        metrics_by_k[key] = {
            "hit_percent": round(
                sum(bool(item["hit"]) for item in available) / len(available) * 100,
                2,
            )
            if available
            else 0.0,
            "mean_precision_percent": k_mean("precision_percent"),
            "mean_passage_recall_percent": k_mean("passage_recall_percent"),
            "mean_source_recall_percent": k_mean("source_recall_percent"),
            "mean_retrieval_f1_percent": k_mean("retrieval_f1_percent"),
            "mean_reciprocal_rank": k_mean("reciprocal_rank", digits=4),
            "mean_average_precision": k_mean("average_precision", digits=4),
            "mean_ndcg": k_mean("ndcg", digits=4),
            "mean_content_term_recall_percent": k_mean("content_term_recall_percent"),
            "mean_context_character_count": round(k_mean("context_character_count")),
        }
    summary["metrics_by_k"] = metrics_by_k
    gates = {
        "error_free": summary["error_free_rate_percent"] == 100,
        "case_pass_rate": summary["pass_rate_percent"] >= 90,
        "hit_at_1": summary["hit_at_1_percent"] >= 80,
        "hit_at_k": summary["hit_at_k_percent"] >= 95,
        "precision_at_k": summary["mean_precision_at_k_percent"] >= 50,
        "passage_recall": summary["mean_passage_recall_percent"] >= 80,
        "source_recall": summary["mean_source_recall_percent"] >= 95,
        "retrieval_f1": summary["mean_retrieval_f1_percent"] >= 65,
        "mrr": summary["mean_reciprocal_rank"] >= 0.8,
        "ndcg": summary["mean_ndcg_at_k"] >= 0.85,
        "content_recall": summary["mean_content_term_recall_percent"] >= 90,
        "unique_chunks": summary["mean_unique_chunk_ratio_percent"] >= 95,
        "p95_latency": summary["p95_latency_ms"] <= 3000,
        "p99_latency": summary["p99_latency_ms"] <= 5000,
    }
    summary["quality_gates"] = gates
    summary["quality_gate_status"] = "PASS" if all(gates.values()) else "FAIL"

    category_summaries = []
    for category in sorted({run["category"] for run in completed}):
        category_runs = [run for run in completed if run["category"] == category]
        category_latencies = [int(run["latency_ms"]) for run in category_runs]

        def category_mean(key: str, *, digits: int = 2) -> float:
            values = [float(run[key]) for run in category_runs]
            return round(sum(values) / len(values), digits) if values else 0.0

        category_passed = sum(bool(run["passed"]) for run in category_runs)
        category_summaries.append(
            {
                "category": category,
                "completed": len(category_runs),
                "passed": category_passed,
                "pass_rate_percent": round(
                    category_passed / len(category_runs) * 100,
                    2,
                ),
                "hit_at_k_percent": round(
                    sum(bool(run["hit_at_k"]) for run in category_runs) / len(category_runs) * 100,
                    2,
                ),
                "mean_source_recall_percent": category_mean("source_recall_percent"),
                "mean_passage_recall_percent": category_mean("passage_recall_percent"),
                "mean_reciprocal_rank": category_mean(
                    "reciprocal_rank",
                    digits=4,
                ),
                "mean_ndcg_at_k": category_mean("ndcg_at_k", digits=4),
                "p95_latency_ms": percentile(category_latencies, 0.95),
            }
        )

    manifest = {
        "schema_version": 1,
        "benchmark_type": "rag_retrieval",
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "configuration": {
            "api_base": api_base,
            "retrieval_mode": retrieval_mode,
            "embedding_model": embedding_profile.model,
            "embedding_provider": embedding_profile.provider,
            "embedding_dimensions": embedding_profile.dimensions,
            "evaluation_top_k": RAG_EVALUATION_TOP_K,
            "warmup_requests": 0,
        },
        "summary": summary,
        "categories": category_summaries,
        "runs": runs,
    }
    batch_results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    manifest_path = batch_results_dir / f"rag-batch-{timestamp}.json"
    report_path = manifest_path.with_suffix(".md")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_markdown_report(manifest, report_path)
    if persistence is not None and database_run_id is not None:
        persistence.finalize_rag_run(
            database_run_id,
            summary=summary,
            manifest_path=manifest_path,
            report_path=report_path,
        )
    return manifest_path, report_path


def execute_rag_comparison(
    cases: list[RagBenchmarkCase],
    *,
    api_base: str = DEFAULT_API_BASE,
    comparison_results_dir: Path = RAG_COMPARISON_RESULTS_DIR,
    transport: httpx.BaseTransport | None = None,
    fail_fast: bool = False,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    persistence: RagEvaluationPersistence | None = None,
    persistence_context: dict | None = None,
    selection_filters: dict | None = None,
) -> tuple[Path, Path]:
    started_at = datetime.now(timezone.utc)
    comparison_id = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    workspace = comparison_results_dir / comparison_id
    runs = []

    for retrieval_mode in RETRIEVAL_MODES:
        manifest_path, report_path = execute_rag_batch(
            cases,
            api_base=api_base,
            results_dir=workspace / retrieval_mode / "cases",
            batch_results_dir=workspace / retrieval_mode / "batches",
            transport=transport,
            fail_fast=fail_fast,
            retrieval_mode=retrieval_mode,
            embedding_model=embedding_model,
            persistence=persistence,
            persistence_context=persistence_context,
            selection_filters={
                **(selection_filters or {}),
                "retrieval_mode": retrieval_mode,
                "comparison_id": comparison_id,
            },
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        runs.append(
            {
                "retrieval_mode": retrieval_mode,
                "manifest_path": str(manifest_path),
                "report_path": str(report_path),
                "summary": manifest["summary"],
            }
        )

    comparison = {
        "schema_version": 1,
        "benchmark_type": "rag_retrieval_comparison",
        "comparison_id": comparison_id,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "selected_case_count": len(cases),
        "retrieval_modes": list(RETRIEVAL_MODES),
        "embedding_model": get_embedding_profile(embedding_model).model,
        "query_embedding_cache": "bypassed",
        "saved_result_reuse": False,
        "warmup_request": False,
        "runs": runs,
    }
    workspace.mkdir(parents=True, exist_ok=True)
    manifest_path = workspace / "comparison.json"
    report_path = workspace / "comparison.md"
    manifest_path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_comparison_report(comparison, report_path)
    return manifest_path, report_path
