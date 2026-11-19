import json
from pathlib import Path
import pytest
from dialoguematch.build import build
from dialoguematch.engine import SearchEngine, rrf, best_fuzzy
from dialoguematch.evaluate import evaluate
from dialoguematch.text import normalize
from dialoguematch.chunker import RawSubtitle, hybrid_chunk, parse_srt


@pytest.fixture
def corpus(tmp_path):
    subs = tmp_path / 'subtitles'
    subs.mkdir()
    (subs / 'tt001.srt').write_text('''1
00:00:10,000 --> 00:00:12,000
We have waited many years.

2
00:00:13,000 --> 00:00:15,000
Messages span 23 years.

3
00:00:16,000 --> 00:00:19,000
Play from the beginning.

4
00:00:20,000 --> 00:00:23,000
Hey Dad, I finished school.
''', encoding='utf-8')
    (subs / 'tt003.srt').write_text('''1
00:00:30,000 --> 00:00:33,000
Are you not entertained?
''', encoding='utf-8')
    source = tmp_path / 'chunks.json'
    source.write_text(json.dumps([
        {'_id': 'tt001_0', 'movie_id': 'tt001', 'start_time': 10, 'end_time': 15, 'text': 'We have waited many years. Messages span 23 years.', 'summary': 'A father learns about stored messages.'},
        {'_id': 'tt001_1', 'movie_id': 'tt001', 'start_time': 16, 'end_time': 23, 'text': 'Play from the beginning. Hey Dad, I finished school.', 'summary': 'Family updates play.'},
        {'_id': 'tt002_0', 'movie_id': 'tt002', 'start_time': 10, 'end_time': 20, 'text': 'The bank robbers take cash.', 'summary': 'A bank robbery.'},
    ]), encoding='utf-8')
    metadata = tmp_path / 'movies.csv'
    metadata.write_text('imdb_id,title\ntt001,Space Movie\ntt002,Bank Movie\ntt003,Arena Movie\n', encoding='utf-8')
    db = tmp_path / 'test.sqlite'
    build(db, source, subs, metadata)
    engine = SearchEngine(db, neural=False, rerank=False)
    yield engine
    engine.close()


def test_exact_quote_has_line_timestamps(corpus):
    results = corpus.search('MESSAGES span 23 years!', mode='quote')['results']
    assert len(results) == 1
    result = results[0]
    assert result['scene_id'] == 'tt001_0'
    assert (result['start'], result['end']) == (13, 15)
    assert result['timestamp_precision'] == 'subtitle_lines'


def test_index_only_preserves_selected_index_order_and_skips_other_channels(corpus):
    class FakeIndex:
        def search(self, query, limit, allowed):
            assert allowed is None
            return ['tt002_0', 'tt001_0', 'tt001_1']
    class NoRerank:
        def rank(self, query, rows):
            raise AssertionError('Index-only search must not rerank')
    corpus.semantic, corpus.reranker = FakeIndex(), NoRerank()
    response = corpus.search('Messages span 23 years!', mode='quote', limit=2, retrieval='index', debug=True)
    assert [r['scene_id'] for r in response['results']] == ['tt002_0', 'tt001_0']
    assert response['channels']['semantic'] == ['tt002_0', 'tt001_0', 'tt001_1']
    assert response['reranker_enabled'] is False
    with pytest.raises(ValueError):
        corpus.search('test', retrieval='invalid')


def test_quote_across_chunk_boundary(corpus):
    result = corpus.search('23 years play from the beginning', mode='quote')['results'][0]
    assert result['movie_id'] == 'tt001'
    assert (result['start'], result['end']) == (13, 19)


def test_literal_quote_inside_human_question(corpus):
    result = corpus.search('I forgot the film. Someone says "Messages span 23 years". What was it?')['results'][0]
    assert result['scene_id'] == 'tt001_0'
    assert (result['start'], result['end']) == (13, 15)


def test_long_quote_spans_more_than_a_boundary_window(tmp_path):
    subs = tmp_path / 'subs'
    subs.mkdir()
    records, entries = [], []
    for i in range(5):
        text = ' '.join(f'signal{i}word{j}' for j in range(16)) + '.'
        start, end = 10+i*10, 18+i*10
        records.append({'_id': f'ttlong_{i}', 'movie_id': 'ttlong', 'start_time': start, 'end_time': end, 'text': text})
        entries.append(f'{i+1}\n00:00:{start:02d},000 --> 00:00:{end:02d},000\n{text}\n')
    (subs/'ttlong.srt').write_text('\n'.join(entries))
    source = tmp_path/'source.json'
    source.write_text(json.dumps(records))
    metadata = tmp_path/'movies.csv'
    metadata.write_text('imdb_id,title\nttlong,Long movie\n')
    db = tmp_path/'long.sqlite'
    build(db, source, subs, metadata)
    engine = SearchEngine(db, neural=False, rerank=False)
    try:
        quote = ' '.join(r['text'] for r in records)
        assert len(quote) > 500
        result = engine.search(quote, mode='quote')['results'][0]
        assert (result['start'], result['end']) == (10, 58)
        assert result['timestamp_precision'] == 'subtitle_lines'
    finally:
        engine.close()


