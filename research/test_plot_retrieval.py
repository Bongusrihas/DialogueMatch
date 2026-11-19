"""Experimental movie-level plot retrieval; never assigns a plot hit a timestamp."""
import csv
import json
import re
import sqlite3
import sys
import tarfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dialoguematch.text import normalize, terms


def main():
    archive = ROOT / 'data/MovieSummaries.tar.gz'
    metadata = defaultdict(set)
    with (ROOT / 'preprocessing/imdb_movies_2000_2025_high_voted.csv').open(encoding='utf-8-sig') as handle:
        for row in csv.DictReader(handle):
            for title in (row['title'], row['original_title']):
                if title and row['year']:
                    metadata[(normalize(title), row['year'])].add(row['imdb_id'])
    with tarfile.open(archive, 'r:gz') as data:
        movie_file = next(m for m in data.getmembers() if m.name.endswith('/movie.metadata.tsv'))
        plot_file = next(m for m in data.getmembers() if m.name.endswith('/plot_summaries.txt'))
        ids = {}
        for raw in data.extractfile(movie_file):
            fields = raw.decode('utf-8').rstrip('\n').split('\t')
            if len(fields) < 4:
                continue
            matches = metadata.get((normalize(fields[2]), fields[3][:4]), set())
            if len(matches) == 1:
                ids[fields[0]] = next(iter(matches))
        con = sqlite3.connect(':memory:')
        con.execute("CREATE VIRTUAL TABLE plots USING fts5(movie_id UNINDEXED, content, tokenize='porter unicode61')")
        covered = set()
        for raw in data.extractfile(plot_file):
            wiki_id, _, plot = raw.decode('utf-8').partition('\t')
            if wiki_id not in ids:
                continue
            movie = ids[wiki_id]
            covered.add(movie)
            sentences = re.split(r'(?<=[.!?])\s+', plot.strip())
            for i in range(0, len(sentences), 2):
                con.execute('INSERT INTO plots VALUES (?,?)', (movie, normalize(' '.join(sentences[i:i + 3]))))
    baseline = json.loads((ROOT / 'research/baseline_movie_no_rerank.json').read_text(encoding='utf-8'))
    labels = {r['query']: r['imdb_id'] for r in csv.DictReader((ROOT / 'preprocessing/evaluation_set.csv').open(encoding='utf-8-sig'))}
    development = {r['query'] for r in json.loads((ROOT / 'research/movie_comparison_subset.json').read_text(encoding='utf-8'))}
    output = []
    for row in baseline['rows']:
        query = row['query']
        tokens = terms(query)[:30]
        expr = ' OR '.join('"' + t + '"' for t in tokens)
        found = [r[0] for r in con.execute('SELECT movie_id FROM plots WHERE plots MATCH ? ORDER BY bm25(plots) LIMIT 100', (expr,))] if expr else []
        movies = list(dict.fromkeys(found))
        target = labels[query]
        output.append({'query': query, 'expected_movie': target, 'covered': target in covered,
                       'split': 'development' if query in development else 'comparison',
                       'plot_rank': movies.index(target) + 1 if target in movies else None,
                       'baseline_rank': row['movie_rank'], 'baseline_top': list(dict.fromkeys(s.rsplit('_', 1)[0] for s in row['top_scene_ids'])),
                       'plot_top': movies[:30]})
    report = {'source': 'https://www.cs.cmu.edu/~ark/personas/', 'matching': 'unique normalized title and exact release year; not independently verified',
              'covered_catalog_movies': len(covered), 'rows': output}
    for split in ('development', 'comparison'):
        subset = [r for r in output if r['split'] == split]
        subset_covered = [r for r in subset if r['covered']]
        report[split] = {'queries': len(subset), 'covered_queries': len(subset_covered),
                         'plot_hit5_all': sum(bool(r['plot_rank'] and r['plot_rank'] <= 5) for r in subset) / len(subset),
                         'plot_hit5_covered': sum(bool(r['plot_rank'] and r['plot_rank'] <= 5) for r in subset_covered) / len(subset_covered) if subset_covered else None,
                         'baseline_hit5_covered': sum(bool(r['baseline_rank'] and r['baseline_rank'] <= 5) for r in subset_covered) / len(subset_covered) if subset_covered else None}
    (ROOT / 'research/plot_experiment.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
