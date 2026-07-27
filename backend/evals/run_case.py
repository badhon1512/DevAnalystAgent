import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

from app.schemas.chat import ChatResponse
from evals.load_cases import load_cases
from evals.models import BenchmarkCase, EvalOptions


DEFAULT_API_BASE = os.getenv("EVAL_API_BASE", "http://127.0.0.1:8000")
RESULTS_DIR = Path(__file__).with_name("results")


def check_api_health(
    api_base: str = DEFAULT_API_BASE,
    *,
    transport: httpx.BaseTransport | None = None,
    timeout_seconds: float = 10.0,
) -> dict:
    with httpx.Client(timeout=timeout_seconds, transport=transport) as client:
        response = client.get(f"{api_base.rstrip('/')}/health")
        response.raise_for_status()
        return response.json()


def find_case(case_id: str) -> BenchmarkCase:
    for case in load_cases():
        if case.id == case_id:
            return case
    raise ValueError(f"Unknown benchmark case: {case_id}")


def build_chat_payload(case: BenchmarkCase, options: EvalOptions | None = None) -> dict:
    selected_options = options or EvalOptions()
    return {
        "query": case.query,
        "conversation_id": "",
        "username": "benchmark_runner",
        "options": selected_options.model_dump(),
    }


def run_case(
    case: BenchmarkCase,
    api_base: str = DEFAULT_API_BASE,
    options: EvalOptions | None = None,
    *,
    results_dir: Path = RESULTS_DIR,
    transport: httpx.BaseTransport | None = None,
    timeout_seconds: float = 120.0,
) -> Path:
    payload = build_chat_payload(case, options)
    run_id = str(uuid4())
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()

    with httpx.Client(timeout=timeout_seconds, transport=transport) as client:
        response = client.post(f"{api_base.rstrip('/')}/chat", json=payload)
        response.raise_for_status()

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    response_data = ChatResponse.model_validate(response.json()).model_dump(mode="json")
    finished_at = datetime.now(timezone.utc)
    result = {
        "case": case.model_dump(),
        "request": payload,
        "response": response_data,
        "run": {
            "run_id": run_id,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "elapsed_ms": elapsed_ms,
            "api_base": api_base,
            "http_status": response.status_code,
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one ProductAI benchmark case.")
    parser.add_argument("case_id", help="Case ID from evals/cases.jsonl")
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
    args = parser.parse_args()

    case = find_case(args.case_id)
    print(f"Running [{case.id}] {case.query}")
    options = EvalOptions(
        model=args.model,
        analysis_depth=args.analysis_depth,
        answer_detail=args.answer_detail,
    )
    result_path = run_case(case, args.api_base, options)

    result = json.loads(result_path.read_text(encoding="utf-8"))
    trace = result["response"]["trace"]
    print(f"Answer: {result['response']['answer']}")
    print(f"Tools used: {', '.join(trace['tools_used']) or 'none'}")
    print(f"Agent latency: {trace['latency_ms']} ms")
    print(f"Saved raw result: {result_path}")


if __name__ == "__main__":
    main()
