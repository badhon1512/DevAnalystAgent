import json
from pathlib import Path

import httpx

from evals.load_cases import load_cases
from evals.models import EvalOptions
from evals.report_batch import build_batch_report
from evals.run_batch import estimate_batch_cost, execute_batch, select_cases
from evals.run_case import build_chat_payload, find_case, run_case
from evals.score_result import score_result


KNOWN_AGENT_TOOLS = {
    "datetime_now",
    "tracestock_mcp_status",
    "get_weather_forecast",
    "get_inventory_schema",
    "run_readonly_inventory_sql",
    "researcher_agent",
    "execute_python_code_tool",
    "search_company_documents",
    "save_chart_tool",
    "generate_report_tool",
    "read_file",
    "write_file",
    "list_directory",
}


def test_load_benchmark_cases() -> None:
    cases = load_cases()

    assert len(cases) == 40
    assert len({case.id for case in cases}) == len(cases)
    assert {
        "rag_policy",
        "sql_analytics",
        "combined_sql_rag",
        "research_orchestration",
        "python_analytics",
        "chart_generation",
        "report_generation",
        "guardrail",
    }.issubset({case.category for case in cases})

    return_window_case = next(case for case in cases if case.id == "rag-return-window-001")
    assert return_window_case.expected_tools == ["search_company_documents"]
    assert return_window_case.expected_answer_contains == []
    assert return_window_case.expected_answer_terms == [["30", "days"]]
    assert return_window_case.max_tool_calls == 2


def test_benchmark_tool_expectations_are_consistent() -> None:
    for case in load_cases():
        expected = set(case.expected_tools)
        forbidden = set(case.forbidden_tools)

        assert expected <= KNOWN_AGENT_TOOLS, case.id
        assert forbidden <= KNOWN_AGENT_TOOLS, case.id
        assert expected.isdisjoint(forbidden), case.id
        assert case.max_tool_calls >= len(expected), case.id


def test_select_batch_cases_by_category_and_limit() -> None:
    selected = select_cases(load_cases(), categories=["guardrail"], limit=2)

    assert len(selected) == 2
    assert all(case.category == "guardrail" for case in selected)


def test_estimate_batch_cost() -> None:
    assert estimate_batch_cost(3, 0.10) == 0.30


def test_build_chat_payload_uses_an_isolated_conversation() -> None:
    case = find_case("rag-return-window-001")

    payload = build_chat_payload(case)

    assert payload["query"] == case.query
    assert payload["conversation_id"] == ""
    assert payload["username"] == "benchmark_runner"
    assert payload["options"]["analysis_depth"] == "balanced"


def test_score_accepts_required_terms_without_an_exact_phrase() -> None:
    case = find_case("rag-return-window-001")
    result = {
        "response": {
            "answer": "Our standard return window is 30 days.",
            "trace": {
                "tools_used": ["search_company_documents"],
                "tool_calls": [{"name": "search_company_documents"}],
            },
        }
    }

    score = score_result(case, result)

    assert score.passed is True
    assert score.score_percent == 100
    assert next(check for check in score.checks if check.name == "required_facts").passed is True


def test_score_detects_a_missing_required_term() -> None:
    case = find_case("rag-return-window-001")
    result = {
        "response": {
            "answer": "Please consult the standard return policy.",
            "trace": {
                "tools_used": ["search_company_documents"],
                "tool_calls": [{"name": "search_company_documents"}],
            },
        }
    }

    score = score_result(case, result)

    assert score.passed is False
    assert score.score_percent == 75
    required_facts = next(
        check for check in score.checks if check.name == "required_facts"
    )
    assert required_facts.passed is False
    assert "30, days" in required_facts.detail


def test_term_matching_does_not_accept_part_of_a_larger_number() -> None:
    case = find_case("rag-return-window-001")
    result = {
        "response": {
            "answer": "The return window is 130 days.",
            "trace": {
                "tools_used": ["search_company_documents"],
                "tool_calls": [{"name": "search_company_documents"}],
            },
        }
    }

    assert score_result(case, result).passed is False


def benchmark_api(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/health":
        return httpx.Response(200, json={"status": "ok"})
    if request.url.path == "/chat":
        request_data = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "conversation_id": "benchmark-conversation",
                "answer": "The return window is 30 calendar days from the sale date.",
                "final_answer": "The return window is 30 calendar days from the sale date.",
                "trace": {
                    "trace_id": "trace-001",
                    "conversation_id": "benchmark-conversation",
                    "latency_ms": 25,
                    "guardrail_status": "allowed",
                    "model": request_data["options"]["model"],
                    "token_usage": {
                        "input_tokens": 20,
                        "output_tokens": 10,
                        "total_tokens": 30,
                        "estimated_total_cost_usd": 0.001,
                    },
                    "tools_used": ["search_company_documents"],
                    "tool_calls": [
                        {
                            "name": "search_company_documents",
                            "args": {"query": request_data["query"]},
                            "result": "30 calendar days from the sale date",
                        }
                    ],
                    "message_count": 3,
                },
                "report": None,
            },
        )
    return httpx.Response(404)


def test_run_case_captures_validated_raw_result(tmp_path) -> None:
    case = find_case("rag-return-window-001")
    result_path = run_case(
        case,
        "http://benchmark.test",
        EvalOptions(model="gpt-4.1"),
        results_dir=tmp_path,
        transport=httpx.MockTransport(benchmark_api),
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["case"]["id"] == case.id
    assert result["request"]["options"]["model"] == "gpt-4.1"
    assert result["response"]["trace"]["tools_used"] == [
        "search_company_documents"
    ]
    assert result["run"]["http_status"] == 200
    assert result["run"]["run_id"]


def test_execute_batch_produces_manifest_scores_and_report(tmp_path) -> None:
    case = find_case("rag-return-window-001")
    manifest_path, report_path = execute_batch(
        [case],
        api_base="http://benchmark.test",
        options=EvalOptions(model="gpt-4.1"),
        budget_usd=0.10,
        estimated_cost_per_case=0.05,
        results_dir=tmp_path / "cases",
        batch_results_dir=tmp_path / "batches",
        transport=httpx.MockTransport(benchmark_api),
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8")

    assert manifest["summary"]["completed"] == 1
    assert manifest["summary"]["passed"] == 1
    assert manifest["summary"]["known_actual_cost_usd"] == 0.001
    assert manifest["runs"][0]["answer"].startswith("The return window")
    assert Path(manifest["runs"][0]["result_path"]).exists()
    assert Path(manifest["runs"][0]["score_path"]).exists()
    assert "# ProductAI Benchmark Report" in report
    assert "rag-return-window-001" in report


def test_batch_report_distinguishes_execution_errors() -> None:
    report = build_batch_report(
        {
            "started_at": "2026-01-01T00:00:00+00:00",
            "configuration": {
                "model": "gpt-4.1",
                "analysis_depth": "balanced",
                "answer_detail": "balanced",
            },
            "summary": {
                "pass_rate_percent": 0,
                "average_score_percent": 0,
                "completed": 0,
                "selected": 1,
                "errors": 1,
                "known_actual_cost_usd": 0,
                "average_agent_latency_ms": 0,
            },
            "runs": [
                {
                    "case_id": "broken-case",
                    "category": "guardrail",
                    "status": "error",
                    "stage": "execute",
                    "error_type": "ConnectError",
                    "error": "Connection refused",
                }
            ],
        }
    )

    assert "ERROR (execute)" in report
    assert "ConnectError" in report
