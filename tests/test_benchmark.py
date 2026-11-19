"""Test benchmark runner and sample database integration."""
from pathlib import Path
from benchmarks.run_benchmark import evaluate_engine_config
from dialoguematch.engine import SearchEngine

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DB = ROOT / "data/sample/dialoguematch.sample.sqlite"


def test_sample_database_exists_and_has_target_movies():
    assert SAMPLE_DB.is_file(), "Sample database must exist"
    engine = SearchEngine(SAMPLE_DB, neural=False, rerank=False)
    try:
        status = engine.status()
        assert status["stats"]["movies"] >= 5
        assert status["stats"]["scenes"] > 500
    finally:
        engine.close()


def test_benchmark_evaluates_exact_and_typo_quotes():
    cases = [
        {
            "id": "test-1",
            "query": "why so serious",
            "movie_id": "tt0468569",
            "category": "exact_quote",
            "mode": "quote",
            "spans": [[1839.0, 1846.0]],
        },
        {
            "id": "test-2",
            "query": "why so seriuos",
            "movie_id": "tt0468569",
            "category": "typo_quote",
            "mode": "quote",
            "spans": [[1839.0, 1846.0]],
        },
    ]
    engine = SearchEngine(SAMPLE_DB, neural=False, rerank=False)
    try:
        report = evaluate_engine_config(engine, cases, "Test-Config")
        assert report["movie_hit1"] == 1.0
        assert report["mrr10"] > 0.8
    finally:
        engine.close()
