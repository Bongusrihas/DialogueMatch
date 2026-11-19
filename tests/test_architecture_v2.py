import json
import threading
from urllib.error import HTTPError
from urllib.request import urlopen

import numpy as np
import pytest

from dialoguematch import server
from dialoguematch.build import build
from dialoguematch.engine import SearchEngine
from dialoguematch.neural import Reranker, build_gap_vectors, rebind_vector_manifest
from dialoguematch.query import analyze_query
from dialoguematch.text import normalize, search_content


@pytest.fixture
def rich_corpus(tmp_path):
    subs = tmp_path / 'subtitles'
    subs.mkdir()
    (subs / 'tt001.srt').write_text(
        '1\n00:00:10,000 --> 00:00:14,000\nMessages span 23 years.\n\n'
        '2\n00:00:15,000 --> 00:00:19,000\nPlay from the beginning.\n',
        encoding='utf-8',
    )
    (subs / 'tt002.srt').write_text(
        '1\n00:00:30,000 --> 00:00:35,000\nAre you not entertained?\n',
        encoding='utf-8',
    )
    source = tmp_path / 'chunks.json'
    source.write_text(
        json.dumps([
            {
                '_id': 'tt001_0',
                'movie_id': 'tt001',
                'start_time': 10,
                'end_time': 19,
                'text': 'Messages span 23 years. Play from the beginning.',
                'summary': 'Cooper watches decades of recorded video messages from his children.',
                'paraphrase': 'A father breaks down watching years of missed family updates.',
                'relationship': 'Cooper and his children',
                'emotion': 'grief',
                'queries': ['dad cries watching 23 years of messages from kids'],
                'keywords': ['video messages', 'time dilation', 'family'],
            },
            {
                '_id': 'tt001_1',
                'movie_id': 'tt001',
                'start_time': 25,
                'end_time': 35,
                'text': 'We must plot a course to the next planet.',
                'summary': 'Crew debates fuel limits and orbital navigation.',
                'paraphrase': 'Astronauts plan their next trajectory.',
                'keywords': ['navigation', 'fuel'],
            },
            {
                '_id': 'tt002_0',
                'movie_id': 'tt002',
                'start_time': 30,
                'end_time': 35,
                'text': 'Are you not entertained?',
                'summary': 'Maximus challenges the roaring arena crowd after defeating opponents.',
                'paraphrase': 'A gladiator confronts spectators in an amphitheater.',
                'keywords': ['gladiator', 'arena', 'crowd'],
            },
        ]),
        encoding='utf-8',
    )
    metadata = tmp_path / 'movies.csv'
    metadata.write_text(
        'imdb_id,title,original_title,year,rating,votes\n'
        'tt001,Interstellar,Interstellar,2014,8.7,2500000\n'
        'tt002,Gladiator,Gladiator,2000,8.5,1800000\n',
        encoding='utf-8',
    )
    db = tmp_path / 'rich.sqlite'
    build(db, source, subs, metadata)
    engine = SearchEngine(db, neural=False, rerank=False)
    yield engine
    engine.close()


def test_preamble_stripping_handles_colon_leadins_and_tot_boilerplate():
    raw = (
        'I am trying to track down a film from a conversation I remember. '
        'Some small details could be wrong, and I cannot give you the year or the name of the lead actor. '
        'The part I remember goes like this: A skinny volunteer emerges from a scientific experiment.'
    )
    assert search_content(raw) == 'A skinny volunteer emerges from a scientific experiment.'

    inline = "What's the name of the movie where a boy has a crush on his neighbor across the street? Please help!"
    assert search_content(inline) == 'a boy has a crush on his neighbor across the street?'


def test_contractions_aligned_between_queries_and_chunks():
    assert normalize("There's no way who's here! I'd say you've won.") == (
        'there is no way who is here i would say you have won'
    )


def test_analyze_query_extracts_three_word_quotes_and_ignores_meta_quotes():
    plan = analyze_query('In Dark Knight, the villain asks "Why so serious?" during dinner.', mode='auto')
    assert plan.embedded_quotes == ['Why so serious?']
    assert plan.has_external_context is True

    meta_plan = analyze_query('“Hey do you recall a movie where a car crashes into a river?”', mode='auto')
    assert meta_plan.embedded_quotes == []


def test_title_resolution_and_catalog_search(rich_corpus):
    assert rich_corpus.resolve_movie('Interstellar') == 'tt001'
    assert rich_corpus.resolve_movie('Interstellar (2014)') == 'tt001'
    assert rich_corpus.resolve_movie('tt002') == 'tt002'
    assert rich_corpus.resolve_movie('tt9999999') is None
    assert rich_corpus.resolve_movie('Nonexistent Film Title') is None

    res = rich_corpus.search('navigation fuel', mode='scene', movie_id='Interstellar')
    assert res['results'][0]['scene_id'] == 'tt001_1'
    assert res['results'][0]['year'] == 2014
    assert res['results'][0]['rating'] == pytest.approx(8.7)

    cat = rich_corpus.catalog_search('inter')
    assert cat['results'][0]['id'] == 'tt001'


