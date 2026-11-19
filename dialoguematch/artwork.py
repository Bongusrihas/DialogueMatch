"""Optional TMDB artwork, resolved by IMDb ID rather than ambiguous film titles."""
import json
import os
from pathlib import Path
import re
import threading
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class MovieArtwork:
    def __init__(self, settings_path=None):
        settings_path = Path(settings_path) if settings_path is not None else Path(__file__).resolve().parent.parent / 'data' / 'artwork.local.json'
        try:
            settings = json.loads(settings_path.read_text(encoding='utf-8-sig'))
            if not isinstance(settings, dict):
                settings = {}
        except (OSError, ValueError):
            settings = {}
        self.token = (os.getenv('TMDB_READ_ACCESS_TOKEN') or settings.get('TMDB_READ_ACCESS_TOKEN', '')).strip()
        self.key = (os.getenv('TMDB_API_KEY') or settings.get('TMDB_API_KEY', '')).strip()
        self.cache = {}
        self.lock = threading.Lock()

    @property
    def enabled(self):
        return bool(self.token or self.key)

    def get(self, movie_id):
        if not re.fullmatch(r'tt\d{7,10}', movie_id):
            raise ValueError('A valid IMDb movie ID is required.')
        if not self.enabled:
            return {'available': False, 'reason': 'not_configured'}
        with self.lock:
            cached = self.cache.get(movie_id)
            if cached and cached[0] > time.monotonic():
                return cached[1]
        query = {'external_source': 'imdb_id'}
        headers = {'Accept': 'application/json', 'User-Agent': 'DialogueMatch/1.0'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        else:
            query['api_key'] = self.key
        request = Request('https://api.themoviedb.org/3/find/' + movie_id + '?' + urlencode(query), headers=headers)
        value = {'available': False, 'reason': 'no_artwork'}
        ttl = 3600
        try:
            with urlopen(request, timeout=5) as response:
                data = json.load(response)
            movies = data.get('movie_results', [])
            # Multiple matches are ambiguous: never substitute a different film.
            if len(movies) == 1:
                movie = movies[0]
                path = movie.get('backdrop_path') or movie.get('poster_path')
                if isinstance(path, str) and re.fullmatch(r'/[A-Za-z0-9_.-]+', path):
                    value = {'available': True, 'url': 'https://image.tmdb.org/t/p/w780' + path,
                             'source_url': 'https://www.themoviedb.org/movie/' + str(int(movie['id'])),
                             'kind': 'backdrop' if movie.get('backdrop_path') else 'poster'}
        except (URLError, TimeoutError, OSError, ValueError, TypeError, KeyError):
            value = {'available': False, 'reason': 'temporarily_unavailable'}
            ttl = 60
        with self.lock:
            if len(self.cache) >= 512:
                self.cache.pop(next(iter(self.cache)))
            self.cache[movie_id] = (time.monotonic() + ttl, value)
        return value
