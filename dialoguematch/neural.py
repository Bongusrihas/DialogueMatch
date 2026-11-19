"""Manifest-bound semantic indexes, multi-index ensemble, and multi-view reranking."""
from collections import defaultdict
import json
import os
from pathlib import Path
import sqlite3

# Encoders use PyTorch. Skip optional TensorFlow/Flax discovery overhead.
os.environ.setdefault('USE_TF', '0')
os.environ.setdefault('USE_FLAX', '0')

from .build import DEFAULT_DB, ROOT, digest
from .text import terms

MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
BGE_PREFIX = 'Represent this sentence for searching relevant passages: '

_SENTENCE_MODELS = {}
_FINE_MODELS = {}


def _configure_threads():
    import torch
    threads = min(8, os.cpu_count() or 4)
    torch.set_num_threads(threads)
    try:
        import faiss
        faiss.omp_set_num_threads(threads)
    except ImportError:
        pass


def query_windows(query, tokenizer, budget):
    tokens = tokenizer.encode(query, add_special_tokens=False)
    if len(tokens) <= budget:
        return [query]
    stride = max(1, budget - min(32, budget // 4))
    windows = []
    for start in range(0, len(tokens), stride):
        windows.append(tokenizer.decode(tokens[start:start + budget], skip_special_tokens=True))
        if start + budget >= len(tokens):
            break
    return windows


class FineEncoder:
    """Direct PyTorch CLS-pooled encoder for the local domain fine-tuned BGE weights."""

    def __init__(self, path):
        import numpy as np
        import torch
        from transformers import AutoModel, AutoTokenizer

        _configure_threads()
        self.np = np
        self.torch = torch
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
        self.model = AutoModel.from_pretrained(str(path), local_files_only=True).to(self.device).eval()
        self.max_seq_length = 512

    def encode(self, texts, batch_size=8, **kwargs):
        chunks = []
        for offset in range(0, len(texts), batch_size):
            inputs = self.tokenizer(
                texts[offset:offset + batch_size],
                padding=True,
                truncation=True,
                max_length=self.max_seq_length,
                return_tensors='pt',
            )
            if self.device != 'cpu':
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with self.torch.inference_mode():
                pooled = self.model(**inputs).last_hidden_state[:, 0]
                normed = self.torch.nn.functional.normalize(pooled, p=2, dim=1)
            chunks.append(normed.cpu().numpy())
        return self.np.concatenate(chunks, axis=0).astype('float32')


def load_fine_encoder(path=None):
    target = str(Path(path or ROOT / 'index_lab/shared/fine_model').resolve())
    if target not in _FINE_MODELS:
        _FINE_MODELS[target] = FineEncoder(target)
    return _FINE_MODELS[target]


def load_encoder(name=MODEL):
    _configure_threads()
    if name not in _SENTENCE_MODELS:
        import torch
        from sentence_transformers import SentenceTransformer

        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        try:
            model = SentenceTransformer(name, device=device, local_files_only=True)
        except OSError:
            model = SentenceTransformer(name, device=device)
        _SENTENCE_MODELS[name] = model
    model = _SENTENCE_MODELS[name]
    model.max_seq_length = 128
    return model


def legacy_document(sid, chunks):
    movie, number = sid.rsplit('_', 1)
    number = int(number)
    current = chunks[sid]['text'].strip()
    if len(current.split()) >= 512:
        return ' '.join(current.split()[:512])
    remaining = 512 - len(current.split())
    selected = []
    for offset in [1, 2]:
        for n in [number - offset, number + offset]:
            summary = chunks.get(f'{movie}_{n}', {}).get('summary', '').strip()
            if summary and remaining:
                words = summary.split()[:remaining]
                selected.append((n, ' '.join(words)))
                remaining -= len(words)
    return '\n\n'.join([text for _, text in sorted(selected)] + [current])


def import_legacy_vectors(db, index_path, ids_path, source_path, sample_count=32):
    """Verify sampled model/document correspondence before importing known local artifacts."""
    import faiss
    import numpy as np

    db = Path(db)
    index = faiss.read_index(str(index_path))
    ids = [str(x) for x in np.load(ids_path, allow_pickle=True).tolist()]
    source = json.loads(Path(source_path).read_text(encoding='utf-8'))
    chunks = {c['_id']: c for c in source}
    if len(ids) != index.ntotal or len(set(ids)) != len(ids) or any(sid not in chunks for sid in ids):
        raise ValueError('Legacy index ID mapping is inconsistent with its source.')
    if index.metric_type != faiss.METRIC_INNER_PRODUCT:
        raise ValueError('Expected an inner-product index.')
    model_name = 'BAAI/bge-large-en-v1.5'
    model = load_encoder(model_name)
    model.max_seq_length = 512
    positions = np.linspace(0, len(ids) - 1, min(sample_count, len(ids)), dtype=int)
    expected = model.encode([legacy_document(ids[int(i)], chunks) for i in positions], normalize_embeddings=True, batch_size=8)
    similarities = []
    for position, vector in zip(positions, expected):
        saved = index.reconstruct(int(position))
        similarity = float(np.dot(vector, saved) / (np.linalg.norm(saved) + 1e-9))
        similarities.append(similarity)
        if abs(float(np.linalg.norm(saved)) - 1) > 0.01 or similarity < 0.999:
            raise ValueError(f'Legacy vector verification failed at {position}: cosine={similarity}')
    con = sqlite3.connect(db)
    available = {r[0] for r in con.execute('SELECT id FROM scenes')}
    con.close()
    keep = [i for i, sid in enumerate(ids) if sid in available]
    target = db.with_suffix('.vectors.npy')
    work = db.with_suffix('.vectors.building.npy')
    vectors = np.lib.format.open_memmap(work, mode='w+', dtype='float32', shape=(len(keep), index.d))
    for offset in range(0, len(keep), 2048):
        positions_batch = keep[offset:offset + 2048]
        vectors[offset:offset + len(positions_batch)] = np.stack([index.reconstruct(i) for i in positions_batch])
    vectors.flush()
    del vectors
    work.replace(target)
    manifest = {
        'format': 1,
        'model': model_name,
        'max_seq_length': 512,
        'normalize': True,
        'query_prefix': BGE_PREFIX,
        'db_sha256': digest(db),
        'vectors_sha256': digest(target),
        'ids': [ids[i] for i in keep],
        'verification': {
            'method': 'sampled embedding reproduction',
            'samples': len(positions),
            'minimum_cosine': min(similarities),
            'source_sha256': digest(source_path),
            'index_sha256': digest(index_path),
        },
        'semantic_scenes': len(keep),
        'lexical_only_scenes': len(available) - len(keep),
    }
    db.with_suffix('.vectors.json').write_text(json.dumps(manifest), encoding='utf-8')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'ids'}, indent=2), flush=True)


