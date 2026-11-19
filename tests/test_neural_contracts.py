import json
import numpy as np
import pytest
from dialoguematch.build import digest
from dialoguematch.neural import SemanticSearch, Reranker


def test_stale_semantic_index_is_rejected_before_model_load(tmp_path):
    db = tmp_path / 'test.sqlite'
    db.write_bytes(b'new database')
    db.with_suffix('.vectors.json').write_text(json.dumps({'db_sha256': 'old'}))
    with pytest.raises(ValueError, match='older corpus'):
        SemanticSearch(db)


def test_vector_id_mapping_and_query_prefix(tmp_path, monkeypatch):
    db = tmp_path / 'test.sqlite'
    db.write_bytes(b'database')
    np.save(db.with_suffix('.vectors.npy'), np.array([[0, 1], [1, 0]], dtype='float32'))
    manifest = {'db_sha256': digest(db), 'vectors_sha256': digest(db.with_suffix('.vectors.npy')),
                'ids': ['second', 'first'], 'model': 'fixture', 'max_seq_length': 512, 'query_prefix': 'search: '}
    db.with_suffix('.vectors.json').write_text(json.dumps(manifest))
    class Encoder:
        def encode(self, queries, **kwargs):
            assert queries == ['search: hello']
            return np.array([[1, 0]], dtype='float32')
    monkeypatch.setattr('dialoguematch.neural.load_encoder', lambda name: Encoder())
    engine = SemanticSearch(db)
    assert engine.search('hello', 1) == ['first']
    assert engine.search('hello', 2, {'second'}) == ['second']


def test_reranker_covers_tail_and_token_budget():
    class Tokenizer:
        def encode(self, text, **kwargs):
            return text.split()
        def decode(self, tokens, **kwargs):
            return ' '.join(tokens)
    class Model:
        tokenizer = Tokenizer()
        def predict(self, pairs, **kwargs):
            assert all(len(a.split()) + len(b.split()) < 512 for a, b in pairs)
            assert any('distinctive_tail_quote' in b for _, b in pairs)
            return [1 if 'distinctive_tail_quote' in b else 0 for _, b in pairs]
    reranker = Reranker.__new__(Reranker)
    reranker.model = Model()
    results = reranker.rank('find this quote', [{'id': 'scene', 'summary': 'summary ' * 100, 'text': 'word ' * 1000 + 'distinctive_tail_quote'}])
    assert results['scene'] == 1


def test_reranker_keeps_a_clue_at_end_of_long_query():
    class Tokenizer:
        def encode(self, text, **kwargs):
            return text.split()
        def decode(self, tokens, **kwargs):
            return ' '.join(tokens)
    class Model:
        tokenizer = Tokenizer()
        def predict(self, pairs, **kwargs):
            assert all(len(a.split()) <= 256 and len(a.split()) + len(b.split()) < 512 for a, b in pairs)
            return [5 if 'distinctive_clue' in a else 0 for a, _ in pairs]
    reranker = Reranker.__new__(Reranker)
    reranker.model = Model()
    result = reranker.rank('filler ' * 300 + 'distinctive_clue', [{'id': 'scene', 'summary': '', 'text': 'short passage'}])
    assert result['scene'] == 5


def test_semantic_search_windows_long_query_before_encoding():
    class Tokenizer:
        def encode(self, text, **kwargs):
            return text.split()
        def decode(self, tokens, **kwargs):
            return ' '.join(tokens)
    class Encoder:
        tokenizer = Tokenizer()
        def encode(self, queries, **kwargs):
            assert all(len(q.split()) <= 16 for q in queries)
            return np.array([[1, 0] if 'needle' in q else [0, 1] for q in queries], dtype='float32')
    search = SemanticSearch.__new__(SemanticSearch)
    search.manifest = {'max_seq_length': 20}
    search.model = Encoder()
    search.ids = ['answer']
    search.vectors = np.array([[1, 0]], dtype='float32')
    assert search.search('filler ' * 50 + 'needle') == ['answer']
