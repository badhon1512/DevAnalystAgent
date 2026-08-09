import argparse
import json
from pathlib import Path

from app.rag.embeddings import DEFAULT_EMBEDDING_MODEL, EMBEDDING_PROFILES
from evals.load_cases import load_cases
from evals.load_rag_cases import find_rag_case, load_rag_cases
from evals.models import EvalOptions
from evals.persistence import EvaluationPersistence
from evals.rag_persistence import RagEvaluationPersistence
from evals.report_batch import write_batch_report
from evals.run_batch import estimate_batch_cost, execute_batch, select_cases
from evals.run_case import DEFAULT_API_BASE, find_case, run_case
from evals.run_rag import (
    execute_rag_batch,
    execute_rag_comparison,
    run_rag_case,
    select_rag_cases,
)
from evals.score_rag import score_rag_result_file
from evals.score_result import score_result_file


MODEL_CHOICES = ["gpt-5.4", "gpt-4.1", "gpt-5.4-nano"]
DEPTH_CHOICES = ["quick", "balanced", "deep"]
DETAIL_CHOICES = ["concise", "balanced", "detailed"]
RETRIEVAL_MODE_CHOICES = ["keyword", "vector", "hybrid"]
EMBEDDING_MODEL_CHOICES = list(EMBEDDING_PROFILES)


def add_embedding_model_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--embedding-model",
        choices=EMBEDDING_MODEL_CHOICES,
        default=DEFAULT_EMBEDDING_MODEL,
    )


def add_execution_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--model", choices=MODEL_CHOICES, default="gpt-5.4")
    parser.add_argument(
        "--analysis-depth",
        choices=DEPTH_CHOICES,
        default="balanced",
    )
    parser.add_argument(
        "--answer-detail",
        choices=DETAIL_CHOICES,
        default="balanced",
    )


def options_from_args(args: argparse.Namespace) -> EvalOptions:
    return EvalOptions(
        model=args.model,
        analysis_depth=args.analysis_depth,
        answer_detail=args.answer_detail,
    )


def print_result_summary(result_path: Path) -> None:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    trace = result["response"]["trace"]
    print(f"Answer: {result['response']['answer']}")
    print(f"Tools used: {', '.join(trace['tools_used']) or 'none'}")
    print(f"Agent latency: {trace['latency_ms']} ms")
    print(f"Saved raw result: {result_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evals",
        description="Run and inspect ProductAI agent evaluations.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List validated cases.")
    list_parser.add_argument("--category")

    run_parser = subparsers.add_parser("run", help="Execute one case.")
    run_parser.add_argument("case_id")
    add_execution_options(run_parser)

    score_parser = subparsers.add_parser("score", help="Score one raw result.")
    score_parser.add_argument("result_path", type=Path)

    batch_parser = subparsers.add_parser(
        "batch",
        help="Preview or execute a selected batch.",
    )
    batch_parser.add_argument("--category", action="append", dest="categories")
    batch_parser.add_argument("--case-id", action="append", dest="case_ids")
    batch_parser.add_argument("--limit", type=int)
    batch_parser.add_argument("--execute", action="store_true")
    batch_parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not save this run to the evaluation history tables.",
    )
    batch_parser.add_argument("--fail-fast", action="store_true")
    batch_parser.add_argument("--budget-usd", type=float, default=1.0)
    batch_parser.add_argument("--estimated-cost-per-case", type=float, default=0.10)
    add_execution_options(batch_parser)

    report_parser = subparsers.add_parser(
        "report",
        help="Regenerate Markdown from a batch manifest.",
    )
    report_parser.add_argument("manifest_path", type=Path)

    rag_parser = subparsers.add_parser(
        "rag",
        help="Run retrieval-only RAG evaluations.",
    )
    rag_subparsers = rag_parser.add_subparsers(dest="rag_command", required=True)

    rag_list_parser = rag_subparsers.add_parser("list", help="List RAG cases.")
    rag_list_parser.add_argument("--category")

    rag_run_parser = rag_subparsers.add_parser("run", help="Run one RAG case.")
    rag_run_parser.add_argument("case_id")
    rag_run_parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    rag_run_parser.add_argument(
        "--retrieval-mode",
        choices=RETRIEVAL_MODE_CHOICES,
        default="hybrid",
    )
    add_embedding_model_option(rag_run_parser)

    rag_score_parser = rag_subparsers.add_parser(
        "score",
        help="Score a saved RAG result.",
    )
    rag_score_parser.add_argument("result_path", type=Path)

    rag_batch_parser = rag_subparsers.add_parser(
        "batch",
        help="Preview or execute a RAG batch.",
    )
    rag_batch_parser.add_argument("--category", action="append", dest="categories")
    rag_batch_parser.add_argument("--case-id", action="append", dest="case_ids")
    rag_batch_parser.add_argument("--limit", type=int)
    rag_batch_parser.add_argument("--execute", action="store_true")
    rag_batch_parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Do not save this RAG run to the evaluation history tables.",
    )
    rag_batch_parser.add_argument("--fail-fast", action="store_true")
    rag_batch_parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    rag_batch_parser.add_argument(
        "--retrieval-mode",
        choices=RETRIEVAL_MODE_CHOICES,
        default="hybrid",
    )
    add_embedding_model_option(rag_batch_parser)

    rag_compare_parser = rag_subparsers.add_parser(
        "compare",
        help="Compare keyword, vector, and hybrid retrieval.",
    )
    rag_compare_parser.add_argument(
        "--category",
        action="append",
        dest="categories",
    )
    rag_compare_parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
    )
    rag_compare_parser.add_argument("--limit", type=int)
    rag_compare_parser.add_argument("--execute", action="store_true")
    rag_compare_parser.add_argument("--no-persist", action="store_true")
    rag_compare_parser.add_argument("--fail-fast", action="store_true")
    rag_compare_parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    add_embedding_model_option(rag_compare_parser)
    return parser


