"""Run illustrative end-to-end probes, not a held-out accuracy benchmark."""
import json
import sys
from urllib.parse import urlencode
from urllib.request import urlopen
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dialoguematch.engine import SearchEngine

CASES = [
    ('Messages span 23 years', 'quote', 'tt0816692', 'tt0816692_77'),
    ('I am going to make this pencil disappear', 'quote', 'tt0468569', 'tt0468569_23'),
    ('The idea is like a virus', 'quote', 'tt1375666', 'tt1375666_78'),
    ('Are you not entertained', 'quote', 'tt0172495', None),
    ('Mesages span 23 years', 'quote', 'tt0816692', 'tt0816692_77'),
    ('You shall not pass', 'quote', 'tt0120737', None),
    ('What is the most resilient parasite', 'quote', 'tt1375666', None),
    ('a man cries after watching 23 years of missing videos', 'scene', 'tt0816692', 'tt0816692_77'),
    ('crying while watching decades of video messages from kids', 'scene', 'tt0816692', 'tt0816692_77'),
    ('magic trick making a pencil disappear', 'scene', 'tt0468569', 'tt0468569_23'),
    ('joker pencil trick in the mob meeting', 'scene', 'tt0468569', 'tt0468569_23'),
    ('hallway fight with zero gravity', 'scene', 'tt1375666', None),
    ('spinning top ending does it fall', 'scene', 'tt1375666', None),
    ('giant mountain that is actually a massive water wave', 'scene', 'tt0816692', None),
    ('joker walking away from hospital explosion in a nurse outfit', 'scene', 'tt0468569', None),
]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    lexical = '--lexical-only' in sys.argv
    http = '--http' in sys.argv
    engine = None if http else SearchEngine(ROOT / 'data/dialoguematch.sqlite', neural=not lexical, rerank=not lexical)
    if http:
        with urlopen('http://127.0.0.1:8765/api/status', timeout=30) as response:
            status = json.load(response)
    else:
        status = engine.status()
    output = {'note': 'Illustrative cases selected during implementation. Movie matches are not scene-level verification. No visual evidence was added.',
              'semantic': status['semantic'], 'reranker': status['reranker'], 'cases': []}
    for query, mode, movie, scene in CASES:
        if http:
            with urlopen('http://127.0.0.1:8765/api/search?' + urlencode({'q': query, 'mode': mode}), timeout=180) as handle:
                response = json.load(handle)
        else:
            response = engine.search(query, mode, limit=10, debug=True)
        hits = response['results']
        record = {'query': query, 'mode': mode, 'expected_movie': movie, 'expected_scene': scene,
                  'movie_rank10': next((i for i, r in enumerate(hits, 1) if r['movie_id'] == movie), None),
                  'scene_rank10': next((i for i, r in enumerate(hits, 1) if r['scene_id'] == scene), None) if scene else None,
                  'status': response['status'], 'elapsed_ms': response['elapsed_ms'],
                  'top3': [{k: r[k] for k in ['scene_id', 'title', 'start', 'end', 'match', 'timestamp_precision']} for r in hits[:3]]}
        output['cases'].append(record)
        print(json.dumps(record), flush=True)
        suffix = 'lexical' if lexical else 'hybrid'
        (ROOT / f'research/fixed_pipeline_{suffix}_results.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    if engine:
        engine.close()


if __name__ == '__main__':
    main()
