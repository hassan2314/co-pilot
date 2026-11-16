import pytest
from evals.retrieval import evaluate


def test_metrics_count_unique_documents_but_keep_chunk_ranks():
    cases = [
        {"query": "one", "relevant_paths": ["a", "b", "a"]},
        {"query": "two", "relevant_paths": ["c"]},
        {"query": "three", "relevant_paths": ["d"]},
    ]
    hits = {"one": [("x",), ("a",), ("a",), ("b",)],
            "two": [("c",)], "three": []}
    report = evaluate(cases, lambda query, k: hits[query], 3)
    assert report["recall_at_k"] == pytest.approx((0.5 + 1 + 0) / 3)
    assert report["mrr_at_k"] == pytest.approx((0.5 + 1 + 0) / 3)
    assert report["results"][0]["retrieved_paths"] == ["x", "a", "a"]


@pytest.mark.parametrize("cases,k", [([], 5), ([{"query": "q", "relevant_paths": []}], 5),
                                    ([{"query": " ", "relevant_paths": ["a"]}], 5),
                                    ([{"query": "q", "relevant_paths": ["a"]}], 0)])
def test_invalid_inputs(cases, k):
    with pytest.raises(ValueError):
        evaluate(cases, lambda *_: [], k)
