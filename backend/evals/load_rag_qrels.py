import json
from collections import defaultdict
from pathlib import Path

from evals.load_rag_cases import RAG_CASES_PATH, load_rag_cases
from evals.models import RagQrel


RAG_QRELS_PATH = Path(__file__).with_name("rag_qrels.jsonl")


def load_rag_qrels(
    path: Path = RAG_QRELS_PATH,
    *,
    cases_path: Path = RAG_CASES_PATH,
) -> list[RagQrel]:
    qrels: list[RagQrel] = []
    seen: set[tuple[str, str]] = set()
    case_ids = {case.id for case in load_rag_cases(cases_path)}

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw_line.strip():
            continue
        try:
            qrel = RagQrel.model_validate(json.loads(raw_line))
        except Exception as exc:
            raise ValueError(f"Invalid RAG qrel at line {line_number}: {exc}") from exc
        if not qrel.chunk_text.strip():
            raise ValueError(f"RAG qrel has empty chunk text at line {line_number}")
        key = (qrel.case_id, qrel.passage_key)
        if key in seen:
            raise ValueError(f"Duplicate RAG qrel for {qrel.case_id}: {qrel.passage_key}")
        if qrel.case_id not in case_ids:
            raise ValueError(f"RAG qrel references unknown case: {qrel.case_id}")
        seen.add(key)
        qrels.append(qrel)

    judged_cases = {qrel.case_id for qrel in qrels}
    missing = sorted(case_ids - judged_cases)
    if missing:
        missing_cases = ", ".join(missing)
        raise ValueError(f"RAG cases without passage qrels: {missing_cases}")
    return qrels


def group_qrels(qrels: list[RagQrel]) -> dict[str, list[RagQrel]]:
    grouped: dict[str, list[RagQrel]] = defaultdict(list)
    for qrel in qrels:
        grouped[qrel.case_id].append(qrel)
    return dict(grouped)


def qrels_for_case(case_id: str) -> list[RagQrel]:
    return group_qrels(load_rag_qrels()).get(case_id, [])
