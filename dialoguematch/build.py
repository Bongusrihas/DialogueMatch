"""Build a versioned SQLite corpus from existing exports and local subtitles."""
from bisect import bisect_left
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sqlite3

from .chunker import hybrid_chunk, parse_srt
from .text import normalize

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / 'data/dialoguematch.sqlite'


_DIGEST_MEMO: dict[tuple[str, int, int], str] = {}


def digest(path):
    p = Path(path)
    st = p.stat()
    key = (str(p.resolve()), st.st_size, st.st_mtime_ns)
    cached = _DIGEST_MEMO.get(key)
    if cached is not None:
        return cached
    cache_file = ROOT / 'data/.digest_cache.json'
    disk_cache = {}
    if st.st_size > 10 * 1024 * 1024 and cache_file.is_file():
        try:
            disk_cache = json.loads(cache_file.read_text(encoding='utf-8'))
            entry = disk_cache.get(key[0])
            if entry and entry.get('size') == key[1] and entry.get('mtime_ns') == key[2]:
                _DIGEST_MEMO[key] = entry['sha256']
                return entry['sha256']
        except (OSError, ValueError, KeyError, TypeError):
            disk_cache = {}
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    val = h.hexdigest()
    _DIGEST_MEMO[key] = val
    if st.st_size > 10 * 1024 * 1024:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            disk_cache[key[0]] = {'size': key[1], 'mtime_ns': key[2], 'sha256': val}
            cache_file.write_text(json.dumps(disk_cache), encoding='utf-8')
        except OSError:
            pass
    return val


