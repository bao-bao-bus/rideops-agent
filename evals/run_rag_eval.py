import argparse
import json
from pathlib import Path

from rideops.api.app import router, rag_service


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def first_relevant_rank(evidence: list[dict], expected_document: str | None, expected_sections: list[str]) -> int | None:
    for index, item in enumerate(evidence, start=1):
        document_match = expected_document is None or item["document_id"] == expected_document
        section_match = not expected_sections or item["section"] in expected_sections
        if document_match and section_match:
            return index
    return None


def evaluate(cases: list[dict], min_score: float = 0.18) -> dict[str, float | int]:
    retrieval_cases = [case for case in cases if not case["should_refuse"]]
    hit_counts = {1: 0, 3: 0, 5: 0}
    reciprocal_ranks: list[float] = []
    refusal_correct = 0
    routing_correct = 0
    for case in cases:
        result = rag_service.query(case["query"], top_k=5, min_score=min_score)
        evidence = [item.model_dump() for item in result.evidence]
        rank = first_relevant_rank(evidence, case["expected_document"], case["expected_sections"])
        if case["should_refuse"]:
            refusal_correct += int(not result.answerable)
        else:
            for k in hit_counts:
                hit_counts[k] += int(rank is not None and rank <= k)
            reciprocal_ranks.append(1 / rank if rank else 0.0)
            refusal_correct += int(result.answerable)
        routed = router.route(case["query"]).skill
        routed_name = routed.name if routed else None
        routing_correct += int(routed_name == case["expected_skill"])
    total_retrieval = len(retrieval_cases)
    return {
        "retrieval_version": "bm25+mock-vector+rrf",
        "case_count": len(cases),
        "retrieval_case_count": total_retrieval,
        "hit_at_1": round(hit_counts[1] / total_retrieval, 4),
        "hit_at_3": round(hit_counts[3] / total_retrieval, 4),
        "hit_at_5": round(hit_counts[5] / total_retrieval, 4),
        "mrr": round(sum(reciprocal_ranks) / total_retrieval, 4),
        "refusal_accuracy": round(refusal_correct / len(cases), 4),
        "skill_routing_accuracy": round(routing_correct / len(cases), 4),
        "min_score": min_score,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Mock RAG baseline evaluation.")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name("rag_eval.jsonl"))
    parser.add_argument("--min-score", type=float, default=0.18)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(load_cases(args.dataset), min_score=args.min_score)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
