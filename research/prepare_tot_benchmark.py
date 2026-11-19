"""Prepare a small real-user movie benchmark using verified Wikidata IMDb IDs.

Source: https://github.com/microsoft/Tip-of-the-Tongue-Known-Item-Retrieval-Dataset-for-Movie-Identification
The downloaded source and output stay in data/. The original requests and their
answer links are not independently verified ground truth.
"""
import csv
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get(url, params):
    request = urllib.request.Request(url + '?' + urllib.parse.urlencode(params), headers={'User-Agent': 'DialogueMatchResearch/1.0 (local benchmark)'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def main():
    con = sqlite3.connect(ROOT / 'data/dialoguematch.sqlite')
    available = {r[0] for r in con.execute('SELECT id FROM movies')}
    con.close()
    queries = {}
    with (ROOT / 'data/tot_source.txt').open(encoding='utf-8') as handle:
        for row in csv.DictReader(handle, delimiter='\t'):
            query = row['QuestionBody'].strip()
            if not query or len(query) > 500:
                continue
            entry = queries.setdefault(query, {'imdb': set(), 'wiki': set()})
            entry['imdb'].update(re.findall(r'tt\d{5,}', row['imdbURL']))
            url = row['wikipediaURL']
            if 'en.wikipedia.org/wiki/' in url:
                entry['wiki'].add(urllib.parse.unquote(url.split('/wiki/', 1)[1]).replace('_', ' '))
    titles = sorted({title for row in queries.values() for title in row['wiki']})
    title_to_entity = {}
    for offset in range(0, len(titles), 40):
        batch = titles[offset:offset + 40]
        result = get('https://en.wikipedia.org/w/api.php', {'action': 'query', 'format': 'json', 'prop': 'pageprops',
                     'ppprop': 'wikibase_item', 'redirects': 1, 'titles': '|'.join(batch)})['query']
        redirect = {x['from']: x['to'] for x in result.get('normalized', []) + result.get('redirects', [])}
        page_ids = {p['title']: p.get('pageprops', {}).get('wikibase_item') for p in result['pages'].values()}
        for title in batch:
            current, visited = title, set()
            while current in redirect and current not in visited:
                visited.add(current)
                current = redirect[current]
            title_to_entity[title] = page_ids.get(current)
    entities = sorted({value for value in title_to_entity.values() if value})
    entity_to_imdb = {}
    for offset in range(0, len(entities), 40):
        result = get('https://www.wikidata.org/w/api.php', {'action': 'wbgetentities', 'format': 'json', 'props': 'claims',
                     'ids': '|'.join(entities[offset:offset + 40])})
        for entity, data in result['entities'].items():
            entity_to_imdb[entity] = {claim['mainsnak']['datavalue']['value'] for claim in data.get('claims', {}).get('P345', [])
                                      if 'datavalue' in claim.get('mainsnak', {})}
    benchmark = []
    for query, source in queries.items():
        ids = set(source['imdb'])
        for title in source['wiki']:
            ids.update(entity_to_imdb.get(title_to_entity.get(title), set()))
        if len(ids) == 1 and next(iter(ids)) in available:
            benchmark.append({'query': query, 'movie_id': next(iter(ids)), 'mode': 'auto', 'category': 'real_user_movie_request'})
    output = ROOT / 'data/tot_benchmark.json'
    output.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'unique_short_requests': len(queries), 'matched_in_catalog': len(benchmark), 'output': str(output)}))


if __name__ == '__main__':
    main()