def rebind_vector_manifest(db):
    """Re-verify existing .vectors.npy integrity and bind manifest to a rebuilt database of the same scenes."""
    db = Path(db)
    manifest_path = db.with_suffix('.vectors.json')
    vectors_path = db.with_suffix('.vectors.npy')
    if not manifest_path.is_file() or not vectors_path.is_file():
        raise FileNotFoundError('Existing vector manifest or array not found.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['vectors_sha256'] != digest(vectors_path):
        raise ValueError('Existing vectors checksum mismatch; run import-legacy or embed.')
    con = sqlite3.connect(db)
    available = {r[0] for r in con.execute('SELECT id FROM scenes')}
    con.close()
    missing = [sid for sid in manifest['ids'] if sid not in available]
    if missing:
        raise ValueError(f'{len(missing)} vector IDs are absent from rebuilt database; run import-legacy or embed.')
    manifest['db_sha256'] = digest(db)
    manifest['lexical_only_scenes'] = len(available) - len(manifest['ids'])
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    return manifest


def encode_document(row):
    # Separate descriptions stay searchable; no movie-title leakage into vectors.
    queries = json.loads(row['queries']) if row['queries'] else []
    paraphrase = row['paraphrase'] if 'paraphrase' in row.keys() else ''
    parts = [p for p in [row['summary'], paraphrase, *queries[:2]] if p]
    return ' '.join(parts).strip() or ' '.join(row['text'].split()[:110])


def build_vectors(db, model_name=MODEL, batch_size=64):
    import numpy as np

    db = Path(db)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute('SELECT * FROM scenes ORDER BY id').fetchall()
    con.close()
    model = load_encoder(model_name)
    model.max_seq_length = 256
    ids = [r['id'] for r in rows]
    target = db.with_suffix('.vectors.npy')
    work = db.with_suffix('.vectors.building.npy')
    vectors = np.lib.format.open_memmap(
        work, mode='w+', dtype='float32', shape=(len(rows), model.get_sentence_embedding_dimension())
    )
    for offset in range(0, len(rows), batch_size):
        vectors[offset:offset + batch_size] = model.encode(
            [encode_document(r) for r in rows[offset:offset + batch_size]],
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if offset % (batch_size * 20) == 0:
            print(f'Embedding {offset}/{len(rows)} scenes', flush=True)
    vectors.flush()
    del vectors
    work.replace(target)
    manifest = {
        'model': model_name,
        'max_seq_length': 256,
        'normalize': True,
        'format': 1,
        'db_sha256': digest(db),
        'vectors_sha256': digest(target),
        'ids': ids,
    }
    db.with_suffix('.vectors.json').write_text(json.dumps(manifest), encoding='utf-8')
    print(f'Semantic index ready: {len(rows)} scenes', flush=True)


def build_gap_vectors(db=DEFAULT_DB, model_name=MODEL, batch_size=128, anchor_count=1024):
    """Build a calibrated supplementary semantic index for recovered movies absent from legacy BGE indexes."""
    import numpy as np

    db = Path(db)
    covered = set()
    main_map = ROOT / 'index_lab/shared/assets/maps/main.json'
    if main_map.is_file():
        covered.update(json.loads(main_map.read_text(encoding='utf-8')))
    elif db.with_suffix('.vectors.json').is_file():
        covered.update(json.loads(db.with_suffix('.vectors.json').read_text(encoding='utf-8'))['ids'])

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    all_rows = con.execute('SELECT * FROM scenes ORDER BY id').fetchall()
    con.close()

    gap_rows = [r for r in all_rows if r['id'] not in covered]
    covered_rows = [r for r in all_rows if r['id'] in covered]
    anchors = []
    if covered_rows and anchor_count > 0:
        positions = np.linspace(0, len(covered_rows) - 1, min(anchor_count, len(covered_rows)), dtype=int)
        anchors = [covered_rows[int(i)] for i in positions]

    combined = gap_rows + anchors
    if not combined:
        print('No uncovered gap scenes found.', flush=True)
        return None

    model = load_encoder(model_name)
    model.max_seq_length = 256
    dim = model.get_sentence_embedding_dimension()
    target = db.with_suffix('.gap.npy')
    work = db.with_suffix('.gap.building.npy')
    vectors = np.lib.format.open_memmap(work, mode='w+', dtype='float32', shape=(len(combined), dim))

    for offset in range(0, len(combined), batch_size):
        batch = combined[offset:offset + batch_size]
        vectors[offset:offset + len(batch)] = model.encode(
            [encode_document(r) for r in batch],
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        if offset % (batch_size * 20) == 0:
            print(f'Embedding supplementary gap scenes {offset}/{len(combined)}', flush=True)
    vectors.flush()
    del vectors
    work.replace(target)

    manifest = {
        'format': 1,
        'model': model_name,
        'max_seq_length': 256,
        'normalize': True,
        'db_sha256': digest(db),
        'vectors_sha256': digest(target),
        'gap_count': len(gap_rows),
        'anchor_count': len(anchors),
        'ids': [r['id'] for r in combined],
    }
    db.with_suffix('.gap.json').write_text(json.dumps(manifest), encoding='utf-8')
    print(f'Supplementary gap index ready: {len(gap_rows)} recovered scenes + {len(anchors)} calibration anchors.', flush=True)
    return manifest


class SemanticSearch:
    def __init__(self, db):
        import numpy as np

        db = Path(db)
        self.manifest = json.loads(db.with_suffix('.vectors.json').read_text(encoding='utf-8'))
        if self.manifest['db_sha256'] != digest(db):
            raise ValueError('Semantic index belongs to an older corpus. Run python -m dialoguematch embed.')
        path = db.with_suffix('.vectors.npy')
        if self.manifest['vectors_sha256'] != digest(path):
            raise ValueError('Semantic index checksum mismatch. Rebuild it.')
        self.vectors = np.load(path, mmap_mode='r', allow_pickle=False)
        self.ids = self.manifest['ids']
        if len(self.ids) != len(self.vectors) or len(set(self.ids)) != len(self.ids):
            raise ValueError('Invalid semantic ID mapping')
        self._id_to_pos = {sid: idx for idx, sid in enumerate(self.ids)}
        self.model = load_encoder(self.manifest['model'])
        self.model.max_seq_length = self.manifest['max_seq_length']

    def search(self, query, limit=100, allowed=None):
        import numpy as np

        prefix = self.manifest.get('query_prefix', '')
        variants = [query]
        if hasattr(self.model, 'tokenizer'):
            budget = max(
                16,
                self.manifest['max_seq_length'] - len(self.model.tokenizer.encode(prefix, add_special_tokens=False)) - 4,
            )
            variants = query_windows(query, self.model.tokenizer, budget)
        self.model.max_seq_length = self.manifest['max_seq_length']
        vectors = self.model.encode([prefix + part for part in variants], normalize_embeddings=True)

        id_to_pos = getattr(self, '_id_to_pos', None)
        if allowed is not None and id_to_pos is not None:
            positions = np.fromiter((id_to_pos[sid] for sid in allowed if sid in id_to_pos), dtype='int64')
            if len(positions) == 0:
                return []
            sub = np.asarray(self.vectors[positions], dtype='float32')
            scores = np.max(sub @ vectors.T, axis=1)
            order = np.argsort(-scores)[:limit]
            return [self.ids[int(positions[i])] for i in order if np.isfinite(scores[i])]

        scores = np.max(self.vectors @ vectors.T, axis=1)
        if allowed is not None:
            scores = np.where(np.array([sid in allowed for sid in self.ids]), scores, -np.inf)
        count = min(limit, len(scores))
        if count == 0:
            return []
        indices = np.argpartition(-scores, count - 1)[:count]
        indices = indices[np.argsort(-scores[indices])]
        return [self.ids[int(i)] for i in indices if np.isfinite(scores[i])]


class _FaissMember:
    """Memory-mapped verified FAISS index member sharing a pooled query encoder."""

    def __init__(self, name: str, weight: float, index_path: Path, ids: list[str], model_kind: str):
        import faiss

        self.name = name
        self.weight = weight
        self.model_kind = model_kind
        self.index = faiss.read_index(str(index_path), faiss.IO_FLAG_MMAP | faiss.IO_FLAG_READ_ONLY)
        self.ids = ids
        if len(self.ids) != self.index.ntotal:
            raise ValueError(f'Index {name} length mismatch ({len(self.ids)} != {self.index.ntotal})')
        by_id = defaultdict(list)
        for pos, sid in enumerate(self.ids):
            by_id[sid].append(pos)
        self._id_positions = dict(by_id)

    def search_vectors(self, query_vecs, limit=150, allowed=None):
        import numpy as np

        if allowed is not None:
            pos_list = []
            for sid in allowed:
                if sid in self._id_positions:
                    pos_list.extend(self._id_positions[sid])
            if not pos_list:
                return []
            positions = np.array(sorted(pos_list), dtype='int64')
            reconstructed = self.index.reconstruct_batch(positions)
            scores = np.max(reconstructed @ query_vecs.T, axis=1)
            order = np.argsort(-scores)
            pairs = ((float(scores[i]), int(positions[i])) for i in order)
        else:
            depth = min(self.index.ntotal, limit)
            scores, positions = self.index.search(query_vecs, depth)
            pairs = sorted(
                (
                    (float(sc), int(pos))
                    for row_s, row_p in zip(scores, positions)
                    for sc, pos in zip(row_s, row_p)
                    if pos >= 0
                ),
                reverse=True,
            )

        out, seen = [], set()
        for _, pos in pairs:
            sid = self.ids[pos]
            if sid not in seen:
                seen.add(sid)
                out.append(sid)
                if len(out) >= limit:
                    break
        return out


class _CalibratedGapSearch:
    """Supplementary MiniLM search over recovered movies calibrated against reference anchors."""

    def __init__(self, db: Path):
        import numpy as np

        self.np = np
        manifest = json.loads(db.with_suffix('.gap.json').read_text(encoding='utf-8'))
        path = db.with_suffix('.gap.npy')
        if manifest['db_sha256'] != digest(db) or manifest['vectors_sha256'] != digest(path):
            raise ValueError('Stale supplementary gap index.')
        self.vectors = np.load(path, mmap_mode='r', allow_pickle=False)
        self.ids = manifest['ids']
        self.gap_count = int(manifest['gap_count'])
        self.gap_ids = self.ids[:self.gap_count]
        self.max_seq_length = manifest.get('max_seq_length', 256)
        self.model = load_encoder(manifest['model'])
        self._id_to_pos = {sid: idx for idx, sid in enumerate(self.gap_ids)}

    def search(self, query: str, limit=40, allowed=None):
        np = self.np
        self.model.max_seq_length = self.max_seq_length
        budget = max(16, self.max_seq_length - 4)
        variants = query_windows(query, self.model.tokenizer, budget)
        qvecs = self.model.encode(variants, normalize_embeddings=True)

        if allowed is not None:
            positions = np.fromiter((self._id_to_pos[sid] for sid in allowed if sid in self._id_to_pos), dtype='int64')
            if len(positions) == 0:
                return []
            sub = np.asarray(self.vectors[positions], dtype='float32')
            scores = np.max(sub @ qvecs.T, axis=1)
            order = np.argsort(-scores)[:limit]
            return [self.gap_ids[int(positions[i])] for i in order if np.isfinite(scores[i])]

        all_scores = np.max(self.vectors @ qvecs.T, axis=1)
        gap_scores = all_scores[:self.gap_count]
        anchor_scores = all_scores[self.gap_count:]
        # Require recovered scenes to beat the 98.5th percentile of reference anchors so
        # unrelated queries never get polluted by the smaller 74-movie cohort.
        floor = 0.38
        if len(anchor_scores) >= 32:
            floor = max(floor, float(np.quantile(anchor_scores, 0.985)) - 0.015)

        qualifying = np.flatnonzero(gap_scores >= floor)
        if len(qualifying) == 0:
            return []
        ordered = qualifying[np.argsort(-gap_scores[qualifying])][:limit]
        return [self.gap_ids[int(i)] for i in ordered]


class MultiIndexSemanticSearch:
    """Fuses domain fine-tuned dialogue/summary indexes, broad BGE indexes, and calibrated gap coverage."""

    SPECS = (
        ('fine_dialogue', 1.10, '02_preprocessing_finetuned_model_dialogue', 'fine'),
        ('fine_summary', 1.00, '04_preprocessing_finetuned_model_summary', 'fine'),
        ('bge_dialogue', 0.80, '18_preprocessing_indexes_movies_t_e_baai', 'bge'),
        ('bge_context', 0.85, '12_preprocessing_indexes_chunk_embeddings_ctx_combined', 'bge'),
    )

    @classmethod
    def is_available(cls, db: Path, lab_root: Path | None = None) -> bool:
        lab = Path(lab_root or ROOT / 'index_lab')
        if Path(db).resolve() != DEFAULT_DB.resolve():
            return False
        if not (lab / 'shared/fine_model/model.safetensors').is_file():
            return False
        for _, _, folder, _ in cls.SPECS:
            if not (lab / folder / 'index.faiss').is_file() or not (lab / folder / 'config.json').is_file():
                return False
        return True

    def __init__(self, db: Path, lab_root: Path | None = None, fallback: SemanticSearch | None = None):
        self.db = Path(db)
        self.lab = Path(lab_root or ROOT / 'index_lab')
        self.fallback = fallback
        self.members: list[_FaissMember] = []
        map_cache: dict[str, list[str]] = {}
        covered_ids: set[str] = set(fallback.ids) if fallback is not None else set()

        for name, weight, folder_name, expected_model in self.SPECS:
            folder = self.lab / folder_name
            cfg = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
            if cfg.get('status') != 'verified_sampled':
                continue
            map_rel = cfg['mapping']
            if map_rel not in map_cache:
                map_cache[map_rel] = json.loads((self.lab / map_rel).read_text(encoding='utf-8'))
            ids = map_cache[map_rel]
            member = _FaissMember(name, weight, folder / 'index.faiss', ids, expected_model)
            self.members.append(member)
            covered_ids.update(ids)

        self.fine_encoder = load_fine_encoder(self.lab / 'shared/fine_model')
        self.bge_encoder = load_encoder('BAAI/bge-large-en-v1.5')
        self.bge_encoder.max_seq_length = 512

        self.gap: _CalibratedGapSearch | None = None
        if self.db.with_suffix('.gap.json').is_file() and self.db.with_suffix('.gap.npy').is_file():
            try:
                self.gap = _CalibratedGapSearch(self.db)
                covered_ids.update(self.gap.gap_ids)
            except (OSError, ValueError):
                self.gap = None

        con = sqlite3.connect(self.db)
        valid_db_ids = {r[0] for r in con.execute('SELECT id FROM scenes')}
        con.close()
        self.ids = sorted(covered_ids & valid_db_ids)

    def _encode_family(self, query: str, family: str):
        import numpy as np

        if family == 'fine':
            budget = max(16, 512 - len(self.fine_encoder.tokenizer.encode(BGE_PREFIX, add_special_tokens=False)) - 4)
            windows = [BGE_PREFIX + part for part in query_windows(query, self.fine_encoder.tokenizer, budget)]
            vecs = self.fine_encoder.encode(windows)
        else:
            self.bge_encoder.max_seq_length = 512
            budget = max(16, 512 - len(self.bge_encoder.tokenizer.encode(BGE_PREFIX, add_special_tokens=False)) - 4)
            windows = [BGE_PREFIX + part for part in query_windows(query, self.bge_encoder.tokenizer, budget)]
            vecs = self.bge_encoder.encode(windows, normalize_embeddings=True, show_progress_bar=False)
        return np.ascontiguousarray(vecs, dtype='float32')

    def search_channels(self, query: str, limit=150, allowed=None) -> dict[str, tuple[float, list[str]]]:
        fine_vecs = self._encode_family(query, 'fine')
        bge_vecs = self._encode_family(query, 'bge')
        results: dict[str, tuple[float, list[str]]] = {}
        for member in self.members:
            vecs = fine_vecs if member.model_kind == 'fine' else bge_vecs
            hits = member.search_vectors(vecs, limit=limit, allowed=allowed)
            results[member.name] = (member.weight, hits)
        if self.gap is not None:
            gap_hits = self.gap.search(query, limit=min(40, limit), allowed=allowed)
            if gap_hits:
                results['semantic_gap'] = (0.75, gap_hits)
        return results

    def search(self, query: str, limit=150, allowed=None) -> list[str]:
        channel_map = self.search_channels(query, limit=max(limit, 100), allowed=allowed)
        scores = defaultdict(float)
        for weight, ranking in channel_map.values():
            for rank, sid in enumerate(ranking, 1):
                scores[sid] += weight / (60 + rank)
        return sorted(scores, key=scores.get, reverse=True)[:limit]


class Reranker:
    DEFAULT_MODEL = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
    FALLBACK_MODEL = 'cross-encoder/ms-marco-MiniLM-L-12-v2'

    def __init__(self, model_name=None):
        import torch
        from sentence_transformers import CrossEncoder

        _configure_threads()
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        chosen = model_name or self.DEFAULT_MODEL
        self.model = None
        for candidate in ([chosen] if model_name else [self.DEFAULT_MODEL, self.FALLBACK_MODEL]):
            try:
                self.model = CrossEncoder(candidate, max_length=512, device=device, local_files_only=True)
                self.model_name = candidate
                break
            except OSError:
                continue
        if self.model is None:
            self.model = CrossEncoder(chosen, max_length=512, device=device)
            self.model_name = chosen

    def rank(self, query, records):
        # Score overlapping query windows so late clues in long memories are never dropped.
        variants = query_windows(query, self.model.tokenizer, 256)
        combined = {}
        for variant in variants:
            for sid, score in self._rank_window(variant, records).items():
                combined[sid] = max(combined.get(sid, float('-inf')), score)
        return combined

    @staticmethod
    def _build_scene_header(query_term_set: set[str], row: dict) -> str:
        """Build a unified, grounded scene header from summary, paraphrase, top synthetic memory match, and cues."""
        summary = (row.get('summary') or '').strip()
        paraphrase = (row.get('paraphrase') or '').strip()
        relationship = (row.get('relationship') or '').strip()
        raw_queries = row.get('queries')
        raw_keywords = row.get('keywords')

        queries_list = []
        if isinstance(raw_queries, str) and raw_queries.startswith('['):
            try:
                queries_list = json.loads(raw_queries)
            except ValueError:
                queries_list = []
        elif isinstance(raw_queries, list):
            queries_list = raw_queries

        keywords_list = []
        if isinstance(raw_keywords, str) and raw_keywords.startswith('['):
            try:
                keywords_list = json.loads(raw_keywords)
            except ValueError:
                keywords_list = []
        elif isinstance(raw_keywords, list):
            keywords_list = raw_keywords

        best_q = ''
        if queries_list:
            if query_term_set:
                best_q = max(queries_list, key=lambda q: (len(set(terms(q)) & query_term_set), len(q)))
            else:
                best_q = queries_list[0]

        parts = []
        if summary:
            parts.append('Scene description: ' + summary)
        prev_beat = (row.get('prev_summary') or '').strip()
        if prev_beat:
            parts.append('Preceding beat: ' + prev_beat[:120])
        if paraphrase:
            parts.append('Event: ' + paraphrase)
        if best_q:
            parts.append('Memory: ' + best_q)
        if relationship:
            parts.append('Characters: ' + relationship)
        if keywords_list:
            parts.append('Cues: ' + ', '.join(keywords_list[:6]))
        return ' | '.join(parts) if parts else 'Scene description: '

    def _rank_window(self, query, records):
        pairs, owners, lengths = [], [], []
        tokenizer = self.model.tokenizer
        query_tokens = tokenizer.encode(query, add_special_tokens=False)
        if len(query_tokens) > 256:
            query = tokenizer.decode(query_tokens[:256], skip_special_tokens=True)
            query_tokens = query_tokens[:256]

        max_doc_tokens = max(64, 480 - len(query_tokens))
        q_terms = set(terms(query))

        for row in records:
            sid = row['id']
            header_cap = min(115, max(24, int(max_doc_tokens * 0.42)))
            header_str = self._build_scene_header(q_terms, row)
            header = tokenizer.encode(header_str, add_special_tokens=False)[:header_cap]
            header_text = tokenizer.decode(header, skip_special_tokens=True)

            dialogue = tokenizer.encode(row.get('text') or '', add_special_tokens=False)
            budget = max(48, max_doc_tokens - len(header) - 6)
            stride = max(32, budget - 40)

            for start in range(0, max(1, len(dialogue)), stride):
                window_tokens = dialogue[start:start + budget]
                document = header_text + '\nDialogue: ' + tokenizer.decode(window_tokens, skip_special_tokens=True)
                pairs.append((query, document))
                owners.append(sid)
                lengths.append(len(header) + len(window_tokens) + 2)
                if start + budget >= len(dialogue):
                    break

        if not pairs:
            return {}

        order = sorted(range(len(pairs)), key=lengths.__getitem__)
        pairs = [pairs[i] for i in order]
        owners = [owners[i] for i in order]
        scores = self.model.predict(pairs, batch_size=32, show_progress_bar=False)
        result = {}
        for sid, score in zip(owners, scores):
            result[sid] = max(result.get(sid, float('-inf')), float(score))
        return result
