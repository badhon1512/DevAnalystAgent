import json
import math
import re
from pathlib import Path

from evals.models import (
    CheckResult,
    RagAtKMetrics,
    RagBenchmarkCase,
    RagBenchmarkMetrics,
    RagBenchmarkScore,
    RagQrel,
)
from evals.load_rag_qrels import qrels_for_case


RAG_K_VALUES = (1, 2, 3, 4, 5, 10)


def normalize_identifier(value: str) -> str:
    normalized = value.lower().replace("\\", "/")
    normalized = Path(normalized).name
    normalized = re.sub(r"\.(md|txt|pdf)$", "", normalized)
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def match_source(expected_source: str, match: dict) -> bool:
    expected = normalize_identifier(expected_source)
    candidates = [
        normalize_identifier(str(match.get("source_path") or "")),
        normalize_identifier(str(match.get("title") or "")),
    ]
    return any(
        expected and candidate and (expected in candidate or candidate in expected)
        for candidate in candidates
    )


def metrics_at_k(
    case: RagBenchmarkCase,
    matches: list[dict],
    k: int,
    qrels: list[RagQrel],
) -> RagAtKMetrics:
    selected = matches[:k]
    relevance_by_key = {qrel.passage_key: qrel.relevance for qrel in qrels}
    retrieved_keys = [str(match.get("passage_key") or "") for match in selected]
    relevance_grades = [relevance_by_key.get(key, 0) for key in retrieved_keys]
    relevant_count = sum(grade > 0 for grade in relevance_grades)
    found_passages = {key for key in retrieved_keys if relevance_by_key.get(key, 0) > 0}
    precision = relevant_count / len(selected) if selected else 0.0
    passage_recall = len(found_passages) / len(qrels) if qrels else 0.0
    retrieval_f1 = (
        2 * precision * passage_recall / (precision + passage_recall)
        if precision + passage_recall
        else 0.0
    )
    relevant_ranks = [rank for rank, grade in enumerate(relevance_grades, start=1) if grade > 0]
    first_rank = min(relevant_ranks) if relevant_ranks else None

    source_ranks: list[int] = []
    for expected_source in case.expected_sources:
        rank = next(
            (
                index
                for index, match in enumerate(selected, start=1)
                if match_source(expected_source, match)
            ),
            None,
        )
        if rank is not None:
            source_ranks.append(rank)

    precision_sum = 0.0
    relevant_seen = 0
    seen_passages: set[str] = set()
    for rank, key in enumerate(retrieved_keys, start=1):
        if relevance_by_key.get(key, 0) > 0 and key not in seen_passages:
            relevant_seen += 1
            precision_sum += relevant_seen / rank
            seen_passages.add(key)
    average_precision = precision_sum / len(qrels) if qrels else 0.0

    dcg = sum(
        (2**grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(relevance_grades, start=1)
        if grade > 0
    )
    ideal_grades = sorted(
        (qrel.relevance for qrel in qrels),
        reverse=True,
    )[: len(selected)]
    ideal_dcg = sum(
        (2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal_grades, start=1)
    )

    content = normalize_text(" ".join(str(match.get("content") or "") for match in selected))
    matched_term_groups = sum(
        any(normalize_text(term) in content for term in terms)
        for terms in case.expected_content_term_groups
    )
    term_count = len(case.expected_content_term_groups)
    return RagAtKMetrics(
        k=k,
        result_count=len(selected),
        relevant_result_count=relevant_count,
        hit=bool(relevant_ranks),
        precision_percent=round(precision * 100, 2),
        passage_recall_percent=round(passage_recall * 100, 2),
        source_recall_percent=round(
            len(source_ranks) / len(case.expected_sources) * 100,
            2,
        ),
        retrieval_f1_percent=round(retrieval_f1 * 100, 2),
        reciprocal_rank=round(1 / first_rank, 4) if first_rank else 0.0,
        average_precision=round(average_precision, 4),
        ndcg=round(dcg / ideal_dcg, 4) if ideal_dcg else 0.0,
        content_term_recall_percent=(
            round(matched_term_groups / term_count * 100, 2) if term_count else 100.0
        ),
        context_character_count=sum(len(str(match.get("content") or "")) for match in selected),
    )


def score_rag_result(
    case: RagBenchmarkCase,
    result: dict,
    *,
    qrels: list[RagQrel] | None = None,
) -> RagBenchmarkScore:
    resolved_qrels = qrels if qrels is not None else qrels_for_case(case.id)
    if not resolved_qrels:
        raise ValueError(f"No passage qrels found for RAG case: {case.id}")
    response = result.get("response", {})
    retrieval_mode = response.get(
        "retrieval_mode",
        result.get("request", {}).get("retrieval_mode", "vector"),
    )
    all_matches = response.get("matches", [])
    matches = all_matches[: case.top_k]
    latency_ms = max(0, int(result.get("run", {}).get("elapsed_ms", 0)))

    source_ranks: list[int] = []
    missing_sources: list[str] = []
    for expected_source in case.expected_sources:
        rank = next(
            (
                index
                for index, match in enumerate(matches, start=1)
                if match_source(expected_source, match)
            ),
            None,
        )
        if rank is None:
            missing_sources.append(expected_source)
        else:
            source_ranks.append(rank)

    relevance_by_key = {qrel.passage_key: qrel.relevance for qrel in resolved_qrels}
    retrieved_keys = [str(match.get("passage_key") or "") for match in matches]
    relevance_grades = [relevance_by_key.get(key, 0) for key in retrieved_keys]
    relevant_ranks = [rank for rank, grade in enumerate(relevance_grades, start=1) if grade > 0]
    found_passages = {key for key in retrieved_keys if relevance_by_key.get(key, 0) > 0}
    hit_at_k = bool(relevant_ranks)
    hit_at_1 = bool(relevant_ranks and min(relevant_ranks) == 1)
    hit_at_3 = bool(relevant_ranks and min(relevant_ranks) <= 3)
    passage_recall_percent = round(len(found_passages) / len(resolved_qrels) * 100)
    source_recall_percent = round(len(source_ranks) / len(case.expected_sources) * 100)
    first_relevant_rank = min(relevant_ranks) if relevant_ranks else None
    reciprocal_rank = round(1 / first_relevant_rank, 4) if first_relevant_rank else 0.0

    relevant_result_count = sum(grade > 0 for grade in relevance_grades)
    precision_at_k_percent = (
        round(relevant_result_count / len(matches) * 100, 2) if matches else 0.0
    )
    recall_fraction = passage_recall_percent / 100
    precision_fraction = precision_at_k_percent / 100
    retrieval_f1_percent = (
        round(
            2 * precision_fraction * recall_fraction / (precision_fraction + recall_fraction) * 100,
            2,
        )
        if precision_fraction + recall_fraction
        else 0.0
    )

    precision_sum = 0.0
    relevant_seen = 0
    seen_passages: set[str] = set()
    for rank, key in enumerate(retrieved_keys, start=1):
        if relevance_by_key.get(key, 0) > 0 and key not in seen_passages:
            relevant_seen += 1
            precision_sum += relevant_seen / rank
            seen_passages.add(key)
    mean_average_precision = round(
        precision_sum / len(resolved_qrels),
        4,
    )

    dcg = sum(
        (2**grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(relevance_grades, start=1)
        if grade > 0
    )
    ideal_grades = sorted(
        (qrel.relevance for qrel in resolved_qrels),
        reverse=True,
    )[: len(matches)]
    ideal_dcg = sum(
        (2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal_grades, start=1)
    )
    ndcg_at_k = round(dcg / ideal_dcg, 4) if ideal_dcg else 0.0

    retrieved_content = normalize_text(
        " ".join(str(match.get("content") or "") for match in matches)
    )
    missing_term_groups = [
        terms
        for terms in case.expected_content_term_groups
        if not any(normalize_text(term) in retrieved_content for term in terms)
    ]
    term_group_count = len(case.expected_content_term_groups)
    content_term_recall_percent = (
        round((term_group_count - len(missing_term_groups)) / term_group_count * 100)
        if term_group_count
        else 100
    )

    chunk_ids = [str(match.get("chunk_id") or "") for match in matches]
    duplicate_chunk_count = len(chunk_ids) - len(set(chunk_ids))
    redundancy_percent = (
        round(duplicate_chunk_count / len(chunk_ids) * 100, 2) if chunk_ids else 0.0
    )
    unique_chunk_ratio_percent = round(100 - redundancy_percent, 2)
    similarity_scores = [
        float(
            match.get("vector_score")
            if retrieval_mode == "hybrid" and match.get("vector_score") is not None
            else match.get("score") or 0
        )
        for match in matches
    ]
    mean_similarity_score = (
        round(sum(similarity_scores) / len(similarity_scores), 4) if similarity_scores else 0.0
    )
    context_character_count = sum(len(str(match.get("content") or "")) for match in matches)
    enough_matches = len(matches) >= case.minimum_matches
    all_sources_found = not missing_sources
    rank_passed = (
        first_relevant_rank is not None and first_relevant_rank <= case.maximum_relevant_rank
    )
    content_passed = not missing_term_groups
    unique_chunks = duplicate_chunk_count == 0
    latency_passed = latency_ms <= case.maximum_latency_ms

    checks = [
        CheckResult(
            name="minimum_matches",
            passed=enough_matches,
            detail=f"Retrieved {len(matches)} of {case.minimum_matches} required matches.",
        ),
        CheckResult(
            name="expected_sources",
            passed=all_sources_found,
            detail=(
                "All expected sources were retrieved."
                if all_sources_found
                else f"Missing sources: {', '.join(missing_sources)}"
            ),
        ),
        CheckResult(
            name="relevant_rank",
            passed=rank_passed,
            detail=(
                f"First relevant result ranked {first_relevant_rank}; "
                f"required rank <= {case.maximum_relevant_rank}."
                if first_relevant_rank is not None
                else "No relevant source was retrieved."
            ),
        ),
        CheckResult(
            name="content_terms",
            passed=content_passed,
            detail=(
                "All expected content concepts were retrieved."
                if content_passed
                else "Missing concept groups: "
                + "; ".join(" | ".join(group) for group in missing_term_groups)
            ),
        ),
        CheckResult(
            name="unique_chunks",
            passed=unique_chunks,
            detail=f"Found {duplicate_chunk_count} duplicate chunk IDs.",
        ),
        CheckResult(
            name="latency_limit",
            passed=latency_passed,
            detail=f"Retrieval took {latency_ms} ms; limit is {case.maximum_latency_ms} ms.",
        ),
    ]
    passed_count = sum(check.passed for check in checks)
    return RagBenchmarkScore(
        case_id=case.id,
        passed=passed_count == len(checks),
        score_percent=round(passed_count / len(checks) * 100),
        checks=checks,
        metrics=RagBenchmarkMetrics(
            retrieval_mode=retrieval_mode,
            result_count=len(matches),
            relevant_result_count=relevant_result_count,
            hit_at_k=hit_at_k,
            hit_at_1=hit_at_1,
            hit_at_3=hit_at_3,
            precision_at_k_percent=precision_at_k_percent,
            passage_recall_percent=passage_recall_percent,
            source_recall_percent=source_recall_percent,
            retrieval_f1_percent=retrieval_f1_percent,
            reciprocal_rank=reciprocal_rank,
            mean_average_precision=mean_average_precision,
            ndcg_at_k=ndcg_at_k,
            content_term_recall_percent=content_term_recall_percent,
            duplicate_chunk_count=duplicate_chunk_count,
            redundancy_percent=redundancy_percent,
            unique_chunk_ratio_percent=unique_chunk_ratio_percent,
            mean_similarity_score=mean_similarity_score,
            context_character_count=context_character_count,
            latency_ms=latency_ms,
            metrics_by_k={
                str(k): metrics_at_k(case, all_matches, k, resolved_qrels) for k in RAG_K_VALUES
            },
        ),
    )


def score_rag_result_file(result_path: Path) -> tuple[RagBenchmarkScore, Path]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    case = RagBenchmarkCase.model_validate(result["case"])
    score = score_rag_result(case, result)
    score_path = result_path.with_suffix(".score.json")
    score_path.write_text(score.model_dump_json(indent=2), encoding="utf-8")
    return score, score_path
