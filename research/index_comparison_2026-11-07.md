# Historical index comparison — 7 November 2026

**Decision: V3 is not the best standalone semantic index on these tests. Preserve the fine-tuned model and its text/summary indexes. Keep the broader BGE metadata/context indexes too. A production replacement is not established by index scores alone.**

Work stayed in `C:\Users\nithi\Desktop\DialogueMatch\data\index-comparison-2026-11-07`. Original indexes were opened for reading; all 43 SHA-256 checks still match. The active application, SQLite corpus, vector manifest and vector file were not replaced. No model was trained and no corpus was re-embedded. Only query vectors and sampled verification embeddings were computed.

## What was evaluated

- 43 index files; 37 unique hashes. Six files are exact duplicates. 24 unique semantic indexes passed sampled model/document/ID verification and were scored. Five semantic indexes remain unidentified; eight classifier-score indexes were audited separately.
- Frozen 502-query suite: 170 recent probes, 310 historical movie queries, and 22 real-user requests. Recent probes contain 40 exact excerpts, 40 small-typo excerpts, 20 normal descriptions, 20 descriptions with long conversational introductions, 20 concise controls paired with the latter scenes, and 30 visual memories.
- 140 query records have exact source-passage labels. The 60 description queries refer to 40 distinct passages; the long/concise pairs are correlated. Quote/typo pairs also share labels. They are not 502 independent held-out examples.
- Native coverage and two exact passage intersections were tested separately. Each semantic result uses the same query set and passage IDs. No filename-based mapping guesses were admitted.
- Main matched corpus: 132,759 passages across 1,903 movies. It contains gold passages for 46 description queries and 60 dialogue queries. Small-index intersection: 5,959 passages; its easier search space is not evidence that an 87-movie index is superior.
- Top-five hit means the expected passage appears among five passage results. Movie hit requires only the expected IMDb ID; it does not establish the correct scene or timestamp. A top-150 hit measures candidate recall before reranking. Movie results are not deduplicated to five distinct titles.

## Same-corpus semantic retrieval

All rows below use precisely the same 132,759 passage IDs, cleaned queries and the standard BGE query instruction. Fine-tuned fusion uses equal reciprocal-rank fusion (constant 60), with 150 candidates per component and no fitted weights.

| Representation | Description passage @5 /46 | Dialogue passage @5 /60 | Description recall @150 /46 |
|---|---:|---:|---:|
| V3 | 11 | 57 | 25 |
| BGE dialogue + emotion/keywords | 25 | 60 | 39 |
| BGE combined current-scene context | 28 | 60 | 37 |
| Fine-tuned dialogue (700 characters) | 35 | 60 | 45 |
| Fine-tuned summary | 33 | 44 | 42 |
| Fine-tuned text + summary (equal RRF) | 41 | 54 | 45 |

The fine-tuned pair improves description hit@5 over V3 by 65.2 percentage points on this subset. A paired bootstrap grouping queries by their 30 source passages gives a descriptive 95% interval of 47.8–80.9 points. This is conditional on the selected scenes, not a population accuracy claim.

## Full original coverage

| Representation | Descriptions @5 /60 | Gold description passages present /60 | Dialogue @5 /80 | Historical movie @5 /310 | Real-user movie @5 /22 |
|---|---:|---:|---:|---:|---:|
| V3 | 14 | 60 | 75 | 110 | 5 |
| BGE dialogue + emotion/keywords | 34 | 60 | 80 | 118 | 5 |
| BGE combined current-scene context | 32 | 60 | 76 | 125 | 7 |
| Fine-tuned dialogue (700 characters) | 35 | 46 | 60 | 63 | 5 |
| Fine-tuned summary | 33 | 46 | 44 | 81 | 5 |
| Fine-tuned text + summary (equal RRF) | 41 | 46 | 54 | 78 | 7 |

The fine-tuned indexes omit many passages, even in movies they contain. Fourteen of the 60 description queries have no gold passage in them. Their absence is counted as a miss in this native table. The full BGE indexes contain all 60. Historical target-movie coverage is 282/310 for V3 and the full BGE indexes and 279/310 for the fine-tuned pair; real-user target coverage is 20/22 for both. These denominators explain part of the low movie totals, not all of them.

The fine-tuned text/summary pair leads described-passage retrieval. BGE dialogue plus emotion/keywords is a stronger broad-coverage default than V3 for this recent suite. BGE combined current-scene context leads the selected broad-coverage configurations on historical and real-user movie requests. Equal fusion is not automatically better: combining the fine-tuned text and summary improves description ranking but reduces dense-only quote hits. Quote handling should retain the existing lexical/exact-match path.

## Complete-app pilot

A deterministic SHA-256 sample selected four queries from each of six categories: normal descriptions, long descriptions, visual memories, real-user requests, exact excerpts and typo excerpts. The uncertain visual label fresh-136 was excluded. Each of 24 queries was run through the same existing lexical retrieval, plot guidance, candidate selection and MS MARCO MiniLM L6 reranker. Only semantic candidate rankings changed. Reranker scores were reused for identical query/passage pairs; query encodings were cached, so this is not a latency benchmark.

| Semantic candidates | Correct movie @5 /24 | Correct passage for descriptions @5 /8 | Description gold in candidate pool /8 | Quote/typo passage @5 /8 |
|---|---:|---:|---:|---:|
| bge_text_metadata | 13 | 3 | 5 | 8 |
| fine_text_summary | 14 | 4 | 7 | 8 |
| v3 | 13 | 3 | 5 | 8 |

