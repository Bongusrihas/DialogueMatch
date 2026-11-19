import json
import threading
from urllib.request import urlopen

import numpy as np
import pytest

from dialoguematch import server
from dialoguematch.build import build
from dialoguematch.context import build_context_index, decompose_query
from dialoguematch.engine import SearchEngine


def test_decompose_query_separates_intro_premise_from_target_scene():
    q1 = (
        'The movie starts with crops failing on Earth and a former pilot leaving his kids, '
        'and much later there is a scene where he sits down and watches 23 years of messages.'
    )
    d1 = decompose_query(q1, mode='auto')
    assert d1.is_decomposed is True
    assert 'crops failing' in d1.global_context
    assert '23 years of messages' in d1.scene_target
    assert d1.global_checks_opening is True
    assert d1.temporal_hint == 'late'

    q2 = (
        'In a movie about a college student creating a social website at Harvard, '
        'his best friend storms in furious that his shares were diluted and smashes a laptop.'
    )
    d2 = decompose_query(q2, mode='auto')
    assert d2.is_decomposed is True
    assert 'Harvard' in d2.global_context
    assert 'smashes a laptop' in d2.scene_target

    q3 = (
        'It is a thriller about a man with short-term memory loss using tattoos to find a killer. '
        'A woman hides all the pens in her house and insults him because he will forget.'
    )
    d3 = decompose_query(q3, mode='scene')
    assert d3.is_decomposed is True
    assert 'short-term memory loss' in d3.global_context
    assert 'hides all the pens' in d3.scene_target

    # Single-scene opening query must NOT split in half, while still capturing opening timing
    q4 = 'At the very beginning of the movie, bank robbers wearing clown masks betray each other.'
    d4 = decompose_query(q4, mode='scene')
    assert d4.is_decomposed is False
    assert d4.temporal_hint == 'opening'
    assert d4.temporal_range == (0.0, 0.18)

    # Quote mode never decomposes
    assert decompose_query(q1, mode='quote').is_decomposed is False


def test_global_context_bridges_intro_clue_to_later_scene(tmp_path, monkeypatch):
    subs = tmp_path / 'subs'
    subs.mkdir()
    source = tmp_path / 'chunks.json'
    # Movie A (tt100): opens with 'balloon house floating with elderly widower', ends with 'talking dog collar broken'
    # Movie B (tt200): also has a scene about 'talking dog collar broken', but its premise is 'cyberpunk hackers in Tokyo'
    source.write_text(
        json.dumps([
            {
                '_id': 'tt100_0',
                'movie_id': 'tt100',
                'start_time': 10,
                'end_time': 100,
                'text': 'We tied thousands of balloons to the chimney and lifted off.',
                'summary': 'An elderly widower ties thousands of colorful balloons to his house and floats into the sky.',
                'keywords': ['balloons', 'widower', 'flying house'],
            },
            {
                '_id': 'tt100_1',
                'movie_id': 'tt100',
                'start_time': 400,
                'end_time': 500,
                'text': 'We are crossing the storm clouds toward the waterfall.',
                'summary': 'Carl and the boy steer the floating house through storm clouds.',
                'keywords': ['storm', 'waterfall'],
            },
            {
                '_id': 'tt100_2',
                'movie_id': 'tt100',
                'start_time': 900,
                'end_time': 1000,
                'text': 'My collar is broken so my voice sounds squeaky today.',
                'summary': 'A golden dog explains that his special translation collar is broken.',
                'keywords': ['dog', 'broken collar', 'voice'],
            },
            {
                '_id': 'tt200_0',
                'movie_id': 'tt200',
                'start_time': 10,
                'end_time': 100,
                'text': 'We infiltrate the Tokyo mainframe tonight.',
                'summary': 'Cyberpunk hackers infiltrate a corporate mainframe in neon Tokyo.',
                'keywords': ['hackers', 'tokyo', 'mainframe'],
            },
            {
                '_id': 'tt200_1',
                'movie_id': 'tt200',
                'start_time': 500,
                'end_time': 600,
                'text': 'My collar is broken so my voice sounds squeaky today.',
                'summary': 'A robotic dog explains that his special translation collar is broken.',
                'keywords': ['dog', 'broken collar', 'voice'],
            },
        ]),
        encoding='utf-8',
    )
    metadata = tmp_path / 'movies.csv'
    metadata.write_text(
        'imdb_id,title,original_title,year,rating,votes\n'
        'tt100,Sky House,Sky House,2009,8.3,900000\n'
        'tt200,Neon Hackers,Neon Hackers,2020,7.1,100000\n',
        encoding='utf-8',
    )
    db = tmp_path / 'ctx_test.sqlite'
    build(db, source, subs, metadata)

    class FakeEncoder:
        max_seq_length = 256
        def encode(self, docs, **kwargs):
            vecs = []
            for d in docs:
                low = d.lower()
                if 'balloon' in low or 'widower' in low or 'sky house' in low:
                    vecs.append([1.0, 0.0])
                elif 'hacker' in low or 'tokyo' in low:
                    vecs.append([0.0, 1.0])
                else:
                    vecs.append([0.5, 0.5])
            arr = np.array(vecs, dtype='float32')
            norms = np.linalg.norm(arr, axis=1, keepdims=True) + 1e-9
            return arr / norms

    monkeypatch.setattr('dialoguematch.neural.load_encoder', lambda name=None: FakeEncoder())
    build_context_index(db)

    engine = SearchEngine(db, neural=False, rerank=False)
    # Enable dense movie vectors on context_index with FakeEncoder even in lexical test
    engine.context_index.encoder = FakeEncoder()
    engine.context_index.vectors = np.load(db.with_suffix('.movies.npy'))

    try:
        query = (
            'The movie starts with an elderly widower tying balloons to his house to float into the sky, '
            'and near the end there is a scene where a dog says his translation collar is broken.'
        )
        res = engine.search(query, mode='auto', debug=True)
        assert res['query_context']['is_decomposed'] is True
        assert res['query_context']['matched_movies'][0]['movie_id'] == 'tt100'
        top = res['results'][0]
        # Must pinpoint the DOG COLLAR scene in Sky House (tt100_2), NOT the intro balloon chunk (tt100_0) and NOT Neon Hackers (tt200_1)!
        assert top['scene_id'] == 'tt100_2'
        assert top['act_label'] == 'Finale'
        assert top['progress'] > 0.85
        assert 'storm clouds' in top['prev_beat']
        assert 'Sky House' in top['why_matched']
    finally:
        engine.close()


