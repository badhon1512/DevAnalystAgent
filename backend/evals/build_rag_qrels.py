import argparse
import json
import re
from pathlib import Path

from app.db.models import Document, DocumentChunk
from app.db.session import SessionLocal
from app.rag.passage_ids import normalize_source_identifier, stable_passage_key
from evals.load_rag_cases import load_rag_cases
from evals.load_rag_qrels import RAG_QRELS_PATH


PASSAGE_OVERRIDES: dict[str, dict[str, set[int]]] = {
    "retrieval-return-window-001": {
        "return_and_refund_policy_2026": {1},
    },
    "retrieval-transfer-and-replenishment-001": {
        "branch_operations_and_stock_transfer_manual": {1},
        "supplier_replenishment_and_lead_time_policy": {7},
    },
    "retrieval-multi-policy-customer-delay-001": {
        "order_fulfillment_and_customer_promise_policy": {3},
        "customer_service_return_exceptions_policy": {3},
    },
    "retrieval-promotion-readiness-001": {
        "pricing_discount_and_promotion_policy": {3, 4},
    },
    "paraphrase-noisy-promotion-001": {
        "pricing_discount_and_promotion_policy": {3, 4},
    },
}

RELEVANCE_OVERRIDES: dict[str, dict[str, dict[int, int]]] = {
    "retrieval-multi-policy-customer-delay-001": {
        "order_fulfillment_and_customer_promise_policy": {3: 1},
        "customer_service_return_exceptions_policy": {3: 1},
    },
    "retrieval-promotion-readiness-001": {
        "pricing_discount_and_promotion_policy": {3: 2, 4: 2},
    },
    "paraphrase-noisy-promotion-001": {
        "pricing_discount_and_promotion_policy": {3: 2, 4: 2},
    },
}


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def contains_term(content: str, term: str) -> bool:
    normalized_content = normalize_text(content)
    normalized_term = normalize_text(term)
    pattern = rf"(?<!\w){re.escape(normalized_term)}(?!\w)"
    return re.search(pattern, normalized_content) is not None


def source_matches(expected_source: str, document: Document) -> bool:
    actual = normalize_source_identifier(document.source_path, document.title)
    expected = normalize_source_identifier(expected_source, expected_source)
    return expected == actual


def matched_group_count(content: str, groups: list[list[str]]) -> int:
    return sum(
        any(contains_term(content, term) for term in alternatives) for alternatives in groups
    )


def build_qrels() -> list[dict]:
    qrels: list[dict] = []
    with SessionLocal() as db:
        rows = (
            db.query(Document, DocumentChunk)
            .join(DocumentChunk, DocumentChunk.document_id == Document.document_id)
            .order_by(Document.title, DocumentChunk.chunk_index)
            .all()
        )
        for case in load_rag_cases():
            for expected_source in case.expected_sources:
                candidates = [
                    (document, chunk)
                    for document, chunk in rows
                    if source_matches(expected_source, document)
                ]
                if not candidates:
                    raise ValueError(f"No indexed chunks found for {case.id}: {expected_source}")
                override_indices = PASSAGE_OVERRIDES.get(case.id, {}).get(expected_source)
                if override_indices is not None:
                    candidates = [
                        (document, chunk)
                        for document, chunk in candidates
                        if chunk.chunk_index in override_indices
                    ]
                    if len(candidates) != len(override_indices):
                        raise ValueError(f"Stale passage override for {case.id}: {expected_source}")
                scored = [
                    (
                        matched_group_count(
                            chunk.content,
                            case.expected_content_term_groups,
                        ),
                        document,
                        chunk,
                    )
                    for document, chunk in candidates
                ]
                best_coverage = max(score for score, _, _ in scored)
                if case.expected_content_term_groups and best_coverage == 0:
                    raise ValueError(f"No answer-bearing passage found for {case.id}")
                for coverage, document, chunk in scored:
                    if override_indices is None and coverage != best_coverage:
                        continue
                    relevance_override = (
                        RELEVANCE_OVERRIDES.get(case.id, {})
                        .get(expected_source, {})
                        .get(chunk.chunk_index)
                    )
                    qrels.append(
                        {
                            "case_id": case.id,
                            "passage_key": stable_passage_key(
                                source_path=document.source_path,
                                title=document.title,
                                version=document.version,
                                content=chunk.content,
                            ),
                            "chunk_text": chunk.content,
                            "relevance": relevance_override
                            or (2 if coverage == len(case.expected_content_term_groups) else 1),
                        }
                    )
    return qrels


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build passage qrels from the versioned evaluation corpus."
    )
    parser.add_argument("--output", type=Path, default=RAG_QRELS_PATH)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        parser.error(f"{args.output} already exists; use --force to replace it")

    qrels = build_qrels()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(qrel, separators=(",", ":")) + "\n" for qrel in qrels),
        encoding="utf-8",
    )
    print(f"Wrote {len(qrels)} passage judgments to {args.output}")


if __name__ == "__main__":
    main()
