# DialogueMatch Archive & Historical Experiments

This directory isolates exploratory research notebooks, legacy prototypes, and experimental artifacts developed during the evolution of DialogueMatch.

## Lineage Overview

1. **Phase 1: Lexical & Subtitle Prototyping (`try_2`)**
   - Exploratory SRT parsing, character/dialogue filtering across subsets (100 movies, 1000 movies).
   - Early experiments with emotional / intent classification and baseline semantic embeddings.

2. **Phase 2: Single-Vector Semantic Search (`V3`)**
   - Single-index BGE retrieval experiments over 1,606 movies.
   - Demonstrated the limitations of single dense vectors for exact quote retrieval and temporal ordering.

3. **Phase 3: Production DialogueMatch Engine (`dialoguematch/`)**
   - Multi-Index Semantic Ensemble (fine-tuned dialogue/summary encoders + BGE combined scene context + MiniLM gap vectors).
   - Unstemmed phrase FTS5 and boundary-bridging quote recovery.
   - Query decomposition (global film premise vs target scene beat) and narrative sequence windows.
   - Multi-view cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`).

> **Note**: Binary checkpoints, large FAISS indexes, and virtual environments have been purged or gitignored to ensure repository hygiene.
