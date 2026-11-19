from bisect import bisect_right
from collections import OrderedDict, defaultdict
import difflib
import json
import math
from pathlib import Path
import re
import sqlite3
import threading
from time import perf_counter

from .context import act_label_for_progress, decompose_query
from .query import analyze_query
from .text import normalize, search_content, terms, timestamp

try:
    from rapidfuzz.fuzz import ratio as _upper_ratio
except ImportError:
    _upper_ratio = None


def rrf(rankings, constant=60):
    scores = defaultdict(float)
    for ranking in rankings:
        for rank, sid in enumerate(dict.fromkeys(ranking), 1):
            scores[sid] += 1 / (constant + rank)
    return dict(scores)


def best_fuzzy(query, text, minimum=0.0):
    q, words = normalize(query).split(), normalize(text).split()
    if not q or not words:
        return 0.0
    n = len(q)
    query_text = ' '.join(q)
    best = 0.0
    for width in {max(1, n - 1), n, n + 1}:
        for i in range(len(words)):
            candidate = ' '.join(words[i:i + width])
            cutoff = max(best, minimum)
            if _upper_ratio is not None and _upper_ratio(query_text, candidate) / 100 + 1e-12 < cutoff:
                continue
            matcher = difflib.SequenceMatcher(None, query_text, candidate)
            if _upper_ratio is None and matcher.quick_ratio() < cutoff:
                continue
            best = max(best, matcher.ratio())
    return best