def test_original_subtitle_recovers_missing_movie(corpus):
    result = corpus.search('are you not entertained', mode='quote')['results'][0]
    assert result['movie_id'] == 'tt003'
    assert 'tt003' in corpus.manifest['stats']['recovered_movies']


def test_no_quote_does_not_fabricate_answer(corpus):
    assert corpus.search('we ride silver unicorns through a waterfall', mode='quote')['results'] == []
    assert corpus.search('anything', movie_id='tt_missing')['status'] == 'movie_unavailable'


def test_movie_filter_applies_to_all_channels(corpus):
    results = corpus.search('messages bank robbers', mode='scene', movie_id='tt002')['results']
    assert results and all(r['movie_id'] == 'tt002' for r in results)


def test_keyword_can_add_candidate_missing_from_dense(corpus):
    class FakeSemantic:
        def search(self, query, limit, allowed):
            return ['tt002_0']
    corpus.semantic = FakeSemantic()
    result = corpus.search('father stored messages', mode='scene', debug=True)
    assert 'tt001_0' in result['candidate_ids']
    assert 'tt001_0' in result['channels']['keyword']
    assert 'tt001_0' not in result['channels']['semantic']


def test_keyword_leader_reaches_reranker_despite_other_channels(corpus, monkeypatch):
    # Simulate rank fusion burying the best independent keyword result below 80.
    import dialoguematch.engine as module
    monkeypatch.setattr(module, 'rrf', lambda rankings, constant=60: {**{f'missing_{i}': 2 for i in range(81)}, 'tt001_0': 1})
    class Ranker:
        def rank(self, query, records):
            assert 'tt001_0' in [r['id'] for r in records]
            return {r['id']: 1 if r['id'] == 'tt001_0' else 0 for r in records}
    corpus.reranker = Ranker()
    assert corpus.search('father stored messages', mode='scene')['results'][0]['scene_id'] == 'tt001_0'


def test_plot_candidates_join_scene_reranking(corpus, monkeypatch):
    class Plots:
        def search(self, query, limit, movie_id):
            return {'results': [{'movie_id': 'tt002', 'excerpt': 'A bank robbery.', 'source_url': 'https://en.wikipedia.org/?curid=1'}]}
        def close(self):
            pass
    class Ranker:
        def rank(self, query, records):
            ids = [r['id'] for r in records]
            assert 'tt001_0' in ids and 'tt002_0' in ids
            assert len(ids) == len(set(ids))
            # Only actual scene text is passed to the scene reranker.
            assert next(r for r in records if r['id'] == 'tt002_0')['text'] == 'The bank robbers take cash.'
            return {sid: (10 if sid == 'tt002_0' else 0) for sid in ids}
    original = corpus._lexical
    monkeypatch.setattr(corpus, '_lexical', lambda expr, limit, movie_id=None: ['tt002_0'] if movie_id == 'tt002' else original(expr, limit, movie_id))
    corpus.plots, corpus.reranker = Plots(), Ranker()
    response = corpus.search('father stored messages', mode='scene', debug=True)
    assert response['channels']['plot_guided'] == ['tt002_0']
    assert response['results'][0]['scene_id'] == 'tt002_0'
    assert response['results'][0]['plot_excerpt'] == 'A bank robbery.'
    assert response['results'][0]['start'] == 10


def test_quote_search_keeps_plot_search_out(corpus):
    class Plots:
        def search(self, *args, **kwargs):
            raise AssertionError('Quotes should not depend on plot matches')
        def close(self):
            pass
    corpus.plots = Plots()
    assert corpus.search('Messages span 23 years', mode='quote')['results'][0]['scene_id'] == 'tt001_0'


def test_rrf_deduplicates_within_channel():
    assert rrf([['a', 'a'], ['b']]) == rrf([['a'], ['b']])


def test_parser_preserves_numeric_dialogue(tmp_path):
    file = tmp_path / 'numeric.srt'
    file.write_text('1\n00:00:01,000 --> 00:00:02,000\n23\n\n2\n00:00:03,000 --> 00:00:04,000\nYears.\n', encoding='utf-8')
    lines = parse_srt(file)
    assert [s.raw_text for s in lines] == ['23', 'Years.']


