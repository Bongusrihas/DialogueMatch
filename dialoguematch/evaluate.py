"""Explicit movie-vs-scene evaluation with coverage and conflicting-label checks."""
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from .text import normalize


def _span_matches(result, movie, start, end):
    """Accept overlapping time spans in the same movie, independent of chunk IDs."""
    return (result['movie_id'] == movie and result['start'] < end
            and result['end'] > start)


def evaluate(engine, path, output):
    path = Path(path)
    if path.suffix == '.json':
        queries = json.loads(path.read_text(encoding='utf-8'))
    else:
        with path.open(encoding='utf-8-sig') as f:
            queries = list(csv.DictReader(f))
    labels = defaultdict(set)
    for q in queries:
        labels[normalize(q['query'])].add(q.get('scene_id') or q.get('imdb_id') or q.get('movie_id'))
    conflicts = {q for q, targets in labels.items() if len(targets) > 1}
    output_rows = []
    for index, q in enumerate(queries):
        movie = q.get('imdb_id') or q.get('movie_id')
        present = engine.con.execute('SELECT 1 FROM movies WHERE id=?', (movie,)).fetchone() is not None
        if normalize(q['query']) in conflicts:
            output_rows.append({'query': q['query'], 'status': 'conflicting_labels'})
            continue
        if not present:
            output_rows.append({'query': q['query'], 'status': 'movie_unavailable'})
            continue
        response = engine.search(q['query'], mode=q.get('mode', 'auto'), limit=10, debug=True)
        results = response['results']
        movie_rank = next((i for i, r in enumerate(results, 1) if r['movie_id'] == movie), None)
        scene_rank = None
        if q.get('scene_id'):
            scene_rank = next((i for i, r in enumerate(results, 1) if r['scene_id'] == q['scene_id']), None)
        span_rank = None
        expected_spans = q.get('spans') or ([] if q.get('start') in (None, '') or q.get('end') in (None, '') else [[q['start'], q['end']]])
        has_span = bool(expected_spans)
        if has_span:
            expected_spans = [(float(start), float(end)) for start, end in expected_spans]
            if any(start < 0 or end <= start for start, end in expected_spans):
                raise ValueError(f'Invalid expected time span for query: {q["query"]}')
            span_rank = next((i for i, r in enumerate(results, 1)
                              if any(_span_matches(r, movie, start, end) for start, end in expected_spans)), None)
        output_rows.append({'query': q['query'], 'status': 'evaluated', 'movie_rank': movie_rank,
                            'scene_rank': scene_rank, 'scene_label_available': bool(q.get('scene_id')),
                            'span_rank': span_rank, 'span_label_available': has_span,
                            'category': q.get('category', 'unspecified'),
                            'candidate_scene_hit': q.get('scene_id') in response['candidate_ids'] if q.get('scene_id') else None,
                            'top_scene_ids': [r['scene_id'] for r in results], 'elapsed_ms': response['elapsed_ms']})
        if index % 20 == 0:
            print(f'Evaluated {index + 1}/{len(queries)}', flush=True)
    valid = [r for r in output_rows if r['status'] == 'evaluated']
    scene = [r for r in valid if r['scene_label_available']]
    spans = [r for r in valid if r['span_label_available']]
    categories = {}
    for category in sorted({r['category'] for r in valid}):
        members = [r for r in valid if r['category'] == category]
        labeled = [r for r in members if r['span_label_available']]
        categories[category] = {'count': len(members),
                                'movie_hit5': sum(bool(r['movie_rank'] and r['movie_rank'] <= 5) for r in members) / len(members),
                                'span_labeled_rows': len(labeled),
                                'span_hit5': sum(bool(r['span_rank'] and r['span_rank'] <= 5) for r in labeled) / len(labeled) if labeled else None}
    times = sorted(r['elapsed_ms'] for r in valid)
    report = {'total': len(queries), 'evaluated': len(valid), 'conflicting_rows': sum(r['status'] == 'conflicting_labels' for r in output_rows),
              'missing_movie_rows': sum(r['status'] == 'movie_unavailable' for r in output_rows),
              'movie_hit5_on_available': sum(bool(r['movie_rank'] and r['movie_rank'] <= 5) for r in valid) / len(valid) if valid else None,
              'scene_labeled_rows': len(scene),
              'scene_hit5': sum(bool(r['scene_rank'] and r['scene_rank'] <= 5) for r in scene) / len(scene) if scene else None,
              'scene_mrr10': sum(1 / r['scene_rank'] if r['scene_rank'] else 0 for r in scene) / len(scene) if scene else None,
              'span_labeled_rows': len(spans),
              'span_hit5': sum(bool(r['span_rank'] and r['span_rank'] <= 5) for r in spans) / len(spans) if spans else None,
              'span_mrr10': sum(1 / r['span_rank'] if r['span_rank'] else 0 for r in spans) / len(spans) if spans else None,
              'candidate_recall_generated': sum(r['candidate_scene_hit'] for r in scene) / len(scene) if scene else None,
              'latency_median_ms': statistics.median(times) if times else None,
              'latency_p95_ms': times[math.ceil(0.95 * len(times)) - 1] if times else None,
              'categories': categories,
              'note': 'Movie metrics do not measure scene accuracy. Available-corpus metrics exclude missing movies. These labels have not been independently verified.',
              'rows': output_rows}
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))
    return report