def _one_edit_apart(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        different = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        return len(different) == 1 or (
            len(different) == 2
            and different[1] == different[0] + 1
            and a[different[0]] == b[different[1]]
            and a[different[1]] == b[different[0]]
        )
    short, long = (a, b) if len(a) < len(b) else (b, a)
    return any(short == long[:i] + long[i + 1:] for i in range(len(long)))


class SearchEngine:
    def __init__(self, db, neural=True, rerank=True):
        self.path = Path(db)
        if not self.path.exists():
            raise FileNotFoundError('Build the corpus first: python -m dialoguematch build')
        self._uri = f'{self.path.resolve().as_uri()}?mode=ro'
        self._local = threading.local()
        self.con = self._open_con()
        self._local.con = self.con

        self.manifest = json.loads(self.con.execute("SELECT value FROM meta WHERE key='manifest'").fetchone()[0])
        self._has_sequences = (
            self.con.execute("SELECT 1 FROM sqlite_master WHERE name='sequences'").fetchone() is not None
        )
        movie_cols = {row[1] for row in self.con.execute('PRAGMA table_info(movies)')}
        self._has_movie_stats = 'votes' in movie_cols and 'year' in movie_cols
        scene_cols = {row[1] for row in self.con.execute('PRAGMA table_info(scenes)')}
        self._has_rich_scenes = 'paraphrase' in scene_cols

        self.semantic = None
        self.reranker = None
        self.plots = None
        self.context_index = None
        self.warnings = []
        self._vocab_lock = threading.Lock()
        self._quote_vocab_by_len: dict[int, list[tuple[int, str]]] | None = None
        self._quote_vocab_set: set[str] | None = None
        self._search_doc_freq: dict[str, int] | None = None
        self._total_docs = max(1, int(self.manifest.get('stats', {}).get('scenes', 1)))
        self._movie_cache_lock = threading.Lock()
        self._movie_bm25_cache: OrderedDict[str, list[tuple[str, dict[str, int], dict[str, int], dict[str, int]]]] = OrderedDict()

        # Preload lightweight movie metadata lookup for instant title resolution and popularity priors.
        self._movies_by_id: dict[str, dict] = {}
        self._title_index: dict[str, list[str]] = defaultdict(list)
        if self._has_movie_stats:
            for r in self.con.execute('SELECT id, title, year, rating, votes, details FROM movies'):
                info = {
                    'id': r['id'],
                    'title': r['title'],
                    'year': int(r['year'] or 0),
                    'rating': float(r['rating'] or 0.0),
                    'votes': int(r['votes'] or 0),
                }
                self._movies_by_id[r['id']] = info
                norm_t = normalize(r['title'])
                if norm_t:
                    self._title_index[norm_t].append(r['id'])
                try:
                    orig = normalize(json.loads(r['details'] or '{}').get('original_title', ''))
                    if orig and orig != norm_t:
                        self._title_index[orig].append(r['id'])
                except ValueError:
                    pass
        else:
            for r in self.con.execute('SELECT id, title FROM movies'):
                self._movies_by_id[r['id']] = {'id': r['id'], 'title': r['title'], 'year': 0, 'rating': 0.0, 'votes': 0}
                norm_t = normalize(r['title'])
                if norm_t:
                    self._title_index[norm_t].append(r['id'])

        if self.path.with_suffix('.plots.sqlite').exists():
            from .plots import PlotSearch
            titles = {mid: info['title'] for mid, info in self._movies_by_id.items()}
            self.plots = PlotSearch(self.path.with_suffix('.plots.sqlite'), titles)

        if self.path.with_suffix('.context.sqlite').exists():
            try:
                from .context import MovieContextIndex
                self.context_index = MovieContextIndex(self.path, neural=neural)
            except (OSError, ValueError):
                self.context_index = None

        if neural and self.path.with_suffix('.vectors.json').exists():
            from .neural import MultiIndexSemanticSearch, SemanticSearch
            base_semantic = SemanticSearch(self.path)
            if MultiIndexSemanticSearch.is_available(self.path):
                self.semantic = MultiIndexSemanticSearch(self.path, fallback=base_semantic)
            else:
                self.semantic = base_semantic
        elif neural:
            self.warnings.append('Semantic index not built; using lexical and phrase retrieval.')

        if rerank:
            from .neural import Reranker
            self.reranker = Reranker()

    def _open_con(self):
        con = sqlite3.connect(self._uri, uri=True, check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    def _conn(self):
        con = getattr(self._local, 'con', None)
        if con is None:
            con = self._open_con()
            self._local.con = con
        return con

    def close(self):
        if self.plots:
            self.plots.close()
        if self.context_index:
            self.context_index.close()
        con = getattr(self._local, 'con', None)
        if con is not None and con is not self.con:
            con.close()
        self.con.close()

    def status(self):
        semantic_mode = (
            'multi_index_ensemble'
            if hasattr(self.semantic, 'search_channels')
            else ('single_index' if self.semantic is not None else 'disabled')
        )
        return {
            'stats': self.manifest['stats'],
            'semantic': self.semantic is not None,
            'semantic_mode': semantic_mode,
            'semantic_scenes': len(self.semantic.ids) if self.semantic else 0,
            'reranker': self.reranker is not None,
            'reranker_model': getattr(self.reranker, 'model_name', None) if self.reranker else None,
            'plot_search': self.plots is not None,
            'global_context': self.context_index is not None,
            'sequence_search': self._has_sequences,
            'warnings': self.warnings,
        }

    def movie_dossier(self, movie_spec: str):
        mid = self.resolve_movie(movie_spec)
        if not mid:
            raise ValueError('Movie not found in library.')
        if self.context_index and mid in self.context_index.dossiers:
            return self.context_index.dossiers[mid]
        return self._movies_by_id.get(mid, {'id': mid, 'title': mid})

    def resolve_movie(self, movie_spec):
        """Resolve an IMDb ID or movie title string to a canonical catalog movie ID."""
        if not movie_spec:
            return None
        spec = str(movie_spec).strip()
        if not spec:
            return None
        if spec in self._movies_by_id:
            return spec
        # Explicit IMDb-style IDs that are absent must report movie_unavailable rather than fuzzy-guessing.
        if re.match(r'^tt[_0-9A-Za-z]+$', spec):
            return None

        year_match = re.search(r'\((\d{4})\)\s*$', spec)
        year_hint = int(year_match.group(1)) if year_match else 0
        title_part = spec[:year_match.start()].strip() if year_match else spec
        norm = normalize(title_part)
        if not norm:
            return None
        candidates = self._title_index.get(norm, [])
        if candidates:
            if year_hint:
                exact_yr = [m for m in candidates if self._movies_by_id[m]['year'] == year_hint]
                if exact_yr:
                    candidates = exact_yr
            return max(candidates, key=lambda m: self._movies_by_id[m]['votes'])
        return None

    def catalog_search(self, query='', limit=15):
        """Return matching catalog movies for UI autocomplete and CLI lookup."""
        cap = max(1, min(50, int(limit)))
        q = str(query or '').strip()
        if not q:
            ordered = sorted(self._movies_by_id.values(), key=lambda m: (m['votes'], m['rating']), reverse=True)
            return {'results': ordered[:cap]}

        q_low = q.casefold()
        q_norm = normalize(q)
        q_tokens = set(q_norm.split())
        scored = []
        for mid, info in self._movies_by_id.items():
            title_norm = normalize(info['title'])
            if mid.casefold().startswith(q_low):
                tier = 4
            elif title_norm == q_norm:
                tier = 3
            elif title_norm.startswith(q_norm) and q_norm:
                tier = 2
            elif q_norm and q_norm in title_norm:
                tier = 1
            elif q_tokens and q_tokens.issubset(set(title_norm.split())):
                tier = 1
            else:
                continue
            scored.append((tier, info['votes'], info['rating'], info))
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return {'results': [item[3] for item in scored[:cap]]}

    def scene_context(self, scene_id: str, neighbors: int = 1):
        """Return a scene along with its immediate chronological neighbors in the same movie."""
        con = self._conn()
        neighbors = max(0, min(3, int(neighbors)))
        target = con.execute('SELECT * FROM scenes WHERE id=?', (scene_id,)).fetchone()
        if not target:
            raise ValueError('Requested scene ID was not found in the library.')
        mid = target['movie_id']
        movie_info = self._movies_by_id.get(mid, {'id': mid, 'title': mid, 'year': 0, 'rating': 0.0})
        all_scenes = con.execute(
            'SELECT id, start, end, text, summary, lines FROM scenes WHERE movie_id=? ORDER BY start',
            (mid,),
        ).fetchall()
        idx = next((i for i, r in enumerate(all_scenes) if r['id'] == scene_id), 0)
        lo = max(0, idx - neighbors)
        hi = min(len(all_scenes), idx + neighbors + 1)
        window = []
        for r in all_scenes[lo:hi]:
            lines = json.loads(r['lines'] or '[]')
            window.append({
                'scene_id': r['id'],
                'is_target': r['id'] == scene_id,
                'start': r['start'],
                'end': r['end'],
                'start_label': timestamp(r['start']),
                'end_label': timestamp(r['end']),
                'summary': r['summary'],
                'dialogue': r['text'],
                'lines': [
                    {
                        'start': ln['start'],
                        'end': ln['end'],
                        'start_label': timestamp(ln['start']),
                        'text': ln['text'],
                    }
                    for ln in lines[:60]
                ],
            })
        return {'movie': movie_info, 'scene_id': scene_id, 'window': window}

    def _ensure_search_df(self):
        if self._search_doc_freq is not None:
            return
        with self._vocab_lock:
            if self._search_doc_freq is not None:
                return
            con = self._open_con()
            try:
                con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.search_vocab USING fts5vocab(main, search, 'row')")
                self._search_doc_freq = {row[0]: int(row[1]) for row in con.execute('SELECT term, doc FROM temp.search_vocab')}
            finally:
                con.close()

    def _ensure_quote_vocab(self):
        if self._quote_vocab_by_len is not None:
            return
        with self._vocab_lock:
            if self._quote_vocab_by_len is not None:
                return
            con = self._open_con()
            try:
                con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS temp.quote_vocab USING fts5vocab(main, quotes, 'row')")
                by_len: dict[int, list[tuple[int, str]]] = defaultdict(list)
                vset: set[str] = set()
                for term, doc in con.execute('SELECT term, doc FROM temp.quote_vocab'):
                    if 3 <= len(term) <= 22 and term.isalpha():
                        by_len[len(term)].append((int(doc), term))
                        vset.add(term)
                self._quote_vocab_by_len = dict(by_len)
                self._quote_vocab_set = vset
            finally:
                con.close()

    def _rare_clue_expression(self, tokens: list[str]) -> str | None:
        """Build a pairwise conjunction of the rarest query terms so multi-clue descriptions don't zero out."""
        if len(tokens) < 3:
            return None
        self._ensure_search_df()
        df_map = self._search_doc_freq or {}

        def approx_df(tok: str) -> int:
            if tok in df_map:
                return df_map[tok]
            # Approximate stem lookup for Porter-tokenized index
            for trim in (1, 2, 3):
                if len(tok) - trim >= 4 and tok[:-trim] in df_map:
                    return df_map[tok[:-trim]]
            return self._total_docs // 20

        ranked = sorted(tokens, key=lambda t: (approx_df(t), -len(t)))
        # Keep up to 5 rarest informative clue words and require any 2 of them together.
        top_rare = ranked[:min(5, len(ranked))]
        pairs = []
        for i in range(len(top_rare)):
            for j in range(i + 1, len(top_rare)):
                pairs.append(f'("{top_rare[i]}" AND "{top_rare[j]}")')
        return ' OR '.join(pairs[:8]) if pairs else None

    @staticmethod
    def _term_counts(text: str) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for tok in normalize(text).split():
            counts[tok] += 1
        return dict(counts)

    def _get_movie_bm25_entries(self, movie_id: str):
        with self._movie_cache_lock:
            cached = self._movie_bm25_cache.get(movie_id)
            if cached is not None:
                self._movie_bm25_cache.move_to_end(movie_id)
                return cached

        con = self._conn()
        if self._has_rich_scenes:
            records = con.execute(
                'SELECT id, text, summary, paraphrase, relationship, emotion, queries, keywords FROM scenes WHERE movie_id=?',
                (movie_id,),
            ).fetchall()
        else:
            records = con.execute(
                'SELECT id, text, summary, queries, keywords FROM scenes WHERE movie_id=?',
                (movie_id,),
            ).fetchall()

        entries = []
        for r in records:
            queries_list = json.loads(r['queries'] or '[]')
            keywords_list = json.loads(r['keywords'] or '[]')
            if self._has_rich_scenes:
                desc = ' '.join(p for p in [r['summary'], r['paraphrase'], r['relationship'], *queries_list] if p)
                kw = ' '.join(p for p in [*keywords_list, r['emotion']] if p)
            else:
                desc = ' '.join([r['summary'], *queries_list])
                kw = ' '.join(keywords_list)
            entries.append((r['id'], self._term_counts(r['text']), self._term_counts(desc), self._term_counts(kw)))

        with self._movie_cache_lock:
            self._movie_bm25_cache[movie_id] = entries
            while len(self._movie_bm25_cache) > 64:
                self._movie_bm25_cache.popitem(last=False)
        return entries

    def _lexical_movie_fast(self, query_terms: list[str], limit: int, movie_id: str) -> list[str]:
        """Thread-safe, sub-millisecond in-memory BM25 over a single movie's scenes using corpus-wide IDF."""
        self._ensure_search_df()
        df_map = self._search_doc_freq or {}
        entries = self._get_movie_bm25_entries(movie_id)
        if not entries or not query_terms:
            return []

        scored = []
        n_docs = self._total_docs
        for sid, dia_tf, desc_tf, kw_tf in entries:
            total = 0.0
            dia_len = max(1, sum(dia_tf.values()))
            desc_len = max(1, sum(desc_tf.values()))
            kw_len = max(1, sum(kw_tf.values()))
            for q in query_terms:
                df = df_map.get(q)
                if df is None and len(q) >= 5:
                    df = df_map.get(q[:-1]) or df_map.get(q[:-2])
                idf = math.log(1.0 + (n_docs - (df or 50) + 0.5) / ((df or 50) + 0.5))

                # Match exact token or shared 5+ char prefix for morphological alignment with Porter stemming
                for tf_map, doc_len, avg_len, weight in (
                    (dia_tf, dia_len, 110.0, 1.0),
                    (desc_tf, desc_len, 55.0, 1.35),
                    (kw_tf, kw_len, 12.0, 0.85),
                ):
                    tf = tf_map.get(q, 0)
                    if tf == 0 and len(q) >= 5:
                        stem = q[:max(4, len(q) - 2)]
                        tf = sum(cnt for tok, cnt in tf_map.items() if len(tok) >= 4 and tok.startswith(stem))
                    if tf > 0:
                        denom = tf + 1.2 * (0.25 + 0.75 * (doc_len / avg_len))
                        total += weight * idf * (tf * 2.2) / denom
            if total > 0.0:
                scored.append((total, sid))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [sid for _, sid in scored[:limit]]

    def _lexical(self, expression, limit, movie_id=None):
        con = self._conn()
        if movie_id:
            # Fast thread-safe path for standard OR term expressions
            if ' AND ' not in expression and '(' not in expression:
                extracted = re.findall(r'"([^"]+)"', expression)
                if extracted:
                    return self._lexical_movie_fast(extracted, limit, movie_id)

            # Boolean fallback using per-thread temp FTS5 table
            if getattr(self._local, 'indexed_movie', None) != movie_id:
                con.execute(
                    'CREATE VIRTUAL TABLE IF NOT EXISTS temp.movie_search '
                    'USING fts5(id UNINDEXED, dialogue, description, keywords, tokenize="porter unicode61")'
                )
                con.execute('DELETE FROM temp.movie_search')
                records = con.execute(
                    'SELECT id, text, summary, queries, keywords FROM scenes WHERE movie_id=?',
                    (movie_id,),
                ).fetchall()
                con.executemany(
                    'INSERT INTO temp.movie_search VALUES (?,?,?,?)',
                    [
                        (
                            r['id'],
                            normalize(r['text']),
                            normalize(' '.join([r['summary'], *json.loads(r['queries'] or '[]')])),
                            normalize(' '.join(json.loads(r['keywords'] or '[]'))),
                        )
                        for r in records
                    ],
                )
                self._local.indexed_movie = movie_id
            return [
                r[0]
                for r in con.execute(
                    'SELECT id FROM temp.movie_search WHERE movie_search MATCH ? ORDER BY bm25(movie_search,0,1,1.3,0.8) LIMIT ?',
                    (expression, limit),
                )
            ]

        return [
            r[0]
            for r in con.execute(
                "SELECT id FROM search WHERE search MATCH ? AND rank MATCH 'bm25(0,1,1.35,0.85)' ORDER BY rank LIMIT ?",
                (expression, limit),
            )
        ]

    def _sequence_candidates(self, expression: str, limit: int = 25, movie_id: str | None = None) -> list[str]:
        """Retrieve scenes belonging to multi-scene chronological narrative windows matching distributed clues."""
        if not self._has_sequences or not expression:
            return []
        con = self._conn()
        sql = 'SELECT movie_id, scene_ids FROM sequences WHERE sequences MATCH ?'
        args = [expression]
        if movie_id:
            sql += ' AND movie_id=?'
            args.append(movie_id)
        sql += ' ORDER BY bm25(sequences) LIMIT 30'
        candidates = []
        seen = set()
        for row in con.execute(sql, args):
            sids = json.loads(row['scene_ids'])
            # Pick the best matching scene inside this 4-scene window
            q_tokens = re.findall(r'"([^"]+)"', expression)
            best_in_win = self._lexical_movie_fast(q_tokens, 2, row['movie_id']) if q_tokens else []
            chosen = [sid for sid in best_in_win if sid in sids] or sids[:2]
            for sid in chosen:
                if sid not in seen:
                    seen.add(sid)
                    candidates.append(sid)
                    if len(candidates) >= limit:
                        return candidates
        return candidates

    def _phrases(self, query, movie_id=None):
        con = self._conn()
        norm_q = normalize(query)
        if not norm_q:
            return {}
        sql = 'SELECT q.scene_id, q.start, q.end, q.raw FROM quotes q CROSS JOIN scenes s ON s.id=q.scene_id WHERE quotes MATCH ?'
        args = ['"' + norm_q + '"']
        if movie_id:
            sql += ' AND s.movie_id=?'
            args.append(movie_id)
        sql += ' ORDER BY bm25(quotes) LIMIT 1000'
        result = {}
        for row in con.execute(sql, args):
            sid = row['scene_id']
            span = {'start': float(row['start']), 'end': float(row['end']), 'text': row['raw'], 'query': norm_q}
            if sid not in result or span['end'] - span['start'] < result[sid]['end'] - result[sid]['start']:
                result[sid] = span
        return result

    def _long_phrases(self, query, movie_id=None):
        """Verify a long quotation against ordered original subtitle lines."""
        con = self._conn()
        words = normalize(query).split()
        if len(words) < 15:
            return {}
        anchors = list(dict.fromkeys([0, len(words) // 2, max(0, len(words) - 8)]))
        movies = set()
        for offset in anchors:
            for sid in self._phrases(' '.join(words[offset:offset + 8]), movie_id):
                row = con.execute('SELECT movie_id FROM scenes WHERE id=?', (sid,)).fetchone()
                if row:
                    movies.add(row[0])
        needle = ' '.join(words)
        matches = {}
        for mid in sorted(movies)[:20]:
            unique = {}
            for row in con.execute('SELECT lines FROM scenes WHERE movie_id=? ORDER BY start', (mid,)):
                for line in json.loads(row[0]):
                    unique[(line['start'], line['end'], line['text'])] = line
            lines = sorted(unique.values(), key=lambda line: (line['start'], line['end']))
            starts, pieces, cursor = [], [], 0
            kept = []
            for line in lines:
                text = normalize(line['text'])
                if text:
                    starts.append(cursor)
                    pieces.append(text)
                    kept.append(line)
                    cursor += len(text) + 1
            document = ' '.join(pieces)
            offset = (' ' + document + ' ').find(' ' + needle + ' ')
            while offset >= 0 and len(matches) < 200:
                first = bisect_right(starts, offset) - 1
                last = bisect_right(starts, offset + len(needle) - 1) - 1
                selected = kept[first:last + 1]
                owner = con.execute(
                    'SELECT id FROM scenes WHERE movie_id=? AND start<=? AND end>? ORDER BY start DESC LIMIT 1',
                    (mid, selected[0]['start'] + 0.05, selected[0]['start']),
                ).fetchone()
                if owner:
                    matches[owner[0]] = {
                        'start': selected[0]['start'],
                        'end': selected[-1]['end'],
                        'text': ' '.join(line['text'] for line in selected),
                        'query': needle,
                    }
                offset = (' ' + document + ' ').find(' ' + needle + ' ', offset + 1)
        return matches

    def _typo_candidates(self, tokens, movie_id=None):
        """Find quote candidates for misspelled dialogue words, including first-letter transpositions and suffixes."""
        self._ensure_quote_vocab()
        vocab_by_len = self._quote_vocab_by_len or {}
        vocab_set = self._quote_vocab_set or set()

        groups = []
        changed = False
        for token in tokens:
            choices = [token]
            if 3 <= len(token) <= 20 and token.isalpha() and token not in vocab_set:
                candidates = []
                for length in (len(token) - 1, len(token), len(token) + 1):
                    for doc_count, word in vocab_by_len.get(length, ()):
                        if _one_edit_apart(token, word):
                            candidates.append((doc_count, word))
                candidates.sort(reverse=True)
                suggestions = [word for _, word in candidates[:4]]
                choices += suggestions
                changed = changed or bool(suggestions)
            groups.append('(' + ' OR '.join('"' + word + '"' for word in dict.fromkeys(choices)) + ')')
        return self._lexical(' AND '.join(groups), 100, movie_id) if changed and groups else []

    def search(self, query, mode='auto', limit=10, movie_id=None, debug=False, retrieval='combined'):
        started = perf_counter()
        if mode not in {'auto', 'quote', 'scene'}:
            raise ValueError('mode must be auto, quote, or scene')
        if not isinstance(query, str) or len(query) > 4000 or not normalize(query):
            raise ValueError('Enter a query of 1–4,000 characters containing words or numbers.')
        if retrieval not in {'combined', 'index'}:
            raise ValueError('Search type must be combined or index.')
        limit = max(1, min(30, int(limit)))

        resolved_movie = None
        if movie_id:
            resolved_movie = self.resolve_movie(movie_id)
            if resolved_movie is None:
                return {
                    'query': query,
                    'status': 'movie_unavailable',
                    'results': [],
                    'message': 'This movie is not in the current library.',
                    'elapsed_ms': 0,
                }
        movie_id = resolved_movie

        if retrieval == 'index':
            return self._search_index(query, mode, limit, movie_id, debug, started)

        con = self._conn()
        plan = analyze_query(query, mode=mode)
        decomp = decompose_query(query, mode=mode)
        normalized = plan.normalized

        exact = self._phrases(query, movie_id) if mode != 'scene' else {}
        if mode != 'scene' and not exact:
            exact = self._long_phrases(query, movie_id)
        exact_from_embedded = False
        if mode != 'scene' and not exact and plan.embedded_quotes:
            for quote in plan.embedded_quotes:
                found = self._phrases(quote, movie_id) or self._long_phrases(quote, movie_id)
                if found:
                    exact.update(found)
                    exact_from_embedded = True

        # Only run full context retrieval alongside exact matches when an embedded quote matched
        # multiple distinct movies and the user provided extra descriptive context outside the quote.
        exact_movies = {sid.rsplit('_', 1)[0] for sid in exact}
        need_context_for_exact = bool(exact and exact_from_embedded and plan.has_external_context and len(exact_movies) > 1)
        skip_broad_channels = bool(exact and not need_context_for_exact)

        # When the query explicitly separates Global Film Context ('starts with X...') from Target Scene ('and in one scene Y...'),
        # focus scene-level channels and cross-encoder reranking on the Target Scene while routing Global Film Context to Movie Dossiers.
        use_decomposed = bool(decomp.is_decomposed and mode != 'quote' and not skip_broad_channels)
        scene_plan = analyze_query(decomp.scene_target, mode=mode) if use_decomposed else plan

        retrieval_query = scene_plan.retrieval_query if mode != 'quote' and not skip_broad_channels else query
        all_tokens = scene_plan.all_tokens
        tokens = scene_plan.tokens
        expression = ' OR '.join('"' + token + '"' for token in tokens)

        rankings = []
        channels = {}

        lexical = self._lexical(expression, 150, movie_id) if not skip_broad_channels else []
        rankings.append(lexical)
        channels['keyword'] = lexical

        # Retain a secondary full-query lexical recall path when decomposed in case global + scene clues co-occur in one chunk
        if use_decomposed and plan.tokens:
            full_expr = ' OR '.join('"' + tok + '"' for tok in plan.tokens)
            full_lex = self._lexical(full_expr, 60, movie_id)
            if full_lex:
                rankings.append(full_lex)
                channels['full_query_lexical'] = full_lex

        if len(tokens) > 1 and not skip_broad_channels:
            if len(tokens) <= 7:
                conjunctive = self._lexical(' AND '.join('"' + token + '"' for token in tokens), 100, movie_id)
            else:
                conjunctive = []
            rankings.append(conjunctive)
            channels['all_clues'] = conjunctive

            rare_expr = self._rare_clue_expression(tokens)
            if rare_expr:
                rare_hits = self._lexical(rare_expr, 100, movie_id)
                if rare_hits:
                    rankings.append(rare_hits)
                    channels['rare_clues'] = rare_hits

        if scene_plan.speech_terms and not skip_broad_channels and mode != 'quote':
            speech_expr = ' OR '.join(f'dialogue:"{tok}"' for tok in scene_plan.speech_terms[:10])
            try:
                speech_hits = self._lexical(speech_expr, 80, movie_id)
            except sqlite3.OperationalError:
                speech_hits = []
            if speech_hits:
                rankings.append(speech_hits)
                channels['speech_clues'] = speech_hits

        if scene_plan.number_anchors and not skip_broad_channels:
            anchors = self._lexical(' OR '.join('"' + t + '"' for t in scene_plan.number_anchors), 100, movie_id)
            rankings.append(anchors)
            channels['numbers'] = anchors

        if not skip_broad_channels and mode in {'quote', 'auto'}:
            words = normalize(retrieval_query).split() if use_decomposed else normalized.split()
            partial = []
            if 4 <= len(words) <= 45:
                for offset in range(min(8, len(words) - 2)):
                    phrase = ' '.join(words[offset:offset + 3])
                    if terms(phrase):
                        partial.extend(self._phrases(phrase, movie_id))
            dedup_partial = list(dict.fromkeys(partial))
            rankings.append(dedup_partial)
            channels['quote_fragments'] = dedup_partial

        allowed = None
        if self.semantic is not None and mode != 'quote' and not skip_broad_channels:
            if movie_id:
                allowed = {r[0] for r in con.execute('SELECT id FROM scenes WHERE movie_id=?', (movie_id,))}
            if hasattr(self.semantic, 'search_channels'):
                sem_channels = self.semantic.search_channels(retrieval_query, 150, allowed)
                sem_combined_scores = defaultdict(float)
                for ch_name, (ch_weight, ch_hits) in sem_channels.items():
                    channels[ch_name] = ch_hits
                    rankings.append(ch_hits)
                    for r_idx, sid in enumerate(ch_hits, 1):
                        sem_combined_scores[sid] += ch_weight / (60 + r_idx)
                semantic = sorted(sem_combined_scores, key=sem_combined_scores.get, reverse=True)[:150]
                channels['semantic'] = semantic
            else:
                semantic = self.semantic.search(retrieval_query, 150, allowed)
                rankings.append(semantic)
                channels['semantic'] = semantic

        if not skip_broad_channels and mode != 'quote' and self._has_sequences:
            seq_expr = self._rare_clue_expression(tokens) or expression
            seq_hits = self._sequence_candidates(seq_expr, 30, movie_id)
            if seq_hits:
                rankings.append(seq_hits)
                channels['sequences'] = seq_hits

        # Global Movie Context Brain: identify candidate Film Worlds from whole-movie dossiers & zoom into their scenes
        matched_movies = []
        global_movie_map = {}
        global_guided_candidates = []
        if self.context_index is not None and mode != 'quote' and not skip_broad_channels:
            if movie_id:
                if movie_id in self.context_index.dossiers:
                    dos = self.context_index.dossiers[movie_id]
                    matched_movies = [{
                        'movie_id': movie_id,
                        'title': dos['title'],
                        'year': dos['year'],
                        'rating': dos['rating'],
                        'characters': dos['characters'][:140],
                        'themes': dos['themes'][:120],
                        'premise': dos['core_premise'][:260],
                        'confidence': 1.0,
                        'raw_score': 1.0,
                    }]
            else:
                g_query = decomp.global_context if use_decomposed else plan.retrieval_query
                sec_query = decomp.scene_target if use_decomposed else ''
                matched_movies = self.context_index.search_movies(
                    g_query,
                    secondary_query=sec_query,
                    opening_focus=decomp.global_checks_opening,
                    ending_focus=(decomp.temporal_hint == 'ending'),
                    limit=8,
                )
            for m_idx, gm in enumerate(matched_movies):
                global_movie_map[gm['movie_id']] = (m_idx, gm)

            # When decomposed (user gave intro/premise + target scene), zoom inside top matched films for the target scene!
            if use_decomposed and matched_movies and not movie_id:
                for gm in matched_movies[:6]:
                    mid = gm['movie_id']
                    in_movie_lex = self._lexical_movie_fast(tokens, 4, mid)
                    global_guided_candidates.extend(in_movie_lex)
                    if self.semantic is not None:
                        m_allowed = {r[0] for r in con.execute('SELECT id FROM scenes WHERE movie_id=?', (mid,))}
                        if m_allowed:
                            global_guided_candidates.extend(self.semantic.search(retrieval_query, 3, m_allowed))
                global_guided_candidates = list(dict.fromkeys(global_guided_candidates))
                if global_guided_candidates:
                    channels['global_context_guided'] = global_guided_candidates
                    rankings.append(global_guided_candidates)

        fused = rrf(rankings)
        for rank_idx, sid in enumerate(exact):
            # Preserve exact match dominance while subtly breaking multi-movie ties by movie popularity
            mid = sid.rsplit('_', 1)[0]
            votes_bonus = min(0.05, math.log10(max(10, self._movies_by_id.get(mid, {}).get('votes', 0) + 10)) * 0.006)
            fused[sid] = fused.get(sid, 0.0) + 1.5 - (rank_idx * 1e-4) + votes_bonus

        candidate_ids = sorted(fused, key=fused.get, reverse=True)[:80]

        channel_leaders = []
        if not skip_broad_channels and mode != 'quote':
            leader_sources = [
                lexical[:5],
                channels.get('rare_clues', [])[:4],
                channels.get('semantic', [])[:5],
                channels.get('fine_dialogue', [])[:4],
                channels.get('fine_summary', [])[:4],
                channels.get('bge_context', [])[:3],
                channels.get('sequences', [])[:3],
                global_guided_candidates[:8],
            ]
            channel_leaders = list(dict.fromkeys(sid for src in leader_sources for sid in src))
            for sid in channel_leaders:
                if sid not in candidate_ids:
                    candidate_ids.append(sid)

        plot_hits = {}
        plot_candidates = []
        tail_candidates = []

        if len(all_tokens) > 45 and not skip_broad_channels:
            tail_expression = ' OR '.join('"' + token + '"' for token in all_tokens[-35:])
            tail_candidates = self._lexical(tail_expression, 15, movie_id)
            channels['tail_clues'] = tail_candidates
            for sid, score in rrf([tail_candidates]).items():
                fused.setdefault(sid, score)
            candidate_ids = list(dict.fromkeys(candidate_ids + tail_candidates))

        if self.plots is not None and mode != 'quote' and not skip_broad_channels:
            plot_query = (decomp.global_context + ' ' + decomp.scene_target).strip() if use_decomposed else retrieval_query
            for hit in self.plots.search(plot_query, limit=5, movie_id=movie_id)['results']:
                mid = hit['movie_id']
                plot_hits[mid] = hit
                lex_in_movie = self._lexical(expression, 3, mid)
                plot_candidates.extend(lex_in_movie)
                # When lexical subtitle stems miss on purely visual queries, pull top semantic scene in that movie.
                if not lex_in_movie and self.semantic is not None:
                    m_allowed = {r[0] for r in con.execute('SELECT id FROM scenes WHERE movie_id=?', (mid,))}
                    if m_allowed:
                        plot_candidates.extend(self.semantic.search(retrieval_query, 2, m_allowed))
            plot_candidates = list(dict.fromkeys(plot_candidates))
            channels['plot_guided'] = plot_candidates
            for sid, score in rrf([plot_candidates]).items():
                fused[sid] = fused.get(sid, 0.0) + score * 0.75
            candidate_ids = list(dict.fromkeys(candidate_ids + plot_candidates))

        rows = {}
        for sid in candidate_ids:
            row = con.execute(
                'SELECT s.*, m.title, m.status AS coverage_status, m.details '
                'FROM scenes s JOIN movies m ON s.movie_id=m.id WHERE s.id=?',
                (sid,),
            ).fetchone()
            if row:
                rows[sid] = dict(row)

        # Attach per-scene timeline flow (progress, act, preceding/next beats) before reranking
        scene_flow_map = self.context_index.get_scene_flow(list(rows.keys())) if self.context_index is not None else {}
        for sid, row in rows.items():
            flow = scene_flow_map.get(sid)
            if flow and flow.get('prev_summary'):
                row['prev_summary'] = flow['prev_summary']

        fuzzy = {}
        if mode in {'quote', 'auto'} and not exact and (mode == 'quote' or len(normalized.split()) <= 50):
            for sid, row in list(rows.items())[:40]:
                ratio = best_fuzzy(query, row['text'], minimum=0.83)
                if ratio >= 0.83:
                    fuzzy[sid] = ratio

        if mode in {'quote', 'auto'} and not exact and not fuzzy and len(plan.quote_tokens) <= 10:
            if mode == 'quote' or len(normalized.split()) <= 10:
                corrected = self._typo_candidates(plan.quote_tokens, movie_id)
                if corrected:
                    channels['spelling'] = corrected
                    for sid in corrected:
                        if sid not in rows:
                            row = con.execute(
                                'SELECT s.*, m.title, m.status AS coverage_status, m.details '
                                'FROM scenes s JOIN movies m ON s.movie_id=m.id WHERE s.id=?',
                                (sid,),
                            ).fetchone()
                            if row:
                                rows[sid] = dict(row)
                        if sid in rows:
                            fused.setdefault(sid, 0.0)
                            ratio = best_fuzzy(query, rows[sid]['text'], minimum=0.82 if mode == 'quote' else 0.85)
                            if ratio >= (0.82 if mode == 'quote' else 0.85):
                                fuzzy[sid] = ratio
                    candidate_ids = list(dict.fromkeys(candidate_ids + corrected))

        scores = {}
        if self.reranker is not None and mode != 'quote' and not exact:
            shortlist = list(rows)[:40]
            shortlist = list(dict.fromkeys(shortlist + channel_leaders + plot_candidates + tail_candidates))
            scores = self.reranker.rank(retrieval_query, [rows[sid] for sid in shortlist if sid in rows])

        # Calibrated hybrid ordering combining cross-encoder discrimination, RRF consensus, global movie context, and timeline alignment.
        max_fused = max((fused.get(sid, 0.0) for sid in rows), default=1.0) or 1.0
        ce_rank = {}
        if scores:
            for r_idx, sid in enumerate(sorted(scores, key=scores.get, reverse=True), 1):
                ce_rank[sid] = r_idx

        top_plot_movies = list(plot_hits.keys())
        # Enrich matched_movies ('Film Worlds') with top Wikipedia plot matches when they aren't already listed
        if top_plot_movies and mode != 'quote' and not movie_id:
            existing_mids = {m['movie_id'] for m in matched_movies}
            for mid in top_plot_movies[:3]:
                if mid not in existing_mids:
                    m_meta = self._movies_by_id.get(mid, {})
                    dos = self.context_index.dossiers.get(mid, {}) if self.context_index else {}
                    matched_movies.insert(
                        min(len(matched_movies), 1),
                        {
                            'movie_id': mid,
                            'title': m_meta.get('title', mid),
                            'year': m_meta.get('year', 0),
                            'rating': m_meta.get('rating', 0.0),
                            'characters': (dos.get('characters') or '')[:140],
                            'themes': (dos.get('themes') or '')[:120],
                            'premise': plot_hits[mid].get('excerpt', '')[:260],
                            'confidence': 0.9,
                            'raw_score': 0.05,
                        },
                    )
                    existing_mids.add(mid)

        all_query_terms = set(plan.tokens)
        t_range = decomp.temporal_range
        best_scene_for_plot_movie = {}
        for mid in top_plot_movies[:3]:
            hit = plot_hits[mid]
            p_score = float(hit.get('score', 0.0))
            shared = len(set(terms(hit.get('excerpt', ''))) & all_query_terms)
            if p_score >= 8.0 and shared >= 2:
                movie_sids = [sid for sid in rows if rows[sid]['movie_id'] == mid]
                if movie_sids:
                    def _plot_scene_key(s):
                        in_t = 0
                        if t_range is not None and s in scene_flow_map:
                            pr = float(scene_flow_map[s]['progress'])
                            in_t = 1 if t_range[0] <= pr <= t_range[1] else -1
                        return (in_t, scores.get(s, -1000.0), fused.get(s, 0.0))
                    best_sid = max(movie_sids, key=_plot_scene_key)
                    # Suppress plot bonus if user explicitly asked for an opening/ending scene and this chunk is at the opposite end
                    if t_range is not None and best_sid in scene_flow_map:
                        pr = float(scene_flow_map[best_sid]['progress'])
                        if abs(pr - 0.5 * (t_range[0] + t_range[1])) > 0.45:
                            continue
                    best_scene_for_plot_movie[best_sid] = top_plot_movies.index(mid)

        def hybrid_value(sid):
            rrf_norm = fused.get(sid, 0.0) / max_fused
            mid = rows[sid]['movie_id']

            # Global film context prior when user explicitly provided movie intro/premise clues
            global_bonus = 0.0
            if use_decomposed and mid in global_movie_map:
                gm_idx, gm_info = global_movie_map[mid]
                if gm_idx < 6 and gm_info.get('raw_score', 0.0) >= 0.028:
                    global_bonus = 0.24 * float(gm_info['confidence']) / (1.0 + 0.35 * gm_idx)
                # Also reward strong Wikipedia plot match on the global premise
                if mid in plot_hits and top_plot_movies.index(mid) < 3:
                    global_bonus += 0.06

            # Narrative timeline alignment bonus ('in the intro', 'much later', 'at the end')
            temporal_bonus = 0.0
            if t_range is not None and sid in scene_flow_map:
                prog = float(scene_flow_map[sid]['progress'])
                lo_t, hi_t = t_range
                if lo_t <= prog <= hi_t:
                    temporal_bonus = 0.10
                elif prog < lo_t:
                    temporal_bonus = -min(0.08, (lo_t - prog) * 0.16)
                else:
                    temporal_bonus = -min(0.08, (prog - hi_t) * 0.16)

            if not scores:
                return rrf_norm + global_bonus + temporal_bonus
            if sid not in scores:
                return -10.0 + rrf_norm + global_bonus + temporal_bonus

            logit = float(scores[sid])
            ce_sig = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, logit / 2.2))))
            ce_rrf_val = 20.0 / (19.0 + ce_rank[sid])
            plot_bonus = 0.0
            if sid in best_scene_for_plot_movie:
                p_idx = best_scene_for_plot_movie[sid]
                plot_bonus = 0.28 / (1.0 + p_idx * 0.5)
            return 0.50 * ce_sig + 0.22 * ce_rrf_val + 0.28 * rrf_norm + plot_bonus + global_bonus + temporal_bonus

        def ordering(sid):
            return (sid in exact, fuzzy.get(sid, 0), hybrid_value(sid), fused.get(sid, 0.0))

        ordered = sorted(rows, key=ordering, reverse=True)
        if mode == 'quote':
            ordered = [sid for sid in ordered if sid in exact or sid in fuzzy]
        elif not exact and not fuzzy and movie_id is None and len(ordered) > 4:
            # Gentle diversity re-ordering: allow up to 3 strong scenes per movie before promoting diverse movies.
            primary, overflow = [], []
            per_movie_counts: dict[str, int] = defaultdict(int)
            for sid in ordered:
                mid = rows[sid]['movie_id']
                per_movie_counts[mid] += 1
                if per_movie_counts[mid] <= 3:
                    primary.append(sid)
                else:
                    overflow.append(sid)
            ordered = primary + overflow

        results = []
        seen_spans = set()
        for sid in ordered:
            if len(results) >= limit:
                break
            row = rows[sid]
            span = exact.get(sid)
            line_data = json.loads(row['lines'])
            if span:
                neighbors = con.execute(
                    'SELECT lines FROM scenes WHERE movie_id=? AND start<=? AND end>=?',
                    (row['movie_id'], span['end'], span['start']),
                ).fetchall()
                unique = {
                    (line['start'], line['end'], line['text']): line
                    for neighbor in neighbors
                    for line in json.loads(neighbor['lines'])
                }
                line_data = sorted(unique.values(), key=lambda line: line['start'])
            if span and line_data:
                choices = []
                for i in range(len(line_data)):
                    for j in range(i + 1, min(i + 16, len(line_data)) + 1):
                        text = ' '.join(s['text'] for s in line_data[i:j])
                        if span.get('query', normalized) in normalize(text):
                            choices.append({'start': line_data[i]['start'], 'end': line_data[j - 1]['end'], 'text': text})
                if choices:
                    span = min(choices, key=lambda s: s['end'] - s['start'])
            start, end = (span['start'], span['end']) if span else (row['start'], row['end'])
            result_sid = sid
            if span:
                key = (row['movie_id'], round(start, 3), round(end, 3))
                if key in seen_spans:
                    continue
                seen_spans.add(key)
                owner = con.execute(
                    'SELECT id, summary FROM scenes WHERE movie_id=? AND start<=? AND end>? ORDER BY start DESC LIMIT 1',
                    (row['movie_id'], start + 0.05, start),
                ).fetchone()
                if owner:
                    result_sid = owner['id']
                    row['summary'] = owner['summary']

            excerpt = span['text'] if span else row['text']
            if not span and len(excerpt) > 700:
                sentences = re.split(r'(?<=[.!?])\s+', excerpt)
                excerpt = max(sentences, key=lambda s: len(set(terms(s)) & set(tokens)))[:700]

            m_info = self._movies_by_id.get(row['movie_id'], {})
            details_obj = json.loads(row['details'])
            matched_channels = [
                ch_name
                for ch_name in ('global_context_guided', 'keyword', 'rare_clues', 'fine_dialogue', 'fine_summary', 'bge_context', 'semantic', 'sequences', 'plot_guided', 'spelling')
                if ch_name in channels and sid in channels[ch_name][:25]
            ]
            if sid in exact:
                matched_channels.insert(0, 'exact_phrase')
            elif sid in fuzzy:
                matched_channels.insert(0, 'fuzzy_quote')

            flow = scene_flow_map.get(result_sid) or scene_flow_map.get(sid)
            if flow:
                progress = round(float(flow['progress']), 3)
                act_label = flow['act_label']
                prev_beat = flow.get('prev_summary', '')
                next_beat = flow.get('next_summary', '')
            else:
                runtime_est = max(1.0, float(details_obj.get('last', end) or end))
                progress = round(min(1.0, max(0.0, 0.5 * (start + end) / runtime_est)), 3)
                act_label = act_label_for_progress(progress)
                prev_beat = ''
                next_beat = ''

            dossier = (
                self.context_index.dossiers.get(row['movie_id'], {})
                if self.context_index is not None
                else {}
            )
            movie_premise = (dossier.get('core_premise') or '')[:220]
            movie_characters = (dossier.get('characters') or '')[:140]
            pct = int(round(progress * 100))

            if sid in exact:
                why_matched = f'Exact dialogue match localized to subtitle timing ({act_label} · {pct}% into film).'
            elif sid in fuzzy:
                why_matched = f'Typo-tolerant quote match against source subtitles ({act_label} · {pct}% into film).'
            elif use_decomposed and row['movie_id'] in global_movie_map:
                why_matched = (
                    f"Film context matched {row['title']}’s global premise · "
                    f'Scene clues pinpointed {act_label} ({pct}% into film).'
                )
            elif row['movie_id'] in plot_hits:
                why_matched = f"Film storyline matched {row['title']} · Candidate scene at {pct}% ({act_label})."
            else:
                why_matched = f'Matched scene semantics & dialogue cues at {pct}% into film ({act_label}).'

            result = {
                'scene_id': result_sid,
                'movie_id': row['movie_id'],
                'title': row['title'],
                'year': m_info.get('year', 0),
                'rating': m_info.get('rating', 0.0),
                'start': start,
                'end': end,
                'start_label': timestamp(start),
                'end_label': timestamp(end),
                'progress': progress,
                'act_label': act_label,
                'prev_beat': prev_beat,
                'next_beat': next_beat,
                'movie_premise': movie_premise,
                'movie_characters': movie_characters,
                'why_matched': why_matched,
                'dialogue': excerpt,
                'summary': row['summary'] or row.get('paraphrase', ''),
                'relationship': row.get('relationship', ''),
                'emotion': row.get('emotion', ''),
                'match': 'exact_quote' if sid in exact else ('approximate_quote' if sid in fuzzy else 'scene_candidate'),
                'evidence_channels': matched_channels,
                'timestamp_precision': 'subtitle_lines' if span and line_data else 'chunk',
                'coverage_status': row['coverage_status'],
                'coverage_flags': details_obj['flags'],
                'source': row['source'],
            }
            if row['movie_id'] in plot_hits:
                hit = plot_hits[row['movie_id']]
                result['plot_excerpt'] = hit['excerpt']
                result['plot_source_url'] = hit['source_url']
            results.append(result)

        status = 'matches' if exact or fuzzy else ('candidates' if results else 'no_match')
        message = (
            'Matches are based on indexed source text.'
            if exact or fuzzy
            else 'These are candidate scenes. Visual details and subtitle timing need verification against the movie release.'
        )
        if not results:
            message = 'No supported match found. Try a longer quote, a distinctive detail, or a movie filter. The source may be incomplete.'
        response = {
            'query': query,
            'mode': mode,
            'status': status,
            'message': message,
            'query_context': {
                'is_decomposed': use_decomposed,
                'global_context': decomp.global_context if use_decomposed else '',
                'scene_target': decomp.scene_target,
                'temporal_hint': decomp.temporal_hint,
                'temporal_label': decomp.temporal_label,
                'matched_movies': matched_movies[:4],
            },
            'results': results,
            'semantic_enabled': self.semantic is not None,
            'reranker_enabled': self.reranker is not None,
            'elapsed_ms': round((perf_counter() - started) * 1000),
        }
        if debug:
            response['candidate_ids'] = candidate_ids
            response['channels'] = channels
            response['reranked_ids'] = list(scores)
            response['reranker_scores'] = scores
            response['fusion_scores'] = dict(fused)
            response['retrieval_query'] = retrieval_query
        return response

    def _search_index(self, query, mode, limit, movie_id, debug, started):
        """Show the selected index's own order, without other retrieval or reranking."""
        if self.semantic is None:
            raise ValueError('Semantic search is unavailable; start the app with a semantic index.')
        con = self._conn()
        allowed = None
        if movie_id:
            allowed = {r[0] for r in con.execute('SELECT id FROM scenes WHERE movie_id=?', (movie_id,))}
        retrieval_query = search_content(query)
        candidates = self.semantic.search(retrieval_query, max(150, limit), allowed)
        results = []
        for sid in candidates:
            row = con.execute(
                'SELECT s.*, m.title, m.status AS coverage_status, m.details '
                'FROM scenes s JOIN movies m ON s.movie_id=m.id WHERE s.id=?',
                (sid,),
            ).fetchone()
            if not row:
                continue
            row_dict = dict(row)
            m_info = self._movies_by_id.get(row_dict['movie_id'], {})
            results.append({
                'scene_id': sid,
                'movie_id': row_dict['movie_id'],
                'title': row_dict['title'],
                'year': m_info.get('year', 0),
                'rating': m_info.get('rating', 0.0),
                'start': row_dict['start'],
                'end': row_dict['end'],
                'start_label': timestamp(row_dict['start']),
                'end_label': timestamp(row_dict['end']),
                'dialogue': row_dict['text'][:700],
                'summary': row_dict['summary'] or row_dict.get('paraphrase', ''),
                'relationship': row_dict.get('relationship', ''),
                'emotion': row_dict.get('emotion', ''),
                'match': 'semantic_candidate',
                'evidence_channels': ['semantic'],
                'timestamp_precision': 'chunk',
                'coverage_status': row_dict['coverage_status'],
                'coverage_flags': json.loads(row_dict['details'])['flags'],
                'source': row_dict['source'],
            })
            if len(results) >= limit:
                break
        response = {
            'query': query,
            'mode': mode,
            'status': 'candidates' if results else 'no_match',
            'message': 'Showing the selected index’s semantic ranking.' if results else 'No passages found in this index. Try another query or index.',
            'results': results,
            'semantic_enabled': True,
            'reranker_enabled': False,
            'retrieval': 'index',
            'elapsed_ms': round((perf_counter() - started) * 1000),
        }
        if debug:
            response['channels'] = {'semantic': candidates}
            response['candidate_ids'] = candidates
            response['retrieval_query'] = retrieval_query
        return response
