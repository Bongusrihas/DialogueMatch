"""Optional movie-level retrieval from the CMU Movie Summary Corpus.

Plot text is not timestamped and is never used as evidence for a scene time.
"""
from collections import defaultdict
import csv
from pathlib import Path
import re
import sqlite3
import tarfile
import threading
from time import perf_counter

from .build import ROOT
from .text import normalize, search_content, terms

SOURCE = 'https://www.cs.cmu.edu/~ark/personas/'


def _title_variants(title: str) -> set[str]:
    norm = normalize(title)
    if not norm:
        return set()
    variants = {norm}
    for article in ('the ', 'a ', 'an '):
        if norm.startswith(article) and len(norm) > len(article) + 2:
            variants.add(norm[len(article):])
    # Also allow matching before a subtitle separator if reasonably distinctive.
    if ':' in title:
        head = normalize(title.split(':', 1)[0])
        if len(head.split()) >= 2:
            variants.add(head)
    return variants


def build_plot_index(db, archive, metadata=None):
    db, archive = Path(db), Path(archive)
    metadata = Path(metadata or ROOT / 'preprocessing/imdb_movies_2000_2025_high_voted.csv')
    con = sqlite3.connect(db)
    available = {row[0] for row in con.execute('SELECT id FROM movies')}
    con.close()

    exact_keys = defaultdict(set)
    near_keys = defaultdict(set)
    with metadata.open(encoding='utf-8-sig') as handle:
        for row in csv.DictReader(handle):
            mid = row.get('imdb_id')
            year_str = str(row.get('year', '')).strip()
            if mid in available and year_str.isdigit():
                yr = int(year_str)
                for raw_title in (row.get('title'), row.get('original_title')):
                    if not raw_title:
                        continue
                    exact_keys[(normalize(raw_title), yr)].add(mid)
                    for variant in _title_variants(raw_title):
                        for delta in (-1, 0, 1):
                            near_keys[(variant, yr + delta)].add(mid)

    if not exact_keys:
        raise ValueError('Plot matching needs catalog movie IDs, titles, and release years in the metadata CSV.')

    target = db.with_suffix('.plots.sqlite')
    temporary = db.with_suffix('.plots.building.sqlite')
    if temporary.exists():
        temporary.unlink()
    con = sqlite3.connect(temporary)
    con.execute("CREATE VIRTUAL TABLE plots USING fts5(movie_id UNINDEXED, wiki_id UNINDEXED, content, tokenize='porter unicode61')")

    with tarfile.open(archive, 'r:gz') as data:
        movie_file = next(m for m in data.getmembers() if m.name.endswith('/movie.metadata.tsv'))
        plot_file = next(m for m in data.getmembers() if m.name.endswith('/plot_summaries.txt'))
        ids = {}
        for raw in data.extractfile(movie_file):
            row = raw.decode('utf-8').rstrip('\n').split('\t')
            if len(row) >= 4 and row[3][:4].isdigit():
                yr = int(row[3][:4])
                norm_title = normalize(row[2])
                matches = exact_keys.get((norm_title, yr), set())
                if not matches:
                    matches = near_keys.get((norm_title, yr), set())
                if len(matches) == 1:
                    ids[row[0]] = next(iter(matches))

        covered = set()
        for raw in data.extractfile(plot_file):
            wiki, _, plot = raw.decode('utf-8').partition('\t')
            if wiki not in ids:
                continue
            movie = ids[wiki]
            covered.add(movie)
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', plot.strip()) if s.strip()]
            for i in range(0, len(sentences), 2):
                window = ' '.join(sentences[i:i + 4])
                if window:
                    con.execute('INSERT INTO plots VALUES (?,?,?)', (movie, wiki, window))
                if i + 4 >= len(sentences):
                    break

    con.execute("INSERT INTO plots(plots) VALUES('optimize')")
    con.commit()
    con.close()
    temporary.replace(target)
    print(f'Plot index ready: {len(covered)} movies; title and year matches are unverified.', flush=True)
    return target


class PlotSearch:
    def __init__(self, path, titles):
        self.uri = f'{Path(path).resolve().as_uri()}?mode=ro'
        self.titles = titles
        self._local = threading.local()
        # Validate database immediately on init
        self._conn()

    def _conn(self):
        con = getattr(self._local, 'con', None)
        if con is None:
            con = sqlite3.connect(self.uri, uri=True, check_same_thread=False)
            self._local.con = con
        return con

    def close(self):
        con = getattr(self._local, 'con', None)
        if con is not None:
            con.close()
            self._local.con = None

    def search(self, query, limit=5, movie_id=None):
        if not isinstance(query, str) or len(query) > 4000 or not normalize(query):
            raise ValueError('Enter a query of 1–4,000 characters containing words or numbers.')
        started = perf_counter()
        cleaned = search_content(query)
        tokens = terms(cleaned)[:40] or normalize(cleaned).split()[:40]
        if not tokens:
            return {'results': [], 'elapsed_ms': 0}

        con = self._conn()
        expression = ' OR '.join('"' + token + '"' for token in tokens)
        sql = 'SELECT movie_id, wiki_id, content, -bm25(plots) AS score FROM plots WHERE plots MATCH ?'
        args = [expression]
        if movie_id:
            sql += ' AND movie_id=?'
            args.append(movie_id)
        sql += ' ORDER BY bm25(plots) LIMIT 160'

        per_movie = defaultdict(list)
        for mid, wiki, content, score in con.execute(sql, args):
            if mid not in self.titles:
                continue
            per_movie[mid].append((float(score), wiki, content))

        # Also boost movies that match multiple distinct clue words within a single passage.
        if len(tokens) >= 2:
            ranked_tokens = sorted(tokens, key=len, reverse=True)[:6]
            pairs = [f'("{a}" AND "{b}")' for idx, a in enumerate(ranked_tokens) for b in ranked_tokens[idx + 1:idx + 3]]
            if pairs:
                pair_sql = 'SELECT movie_id, wiki_id, content, -bm25(plots) AS score FROM plots WHERE plots MATCH ?'
                pair_args = [' OR '.join(pairs)]
                if movie_id:
                    pair_sql += ' AND movie_id=?'
                    pair_args.append(movie_id)
                pair_sql += ' ORDER BY bm25(plots) LIMIT 60'
                for mid, wiki, content, score in con.execute(pair_sql, pair_args):
                    if mid in self.titles:
                        per_movie[mid].append((float(score) * 1.25, wiki, content))

        scored_movies = []
        for mid, hits in per_movie.items():
            # Deduplicate identical excerpts per movie and aggregate top-3 distinct plot windows
            seen_content = set()
            unique_hits = []
            for sc, wiki, content in sorted(hits, key=lambda item: item[0], reverse=True):
                if content not in seen_content:
                    seen_content.add(content)
                    unique_hits.append((sc, wiki, content))
            weights = (1.0, 0.35, 0.15)
            agg = sum(w * item[0] for w, item in zip(weights, unique_hits[:3]))
            best_sc, best_wiki, best_content = unique_hits[0]
            scored_movies.append((agg, mid, best_wiki, best_content))

        scored_movies.sort(key=lambda item: item[0], reverse=True)
        cap = max(1, min(int(limit), 20))
        results = [
            {
                'movie_id': mid,
                'title': self.titles.get(mid, mid),
                'excerpt': content,
                'source_url': 'https://en.wikipedia.org/?curid=' + wiki,
                'score': round(agg, 4),
            }
            for agg, mid, wiki, content in scored_movies[:cap]
        ]
        return {'results': results, 'elapsed_ms': round((perf_counter() - started) * 1000)}
