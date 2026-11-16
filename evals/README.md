# Retrieval quality evaluation

This offline benchmark measures the real `app.rag.search` results against manually labeled document filenames. It reports mean document Recall@K and MRR@K, plus each query's ranked paths and scores. K counts retrieved **chunks**, as in the application; repeated chunks from the same document occupy rank positions but count once toward recall. MRR uses the first relevant chunk's rank, or zero if none appears within K. These metrics assess retrieval, not generated answer quality.

1. Start the API and PostgreSQL with pgvector as described in the main README. Use a separate evaluation database: the sample ingestion writes to its index.
2. Set `DATABASE_URL`, `LLM_PROVIDER`, and any provider API keys in your shell to match the index. For example, `export LLM_PROVIDER=local DATABASE_URL=postgresql://acme:acme@localhost:5432/docs`. The evaluator reads environment variables; it does not load `.env` itself. If you change embedding provider, reset and reingest using the application's documented workflow.
3. Ingest the sample Markdown files using `POST /v1/ingest` with `{"folder":"acme-handbook"}`.
4. From the repository root, run:

```bash
python -m evals.retrieval evals/handbook.json --k 5
```

The sample has five illustrative questions and is not a representative production benchmark. For meaningful comparisons, create a larger reviewed JSON dataset of objects with `query` and `relevant_paths` (the exact indexed filenames). Label all known relevant documents for each question. Keep the dataset, indexed corpus, provider, and K fixed when comparing changes. The evaluator fails if a labeled document is not indexed or the embedding provider differs from the index; it never modifies the index. Hosted embedding providers may charge for query embeddings. Results can vary when the corpus or search configuration changes.
