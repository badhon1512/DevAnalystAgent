import json
from pathlib import Path

from evals.models import RagBenchmarkCase


RAG_CASES_PATH = Path(__file__).with_name("rag_cases.jsonl")


def load_rag_cases(path: Path = RAG_CASES_PATH) -> list[RagBenchmarkCase]:
    cases: list[RagBenchmarkCase] = []
    seen_ids: set[str] = set()

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue
        try:
            case = RagBenchmarkCase.model_validate(json.loads(line))
        except Exception as exc:
            raise ValueError(f"Invalid RAG case at line {line_number}: {exc}") from exc
        if case.id in seen_ids:
            raise ValueError(f"Duplicate RAG benchmark case ID: {case.id}")
        if case.maximum_relevant_rank > case.top_k:
            raise ValueError(
                f"RAG case {case.id} has maximum_relevant_rank greater than top_k"
            )
        seen_ids.add(case.id)
        cases.append(case)

    return cases


def find_rag_case(case_id: str, path: Path = RAG_CASES_PATH) -> RagBenchmarkCase:
    for case in load_rag_cases(path):
        if case.id == case_id:
            return case
    raise ValueError(f"Unknown RAG benchmark case: {case_id}")
