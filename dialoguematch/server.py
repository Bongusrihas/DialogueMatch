from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlparse

from .artwork import MovieArtwork
from .build import ROOT
from .indexes import IndexSelector

_CLIENT_DISCONNECT = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)
_ALLOWED_ASSETS = {
    '/assets/cinema-hero.png',
    '/assets/cinema-hero-v2.png',
    '/assets/cinema-atlas.png',
    *(f'/assets/cinema-theme-{n}.png' for n in range(6)),
}


def serve(engine, port=8765):
    lock = threading.Lock()
    artwork = MovieArtwork()
    indexes = IndexSelector(engine)
    pid_file = ROOT / 'data/server.pid'

    class Handler(BaseHTTPRequestHandler):
        def _write_response(self, status_code: int, body: bytes, content_type: str, cache_control: str = 'no-store'):
            try:
                self.send_response(status_code)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', cache_control)
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                self.wfile.write(body)
            except _CLIENT_DISCONNECT:
                return

        def do_GET(self):
            url = urlparse(self.path)
            try:
                if url.path == '/':
                    body = Path(__file__).with_name('web.html').read_bytes()
                    self._write_response(200, body, 'text/html; charset=utf-8')
                    return

                if url.path in _ALLOWED_ASSETS:
                    body = (Path(__file__).parent / 'assets' / Path(url.path).name).read_bytes()
                    self._write_response(200, body, 'image/png', cache_control='public, max-age=86400')
                    return

                if url.path == '/api/status':
                    value = engine.status()
                    value['artwork_enabled'] = artwork.enabled
                    value['indexes'] = indexes.options()
                    self._write_response(200, json.dumps(value).encode('utf-8'), 'application/json')
                    return

                if url.path == '/api/artwork':
                    args = parse_qs(url.query)
                    value = artwork.get(args.get('movie', [''])[0])
                    self._write_response(200, json.dumps(value).encode('utf-8'), 'application/json', cache_control='private, max-age=3600')
                    return

                if url.path == '/api/catalog':
                    args = parse_qs(url.query)
                    q = args.get('q', [''])[0]
                    try:
                        lim = int(args.get('limit', ['12'])[0])
                    except ValueError:
                        lim = 12
                    value = engine.catalog_search(q, limit=lim) if hasattr(engine, 'catalog_search') else {'results': []}
                    self._write_response(200, json.dumps(value).encode('utf-8'), 'application/json')
                    return

                if url.path == '/api/dossier':
                    args = parse_qs(url.query)
                    spec = args.get('movie', [''])[0]
                    if not spec or not hasattr(engine, 'movie_dossier'):
                        raise ValueError('A valid movie identifier is required.')
                    value = engine.movie_dossier(spec)
                    self._write_response(200, json.dumps(value).encode('utf-8'), 'application/json')
                    return

                if url.path == '/api/scene':
                    args = parse_qs(url.query)
                    sid = args.get('id', [''])[0]
                    if not sid:
                        raise ValueError('A scene ID is required.')
                    try:
                        neighbors = int(args.get('neighbors', ['1'])[0])
                    except ValueError:
                        neighbors = 1
                    if not hasattr(engine, 'scene_context'):
                        raise ValueError('Scene context is unavailable.')
                    value = engine.scene_context(sid, neighbors=neighbors)
                    self._write_response(200, json.dumps(value).encode('utf-8'), 'application/json')
                    return

                if url.path == '/api/search':
                    args = parse_qs(url.query)
                    try:
                        limit = int(args.get('k', ['10'])[0])
                    except ValueError:
                        raise ValueError('Result count must be a whole number from 1 to 30.')
                    if not 1 <= limit <= 30:
                        raise ValueError('Result count must be from 1 to 30.')
                    selected_index = args.get('index', ['current'])[0]
                    with lock:
                        indexes.activate(selected_index)
                        result = engine.search(
                            args.get('q', [''])[0],
                            args.get('mode', ['auto'])[0],
                            limit=limit,
                            movie_id=args.get('movie', [None])[0],
                            retrieval=args.get('retrieval', ['combined'])[0],
                        )
                        result['index'] = selected_index
                        result['requested_k'] = limit
                    self._write_response(200, json.dumps(result).encode('utf-8'), 'application/json')
                    return

                if url.path == '/api/movies':
                    args = parse_qs(url.query)
                    plots = getattr(engine, 'plots', None)
                    result = (
                        plots.search(args.get('q', [''])[0], movie_id=args.get('movie', [None])[0])
                        if plots
                        else {'results': [], 'unavailable': True}
                    )
                    self._write_response(200, json.dumps(result).encode('utf-8'), 'application/json')
                    return

                try:
                    self.send_error(404)
                except _CLIENT_DISCONNECT:
                    pass
            except _CLIENT_DISCONNECT:
                return
            except ValueError as exc:
                body = json.dumps({'error': str(exc)}).encode('utf-8')
                self._write_response(400, body, 'application/json')
            except Exception as exc:
                print(f'Search failed: {type(exc).__name__}: {exc}', flush=True)
                try:
                    self.send_error(500, 'Search failed. See the local server console.')
                except _CLIENT_DISCONNECT:
                    pass

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    if port != 0:
        try:
            pid_file.parent.mkdir(parents=True, exist_ok=True)
            pid_file.write_text(str(os.getpid()), encoding='utf-8')
        except OSError:
            pass
    print(f'DialogueMatch is running at http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if port != 0:
            try:
                if pid_file.exists() and pid_file.read_text(encoding='utf-8').strip() == str(os.getpid()):
                    pid_file.unlink()
            except OSError:
                pass
        server.server_close()