def validate_batch_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.budget_usd <= 0:
        parser.error("--budget-usd must be greater than 0")
    if args.estimated_cost_per_case <= 0:
        parser.error("--estimated-cost-per-case must be greater than 0")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "rag":
        if args.rag_command == "list":
            cases = load_rag_cases()
            if args.category:
                cases = [case for case in cases if case.category == args.category]
            print(f"Loaded {len(cases)} RAG case(s).")
            for case in cases:
                print(f"- [{case.id}] {case.category}: {case.query}")
            return

        if args.rag_command == "run":
            case = find_rag_case(args.case_id)
            result_path = run_rag_case(
                case,
                args.api_base,
                retrieval_mode=args.retrieval_mode,
                embedding_model=args.embedding_model,
            )
            score, score_path = score_rag_result_file(result_path)
            print(f"Case: {case.id}")
            print(f"Score: {score.score_percent}%")
            print(f"Hit@K: {'yes' if score.metrics.hit_at_k else 'no'}")
            print(f"MRR: {score.metrics.reciprocal_rank:.4f}")
            print(f"Latency: {score.metrics.latency_ms} ms")
            print(f"Saved raw result: {result_path}")
            print(f"Saved score: {score_path}")
            return

        if args.rag_command == "score":
            score, score_path = score_rag_result_file(args.result_path)
            for check in score.checks:
                print(f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
            print(f"Score: {score.score_percent}%")
            print(f"Saved score: {score_path}")
            return

        if args.limit is not None and args.limit < 1:
            parser.error("--limit must be at least 1")
        try:
            selected = select_rag_cases(
                load_rag_cases(),
                categories=args.categories,
                case_ids=args.case_ids,
                limit=args.limit,
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(f"Selected {len(selected)} RAG case(s):")
        for case in selected:
            print(f"- [{case.id}] {case.category}: {case.query}")
        if not selected:
            return
        if not args.execute:
            print("Preview only. Add --execute to query the retrieval API.")
            return
        run_options = {
            "api_base": args.api_base,
            "fail_fast": args.fail_fast,
            "embedding_model": args.embedding_model,
            "persistence": (
                None if args.no_persist else RagEvaluationPersistence()
            ),
            "selection_filters": {
                "categories": args.categories or [],
                "case_ids": args.case_ids or [],
                "limit": args.limit,
                "embedding_model": args.embedding_model,
            },
        }
        if args.rag_command == "compare":
            manifest_path, report_path = execute_rag_comparison(
                selected,
                **run_options,
            )
            print(f"Saved comparison manifest: {manifest_path}")
            print(f"Saved comparison report: {report_path}")
            return

        manifest_path, report_path = execute_rag_batch(
            selected,
            retrieval_mode=args.retrieval_mode,
            **run_options,
        )
        print(f"Saved RAG manifest: {manifest_path}")
        print(f"Saved RAG report: {report_path}")
        return

    if args.command == "list":
        cases = load_cases()
        if args.category:
            cases = [case for case in cases if case.category == args.category]
        print(f"Loaded {len(cases)} case(s).")
        for case in cases:
            print(f"- [{case.id}] {case.category}: {case.query}")
        return

    if args.command == "run":
        case = find_case(args.case_id)
        print(f"Running [{case.id}] {case.query}")
        print_result_summary(
            run_case(case, args.api_base, options_from_args(args))
        )
        return

    if args.command == "score":
        score, score_path = score_result_file(args.result_path)
        for check in score.checks:
            print(f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
        print(f"Score: {score.score_percent}%")
        print(f"Overall: {'PASS' if score.passed else 'FAIL'}")
        print(f"Saved score: {score_path}")
        return

    if args.command == "report":
        print(f"Saved readable report: {write_batch_report(args.manifest_path)}")
        return

    validate_batch_args(parser, args)
    try:
        selected = select_cases(
            load_cases(),
            categories=args.categories,
            case_ids=args.case_ids,
            limit=args.limit,
        )
    except ValueError as exc:
        parser.error(str(exc))

    estimated_cost = estimate_batch_cost(
        len(selected),
        args.estimated_cost_per_case,
    )
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

    try:
        manifest_path, report_path = execute_batch(
            selected,
            api_base=args.api_base,
            options=options_from_args(args),
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
