import json
import threading
from urllib.error import HTTPError
from urllib.request import urlopen

import faiss
import numpy as np
import pytest

from dialoguematch.indexes import IndexSelector, LabSemanticSearch
from dialoguematch import server


def test_index_search_deduplicates_sentence_hits_and_filters_movies():
    index = faiss.IndexFlatIP(2)
    index.add(np.array([[1, 0], [.9, .1], [.8, .2], [0, 1]], dtype='float32'))
    class Tokenizer:
        def encode(self, text, add_special_tokens=False):
            return [1]
    class Encoder:
        tokenizer = Tokenizer()
        def encode(self, texts, normalize_embeddings=True):
            return np.array([[1, 0]] * len(texts), dtype='float32')
    search = LabSemanticSearch.__new__(LabSemanticSearch)
    search.index, search.ids, search.sentence = index, ['m1_1', 'm1_1', 'm2_1', 'm3_1'], True
    search.model_name, search.model, search.tokenizer, search.max_length = 'mini', Encoder(), Tokenizer(), 256
    assert search.search('example', limit=2) == ['m1_1', 'm2_1']
    assert search.search('example', limit=2, allowed={'m2_1', 'm3_1'}) == ['m2_1', 'm3_1']
    assert search.search('example', allowed=set()) == []


def test_selector_rejects_unverified_or_unknown_index(tmp_path):
    class Semantic:
        ids = ['x']
    class Engine:
        semantic = Semantic()
    (tmp_path / 'catalog.json').write_text(json.dumps([
        {'folder': '../escape', 'status': 'verified_sampled'},
        {'folder': 'unsafe', 'status': 'unverified'}]))
    selector = IndexSelector(Engine(), tmp_path)
    assert [x['id'] for x in selector.options()] == ['current']
    with pytest.raises(ValueError):
        selector.activate('../escape')


def test_search_endpoint_passes_index_and_result_count(monkeypatch):
    class Semantic:
        ids = ['one']
    class Engine:
        semantic = Semantic()
        def status(self):
            return {'stats': {'movies': 1, 'scenes': 1}, 'semantic': True, 'reranker': False}
        def search(self, query, mode, limit, movie_id, retrieval):
            return {'results': [{'scene_id': str(i)} for i in range(limit)], 'retrieval': retrieval}
    class Selector:
        def __init__(self, engine): self.engine = engine
        def options(self): return [{'id': 'current', 'label': 'Current'}, {'id': 'other', 'label': 'Other'}]
        def activate(self, name):
            if name not in {'current', 'other'}: raise ValueError('Unknown or unavailable search index.')
            self.engine.selected = name
    class Artwork:
        enabled = False
    ready = threading.Event()
    instance = []
    original_server = server.ThreadingHTTPServer
    class TestServer(original_server):
        def __init__(self, address, handler):
            super().__init__(address, handler)
            instance.append(self)
            ready.set()
    monkeypatch.setattr(server, 'ThreadingHTTPServer', TestServer)
    monkeypatch.setattr(server, 'IndexSelector', Selector)
    monkeypatch.setattr(server, 'MovieArtwork', Artwork)
    engine = Engine()
    thread = threading.Thread(target=server.serve, args=(engine, 0), daemon=True)
    thread.start()
    assert ready.wait(5)
    base = f'http://127.0.0.1:{instance[0].server_port}'
    try:
        status = json.load(urlopen(base + '/api/status'))
        assert len(status['indexes']) == 2
        result = json.load(urlopen(base + '/api/search?q=test&index=other&k=3&retrieval=index'))
        assert engine.selected == 'other' and result['index'] == 'other'
        assert result['requested_k'] == 3 and len(result['results']) == 3 and result['retrieval'] == 'index'
        for query in ['k=0', 'k=31', 'k=abc', 'index=missing']:
            with pytest.raises(HTTPError) as exc:
                urlopen(base + '/api/search?q=test&' + query)
            assert exc.value.code == 400
    finally:
        instance[0].shutdown()
        thread.join(timeout=5)
