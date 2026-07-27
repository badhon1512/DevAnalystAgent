import argparse
import json
import math
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import httpx

from evals.load_cases import load_cases
from evals.models import BenchmarkCase, EvalOptions
from evals.persistence import EvaluationPersistence
from evals.report_batch import write_batch_report
from evals.run_case import (
    DEFAULT_API_BASE,
    RESULTS_DIR,
    check_api_health,
    run_case,
)
from evals.score_result import score_result_file


BATCH_RESULTS_DIR = Path(__file__).with_name("results") / "batches"


def select_cases(
    cases: list[BenchmarkCase],
    categories: list[str] | None = None,
    case_ids: list[str] | None = None,
    limit: int | None = None,
) -> list[BenchmarkCase]:
    selected = cases

    if categories:
        category_set = set(categories)
        selected = [case for case in selected if case.category in category_set]

    if case_ids:
        case_id_set = set(case_ids)
        selected = [case for case in selected if case.id in case_id_set]
        missing_ids = sorted(case_id_set - {case.id for case in selected})
        if missing_ids:
            raise ValueError(f"Unknown benchmark case IDs: {', '.join(missing_ids)}")

    if limit is not None:
        selected = selected[:limit]

    return selected


def estimate_batch_cost(case_count: int, estimated_cost_per_case: float) -> float:
    return round(case_count * estimated_cost_per_case, 6)


def read_result_metrics(result_path: Path) -> dict:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    trace = result["response"]["trace"]
    cost = trace.get("token_usage", {}).get("estimated_total_cost_usd")
    return {
        "answer": result["response"]["answer"],
        "final_answer": result["response"].get("final_answer"),
        "cost_usd": float(cost) if cost is not None else None,
        "agent_latency_ms": trace["latency_ms"],
        "tool_count": len(trace["tool_calls"]),
        "tools_used": trace["tools_used"],
        "trace_id": trace.get("trace_id"),
        "guardrail_status": trace.get("guardrail_status"),
        "model": trace.get("model"),
        "input_tokens": trace.get("token_usage", {}).get("input_tokens", 0),
        "output_tokens": trace.get("token_usage", {}).get("output_tokens", 0),
        "total_tokens": trace.get("token_usage", {}).get("total_tokens", 0),
    }


def percentile_95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def build_batch_configuration(
    *,
    api_base: str,
    options: EvalOptions,
    budget_usd: float,
    estimated_cost_per_case: float,
    fail_fast: bool,
) -> dict:
    return {
        "api_base": api_base,
        **options.model_dump(),
        "budget_usd": budget_usd,
        "estimated_cost_per_case": estimated_cost_per_case,
        "estimated_batch_cost_usd": None,
        "fail_fast": fail_fast,
    }


