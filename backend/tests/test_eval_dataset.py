import json
from pathlib import Path


def test_rag_eval_dataset_has_30_to_50_labeled_cases():
    path = Path(__file__).parents[2] / "evals" / "rag_eval.jsonl"
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert 30 <= len(cases) <= 50
    required = {"query", "expected_skill", "expected_document", "expected_sections", "should_refuse"}
    assert all(required <= set(case) for case in cases)
    assert any(case["should_refuse"] for case in cases)
    assert any(not case["should_refuse"] for case in cases)