def test_unstemmed_quote_typo_catches_suffix_and_first_letter_transposition(rich_corpus):
    r1 = rich_corpus.search('are you not entertainned', mode='quote')
    assert r1['results'] and r1['results'][0]['scene_id'] == 'tt002_0'

    r2 = rich_corpus.search('era you not entertained', mode='quote')
    assert r2['results'] and r2['results'][0]['scene_id'] == 'tt002_0'


def test_paraphrase_and_sequence_windows_indexed(rich_corpus):
    # 'breaks down' and 'amphitheater' exist only in the new paraphrase field, not summary or dialogue!
    r1 = rich_corpus.search('gladiator confronts spectators in an amphitheater', mode='scene', debug=True)
    assert r1['results'][0]['scene_id'] == 'tt002_0'
    assert 'rare_clues' in r1['channels']

    # Multi-beat query combining beat from tt001_0 ('missed family updates') and tt001_1 ('orbital navigation')
    r2 = rich_corpus.search('missed family updates then orbital navigation trajectory', mode='scene', debug=True)
    assert 'sequences' in r2['channels']
    assert r2['results'][0]['movie_id'] == 'tt001'


def test_scene_context_returns_neighbors_and_lines(rich_corpus):
    ctx = rich_corpus.scene_context('tt001_0', neighbors=1)
    assert ctx['movie']['title'] == 'Interstellar'
    assert [w['scene_id'] for w in ctx['window']] == ['tt001_0', 'tt001_1']
    assert ctx['window'][0]['is_target'] is True
    assert len(ctx['window'][0]['lines']) == 2


def test_reranker_scores_rich_prose_view_when_present():
    class Tokenizer:
        def encode(self, text, **kwargs):
            return text.split()
        def decode(self, tokens, **kwargs):
            return ' '.join(tokens)

    class Model:
        tokenizer = Tokenizer()
        def predict(self, pairs, **kwargs):
            assert all(len(a.split()) + len(b.split()) < 512 for a, b in pairs)
            return [9.0 if 'amphitheater' in b else -5.0 for _, b in pairs]

    reranker = Reranker.__new__(Reranker)
    reranker.model = Model()
    scores = reranker.rank(
        'gladiator in amphitheater',
        [{
            'id': 'tt002_0',
            'summary': 'Maximus speaks.',
            'paraphrase': 'A gladiator confronts spectators in an amphitheater.',
            'queries': '["man shouts in arena"]',
            'keywords': '["gladiator"]',
            'text': 'Are you not entertained?',
        }],
    )
    assert scores['tt002_0'] == 9.0


def test_rebind_manifest_and_gap_vectors(rich_corpus, monkeypatch):
    db = rich_corpus.path
    vec_path = db.with_suffix('.vectors.npy')
    np.save(vec_path, np.array([[1.0, 0.0], [0.0, 1.0]], dtype='float32'))
    from dialoguematch.build import digest
    db.with_suffix('.vectors.json').write_text(
        json.dumps({
            'format': 1,
            'model': 'fixture',
            'max_seq_length': 128,
            'normalize': True,
            'db_sha256': 'stale_hash',
            'vectors_sha256': digest(vec_path),
            'ids': ['tt001_0', 'tt001_1'],
        }),
        encoding='utf-8',
    )
    rebound = rebind_vector_manifest(db)
    assert rebound['db_sha256'] == digest(db)
    assert rebound['lexical_only_scenes'] == 1

    class FakeEncoder:
        max_seq_length = 128
        def get_sentence_embedding_dimension(self):
            return 2
        def encode(self, docs, **kwargs):
            return np.ones((len(docs), 2), dtype='float32')

    monkeypatch.setattr('dialoguematch.neural.load_encoder', lambda name: FakeEncoder())
    # Force fallback to .vectors.json coverage by pointing ROOT away from real index_lab
    monkeypatch.setattr('dialoguematch.neural.ROOT', db.parent)
    gap_man = build_gap_vectors(db, anchor_count=2)
    assert gap_man['gap_count'] == 1
    assert gap_man['ids'][0] == 'tt002_0'


def test_server_catalog_and_scene_endpoints(rich_corpus, monkeypatch):
    class Artwork:
        enabled = False
    ready = threading.Event()
    instances = []
    orig = server.ThreadingHTTPServer

    class TestServer(orig):
        def __init__(self, address, handler):
            super().__init__(address, handler)
            instances.append(self)
            ready.set()

    monkeypatch.setattr(server, 'ThreadingHTTPServer', TestServer)
    monkeypatch.setattr(server, 'MovieArtwork', Artwork)
    thread = threading.Thread(target=server.serve, args=(rich_corpus, 0), daemon=True)
    thread.start()
    assert ready.wait(5)
    base = f'http://127.0.0.1:{instances[0].server_port}'
    try:
        cat = json.load(urlopen(base + '/api/catalog?q=gladiator'))
        assert cat['results'][0]['id'] == 'tt002'
        ctx = json.load(urlopen(base + '/api/scene?id=tt001_0'))
        assert ctx['scene_id'] == 'tt001_0'
        assert len(ctx['window']) == 2
        with pytest.raises(HTTPError) as exc:
            urlopen(base + '/api/scene?id=missing_scene')
        assert exc.value.code == 400
    finally:
        instances[0].shutdown()
        thread.join(timeout=5)