def execute_batch(
    cases: list[BenchmarkCase],
    *,
    api_base: str,
    options: EvalOptions,
    budget_usd: float,
    estimated_cost_per_case: float,
    fail_fast: bool = False,
    results_dir: Path = RESULTS_DIR,
    batch_results_dir: Path = BATCH_RESULTS_DIR,
    transport: httpx.BaseTransport | None = None,
    persistence: EvaluationPersistence | None = None,
    persistence_context: dict | None = None,
    selection_filters: dict | None = None,
    existing_database_run_id: UUID | None = None,
) -> tuple[Path, Path]:
    estimated_cost = estimate_batch_cost(len(cases), estimated_cost_per_case)
    if estimated_cost > budget_usd:
        raise ValueError(
            f"Estimated batch cost ${estimated_cost:.4f} exceeds budget ${budget_usd:.4f}"
        )

    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    runs: list[dict] = []
    configuration = build_batch_configuration(
        api_base=api_base,
        options=options,
        budget_usd=budget_usd,
        estimated_cost_per_case=estimated_cost_per_case,
        fail_fast=fail_fast,
    )
    configuration["estimated_batch_cost_usd"] = estimated_cost
    database_run_id = existing_database_run_id

    if persistence:
        if database_run_id is None:
            database_run_id = persistence.create_run(
                cases,
                options,
                estimated_cost_usd=estimated_cost,
                configuration=configuration,
                selection_filters=selection_filters,
                context=persistence_context,
            )
        persistence.mark_run_running(database_run_id)

    try:
        check_api_health(api_base, transport=transport)
    except Exception as exc:
        if persistence and database_run_id:
            persistence.fail_run(database_run_id, exc)
        raise

    for sequence_number, case in enumerate(cases, start=1):
        stage = "execute"
        case_result_id = None
        try:
            if persistence and database_run_id:
                stage = "persist_start"
                case_result_id = persistence.start_case(
                    database_run_id,
                    case,
                    sequence_number=sequence_number,
                )
                stage = "execute"
            result_path = run_case(
                case,
                api_base,
                options,
                results_dir=results_dir,
                transport=transport,
            )
            stage = "score"
            score, score_path = score_result_file(result_path)
            metrics = read_result_metrics(result_path)
            if persistence and database_run_id and case_result_id:
                stage = "persist_result"
                persistence.complete_case(
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
                    "query": case.query,
                    "status": "completed",
                    "passed": score.passed,
                    "score_percent": score.score_percent,
                    **metrics,
                    "result_path": str(result_path),
                    "score_path": str(score_path),
                }
            )
        except Exception as exc:
            if persistence and case_result_id:
                try:
                    persistence.fail_case(
                        case_result_id,
                        stage=stage,
                        error=exc,
                    )
                except Exception:
                    pass
            runs.append(
                {
                    "case_id": case.id,
                    "category": case.category,
                    "query": case.query,
                    "status": "error",
                    "stage": stage,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            if fail_fast:
                break

    finished_at = datetime.now(timezone.utc)
    completed = [run for run in runs if run["status"] == "completed"]
    scores = [run["score_percent"] for run in completed]
    costs = [run["cost_usd"] for run in completed if run["cost_usd"] is not None]
    latencies = [run["agent_latency_ms"] for run in completed]
    input_tokens = sum(run["input_tokens"] for run in completed)
    output_tokens = sum(run["output_tokens"] for run in completed)
    total_tokens = sum(run["total_tokens"] for run in completed)
    passed = sum(bool(run["passed"]) for run in completed)

    manifest = {
        "schema_version": 1,
        "database_run_id": str(database_run_id) if database_run_id else None,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "configuration": configuration,
        "summary": {
            "selected": len(cases),
            "attempted": len(runs),
            "completed": len(completed),
            "errors": len(runs) - len(completed),
            "passed": passed,
            "failed": len(completed) - passed,
            "pass_rate_percent": round(passed / len(completed) * 100, 2) if completed else 0,
            "average_score_percent": round(sum(scores) / len(scores), 2) if scores else 0,
            "average_agent_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
            "minimum_agent_latency_ms": min(latencies) if latencies else 0,
            "maximum_agent_latency_ms": max(latencies) if latencies else 0,
            "p95_agent_latency_ms": percentile_95(latencies),
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "known_actual_cost_usd": round(sum(costs), 8),
            "duration_ms": int((time.perf_counter() - started) * 1000),
        },
        "runs": runs,
    }

    batch_results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    manifest_path = batch_results_dir / f"batch-{timestamp}.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path = write_batch_report(manifest_path)
    if persistence and database_run_id:
        try:
            persistence.finalize_run(
                database_run_id,
                summary=manifest["summary"],
                manifest_path=manifest_path,
                report_path=report_path,
            )
        except Exception as exc:
            persistence.fail_run(database_run_id, exc)
            raise
    return manifest_path, report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or execute ProductAI benchmark cases.")
    parser.add_argument("--category", action="append", dest="categories")
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument(
        "--model",
        choices=["gpt-5.4", "gpt-4.1", "gpt-5.4-nano"],
        default="gpt-5.4",
    )
    parser.add_argument(
        "--analysis-depth",
        choices=["quick", "balanced", "deep"],
        default="balanced",
    )
    parser.add_argument(
        "--answer-detail",
        choices=["concise", "balanced", "detailed"],
        default="balanced",
    )
    parser.add_argument("--budget-usd", type=float, default=1.0)
    parser.add_argument("--estimated-cost-per-case", type=float, default=0.10)
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.budget_usd <= 0:
        parser.error("--budget-usd must be greater than 0")
    if args.estimated_cost_per_case <= 0:
        parser.error("--estimated-cost-per-case must be greater than 0")

    try:
        selected = select_cases(
            load_cases(),
            categories=args.categories,
            case_ids=args.case_ids,
            limit=args.limit,
        )
    except ValueError as exc:
        parser.error(str(exc))

    estimated_cost = estimate_batch_cost(len(selected), args.estimated_cost_per_case)
    print(f"Selected {len(selected)} case(s):")
    for case in selected:
        print(f"- [{case.id}] {case.category}: {case.query}")
    print(f"Estimated cost: ${estimated_cost:.4f}")
    print(f"Budget: ${args.budget_usd:.4f}")

    if not selected:
        print("No cases matched the filters.")
        return
    if not args.execute:
        print("Preview only. Add --execute to make API calls.")
        return

    options = EvalOptions(
        model=args.model,
        analysis_depth=args.analysis_depth,
        answer_detail=args.answer_detail,
    )
    try:
        manifest_path, report_path = execute_batch(
            selected,
            api_base=args.api_base,
            options=options,
            budget_usd=args.budget_usd,
            estimated_cost_per_case=args.estimated_cost_per_case,
            fail_fast=args.fail_fast,
            persistence=(
                None if args.no_persist else EvaluationPersistence()
            ),
            selection_filters={
                "categories": args.categories,
                "case_ids": args.case_ids,
                "limit": args.limit,
            },
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(f"Saved batch manifest: {manifest_path}")
    print(f"Saved readable report: {report_path}")


if __name__ == "__main__":
    main()
