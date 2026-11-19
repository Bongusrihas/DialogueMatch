"""Run reproducible v2 benchmarks across Quote Pilot, Long Queries, Fresh-150, Paired-20, ToT-22, and Subset-30."""
from collections import Counter
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dialoguematch.engine import SearchEngine
from dialoguematch.evaluate import evaluate


def run_fresh(engine: SearchEngine, query_rel: str, out_rel: str):
    cases = json.loads((ROOT / query_rel).read_text(encoding='utf-8'))
    rows = []
    for idx, case in enumerate(cases, 1):
        resp = engine.search(case['query'], case.get('mode', 'auto'), limit=10, debug=True)
        hits = resp['results']
        movie_rank = next((n for n, r in enumerate(hits, 1) if r['movie_id'] == case['movie_id']), None)
        scene_rank = None
        if case.get('scene_id') or ('start' in case and 'end' in case):
            scene_rank = next(
                (
                    n
                    for n, r in enumerate(hits, 1)
                    if r['movie_id'] == case['movie_id']
                    and r['start'] < case.get('end', -1)
                    and r['end'] > case.get('start', 1e9)
                ),
                None,
            )
        cand_hit = case.get('scene_id') in resp['candidate_ids'] if case.get('scene_id') else None
        rerank_hit = case.get('scene_id') in resp.get('reranked_ids', []) if case.get('scene_id') else None
        diagnosis = (
            'hit'
            if scene_rank
            else 'movie_only_unverified'
            if not case.get('scene_id') and movie_rank
            else 'visual_or_movie_miss'
            if not case.get('scene_id')
            else 'candidate_miss'
            if not cand_hit
            else 'shortlist_excluded'
            if not rerank_hit
            else 'reranking_miss'
        )
        rows.append({
            'id': case.get('id', f'q-{idx}'),
            'title': case.get('title', case['movie_id']),
            'category': case.get('category', 'unspecified'),
            'movie_rank': movie_rank,
            'scene_rank': scene_rank,
            'candidate_hit': cand_hit,
            'reranked_hit': rerank_hit,
            'elapsed_ms': resp['elapsed_ms'],
            'diagnosis': diagnosis,
        })
        if idx % 25 == 0 or idx == len(cases):
            print(f'[{query_rel}] {idx}/{len(cases)} completed', flush=True)

    categories = {}
    for cat in dict.fromkeys(r['category'] for r in rows):
        members = [r for r in rows if r['category'] == cat]
        times = sorted(r['elapsed_ms'] for r in members)
        entry = {
            'count': len(members),
            'movie_hit1': sum(bool(r['movie_rank'] == 1) for r in members),
            'movie_hit5': sum(bool(r['movie_rank'] and r['movie_rank'] <= 5) for r in members),
            'movie_hit10': sum(bool(r['movie_rank'] and r['movie_rank'] <= 10) for r in members),
            'median_ms': statistics.median(times) if times else 0,
            'p95_ms': times[math.ceil(0.95 * len(times)) - 1] if times else 0,
        }
        if cat != 'visual_memory':
            entry.update({
                'scene_hit1': sum(bool(r['scene_rank'] == 1) for r in members),
                'scene_hit5': sum(bool(r['scene_rank'] and r['scene_rank'] <= 5) for r in members),
                'scene_hit10': sum(bool(r['scene_rank'] and r['scene_rank'] <= 10) for r in members),
            })
        categories[cat] = entry

    payload = {
        'status': engine.status(),
        'categories': categories,
        'diagnoses': dict(Counter(r['diagnosis'] for r in rows)),
        'rows': rows,
    }
    (ROOT / out_rel).write_text(json.dumps(payload, indent=2), encoding='utf-8')
    return payload


def main():
    engine = SearchEngine(ROOT / 'data/dialoguematch.sqlite')
    try:
        print('Engine status:', json.dumps(engine.status(), indent=2), flush=True)
        quote_rep = evaluate(engine, ROOT / 'research/quote_pilot.json', ROOT / 'research/v2_quote_pilot.json')
        long_rep = evaluate(engine, ROOT / 'research/long_query_cases.json', ROOT / 'research/v2_long_queries.json')
        subset_rep = evaluate(engine, ROOT / 'research/movie_comparison_subset.json', ROOT / 'research/v2_movie_subset30.json')
        tot_rep = None
        if (ROOT / 'data/tot_benchmark.json').is_file():
            tot_rep = evaluate(engine, ROOT / 'data/tot_benchmark.json', ROOT / 'research/v2_tot_22.json')
        fresh_rep = run_fresh(engine, 'research/fresh150_queries.json', 'research/v2_fresh150_results.json')
        paired_rep = run_fresh(engine, 'research/fresh150_paired20_queries.json', 'research/v2_fresh150_paired20.json')

        summary = {
            'quote_pilot_span_hit5': quote_rep['span_hit5'],
            'long_queries_span_hit5': long_rep['span_hit5'],
            'long_queries_categories': long_rep['categories'],
            'movie_subset30_hit5': subset_rep['movie_hit5_on_available'],
            'tot22_movie_hit5': tot_rep['movie_hit5_on_available'] if tot_rep else None,
            'fresh150_categories': fresh_rep['categories'],
            'fresh150_diagnoses': fresh_rep['diagnoses'],
            'paired20_categories': paired_rep['categories'],
        }
        (ROOT / 'research/v2_benchmark_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        print('\n=== V2 BENCHMARK SUMMARY ===')
        print(json.dumps(summary, indent=2))
    finally:
        engine.close()


if __name__ == '__main__':
    main()