def test_chunker_preserves_short_quotes_and_raw_cues():
    chunks = hybrid_chunk([RawSubtitle(1, 1, 3, 'COOPER: [crying] Stay.')], 'tt001')
    assert len(chunks) == 1
    assert chunks[0].text == 'Stay.'
    assert '[crying]' in chunks[0].to_dict()['raw_text']
    assert chunks[0].to_dict()['subtitle_lines'][0]['start'] == 1


def test_chunker_never_merges_across_large_gap():
    chunks = hybrid_chunk([RawSubtitle(1, 0, 30, 'We need to leave this place immediately.'), RawSubtitle(2, 200, 205, 'Please come back and help us.')], 'tt001')
    assert [(c.start_time, c.end_time) for c in chunks] == [(0, 30), (200, 205)]
    assert chunks[1].to_dict()['overlap_text']


def test_chunker_word_budget_includes_next_line():
    chunks = hybrid_chunk([RawSubtitle(1, 0, 25, 'one two three four'), RawSubtitle(2, 26, 50, 'five six seven eight')], 'tt001', word_hard_limit=6)
    assert all(c.word_count <= 6 for c in chunks)
    assert len(chunks) == 2


def test_normalizes_contractions_and_smart_quotes():
    assert normalize('I’m sure you can’t.') == 'i am sure you cannot'


def test_evaluation_does_not_count_movie_as_scene_success(corpus, tmp_path):
    query_file = tmp_path / 'queries.json'
    query_file.write_text(json.dumps([{'query': 'Messages span 23 years', 'movie_id': 'tt001', 'scene_id': 'tt001_1', 'mode': 'quote'}]))
    report = evaluate(corpus, query_file, tmp_path / 'report.json')
    assert report['movie_hit5_on_available'] == 1
    assert report['scene_hit5'] == 0


def test_evaluation_checks_time_span_and_movie(corpus, tmp_path):
    path = tmp_path / 'queries.json'
    path.write_text(json.dumps([
        {'query': 'Messages span 23 years', 'movie_id': 'tt001', 'spans': [[50, 55], [13, 16]], 'mode': 'quote'},
        {'query': 'Are you not entertained', 'movie_id': 'tt003', 'start': 50, 'end': 55, 'mode': 'quote'},
    ]))
    report = evaluate(corpus, path, tmp_path / 'report.json')
    assert report['movie_hit5_on_available'] == 1
    assert report['span_labeled_rows'] == 2
    assert report['span_hit5'] == 0.5


def test_conflicting_labels_are_reported(corpus, tmp_path):
    path = tmp_path / 'queries.json'
    path.write_text(json.dumps([{'query': 'goodbye', 'movie_id': 'tt001'}, {'query': 'goodbye', 'movie_id': 'tt002'}]))
    report = evaluate(corpus, path, tmp_path / 'report.json')
    assert report['conflicting_rows'] == 2 and report['evaluated'] == 0


def test_fuzzy_quote_retains_typos(corpus):
    result = corpus.search('Mesages span 23 years', mode='quote')['results'][0]
    assert result['scene_id'] == 'tt001_0'
    assert result['match'] == 'approximate_quote'


def test_quote_typo_can_retrieve_without_original_token(corpus):
    response = corpus.search('bnak robberz', mode='quote', debug=True)
    assert 'tt002_0' in response['channels']['spelling']
    assert response['results'][0]['scene_id'] == 'tt002_0'


def test_fuzzy_cutoff_preserves_qualifying_scores(monkeypatch):
    import difflib
    import dialoguematch.engine as module
    examples = [('mesages span 23 years', 'Earlier words. Messages span 23 years. Play from the beginning.'),
                ('we ride silver unicorns', 'A completely unrelated and ordinary conversation.'),
                ('i am your father', 'No. I am your father. Search your feelings.')]
    accelerated = module._upper_ratio
    for query, text in examples:
        words = normalize(text).split()
        q = normalize(query).split()
        expected = max(difflib.SequenceMatcher(None, ' '.join(q), ' '.join(words[i:i + width])).ratio()
                       for width in {max(1, len(q) - 1), len(q), len(q) + 1}
                       for i in range(len(words)))
        for implementation in [accelerated, None]:
            monkeypatch.setattr(module, '_upper_ratio', implementation)
            actual = best_fuzzy(query, text, minimum=0.83)
            if expected >= 0.83:
                assert actual == pytest.approx(expected)
            else:
                assert actual < 0.83


def test_invalid_input(corpus):
    with pytest.raises(ValueError):
        corpus.search('" * --')
    with pytest.raises(ValueError):
        corpus.search('a' * 4001)


def test_search_content_preserves_uncertain_scene_clues():
    from dialoguematch.text import search_content
    assert search_content('I cannot remember the title. A drummer dodges a chair.') == 'A drummer dodges a chair.'
    assert search_content('I think it was 2008. I remember a red car.') == 'I think it was 2008. I remember a red car.'
    assert search_content('I cannot remember the title.') == 'I cannot remember the title.'
