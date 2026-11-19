# Retrieval iteration — 7 November 2026

## What was measured

The 310 existing queries in `preprocessing/evaluation_set.csv` label movies, not scene time spans. They are historical project data, not an independently collected user sample, and their labels have not been independently checked. With semantic retrieval enabled and reranking disabled, 152/310 expected movies were present in the top five returned passages (`baseline_movie_no_rerank.json`). Median search time was 1,403.5 ms and p95 was 3,879 ms for this run; startup and model loading are excluded.

The 30-query comparison subset takes the first query for each of the first 30 distinct movies; it is not random. Lexical-only found 13/30 expected movies in the first five passages, semantic hybrid without reranking found 12/30, and semantic hybrid with reranking found 16/30. These are movie metrics, not scene metrics. Files: `movie_subset_lexical.json`, `baseline_movie_no_rerank.json`, `movie_subset_reranked.json`.

The full reranked run found the expected movie in the first five passages for 163/310 queries (52.6%); the no-rerank run found 152/310 (49.0%). Reranking gained 27 cases and lost 16. The reranked run's median latency was 2,849 ms and p95 was 4,608 ms, excluding startup; other experiments ran concurrently for part of this run. See `movie_reranked_310.json`. These results do not demonstrate scene accuracy or performance on new users.

`scene_span_smoke.json` reuses eight examples from earlier debugging. `quote_pilot.json` has 14 manually selected quote and typo probes; the acceptable times were obtained by inspecting the local subtitle index. Multiple valid subtitle occurrences are recorded where found. These are development probes, not representative or independent accuracy tests. Quote span Hit@5 changed from 12/14 to 13/14 after the spelling fallback; generic phrases can occur in many films. A span hit only requires overlap and may reward an overly broad chunk.

On one Joker description, with the lexical path and no reranker, the pre-change fuzzy matcher took 13,483 ms and the optimized matcher 980 ms; the top 10 scene IDs and match labels were the same. This is one paired measurement, not a latency guarantee.

## Plot experiment

The [CMU Movie Summary Corpus](https://www.cs.cmu.edu/~ark/personas/) supplies Wikipedia-derived descriptions under CC BY-SA. A conservative title-and-year join covered 1,008 local movies. On the 280 existing queries outside the 30-query subset, 148 expected movies had a matched plot. Plot-only top-five movie Hit was 68/148 on covered queries and 68/280 overall. These labels and joins are unverified; the source predates many catalog entries. Results in `plot_experiment.json` were inspected during development, so neither set is a clean held-out final test.

Plot suggestions are displayed separately from timed scenes. Plot text is not time-aligned, and the join does not prove that a title/year match is correct. The separate feature cannot be interpreted as improving timed scene accuracy.

## Real-user requests

The [Microsoft tip-of-the-tongue dataset](https://github.com/microsoft/Tip-of-the-Tongue-Known-Item-Retrieval-Dataset-for-Movie-Identification) contains historical requests and community answer links. `prepare_tot_benchmark.py` selects requests no longer than the current 500-character limit and resolves linked Wikipedia pages through Wikidata IMDb IDs. Only entries with one unambiguous ID present in the catalog are retained: 22 requests. The link resolution verifies ID correspondence, not the original community answer. A small, selected dataset cannot establish general accuracy or independence from model training data.

On those 22 requests, lexical-only and the full semantic-and-reranking path each returned the expected movie in the first five passages for 5 queries. Plot-only top-five movie search returned 2. A proposed large filler-word stop list improved lexical Hit@5 to 7/22 but hurt one case and removes potentially meaningful clues; it was not enabled. Searching individual sentences separately returned the expected movie in the top five distinct movies for 3/22 in a separate lexical experiment; it was not enabled. Both exploratory variants used this same small sample and are not held-out validations. Original request text and the generated selection are stored locally under `data/`.

## Remaining work

Create independently checked, time-span-labeled user queries across diverse movies, with ambiguous and out-of-corpus examples; review source completeness and video-release alignment; evaluate visual-only queries against actual visual evidence; and compare the complete pipeline's ranking and latency on that benchmark. The current measurements do not establish that scene search is good enough for general use.
