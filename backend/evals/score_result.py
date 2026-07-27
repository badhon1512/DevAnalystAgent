import argparse
import json
import re
from pathlib import Path

from evals.models import BenchmarkCase, BenchmarkScore, CheckResult


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def contains_term(text: str, term: str) -> bool:
    normalized_term = normalize_text(term)
    pattern = rf"(?<!\w){re.escape(normalized_term)}(?!\w)"
    return re.search(pattern, text) is not None


def score_result(case: BenchmarkCase, result: dict) -> BenchmarkScore:
    response = result["response"]
    trace = response["trace"]
    answer = normalize_text(response["answer"])
    tools_used = set(trace["tools_used"])
    tool_call_count = len(trace["tool_calls"])

    missing_tools = sorted(set(case.expected_tools) - tools_used)
    expected_tools_passed = not missing_tools

    used_forbidden_tools = sorted(set(case.forbidden_tools) & tools_used)
    forbidden_tools_passed = not used_forbidden_tools

    missing_facts = [
        fact
        for fact in case.expected_answer_contains
        if normalize_text(fact) not in answer
    ]
    missing_term_groups = [
        terms
        for terms in case.expected_answer_terms
        if not all(contains_term(answer, term) for term in terms)
    ]
    required_facts_passed = not missing_facts and not missing_term_groups

    missing_fact_details = [*missing_facts]
    missing_fact_details.extend(
        f"all terms ({', '.join(terms)})" for terms in missing_term_groups
    )

    tool_limit_passed = tool_call_count <= case.max_tool_calls

    checks = [
        CheckResult(
            name="expected_tools",
            passed=expected_tools_passed,
            detail=(
                "All expected tools were used."
                if expected_tools_passed
                else f"Missing tools: {', '.join(missing_tools)}"
            ),
        ),
        CheckResult(
            name="forbidden_tools",
            passed=forbidden_tools_passed,
            detail=(
                "No forbidden tools were used."
                if forbidden_tools_passed
                else f"Forbidden tools used: {', '.join(used_forbidden_tools)}"
            ),
        ),
        CheckResult(
            name="required_facts",
            passed=required_facts_passed,
            detail=(
                "All required facts were present."
                if required_facts_passed
                else f"Missing facts: {', '.join(missing_fact_details)}"
            ),
        ),
        CheckResult(
            name="tool_call_limit",
            passed=tool_limit_passed,
            detail=f"Used {tool_call_count} of {case.max_tool_calls} allowed tool calls.",
        ),
    ]

    passed_count = sum(check.passed for check in checks)
    score_percent = round(passed_count / len(checks) * 100)
    return BenchmarkScore(
        case_id=case.id,
        passed=passed_count == len(checks),
        score_percent=score_percent,
        checks=checks,
    )


def score_result_file(result_path: Path) -> tuple[BenchmarkScore, Path]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    case = BenchmarkCase.model_validate(result["case"])
    score = score_result(case, result)

    score_path = result_path.with_suffix(".score.json")
    score_path.write_text(
        score.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return score, score_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Score one ProductAI benchmark result.")
    parser.add_argument("result_path", type=Path)
    args = parser.parse_args()

    score, score_path = score_result_file(args.result_path)
    print(f"Case: {score.case_id}")
    for check in score.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status} {check.name}: {check.detail}")
    print(f"Score: {score.score_percent}%")
    print(f"Overall: {'PASS' if score.passed else 'FAIL'}")
    print(f"Saved score: {score_path}")


if __name__ == "__main__":
    main()
