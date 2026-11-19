# Unified search results

The UI now renders one list from `/api/search`. Plot retrieval selects up to five movies; keyword search within each retrieves up to three subtitle candidates. These join the original subtitle candidates. The original top 50 scene shortlist is preserved in full and all additional plot-guided candidates join the scene reranker. Reranking uses the original scene text and summary, not the movie plot. Matching plot excerpts appear in collapsed details with source attribution. Quote searches retain their previous path.

Validation: 25 tests passed; JavaScript syntax check passed; live HTTP searches returned a single scene-result structure. The Interstellar recorded-messages query remained rank one in the live check. On the same 30-query movie comparison subset, the original and unified reranked systems each scored 16/30 movie Hit@5, with no change in which queries passed that cutoff. This small historical subset has no scene-time labels and does not establish broader quality. New results: `movie_subset_unified.json`.

Additional retrieval and reranking increase cost. This run measured median search latency of 6,406 ms and p95 of 13,743 ms versus 2,619 ms and 3,230 ms in the earlier subset run. The runs occurred under different concurrent loads, so they are not a controlled latency comparison.
