import io
import json
from urllib.error import URLError
import pytest
from dialoguematch.artwork import MovieArtwork


@pytest.fixture
def artwork(monkeypatch, tmp_path):
    monkeypatch.delenv('TMDB_READ_ACCESS_TOKEN', raising=False)
    monkeypatch.delenv('TMDB_API_KEY', raising=False)
    return MovieArtwork(settings_path=tmp_path / 'missing.json')


def test_disabled_provider_never_calls_network(artwork, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail('Disabled artwork must not contact TMDB')
    monkeypatch.setattr('dialoguematch.artwork.urlopen', unexpected)
    assert artwork.get('tt0172495')['reason'] == 'not_configured'
    with pytest.raises(ValueError):
        artwork.get('../not-a-movie')


def test_local_settings_and_environment_precedence(tmp_path, monkeypatch):
    monkeypatch.delenv('TMDB_READ_ACCESS_TOKEN', raising=False)
    path = tmp_path / 'artwork.local.json'
    path.write_text(json.dumps({'TMDB_READ_ACCESS_TOKEN': 'local-test-token'}))
    assert MovieArtwork(settings_path=path).token == 'local-test-token'
    monkeypatch.setenv('TMDB_READ_ACCESS_TOKEN', 'environment-test-token')
    assert MovieArtwork(settings_path=path).token == 'environment-test-token'


def test_imdb_lookup_uses_bearer_and_caches_backdrop(artwork, monkeypatch):
    artwork.token = 'test-token'
    calls = []
    def response(request, timeout):
        calls.append(request)
        assert '/find/tt0172495?external_source=imdb_id' in request.full_url
        assert request.get_header('Authorization') == 'Bearer test-token'
        assert timeout == 5
        return io.BytesIO(json.dumps({'movie_results': [{'id': 98, 'backdrop_path': '/gladiator.jpg'}]}).encode())
    monkeypatch.setattr('dialoguematch.artwork.urlopen', response)
    result = artwork.get('tt0172495')
    assert result['url'] == 'https://image.tmdb.org/t/p/w780/gladiator.jpg'
    assert result['source_url'] == 'https://www.themoviedb.org/movie/98'
    assert artwork.get('tt0172495') == result
    assert len(calls) == 1


@pytest.mark.parametrize('movies', [[], [{'id': 1}, {'id': 2}], [{'id': 1, 'poster_path': '//bad.example/image.jpg'}]])
def test_invalid_or_ambiguous_artwork_is_not_used(artwork, monkeypatch, movies):
    artwork.key = 'test-key'
    monkeypatch.setattr('dialoguematch.artwork.urlopen', lambda *a, **k: io.BytesIO(json.dumps({'movie_results': movies}).encode()))
    assert not artwork.get('tt0172495')['available']


def test_outage_is_a_cached_fallback(artwork, monkeypatch):
    artwork.token = 'test-token'
    calls = []
    def unavailable(*args, **kwargs):
        calls.append(1)
        raise URLError('offline')
    monkeypatch.setattr('dialoguematch.artwork.urlopen', unavailable)
    assert artwork.get('tt0172495')['reason'] == 'temporarily_unavailable'
    assert not artwork.get('tt0172495')['available']
    assert len(calls) == 1


def test_poster_is_used_when_backdrop_is_absent(artwork, monkeypatch):
    artwork.key = 'test-key'
    def response(request, timeout):
        assert 'api_key=test-key' in request.full_url
        return io.BytesIO(json.dumps({'movie_results': [{'id': 98, 'backdrop_path': None, 'poster_path': '/poster.jpg'}]}).encode())
    monkeypatch.setattr('dialoguematch.artwork.urlopen', response)
    result = artwork.get('tt0172495')
    assert result['kind'] == 'poster'
    assert result['url'].endswith('/poster.jpg')
