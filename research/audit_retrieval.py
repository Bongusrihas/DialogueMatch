"""Offline, standard-library diagnostics; no database, model, or API calls.

Run: python research/audit_retrieval.py --lexical
Writes research/audit_results.json. Lexical probes are illustrative, not a benchmark.
"""
import argparse
import ast
import collections
import csv
import json
from pathlib import Path
import re
import sqlite3

ROOT = Path(__file__).resolve().parents[1]


def audit_labels(path):
    with path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    groups = collections.defaultdict(collections.Counter)
    for row in rows:
        groups[row["query"].strip().lower()][row["imdb_id"]] += 1
    conflicts = {query: dict(counts) for query, counts in groups.items() if len(counts) > 1}
    return {
        "rows": len(rows),
        "columns": list(rows[0]) if rows else [],
        "unique_queries": len(groups),
        "queries_with_multiple_movie_labels": len(conflicts),
        "query_only_top1_ceiling_count": sum(max(c.values()) for c in groups.values()),
        "query_only_movie_hit5_ceiling_count": sum(sum(sorted(c.values(), reverse=True)[:5]) for c in groups.values()),
        "conflict_examples": dict(list(conflicts.items())[:3]),
    }


def audit_chunker():
    path = ROOT / "preprocessing/process/movie_chunker.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    # The only project import is an external scraper. Do not load or call it.
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and node.module == "process.external_scrape"
    )]
    namespace = {"__name__": "__main__"}
    exec(compile(tree, str(path), "exec"), namespace)
    subtitle = namespace["RawSubtitle"]
    chunk = namespace["hybrid_chunk"]
    first = subtitle(1, 0, 30, "We need to leave this place immediately.")
    far = subtitle(2, 200, 205, "Please come back and help us.")
    near = subtitle(2, 40, 70, "Please come back and help us.")
    merged = chunk([first, far], movie_id="synthetic")
    separate = chunk([first, near], movie_id="synthetic")
    return {
        "synthetic_input_intervals": [[0, 30], [200, 205]],
        "synthetic_output_intervals": [[c.start_time, c.end_time] for c in merged],
        "synthetic_split_reasons": [c.split_reason for c in merged],
        "overlap_computed": bool(separate[1].overlap_text),
        "overlap_exported": "overlap_text" in separate[1].to_dict(),
        "cleanup_input": "COOPER: [crying] I am watching the screen.",
        "cleanup_output": namespace["clean_text"]("COOPER: [crying] I am watching the screen."),
    }


