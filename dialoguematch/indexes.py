"""Select sampled-verified local semantic indexes for the search pipeline."""
from collections import OrderedDict, defaultdict
import json
from pathlib import Path

from .neural import BGE_PREFIX, load_encoder, load_fine_encoder, query_windows

PREFIX = BGE_PREFIX


class LabSemanticSearch:
    def __init__(self, folder):
        import faiss

        folder = Path(folder)
        root = folder.parent
        config = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
        if config['status'] != 'verified_sampled':
            raise ValueError('This index has not been verified for text search.')
        self.index = faiss.read_index(str(folder / 'index.faiss'), faiss.IO_FLAG_MMAP | faiss.IO_FLAG_READ_ONLY)
        self.ids = json.loads((root / config['mapping']).read_text(encoding='utf-8'))
        if len(self.ids) != self.index.ntotal:
            raise ValueError('The selected index and its passage mapping do not match.')
        self.sentence = config.get('unit') == 'sentence'
        self.model_name = config['model']

        by_id = defaultdict(list)
        for pos, sid in enumerate(self.ids):
            by_id[sid].append(pos)
        self._id_positions = dict(by_id)

        if self.model_name == 'fine':
            self.model = load_fine_encoder(root / 'shared/fine_model')
            self.tokenizer = self.model.tokenizer
            self.max_length = 512
        else:
            names = {
                'bge': 'BAAI/bge-large-en-v1.5',
                'base': 'BAAI/bge-base-en',
                'mini': 'sentence-transformers/all-MiniLM-L6-v2',
            }
            self.model = load_encoder(names[self.model_name])
            self.max_length = 256 if self.model_name == 'mini' else 512
            self.model.max_seq_length = self.max_length
            self.tokenizer = self.model.tokenizer

    def search(self, query, limit=100, allowed=None):
        import numpy as np

        prefix = PREFIX if self.model_name in {'bge', 'base', 'fine'} else ''
        budget = max(16, self.max_length - len(self.tokenizer.encode(prefix, add_special_tokens=False)) - 4)
        windows = [prefix + part for part in query_windows(query, self.tokenizer, budget)]
        if self.model_name == 'fine':
            vectors = self.model.encode(windows)
        else:
            if hasattr(self.model, 'max_seq_length'):
                self.model.max_seq_length = self.max_length
            vectors = self.model.encode(windows, normalize_embeddings=True)
        vectors = np.ascontiguousarray(vectors, dtype='float32')

        if allowed is not None:
            id_positions = getattr(self, '_id_positions', None)
            if id_positions is not None:
                pos_list = []
                for sid in allowed:
                    if sid in id_positions:
                        pos_list.extend(id_positions[sid])
                positions = np.array(sorted(pos_list), dtype='int64')
            else:
                positions = np.fromiter((i for i, sid in enumerate(self.ids) if sid in allowed), dtype='int64')
            if not len(positions):
                return []
            values = self.index.reconstruct_batch(positions)
            scores = np.max(values @ vectors.T, axis=1)
            order = np.argsort(-scores)
            pairs = ((float(scores[i]), int(positions[i])) for i in order)
        else:
            depth = min(self.index.ntotal, max(limit, 1500 if self.sentence else limit))
            scores, positions = self.index.search(vectors, depth)
            pairs = sorted(
                (
                    (float(score), int(pos))
                    for row, inds in zip(scores, positions)
                    for score, pos in zip(row, inds)
                    if pos >= 0
                ),
                reverse=True,
            )
        found, seen = [], set()
        for _, position in pairs:
            sid = self.ids[position]
            if sid not in seen:
                seen.add(sid)
                found.append(sid)
                if len(found) >= limit:
                    break
        return found


class IndexSelector:
    def __init__(self, engine, lab_root=None):
        self.engine = engine
        self.default = engine.semantic
        self.active = 'current'
        self.root = Path(lab_root or Path(__file__).resolve().parents[1] / 'index_lab')
        self.choices = {}
        self._loaded: OrderedDict[str, LabSemanticSearch] = OrderedDict()
        catalog = self.root / 'catalog.json'
        if catalog.exists() and self.default is not None:
            for entry in json.loads(catalog.read_text(encoding='utf-8')):
                name = entry['folder']
                if entry['status'] != 'verified_sampled' or Path(name).name != name:
                    continue
                folder = self.root / name
                if (folder / 'index.faiss').is_file() and (folder / 'config.json').is_file():
                    try:
                        config = json.loads((folder / 'config.json').read_text(encoding='utf-8'))
                        if config.get('status') != 'verified_sampled' or not (self.root / config['mapping']).is_file():
                            continue
                        if config.get('model') == 'fine' and not (self.root / 'shared/fine_model/model.safetensors').is_file():
                            continue
                    except (OSError, ValueError, KeyError, TypeError):
                        continue
                    self.choices[name] = entry

    def options(self):
        label = 'Ensemble · Fine-tuned + BGE + Full Library' if hasattr(self.default, 'search_channels') else 'Current app index'
        return [
            {'id': 'current', 'label': label, 'count': len(self.default.ids) if self.default else 0},
            *[
                {'id': name, 'label': entry['original_path'], 'count': entry['count']}
                for name, entry in self.choices.items()
            ],
        ]

    def get(self, name):
        if name == 'current':
            return self.default
        if name not in self.choices:
            raise ValueError('Unknown or unavailable search index.')
        if name in self._loaded:
            self._loaded.move_to_end(name)
            return self._loaded[name]
        loaded = LabSemanticSearch(self.root / name)
        self._loaded[name] = loaded
        while len(self._loaded) > 4:
            self._loaded.popitem(last=False)
        return loaded

    def activate(self, name):
        if name == self.active:
            return
        target = self.get(name)
        self.engine.semantic = target
        self.active = name
