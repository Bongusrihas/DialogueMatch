"""Global movie context dossiers, narrative timeline positioning, and query decomposition.

Bridges whole-film knowledge (intro/premise, character web, themes, ending) with
local scene/dialogue retrieval so multi-part memories ('the movie starts with X,
and in one scene he says Y') separate global film clues from target scene clues.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
import threading
from time import perf_counter

from .build import DEFAULT_DB, digest
from .text import normalize, search_content, terms

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'

# Narrative timeline cues indicating where the TARGET scene sits in the film.
_TEMPORAL_PATTERNS = [
    (
        'opening',
        (0.0, 0.18),
        'Opening / Intro',
        re.compile(
            r'\b(?:opening scene|very beginning|at the (?:very )?(?:beginning|start)|'
            r'in the (?:intro|opening|first scene|beginning)|right at the start|first few minutes)\b',
            re.IGNORECASE,
        ),
    ),
    (
        'ending',
        (0.78, 1.0),
        'Ending / Climax',
        re.compile(
            r'\b(?:final scene|ending scene|last scene|at the (?:very )?end|near the end|towards? the end|'
            r'in the (?:climax|finale|ending)|right before the credits|end of the (?:movie|film))\b',
            re.IGNORECASE,
        ),
    ),
    (
        'late',
        (0.55, 0.96),
        'Later in film',
        re.compile(
            r'\b(?:much later|later on|later in the (?:movie|film|story)|eventually|afterward|years later in the film)\b',
            re.IGNORECASE,
        ),
    ),
    (
        'early',
        (0.05, 0.36),
        'Early in film',
        re.compile(
            r'\b(?:early on|early in the (?:movie|film)|near the beginning|in the first half)\b',
            re.IGNORECASE,
        ),
    ),
    (
        'middle',
        (0.28, 0.75),
        'Mid-film',
        re.compile(
            r'\b(?:halfway through|in the middle of the (?:movie|film)|midway through)\b',
            re.IGNORECASE,
        ),
    ),
]

# Explicit transition phrases splitting <Global Film Context> from <Target Scene / Dialogue>.
_SCENE_TRANSITION_SPLITS = [
    re.compile(
        r'^(?P<global>.{18,}?)(?:[,.;—]+|\s+and\s+|\s+but\s+)\s*'
        r'(?:and\s+|but\s+|then\s+)?'
        r'(?P<connector>'
        r'(?:much\s+)?later(?:\s+on|\s+in\s+the\s+(?:movie|film))?\s+(?:there(?:\'s| is)\s+(?:a|one|this)\s+(?:[a-z-]+\s+){0,2}(?:scene|part|moment)\s+(?:where|when|in which)|in\s+(?:a|one)\s+(?:scene|part|moment)|,)?|'
        r'there(?:\'s| is)\s+(?:a|one|this|another)\s+(?:[a-z-]+\s+){0,2}?(?:scene|part|moment|sequence)\s+(?:in\s+it\s+)?(?:where|when|in which)|'
        r'in\s+(?:one|a\s+specific|a\s+particular|a\s+famous|a\s+later|the\s+final|the\s+last)\s+(?:[a-z-]+\s+){0,2}?(?:scene|part|moment)(?:[,\s]+(?:where|when))?|'
        r'at\s+one\s+point(?:[,\s]+(?:in\s+the\s+(?:movie|film)))?|'
        r'(?:near|towards?|at)\s+the\s+(?:very\s+)?end(?:\s+of\s+the\s+(?:movie|film))?[,\s]+(?:there(?:\'s| is)\s+a\s+scene\s+where\s+)?'
        r')\s*(?P<scene>.{15,})$',
        re.IGNORECASE | re.DOTALL,
    ),
    # "In a movie/thriller about <Global Premise>, <Target Scene>"
    re.compile(
        r'^(?:it(?:\'s| is)\s+|in\s+|from\s+)?(?:a|an|this|that|the)\s+(?:[a-z0-9-]+\s+){0,3}?'
        r'(?:movie|film|thriller|comedy|drama|horror|sci-?fi|mystery|western|story)\s+'
        r'(?:about|where|in which|that\s+(?:starts|opens|begins|follows)(?:\s+with)?)\s+'
        r'(?P<global>[^,.;]{15,180}?)[,;]\s+'
        r'(?:and\s+)?(?P<scene>.{18,})$',
        re.IGNORECASE | re.DOTALL,
    ),
]

_GLOBAL_FRAMING = re.compile(
    r'\b(?:'
    r'(?:movie|film|story|thriller|comedy|drama|horror|mystery|western|sci-?fi)\s+(?:is\s+)?(?:about|where|in which|follows|starts\s+with|opens\s+with|begins\s+with|centers\s+on|takes\s+place)|'
    r'(?:starts|opens|begins)\s+with\b|'
    r'in\s+the\s+(?:intro|opening|beginning)\s+of\s+the\s+(?:movie|film)|'
    r'main\s+character\s+is|protagonist\s+is|throughout\s+the\s+(?:movie|film)|'
    r'(?:sci-?fi|animated|horror|thriller|comedy|action|drama|war|superhero)\s+(?:movie|film)'
    r')\b',
    re.IGNORECASE,
)

_OPENING_CUE = re.compile(
    r'\b(?:starts?\s+with|opens?\s+with|begins?\s+with|in\s+the\s+(?:intro|opening|beginning)|opening\s+(?:scene|montage|sequence))\b',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DecomposedQuery:
    original: str
    cleaned: str
    is_decomposed: bool
    global_context: str
    scene_target: str
    global_checks_opening: bool = False
    temporal_hint: str | None = None
    temporal_range: tuple[float, float] | None = None
    temporal_label: str | None = None


def _detect_temporal(text: str) -> tuple[str | None, tuple[float, float] | None, str | None]:
    for name, span, label, pattern in _TEMPORAL_PATTERNS:
        if pattern.search(text):
            return name, span, label
    return None, None, None


def decompose_query(query: str, mode: str = 'auto') -> DecomposedQuery:
    cleaned = search_content(query) if mode != 'quote' else query.strip()
    if mode == 'quote' or not cleaned:
        return DecomposedQuery(
            original=query,
            cleaned=cleaned,
            is_decomposed=False,
            global_context='',
            scene_target=cleaned,
        )

    # 1. Check explicit transition connectors ("starts with X, and later there's a scene where Y")
    for splitter in _SCENE_TRANSITION_SPLITS:
        m = splitter.match(cleaned)
        if m:
            g_part = m.group('global').strip(' ,.;:—-')
            connector = m.groupdict().get('connector', '') or ''
            s_part = m.group('scene').strip(' ,.;:—-')
            if len(terms(g_part)) >= 3 and len(terms(s_part)) >= 3:
                t_hint, t_range, t_label = _detect_temporal(connector + ' ' + s_part)
                if t_hint is None and re.search(r'\blater\b', connector, re.IGNORECASE):
                    t_hint, t_range, t_label = 'late', (0.45, 0.96), 'Later in film'
                return DecomposedQuery(
                    original=query,
                    cleaned=cleaned,
                    is_decomposed=True,
                    global_context=g_part,
                    scene_target=s_part,
                    global_checks_opening=bool(_OPENING_CUE.search(g_part)),
                    temporal_hint=t_hint,
                    temporal_range=t_range,
                    temporal_label=t_label,
                )

    # 2. Check multi-sentence premise sentence(s) followed by specific scene/dialogue sentence(s)
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned) if s.strip()]
    if len(sentences) >= 2 and _GLOBAL_FRAMING.search(sentences[0]):
        # Group leading premise sentences vs trailing scene sentences
        split_idx = 1
        while split_idx < len(sentences) - 1 and _GLOBAL_FRAMING.search(sentences[split_idx]):
            split_idx += 1
        g_part = ' '.join(sentences[:split_idx]).strip()
        s_part = ' '.join(sentences[split_idx:]).strip()
        if len(terms(g_part)) >= 3 and len(terms(s_part)) >= 3:
            t_hint, t_range, t_label = _detect_temporal(s_part)
            return DecomposedQuery(
                original=query,
                cleaned=cleaned,
                is_decomposed=True,
                global_context=g_part,
                scene_target=s_part,
                global_checks_opening=bool(_OPENING_CUE.search(g_part)),
                temporal_hint=t_hint,
                temporal_range=t_range,
                temporal_label=t_label,
            )

    # 3. Single unified scene description — still check if it specifies a timeline position (e.g. "In the opening scene...")
    t_hint, t_range, t_label = _detect_temporal(cleaned)
    return DecomposedQuery(
        original=query,
        cleaned=cleaned,
        is_decomposed=False,
        global_context='',
        scene_target=cleaned,
        global_checks_opening=(t_hint == 'opening'),
        temporal_hint=t_hint,
        temporal_range=t_range,
        temporal_label=t_label,
    )


def act_label_for_progress(progress: float) -> str:
    p = max(0.0, min(1.0, float(progress)))
    if p <= 0.14:
        return 'Opening'
    if p <= 0.32:
        return 'Early Act'
    if p <= 0.68:
        return 'Mid-Film'
    if p <= 0.86:
        return 'Late Act'
    return 'Finale'


_CAP_NAME = re.compile(r'\b([A-Z][a-z]{2,15}(?:\s+[A-Z][a-z]{2,15})?)\b')
_COMMON_CAP_STOP = {
    'The', 'This', 'That', 'There', 'They', 'Their', 'Then', 'When', 'Where', 'What', 'While',
    'After', 'Before', 'During', 'Meanwhile', 'Inside', 'Outside', 'Later', 'Suddenly', 'Finally',
    'However', 'Despite', 'Amid', 'Both', 'Two', 'Three', 'One', 'Some', 'Many', 'Several',
    'Scene', 'Someone', 'Somebody', 'Everyone', 'Nobody', 'Man', 'Woman', 'Men', 'Women', 'Boy', 'Girl',
}


def _extract_characters_and_relations(rows) -> str:
    rel_snippets = []
    name_counts: Counter[str] = Counter()
    for r in rows:
        rel = (r['relationship'] or '').strip() if 'relationship' in r.keys() else ''
        if rel and len(rel_snippets) < 6 and rel not in rel_snippets:
            rel_snippets.append(rel)
        summary = (r['summary'] or '').strip()
        for m in _CAP_NAME.finditer(summary):
            cand = m.group(1)
            first_word = cand.split()[0]
            if first_word not in _COMMON_CAP_STOP:
                name_counts[cand] += 1
    top_names = [name for name, cnt in name_counts.most_common(8) if cnt >= 2]
    parts = []
    if top_names:
        parts.append(', '.join(top_names))
    if rel_snippets:
        parts.append(' · '.join(rel_snippets[:4]))
    return ' — '.join(parts)[:380]


def _extract_themes(rows) -> str:
    kw_counts: Counter[str] = Counter()
    for r in rows:
        try:
            kws = json.loads(r['keywords'] or '[]')
        except ValueError:
            kws = []
        for k in kws:
            clean_k = str(k).strip().lower()
            if clean_k:
                kw_counts[clean_k] += 1
    return ', '.join(k for k, _ in kw_counts.most_common(14))


def _condense_beats(rows, max_items=6) -> str:
    if not rows:
        return ''
    if len(rows) <= max_items:
        picked = rows
    else:
        step = (len(rows) - 1) / max(1, max_items - 1)
        picked = [rows[round(i * step)] for i in range(max_items)]
    beats = []
    for r in picked:
        s = (r['summary'] or '').strip()
        if not s and 'paraphrase' in r.keys():
            s = (r['paraphrase'] or '').strip()
        if not s:
            s = ' '.join((r['text'] or '').split()[:25])
        if s and s not in beats:
            beats.append(s)
    return ' '.join(beats)[:900]


def build_context_index(db=DEFAULT_DB, model_name=MODEL, batch_size=128):
    """Synthesize whole-movie dossiers, scene-flow metadata, and neural movie embeddings for all catalog films."""
    import numpy as np
    from .neural import load_encoder

    db = Path(db)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    movie_cols = {row[1] for row in con.execute('PRAGMA table_info(movies)')}
    has_stats = 'year' in movie_cols and 'votes' in movie_cols
    if has_stats:
        movies = con.execute('SELECT id, title, year, rating, votes FROM movies ORDER BY id').fetchall()
    else:
        movies = [
            {'id': r['id'], 'title': r['title'], 'year': 0, 'rating': 0.0, 'votes': 0}
            for r in con.execute('SELECT id, title FROM movies ORDER BY id')
        ]

    # Load optional Wikipedia plot passages per movie if available
    plots_by_movie: dict[str, list[str]] = defaultdict(list)
    plots_path = db.with_suffix('.plots.sqlite')
    if plots_path.is_file():
        pcon = sqlite3.connect(plots_path)
        for mid, content in pcon.execute('SELECT movie_id, content FROM plots'):
            plots_by_movie[mid].append(content)
        pcon.close()

    ctx_target = db.with_suffix('.context.sqlite')
    ctx_temp = db.with_suffix('.context.building.sqlite')
    if ctx_temp.exists():
        ctx_temp.unlink()

    out = sqlite3.connect(ctx_temp)
    out.executescript('''
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        CREATE TABLE movie_dossiers(
            movie_id TEXT PRIMARY KEY,
            title TEXT,
            year INTEGER,
            rating REAL,
            votes INTEGER,
            runtime REAL,
            scene_count INTEGER,
            characters TEXT,
            themes TEXT,
            opening_arc TEXT,
            core_premise TEXT,
            ending_arc TEXT
        );
        CREATE VIRTUAL TABLE movie_dossiers_fts USING fts5(
            movie_id UNINDEXED,
            title_cast,
            opening_arc,
            core_premise,
            ending_arc,
            themes,
            tokenize='porter unicode61'
        );
        CREATE TABLE scene_flow(
            scene_id TEXT PRIMARY KEY,
            movie_id TEXT,
            seq_index INTEGER,
            total_scenes INTEGER,
            progress REAL,
            act_label TEXT,
            prev_summary TEXT,
            next_summary TEXT
        );
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
    ''')

    vector_docs = []
    vector_movie_ids = []

    for m_idx, m in enumerate(movies):
        mid = m['id']
        scenes = con.execute('SELECT * FROM scenes WHERE movie_id=? ORDER BY start', (mid,)).fetchall()
        if not scenes:
            continue

        runtime = max(1.0, max(float(s['end']) for s in scenes))
        n_scenes = len(scenes)

        # Build per-scene timeline progress & immediate before/after story flow
        scene_beats = []
        for s in scenes:
            beat = (s['summary'] or '').strip()
            if not beat and 'paraphrase' in s.keys():
                beat = (s['paraphrase'] or '').strip()
            if not beat:
                beat = ' '.join((s['text'] or '').split()[:22])
            scene_beats.append(beat)

        flow_rows = []
        for idx, s in enumerate(scenes):
            midpoint = 0.5 * (float(s['start']) + float(s['end']))
            progress = round(min(1.0, max(0.0, midpoint / runtime)), 4)
            act = act_label_for_progress(progress)
            prev_b = scene_beats[idx - 1][:220] if idx > 0 else ''
            next_b = scene_beats[idx + 1][:220] if idx + 1 < n_scenes else ''
            flow_rows.append((s['id'], mid, idx, n_scenes, progress, act, prev_b, next_b))
        out.executemany('INSERT INTO scene_flow VALUES(?,?,?,?,?,?,?,?)', flow_rows)

        # Synthesize Opening Arc (first ~16% of scenes), Core Premise, and Ending Arc (last ~16% of scenes)
        open_cut = max(1, min(8, round(n_scenes * 0.16)))
        end_cut = max(1, min(8, round(n_scenes * 0.16)))
        opening_scenes = scenes[:open_cut]
        ending_scenes = scenes[-end_cut:]

        wiki_chunks = plots_by_movie.get(mid, [])
        wiki_open = wiki_chunks[0][:420] if wiki_chunks else ''
        wiki_end = wiki_chunks[-1][:420] if len(wiki_chunks) >= 2 else ''
        wiki_core = ' '.join(wiki_chunks[:3])[:700] if wiki_chunks else ''

        characters = _extract_characters_and_relations(scenes)
        themes = _extract_themes(scenes)
        opening_arc = ' '.join(p for p in [wiki_open, _condense_beats(opening_scenes, 4)] if p)[:950]
        core_premise = ' '.join(p for p in [wiki_core, _condense_beats(scenes, 8)] if p)[:1200]
        ending_arc = ' '.join(p for p in [wiki_end, _condense_beats(ending_scenes, 4)] if p)[:950]

        out.execute(
            'INSERT INTO movie_dossiers VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (
                mid,
                m['title'],
                int(m['year'] or 0),
                float(m['rating'] or 0.0),
                int(m['votes'] or 0),
                runtime,
                n_scenes,
                characters,
                themes,
                opening_arc,
                core_premise,
                ending_arc,
            ),
        )
        out.execute(
            'INSERT INTO movie_dossiers_fts VALUES(?,?,?,?,?,?)',
            (
                mid,
                normalize(f"{m['title']} {characters}"),
                normalize(opening_arc),
                normalize(core_premise),
                normalize(ending_arc),
                normalize(themes),
            ),
        )

        # 3 neural semantic views per movie: Premise+Characters+Themes, Opening/Intro Arc, Ending/Climax Arc
        vector_movie_ids.append(mid)
        vector_docs.append(f"{m['title']} ({m['year'] or ''}). Characters: {characters}. Themes: {themes}. Premise: {core_premise}"[:900])
        vector_docs.append(f"Opening & intro of {m['title']}: {opening_arc}"[:800])
        vector_docs.append(f"Climax & ending of {m['title']}: {ending_arc}"[:800])

        if (m_idx + 1) % 500 == 0:
            print(f'Synthesized global dossiers for {m_idx + 1}/{len(movies)} movies', flush=True)

    con.close()

    # Encode all 3 * N_movies dossier views into a compact float32 matrix
    encoder = load_encoder(model_name)
    encoder.max_seq_length = 256
    vecs = (
        encoder.encode(
            vector_docs,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype('float32')
        if vector_docs
        else np.zeros((0, 384), dtype='float32')
    )

    vec_target = db.with_suffix('.movies.npy')
    vec_temp = db.with_suffix('.movies.building.npy')
    np.save(vec_temp, vecs)
    vec_temp.replace(vec_target)

    meta_info = {
        'schema': 1,
        'db_sha256': digest(db),
        'vectors_sha256': digest(vec_target),
        'model': model_name,
        'movies': len(vector_movie_ids),
        'views_per_movie': 3,
        'movie_ids': vector_movie_ids,
    }
    out.execute('INSERT INTO meta VALUES(?,?)', ('manifest', json.dumps(meta_info)))
    out.execute("INSERT INTO movie_dossiers_fts(movie_dossiers_fts) VALUES('optimize')")
    out.commit()
    out.close()
    ctx_temp.replace(ctx_target)
    db.with_suffix('.movies.json').write_text(json.dumps(meta_info, indent=2), encoding='utf-8')
    print(f'Global movie context ready: {len(vector_movie_ids)} film dossiers ({len(vecs)} narrative vectors).', flush=True)
    return meta_info


class MovieContextIndex:
    """Fast hybrid lexical + dense whole-movie context retriever and scene-flow provider."""

    def __init__(self, db: Path, neural: bool = True):
        import numpy as np

        self.db = Path(db)
        self.ctx_path = self.db.with_suffix('.context.sqlite')
        if not self.ctx_path.is_file():
            raise FileNotFoundError('Context index not found; run python -m dialoguematch build-context')
        self._uri = f'{self.ctx_path.resolve().as_uri()}?mode=ro'
        self._local = threading.local()
        con = self._conn()
        self.manifest = json.loads(con.execute("SELECT value FROM meta WHERE key='manifest'").fetchone()[0])

        # Preload lightweight movie dossiers dictionary in memory (~2MB for 2,000 films) for 0ms card enrichment
        self.dossiers: dict[str, dict] = {}
        for r in con.execute('SELECT * FROM movie_dossiers'):
            self.dossiers[r['movie_id']] = dict(r)

        self.vectors = None
        self.movie_ids: list[str] = self.manifest.get('movie_ids', [])
        self.encoder = None
        vec_path = self.db.with_suffix('.movies.npy')
        if neural and vec_path.is_file() and len(self.movie_ids) > 0:
            try:
                from .neural import load_encoder
                self.vectors = np.load(vec_path, mmap_mode='r', allow_pickle=False)
                self.encoder = load_encoder(self.manifest.get('model', MODEL))
            except (OSError, ValueError):
                self.vectors = None
                self.encoder = None

    def _conn(self):
        con = getattr(self._local, 'con', None)
        if con is None:
            con = sqlite3.connect(self._uri, uri=True, check_same_thread=False)
            con.row_factory = sqlite3.Row
            self._local.con = con
        return con

    def close(self):
        con = getattr(self._local, 'con', None)
        if con is not None:
            con.close()
            self._local.con = None

    def get_scene_flow(self, scene_ids: list[str]) -> dict[str, dict]:
        if not scene_ids:
            return {}
        con = self._conn()
        placeholders = ','.join('?' for _ in scene_ids)
        rows = con.execute(f'SELECT * FROM scene_flow WHERE scene_id IN ({placeholders})', list(scene_ids)).fetchall()
        return {r['scene_id']: dict(r) for r in rows}

    def search_movies(
        self,
        global_query: str,
        secondary_query: str = '',
        opening_focus: bool = False,
        ending_focus: bool = False,
        limit: int = 8,
    ) -> list[dict]:
        """Rank whole movies by combining lexical dossier BM25 and 3-view neural movie embeddings."""
        started = perf_counter()
        con = self._conn()
        q_tokens = terms(global_query)[:35] or normalize(global_query).split()[:35]
        sec_tokens = terms(secondary_query)[:20] if secondary_query else []

        rrf_scores: dict[str, float] = defaultdict(float)

        # 1. Lexical FTS5 over movie dossiers (weighting opening_arc higher when query describes film intro)
        if q_tokens:
            expr = ' OR '.join('"' + t + '"' for t in q_tokens)
            bm25_weights = (
                'bm25(0, 1.4, 3.0, 1.4, 0.7, 1.1)'
                if opening_focus
                else 'bm25(0, 1.4, 0.9, 1.5, 2.8, 1.1)'
                if ending_focus
                else 'bm25(0, 1.5, 1.3, 1.8, 1.1, 1.2)'
            )
            lex_rows = con.execute(
                f"SELECT movie_id FROM movie_dossiers_fts WHERE movie_dossiers_fts MATCH ? AND rank MATCH '{bm25_weights}' ORDER BY rank LIMIT 60",
                (expr,),
            ).fetchall()
            for rank_idx, r in enumerate(lex_rows, 1):
                rrf_scores[r[0]] += 1.25 / (30 + rank_idx)

            # Pairwise rare-term boost on dossiers
            if len(q_tokens) >= 2:
                longest = sorted(q_tokens, key=len, reverse=True)[:5]
                pairs = [f'("{a}" AND "{b}")' for i, a in enumerate(longest) for b in longest[i + 1:i + 3]]
                if pairs:
                    pair_rows = con.execute(
                        'SELECT movie_id FROM movie_dossiers_fts WHERE movie_dossiers_fts MATCH ? ORDER BY bm25(movie_dossiers_fts) LIMIT 30',
                        (' OR '.join(pairs),),
                    ).fetchall()
                    for rank_idx, r in enumerate(pair_rows, 1):
                        rrf_scores[r[0]] += 1.15 / (25 + rank_idx)

        if sec_tokens:
            sec_expr = ' OR '.join('"' + t + '"' for t in sec_tokens)
            sec_rows = con.execute(
                'SELECT movie_id FROM movie_dossiers_fts WHERE movie_dossiers_fts MATCH ? ORDER BY bm25(movie_dossiers_fts) LIMIT 40',
                (sec_expr,),
            ).fetchall()
            for rank_idx, r in enumerate(sec_rows, 1):
                rrf_scores[r[0]] += 0.45 / (35 + rank_idx)

        # 2. Dense 3-view neural whole-movie search (Premise, Opening, Ending)
        if self.vectors is not None and self.encoder is not None and len(self.vectors) == 3 * len(self.movie_ids):
            import numpy as np

            self.encoder.max_seq_length = 256
            encode_inputs = [global_query] + ([secondary_query] if secondary_query else [])
            qvecs = self.encoder.encode(encode_inputs, normalize_embeddings=True, show_progress_bar=False).astype('float32')
            sims = (self.vectors @ qvecs[0]).reshape(len(self.movie_ids), 3)
            # Columns: 0 = core_premise, 1 = opening_arc, 2 = ending_arc
            if opening_focus:
                movie_dense = 0.45 * sims[:, 0] + 0.55 * sims[:, 1]
            elif ending_focus:
                movie_dense = 0.45 * sims[:, 0] + 0.55 * sims[:, 2]
            else:
                movie_dense = np.maximum(sims[:, 0], 0.88 * np.maximum(sims[:, 1], sims[:, 2]))

            if len(encode_inputs) > 1:
                sec_sims = np.max((self.vectors @ qvecs[1]).reshape(len(self.movie_ids), 3), axis=1)
                movie_dense = movie_dense + 0.25 * sec_sims

            top_k = min(60, len(movie_dense))
            top_idx = np.argpartition(-movie_dense, top_k - 1)[:top_k]
            top_idx = top_idx[np.argsort(-movie_dense[top_idx])]
            for rank_idx, idx in enumerate(top_idx, 1):
                if float(movie_dense[int(idx)]) >= 0.24:
                    rrf_scores[self.movie_ids[int(idx)]] += 1.35 / (30 + rank_idx)

        ordered = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)[:limit]
        max_sc = ordered[0][1] if ordered else 1.0
        results = []
        for mid, raw_sc in ordered:
            dos = self.dossiers.get(mid)
            if not dos:
                continue
            snippet = (
                dos['opening_arc']
                if opening_focus and dos['opening_arc']
                else dos['ending_arc']
                if ending_focus and dos['ending_arc']
                else dos['core_premise']
            )
            results.append({
                'movie_id': mid,
                'title': dos['title'],
                'year': dos['year'],
                'rating': dos['rating'],
                'characters': dos['characters'][:140],
                'themes': dos['themes'][:120],
                'premise': snippet[:260] + ('…' if len(snippet) > 260 else ''),
                'confidence': round(min(0.99, raw_sc / max(0.05, max_sc)), 3),
                'raw_score': round(raw_sc, 5),
                'elapsed_ms': round((perf_counter() - started) * 1000),
            })
        return results
