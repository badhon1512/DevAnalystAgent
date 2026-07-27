from pathlib import Path

from pydantic import ValidationError

from evals.models import BenchmarkCase

CASES_PATH = Path(__file__).with_name("cases.jsonl")


def load_cases(path: Path = CASES_PATH) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []

    with path.open(encoding="utf-8") as case_file:
        for line_number, line in enumerate(case_file, start=1):
            if not line.strip():
                continue

            try:
                cases.append(BenchmarkCase.model_validate_json(line))
            except ValidationError as exc:
                raise ValueError(
                    f"Invalid benchmark case in {path} on line {line_number}"
                ) from exc

    return cases


def main() -> None:
    cases = load_cases()
    print(f"Loaded {len(cases)} benchmark case(s).")

    for case in cases:
        print(f"\n[{case.id}] {case.category}")
        print(f"Query: {case.query}")
        print(f"Expected tools: {', '.join(case.expected_tools) or 'none'}")
        print(f"Forbidden tools: {', '.join(case.forbidden_tools) or 'none'}")
        print(f"Required facts: {', '.join(case.expected_answer_contains) or 'none'}")
        term_groups = [" + ".join(terms) for terms in case.expected_answer_terms]
        print(f"Required term groups: {', '.join(term_groups) or 'none'}")
        print(f"Maximum tool calls: {case.max_tool_calls}")


if __name__ == "__main__":
    main()