In all four long-description pilot cases, the fine-tuned pair supplied the gold passage and it reached the reranker; only one reached the final top five. Replacing vectors alone therefore does not resolve the current application bottleneck. The pilot is small and exploratory, and does not establish a production winner.

## Verification findings and limits

- The local fine-tuned weights are usable. Their newer Sentence Transformers module schema is incompatible with the installed loader, so verification used the local Transformer, CLS pooling and normalization directly. The model card records 80,000 training pairs, MultipleNegativesRankingLoss, two epochs and 1024 dimensions. Its training-pair manifest and held-out split are unavailable.
- Fine-tuned indexes contain 132,759 vectors, while their current JSON contains 132,763 rows. Recovered source offsets change at index positions 22,721, 28,933, 63,820 and 111,001. The summary mapping was verified at 52 positions including boundaries. Dialogue reproduction also required truncating source text to 700 characters; it passed 84 samples including boundaries. Extra fields require emotion, relationship, keywords in that order and passed 32 samples. These are reconstruction findings, not new training.
- None of the 502 test strings exactly matches the 663,680 distinct generated query strings available in the fine-tuning source, after lowercase/whitespace normalization. This does not establish that their target passages, movies or similar paraphrases were held out during training.
- The `movies_colbert.index` file contains 384-dimensional MiniLM sentence embeddings, not a ColBERT checkpoint. Its 2,539,897 sentence vectors map repeatedly to source passages. The comparison deduplicates passage results after retrieving up to 1,500 sentence vectors. It evaluates single-vector query-to-sentence retrieval, not ColBERT token-level MaxSim or the complete historical notebook pipeline.
- Seven of eight unique emotion/intent feature indexes have descending classifier confidence values in every sampled row. Their constructors appear to discard label identity. Such coordinates describe confidence rank, not fixed emotion/intent labels. The 1,000-movie summary-intent index differs and needs its own verified constructor. None was silently treated as a semantic embedding index.
- Raw queries and instruction/label variants were tested separately. BGE-base received an additional standard instruction variant; MiniLM received the historical `query:` variant; combined BGE context received its custom movie-query instruction. Their full results are in the CSV. Do not choose a query protocol using these labels and call it held-out tuning.
- A seeded V3 audit sampled 512 constructed documents: one exceeded 510 content tokens, zero lost all current dialogue, and median retained current-dialogue fraction was 100%. Truncation is not supported as the main explanation for its poorer scores here. V3 adds neighboring summaries before current dialogue and omits the current summary; representation dilution and query alignment are hypotheses requiring controlled ablations.
- Recent labels are derived from source subtitles and existing summaries, not independently checked video. Small typo probes are not an extensive spelling benchmark. Historical labels and community answers can be wrong. Visual memory fresh-136 is explicitly tentative; raw metrics preserve its label, while the pilot excludes it. These tests measure usefulness within the existing corpus, not unseen-movie generalization.

## Recommendation

Keep the fine-tuned weights, its dialogue and summary indexes, their JSON and recovered ID mapping. Keep `movies_t_e_baai.index` and `chunk_embeddings_ctx_combined.index` with their verified sources. Preserve the current production vector/manifest/database files while comparing a replacement.

For the next architecture, keep exact/typo dialogue retrieval, use separate current-scene text and summary retrieval, retain a broad-coverage BGE channel, then combine candidates into the existing single result list. Expand fine-tuned passage coverage before relying on it alone. Evaluate and improve candidate selection and description reranking against the fixed misses, particularly conversational introductions. A movie-level result must remain separate from evidence for a timestamp.

V3 can remain a baseline or optional context channel, but these results do not justify calling it the best or deleting the alternatives. The six duplicate files are the only byte-identical redundancy proven here. No deletion was performed.

## Unidentified semantic indexes

- `preprocessing\indexes\chunk_embeddings_ctx_meta.index` — current model/document reconstruction did not pass; excluded from quality claims.
- `preprocessing\indexes\chunk_embeddings_ctx_raw.index` — current model/document reconstruction did not pass; excluded from quality claims.
- `preprocessing\indexes\movies.index` — current model/document reconstruction did not pass; excluded from quality claims.
- `preprocessing\indexes\movies_only_summary.index` — current model/document reconstruction did not pass; excluded from quality claims.
- `preprocessing\indexes\movies_only_text.index` — current model/document reconstruction did not pass; excluded from quality claims.

## Artifacts

- `summary.json`: selected metrics, coverage, package versions, query hash and pilot summary.
- `leaderboard.csv`: every index/protocol/scope/cohort metric. `native_summary.csv`: compact native coverage comparison.
- `query_comparison.json`: frozen queries, labels, ranks and top-ten candidates for the leading configurations.
- `index_results.json`, `fusion_results.json` and referenced per-query files: full retrieval results.
- `verification.json`, `leader_verification.json`, `original_integrity.json`, `fine_alignment_probe.json`, `classification_feature_audit.json`, `v3_truncation_audit.json`: audit evidence.
- `pipeline_pilot.json`, `pilot_queries.json`, `pilot_rerank_cache.json`: reproducible pilot results and cached model scores.
- `duplicates.json`: groups of byte-identical files. Original file hashes are in `inventory.json`.

The Python comparison scripts and cached query vectors are retained in this temporary folder. Reuse the frozen `queries.json`; run `evaluate_indexes.py`, `compare_fusions.py`, `pipeline_pilot.py`, and `make_report.py` to refresh results using the saved registry and query vectors. Original source/index files must remain in place. Training, corpus rebuilding and notebook/API execution are not required.
