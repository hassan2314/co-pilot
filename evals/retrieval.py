"""Evaluate ranked chunk retrieval against document-level relevance labels."""
import argparse
import json
from pathlib import Path


def evaluate(cases, search, k):
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer")
    if not isinstance(cases, list) or not cases:
        raise ValueError("dataset must be a non-empty list")
    results = []
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each case must be an object")
        query = case.get("query")
        labels = case.get("relevant_paths")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("each case needs a non-empty query")
        if not isinstance(labels, list) or not labels or any(not isinstance(p, str) or not p.strip() for p in labels):
            raise ValueError("each case needs non-empty relevant_paths")
        relevant = set(labels)
        # K counts chunks, as in the production search. Repeated documents still
        # occupy ranking positions but count only once towards document recall.
        ranked = [row[0] for row in search(query, k)][:k]
        found = relevant.intersection(ranked)
        first = next((rank for rank, path in enumerate(ranked, 1) if path in relevant), None)
        results.append({"query": query, "relevant_paths": sorted(relevant), "retrieved_paths": ranked,
                        "recall": len(found) / len(relevant),
                        "reciprocal_rank": 1 / first if first else 0.0})
    return {"k": k, "queries": len(results),
            "recall_at_k": sum(r["recall"] for r in results) / len(results),
            "mrr_at_k": sum(r["reciprocal_rank"] for r in results) / len(results),
            "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="JSON array of query/relevant_paths cases")
    parser.add_argument("--k", type=int, default=5, help="number of chunks to retrieve (default: 5)")
    args = parser.parse_args()
    try:
        cases = json.loads(args.dataset.read_text(encoding="utf-8"))
        from app.rag import document_paths, search, _db, _provider_conflict
        # Reject invalid/missing labels and mismatched embedding spaces rather than
        # reporting misleading zero scores for an unprepared index.
        if not isinstance(cases, list) or not cases:
            raise ValueError("dataset must be a non-empty list")
        indexed = set(document_paths())
        for case in cases:
            if isinstance(case, dict) and isinstance(case.get("relevant_paths"), list):
                missing = {p for p in case["relevant_paths"] if isinstance(p, str)} - indexed
                if missing:
                    raise ValueError(f"relevant documents not indexed: {', '.join(sorted(missing))}")
        with _db() as conn:
            with conn.cursor() as cur:
                conflict = _provider_conflict(cur)
                if conflict:
                    raise ValueError(conflict)
        report = evaluate(cases, search, args.k)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"evaluation failed: {exc}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
