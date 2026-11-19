import sqlite3

import pytest

from dialoguematch.plots import PlotSearch


def test_plot_results_are_movie_only_and_filterable(tmp_path):
    path = tmp_path / 'plots.sqlite'
    con = sqlite3.connect(path)
    con.execute("CREATE VIRTUAL TABLE plots USING fts5(movie_id UNINDEXED, wiki_id UNINDEXED, content, tokenize='porter unicode61')")
    con.executemany('INSERT INTO plots VALUES (?,?,?)', [
        ('tt1', '101', 'A masked villain blows up a hospital.'),
        ('tt1', '101', 'The villain escapes in a nurse uniform.'),
        ('tt2', '102', 'A nurse works in a hospital.'),
        ('tt_deleted', '103', 'A nurse works in a hospital.'),
    ])
    con.commit()
    con.close()
    index = PlotSearch(path, {'tt1': 'First', 'tt2': 'Second'})
    try:
        hits = index.search('hospital nurse')['results']
        assert len({h['movie_id'] for h in hits}) == len(hits)
        assert {h['movie_id'] for h in hits} == {'tt1', 'tt2'}
        assert all('start' not in h and h['source_url'].startswith('https://en.wikipedia.org/?curid=') for h in hits)
        assert [h['movie_id'] for h in index.search('hospital nurse', movie_id='tt2')['results']] == ['tt2']
        with pytest.raises(ValueError):
            index.search('!')
    finally:
        index.close()
