# Implementation and validation — 30 October 2026

The runnable application is in `dialoguematch/`. Start it with `python -m dialoguematch serve` and open http://127.0.0.1:8765. The root README contains build, evaluation, and shutdown commands.

## Built artifacts

- 2,000 catalog movies, 178,175 indexed passages.
- 74 movies recovered from existing local subtitle files.
- No absent movie IDs among this build's requested catalog/evaluation IDs. This does not mean every movie's subtitle is complete.
- 109 movie records flagged for coverage review; flags include short timelines, late starts, and missing original subtitle lines.
- No subtitle parse exceptions or duplicate chunk IDs during this build.
- 165,300 scenes have imported BGE semantic vectors; 12,875 recovered/additional scenes use quote and keyword retrieval. `python -m dialoguematch embed` builds fresh semantic vectors for the entire corpus if desired.
- The legacy import reproduced 32 evenly spaced vectors from their source documents. Minimum cosine agreement was 0.9999998798. The new manifest records model, normalization, query prefix, scene IDs, source/index checksums, and the current database checksum. This is sampled validation.

## Verification

`python -m pytest tests -q`: **19 passed**. Tests cover actual failure modes: crossing a subtitle/chunk boundary, exact quote timing, recovering missing movies, independent lexical candidates, filtering, no supported quote, typo matching, numeric subtitle dialogue, short quotes, safe chunk boundaries, preserved original cues, conflicting labels, separate movie/scene metrics, stale semantic indexes, ID mapping, query prefixes, and reranker coverage of the end of long dialogue.

The full application was exercised through its HTTP API using `research/validate_fixed_pipeline.py --http`. Results are saved in `research/fixed_pipeline_hybrid_results.json`. These 15 selected examples are diagnostic probes, not an independent held-out benchmark.

| Query | Observed result |
|---|---|
| Messages span 23 years | Correct scene rank 1; subtitle interval 4675.451–4678.804 seconds |
| I am going to make this pencil disappear | Correct scene rank 1; 1407.760–1410.448 seconds |
| The idea is like a virus | Correct scene rank 1; 7120.139–7123.068 seconds |
| Are you not entertained | Gladiator rank 1 after local subtitle recovery; 4309.590–4313.671 seconds; another film also quotes it |
| Mesages span 23 years | Correct scene rank 1 through approximate quote matching; timing remains passage-level |
| A man cries after watching 23 years of missing videos | Correct Interstellar passage rank 1 |
| Crying while watching decades of video messages from kids | Correct Interstellar passage rank 1 |
| Magic trick making a pencil disappear | Correct Dark Knight passage rank 1 |
| Joker pencil trick in the mob meeting | Correct Dark Knight passage rank 1 |
| Giant mountain that is actually a massive water wave | Interstellar movie rank 1; returned passage `_69`; no independently labeled visual span |
| Joker walking away from hospital explosion in a nurse outfit | Correct movie rank 9; scene correctness unverified |
| Hallway fight with zero gravity | Inception missing from top 10 |
| Spinning top ending does it fall | Inception missing from top 10 |
| What is the most resilient parasite | No quote match in the indexed Inception source |
| You shall not pass | Matches quotation in other films; the expected Fellowship passage is absent from its partial local source |

The exact-quote examples took approximately 0.08–0.19 seconds in the recorded hybrid run. The selected scene queries took approximately 25–57 seconds on this CPU-only machine. These are individual diagnostic timings, not p95 measurements. A subsequent batching change groups reranker inputs by length to reduce padding; it does not change candidate generation. CPU scene-search latency remains a practical limitation.

After that final batching change and a server restart, the original “a man cries after watching 23 years of missing videos” query still returned `tt0816692_77` at rank 1 in 20.590 seconds. The response is saved in `research/final_smoke.json`. The final browser quote check returned The Dark Knight at 00:23:27–00:23:30 in approximately 0.1 seconds; its screenshot is `research/dialoguematch-running.png`.

The browser interface was inspected visually and exercised through its search controls. It displays matching dialogue, source-relative timestamps, generated descriptions separately, and coverage flags. Exact matches and scene candidates are labeled differently. The local server is restricted to 127.0.0.1.

## Remaining source limitations

The software repairs do not create dialogue missing from a subtitle file, correct mistranslations automatically, verify release-specific timing against video, or supply visual observations absent from subtitles. Those require corrected source files or video/audio descriptions. Existing generated summaries can still be wrong. The app therefore returns evidence and candidate labels rather than claiming all searches are resolved.

Original exports and old notebook indexes were preserved. The new database and vectors are in the ignored `data/` folder. The old notebooks remain historical experiments; the supported entry point is the new package. Historical audit reports describe the pre-repair snapshot.