def lexical_probes(chunks):
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE VIRTUAL TABLE scenes USING fts5(scene_id UNINDEXED, dialogue, summary, tokenize='unicode61')")
    connection.executemany("INSERT INTO scenes VALUES (?, ?, ?)", (
        (c["_id"], c.get("text", ""), c.get("summary", "")) for c in chunks
    ))
    probes = [
        ("Messages span 23 years", "tt0816692_77"),
        ("23 years messages", "tt0816692_77"),
        ("a man cries after watching 23 years of missing videos", "tt0816692_77"),
        ("I am going to make this pencil disappear", "tt0468569_23"),
        ("The idea is like a virus", "tt1375666_78"),
    ]
    movie_probes = [
        ("joker pencil trick in the mob meeting", "tt0468569"),
        ("magic trick making a pencil disappear", "tt0468569"),
        ("joker walking away from hospital explosion in a nurse outfit", "tt0468569"),
        ("hallway fight with zero gravity", "tt1375666"),
        ("spinning top ending does it fall", "tt1375666"),
        ("crying while watching decades of video messages from kids", "tt0816692"),
        ("giant mountain that is actually a massive water wave", "tt0816692"),
        ("What is the most resilient parasite", "tt1375666"),
        ("Are you not entertained", "tt0172495"),
        ("You shall not pass", "tt0120737"),
    ]
    probes += [(query, movie) for query, movie in movie_probes]
    output = []
    for query, target in probes:
        # OR all alphanumeric terms, no expansion, no model, no movie filter.
        expression = " OR ".join('"' + term + '"' for term in re.findall(r"\w+", query.lower()))
        hits = connection.execute(
            "SELECT scene_id, bm25(scenes) FROM scenes WHERE scenes MATCH ? ORDER BY bm25(scenes) LIMIT 200",
            (expression,),
        ).fetchall()
        movie_id = target.split("_")[0]
        normalized_query = " ".join(re.findall(r"\w+", query.casefold()))
        movie_chunks = [c for c in chunks if c["movie_id"] == movie_id]
        phrase_ids = [c["_id"] for c in movie_chunks if normalized_query in
                      " ".join(re.findall(r"\w+", c.get("text", "").casefold()))]
        phrase_hits = connection.execute(
            "SELECT scene_id FROM scenes WHERE scenes MATCH ? ORDER BY bm25(scenes) LIMIT 200",
            ('dialogue : "' + normalized_query + '"',),
        ).fetchall()
        output.append({
            "query": query, "target_id": target,
            "target_type": "scene" if "_" in target else "movie",
            "target_rank_within_200": next((i for i, (sid, _) in enumerate(hits, 1)
                if (sid == target if "_" in target else sid.split("_")[0] == movie_id)), None),
            "top5_scene_ids": [sid for sid, _ in hits[:5]],
            "expected_movie_chunk_count": len(movie_chunks),
            "normalized_quote_found_in_expected_movie": phrase_ids,
            "phrase_search_target_rank_within_200": next((i for i, (sid,) in enumerate(phrase_hits, 1)
                if (sid == target if "_" in target else sid.split("_")[0] == movie_id)), None),
        })
    connection.close()
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lexical", action="store_true")
    args = parser.parse_args()
    result = {"evaluation": {}, "chunker": audit_chunker()}
    for filename in ["evaluation_set.csv", "dialogue_only_eval_300.csv"]:
        result["evaluation"][filename] = audit_labels(ROOT / "preprocessing" / filename)
    print("Evaluation and chunker audit complete.", flush=True)
    path = ROOT / "preprocessing/chunks-context-top2k.json"
    chunks = json.loads(path.read_text(encoding="utf-8"))
    result["corpus"] = {
        "path": str(path.relative_to(ROOT)), "chunks": len(chunks),
        "movies": len({c["movie_id"] for c in chunks}),
        "duration_over_100_seconds": sum(c.get("duration", 0) > 100 for c in chunks),
        "text_over_145_words": sum(len(c.get("text", "").split()) > 145 for c in chunks),
        "interstellar_77": [
            {k: c.get(k) for k in ["_id", "start_time", "end_time", "summary"]}
            for c in chunks if c["_id"] == "tt0816692_77"
        ],
    }
    movie_ids = {c["movie_id"] for c in chunks}
    with (ROOT / "preprocessing/evaluation_set.csv").open(encoding="utf-8-sig") as handle:
        evaluation = list(csv.DictReader(handle))
    missing = [r for r in evaluation if r["imdb_id"] not in movie_ids]
    result["corpus"]["evaluation_coverage"] = {
        "evaluation_rows": len(evaluation),
        "expected_movies": len({r["imdb_id"] for r in evaluation}),
        "rows_whose_movie_is_absent": len(missing),
        "missing_movie_ids": sorted({r["imdb_id"] for r in missing}),
    }
    result["corpus"]["coverage_spot_checks"] = {}
    for movie_id in ["tt1375666", "tt0120737", "tt0172495", "tt0468569"]:
        selected = [c for c in chunks if c["movie_id"] == movie_id]
        result["corpus"]["coverage_spot_checks"][movie_id] = {
            "chunks": len(selected),
            "first_start_seconds": min((c["start_time"] for c in selected), default=None),
            "last_end_seconds": max((c["end_time"] for c in selected), default=None),
        }
    print("Corpus audit complete.", flush=True)
    if args.lexical:
        result["lexical_probe_method"] = "SQLite FTS5 BM25 on dialogue plus summary; OR terms; top 200; illustrative queries selected during inspection, not held-out evaluation."
        result["lexical_probes"] = lexical_probes(chunks)
    output = Path(__file__).with_name("audit_results.json")
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output}", flush=True)
    if args.lexical:
        print(json.dumps(result["lexical_probes"], indent=2), flush=True)


if __name__ == "__main__":
    main()