def _safe_int(val, default=0):
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def build(db=DEFAULT_DB, source=None, subtitles=None, metadata=None, all_subtitles=False):
    default_source = source is None
    source = Path(source or ROOT / 'V3/scene-finder.chunks_paraphrase.json')
    subtitles = Path(subtitles or ROOT / 'preprocessing/raw/subtitles')
    metadata = Path(metadata or ROOT / 'preprocessing/imdb_movies_2000_2025_high_voted.csv')
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    temporary = db.with_suffix('.building.sqlite')
    if temporary.exists():
        temporary.unlink()

    chunks = json.loads(source.read_text(encoding='utf-8'))

    # Supplement missing relationship/emotion/queries fields from read-only lab sources when building default corpus.
    extra_by_id = {}
    if default_source:
        for aux_rel in ('index_lab/shared/assets/sources/fine.json', 'index_lab/shared/assets/sources/context.json'):
            aux_path = ROOT / aux_rel
            if aux_path.is_file():
                try:
                    for item in json.loads(aux_path.read_text(encoding='utf-8')):
                        sid = item.get('_id')
                        if sid and sid not in extra_by_id:
                            extra_by_id[sid] = item
                except (OSError, ValueError):
                    pass

    titles = {}
    movie_meta = {}
    if metadata.exists():
        with metadata.open(encoding='utf-8-sig') as f:
            for r in csv.DictReader(f):
                mid = r.get('imdb_id', r.get('id'))
                if not mid:
                    continue
                titles[mid] = r.get('title', '')
                movie_meta[mid] = {
                    'original_title': r.get('original_title', ''),
                    'year': _safe_int(r.get('year'), 0),
                    'rating': _safe_float(r.get('rating'), 0.0),
                    'votes': _safe_int(r.get('votes'), 0),
                }

    groups = defaultdict(list)
    for chunk in chunks:
        groups[chunk['movie_id']].append(chunk)
    requested = set(groups) | set(titles)

    if default_source:
        evaluation = ROOT / 'preprocessing/evaluation_set.csv'
        if evaluation.exists():
            with evaluation.open(encoding='utf-8-sig') as f:
                requested.update(r['imdb_id'] for r in csv.DictReader(f))
    if all_subtitles:
        requested.update(p.stem for p in subtitles.glob('tt*.srt'))

    con = sqlite3.connect(temporary)
    con.executescript('''
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA cache_size=-262144;
        PRAGMA temp_store=MEMORY;
        CREATE TABLE scenes(
            id TEXT PRIMARY KEY,
            movie_id TEXT,
            start REAL,
            end REAL,
            text TEXT,
            summary TEXT,
            queries TEXT,
            keywords TEXT,
            lines TEXT,
            source TEXT,
            paraphrase TEXT DEFAULT '',
            relationship TEXT DEFAULT '',
            emotion TEXT DEFAULT ''
        );
        CREATE INDEX by_movie_time ON scenes(movie_id, start);
        CREATE TABLE movies(
            id TEXT PRIMARY KEY,
            title TEXT,
            status TEXT,
            details TEXT,
            year INTEGER DEFAULT 0,
            rating REAL DEFAULT 0.0,
            votes INTEGER DEFAULT 0
        );
        CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
        CREATE VIRTUAL TABLE search USING fts5(
            id UNINDEXED,
            dialogue,
            description,
            keywords,
            tokenize='porter unicode61'
        );
        CREATE VIRTUAL TABLE quotes USING fts5(
            scene_id UNINDEXED,
            start UNINDEXED,
            end UNINDEXED,
            raw UNINDEXED,
            dialogue,
            tokenize='unicode61'
        );
        CREATE VIRTUAL TABLE sequences USING fts5(
            movie_id UNINDEXED,
            scene_ids UNINDEXED,
            start UNINDEXED,
            end UNINDEXED,
            narrative,
            tokenize='porter unicode61'
        );
    ''')

    stats = {
        'movies': 0,
        'scenes': 0,
        'sequences': 0,
        'recovered_movies': [],
        'missing_movies': [],
        'suspect_movies': [],
        'parse_errors': {},
        'duplicate_ids': 0,
    }

    for movie_no, mid in enumerate(sorted(requested)):
        records = sorted(groups.get(mid, []), key=lambda c: float(c.get('start_time', 0)))
        srt = subtitles / f'{mid}.srt'
        lines = []
        if srt.exists():
            try:
                lines = parse_srt(srt)
            except (ValueError, OSError) as exc:
                stats['parse_errors'][mid] = str(exc)
        if not records and lines:
            records = [c.to_dict() for c in hybrid_chunk(lines, mid)]
            stats['recovered_movies'].append(mid)
        if not records:
            stats['missing_movies'].append(mid)
            continue

        last = max(float(c.get('end_time', 0)) for c in records)
        first = min(float(c.get('start_time', 0)) for c in records)
        flags = []
        if last < 3600:
            flags.append('Short subtitle timeline: may be a short film or partial release')
        if first > 300:
            flags.append('Subtitle timeline starts after five minutes')
        if not lines:
            flags.append('Original subtitle lines unavailable; timestamps are chunk-level')
        status = 'needs_review' if flags else 'unverified'
        if flags:
            stats['suspect_movies'].append(mid)

        m_info = movie_meta.get(mid, {})
        details_payload = {
            'flags': flags,
            'first': first,
            'last': last,
            'source': str(srt) if lines else str(source),
            'original_title': m_info.get('original_title', ''),
        }
        con.execute(
            'INSERT INTO movies VALUES(?,?,?,?,?,?,?)',
            (
                mid,
                titles.get(mid, mid),
                status,
                json.dumps(details_payload),
                m_info.get('year', 0),
                m_info.get('rating', 0.0),
                m_info.get('votes', 0),
            ),
        )

        starts = [s.start for s in lines]
        valid_records = []
        seq_entries = []

        for c in records:
            start, end = float(c.get('start_time', 0)), float(c.get('end_time', 0))
            if start < 0 or end <= start or not c.get('text', '').strip():
                continue
            sid = c['_id']
            aux = extra_by_id.get(sid, {})

            lo = bisect_left(starts, start - 0.05)
            selected = [s for s in lines[lo:bisect_left(starts, end)] if s.end <= end + 0.5]
            # Attach line times only when the raw source actually corresponds to this chunk.
            overlap = set(normalize(c['text']).split()) & set(normalize(' '.join(s.raw_text for s in selected)).split())
            if len(overlap) / max(1, len(set(normalize(c['text']).split()))) < 0.7:
                selected = []
            line_data = [{'start': s.start, 'end': s.end, 'text': s.raw_text} for s in selected]
            raw = ' '.join(s.raw_text for s in selected) or c.get('raw_text') or c['text']

            summary = c.get('summary') or aux.get('summary') or ''
            paraphrase = c.get('paraphrase') or aux.get('paraphrase') or ''
            relationship = c.get('relationship') or aux.get('relationship') or ''
            emotion = c.get('emotion') or aux.get('emotion') or ''
            queries_list = c.get('queries') or aux.get('queries') or []
            keywords_list = c.get('keywords') or aux.get('keywords') or []

            values = (
                sid,
                mid,
                start,
                end,
                raw,
                summary,
                json.dumps(queries_list),
                json.dumps(keywords_list),
                json.dumps(line_data),
                str(srt) if selected else str(source),
                paraphrase,
                relationship,
                emotion,
            )
            try:
                con.execute('INSERT INTO scenes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', values)
            except sqlite3.IntegrityError:
                stats['duplicate_ids'] += 1
                continue

            description = ' '.join(part for part in [summary, paraphrase, relationship, *queries_list] if part)
            kw_text = ' '.join(part for part in [*keywords_list, emotion] if part)
            con.execute(
                'INSERT INTO search VALUES(?,?,?,?)',
                (sid, normalize(raw), normalize(description), normalize(kw_text)),
            )
            valid_records.append((start, end, sid))
            con.execute('INSERT INTO quotes VALUES(?,?,?,?,?)', (sid, start, end, raw, normalize(raw)))
            stats['scenes'] += 1

            beat = ' '.join(part for part in [summary, paraphrase, relationship, ' '.join(keywords_list)] if part).strip()
            if not beat:
                beat = ' '.join(raw.split()[:45])
            seq_entries.append((sid, start, end, beat))

        # Index overlapping 4-scene chronological narrative windows for multi-beat memories.
        if seq_entries:
            step = 2 if len(seq_entries) > 4 else max(1, len(seq_entries))
            for idx in range(0, len(seq_entries), step):
                win = seq_entries[idx:idx + 4]
                if not win:
                    continue
                narrative = normalize(' '.join(item[3] for item in win))
                if narrative:
                    con.execute(
                        'INSERT INTO sequences VALUES(?,?,?,?,?)',
                        (
                            mid,
                            json.dumps([item[0] for item in win]),
                            win[0][1],
                            win[-1][2],
                            narrative,
                        ),
                    )
                    stats['sequences'] += 1
                if idx + 4 >= len(seq_entries):
                    break

        # Index boundary bridges for quotes crossing chunk boundaries.
        if lines and valid_records:
            for prior, current in zip(valid_records, valid_records[1:]):
                if current[0] - prior[1] > 5:
                    continue
                boundary = bisect_left(starts, current[0] - 0.05)
                window = lines[max(0, boundary - 2):boundary + 2]
                if not window or any(b.start - a.end > 5 for a, b in zip(window, window[1:])):
                    continue
                raw = ' '.join(s.raw_text for s in window)
                con.execute('INSERT INTO quotes VALUES(?,?,?,?,?)', (prior[2], window[0].start, window[-1].end, raw, normalize(raw)))

        stats['movies'] += 1
        if movie_no % 100 == 0:
            print(f'Indexed {movie_no + 1}/{len(requested)} movies; {stats["scenes"]} scenes', flush=True)

    manifest = {'schema': 2, 'source': str(source.resolve()), 'source_sha256': digest(source), 'stats': stats}
    con.execute('INSERT INTO meta VALUES(?,?)', ('manifest', json.dumps(manifest)))
    con.execute("INSERT INTO search(search) VALUES('optimize')")
    con.execute("INSERT INTO quotes(quotes) VALUES('optimize')")
    con.execute("INSERT INTO sequences(sequences) VALUES('optimize')")
    con.commit()
    con.close()
    temporary.replace(db)
    db.with_suffix('.coverage.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({k: v if not isinstance(v, list) else len(v) for k, v in stats.items()}), flush=True)
    return manifest