def test_dossier_endpoint(tmp_path, monkeypatch):
    subs = tmp_path / 'subs'
    subs.mkdir()
    source = tmp_path / 'chunks.json'
    source.write_text(
        json.dumps([
            {
                '_id': 'tt100_0',
                'movie_id': 'tt100',
                'start_time': 10,
                'end_time': 80,
                'text': 'Hello there.',
                'summary': 'Cooper greets Murph on the porch.',
                'relationship': 'Cooper and Murph',
                'keywords': ['porch', 'family'],
            }
        ]),
        encoding='utf-8',
    )
    metadata = tmp_path / 'movies.csv'
    metadata.write_text('imdb_id,title,year,rating,votes\ntt100,Test Film,2014,8.7,500\n', encoding='utf-8')
    db = tmp_path / 'd.sqlite'
    build(db, source, subs, metadata)
    monkeypatch.setattr(
        'dialoguematch.neural.load_encoder',
        lambda name=None: type('E', (), {'max_seq_length': 256, 'encode': lambda self, d, **k: np.ones((len(d), 2), dtype='float32')})(),
    )
    build_context_index(db)
    eng = SearchEngine(db, neural=False, rerank=False)

    ready = threading.Event()
    holder = []
    orig = server.ThreadingHTTPServer

    class Srv(orig):
        def __init__(self, addr, h):
            super().__init__(addr, h)
            holder.append(self)
            ready.set()

    monkeypatch.setattr(server, 'ThreadingHTTPServer', Srv)
    monkeypatch.setattr(server, 'MovieArtwork', type('A', (), {'enabled': False}))
    t = threading.Thread(target=server.serve, args=(eng, 0), daemon=True)
    t.start()
    assert ready.wait(5)
    base = f'http://127.0.0.1:{holder[0].server_port}'
    try:
        dos = json.load(urlopen(base + '/api/dossier?movie=Test+Film'))
        assert dos['movie_id'] == 'tt100'
        assert 'Cooper' in dos['core_premise']
    finally:
        holder[0].shutdown()
        t.join(timeout=5)
        eng.close()
