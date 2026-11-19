# Long dialogue and natural-description audit

This development audit contains 26 probes: six literal dialogue excerpts, six natural descriptions, four literal quotes inside human questions, four visual/source-limit examples, and six descriptions with a long conversational introduction. Queries and local-source time labels are in `long_query_cases.json`. They were constructed for debugging, not independently sampled from users or verified against video. A scene hit means temporal overlap with the labeled subtitle passage; it does not prove visual correctness.

## Bugs found and repaired

- **Input rejection:** the server and input field rejected everything over 500 characters. The limit is now 4,000. Five of the six direct excerpts were actually rejected in the initial run. The long natural descriptions also exceeded the old limit.
- **Quotes crossing many chunks:** the phrase index contained only individual chunks and small boundary bridges. Long quotations are now verified against ordered original subtitle lines in anchor-selected movies, and returned with the full matched span. Anchor matches alone are not accepted as full quotes.
- **Literal quote wrapped in a question:** surrounding request text obscured the phrase. A literal quote of four or more words inside double quotation marks now has its own exact search path. Only the matching source span receives the exact-match label.
- **Query truncation:** semantic encoding and reranking could drop late clues. Both now use overlapping tokenizer-budgeted query windows. Later keyword clues also have an independent retrieval path. Long automatic descriptions avoid a costly whole-paragraph fuzzy-quote comparison; explicit quote mode still supports fuzzy matching.
- **Shortlist exclusion risk:** code inspection showed that leading independent keyword/semantic candidates can be buried by fusion. The top five of each are now retained for reranking. This does not force them into the final answer. The final Avengers trace establishes a scoring failure, not a missing candidate; the earlier trace was insufficient to attribute that particular miss to shortlist exclusion.
- **Conversational filler:** a conservative set of complete, standalone request sentences is removed from description retrieval. Sentences containing years, actor names, uncertainty, or remembered actions are retained. The original query remains in the response.
- **Keyword latency:** global keyword search now uses FTS5's native rank ordering. Searches within a movie use a small temporary movie-specific text index. A traced operation originally stalled while querying the global corpus for one movie; one isolated local-index check took 0.051 seconds. These use different document-frequency scopes and are not interchangeable BM25 score distributions. No corpus or saved semantic vectors were overwritten.

## Measured results and experiments

`long_query_baseline.json` is an **incomplete** initial run: it stopped after ten probes when a filtered keyword search stalled. It is not a complete before/after benchmark. `long_query_after.json` is an intermediate run, and `long_query_refined.json` tests the subsequent candidate/description changes. Reports retain failed experiments rather than replacing them with successful examples.

The six long direct excerpts all returned their complete subtitle spans at rank one after repair, with median search time 441 ms in that run. The four embedded literal quotes all returned the relevant span at rank one, with median search time 124 ms. These are selected development examples and exclude startup.

The refined description run found five of six ordinary descriptions and four of six longer descriptions in the first five results with 128-token query windows. A separately recorded comparison (`long_query_context256.json`) enlarged query windows to 256 tokens while budgeting the dialogue to keep pairs within 512 tokens. This found five of six longer descriptions in the first five, recovering the long Avengers description at rank 3. Its Whiplash movie result worsened, while the exact labeled scene remained a miss in both configurations. The 256-token setting is retained; the ordinary description probes fit below 128 tokens and use the same complete query in either setting. This is an exploratory change tested on the same development sample, not held-out validation.

The preserved eight-example lexical regression set still had eight accepted span hits in the first five. Automated checks also cover long quotes across many chunks, quoted questions, late query clues, movie filtering, candidate retention, and source/ID contracts. Neural startup disables unused TensorFlow/Flax discovery for these PyTorch models.

## Remaining misses: source and ranking evidence

| Probe | What the trace establishes | Remaining issue |
|---|---|---|
| Shield hero hears “on your left,” allies assemble | Endgame passage `tt4154796_108` is keyword rank 1, candidate rank 5 in a traced run, and is reranked; final rank 16 | Cross-encoder favors generic military/radio passages. The expected scene's score was -8.565 versus -5.625 for the first result. These are model scores, not calibrated probabilities. |
| Long padded drummer/abusive teacher memory | Correct passage reaches retrieval and reranking, but a different Whiplash passage wins | Correct movie can mask incorrect localization. Retain the narrow label rather than changing it to count a pass. |
| Hotel corridor changes gravity | Inception appears at movie rank 8 in the visual probe; there is no video-verified scene label | Subtitles/descriptions do not reliably ground the visible rotating fight. Movie identification is not a verified scene hit. |
| Villain in nurse costume detonates hospital | Dark Knight is absent from the returned top ten for this wording; local subtitle timeline ends at 4,814.194 seconds and its indexed summaries do not describe the hospital/nurse event | Source coverage and visual evidence are insufficient. Both local subtitle folders and historical exports were checked; no longer local version was recovered. |
| Wizard on bridge confronts fiery monster | Fellowship has only 20 passages and its local timeline ends at 2,392 seconds; expected quote is absent in the prior source audit | Partial/suspect source. The alternate local folder contains the same 154-line file. |
| Black-coated man dodges rooftop bullets | `tt0133093` has no movie record in the current database | Out of catalog; no retrieval or reranking model can return a stored scene that is absent. |

The source limitations are findings about these local files, not proof of universal impossibility. Correct, complete, release-aligned sources or verified visual descriptions are needed to resolve them. Fine-tuning on these few generated examples would risk memorizing them; this iteration improves the retrieval/ranking pipeline without claiming trained-weight improvements or general accuracy.

## Final verification

`python -m pytest tests -q`: 39 passed. The running app was restarted with the revised pipeline. Live HTTP checks verified the 4,000-character input limit, a 1,157-character quote returning the expected Interstellar scene with exact-quote evidence, and a quotation inside a human question returning the same scene. `long_query_final.json` combines the final relevant runs with a note about which configuration each record uses. Of 22 labeled subtitle probes, 20 returned an overlapping accepted span in the first five. The four visual/source-limit probes are separate unresolved cases, not successful scene localizations. No model weights were retrained and no source corpus was replaced.
