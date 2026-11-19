"""Frozen, source-derived 150-query diagnostic audit; not an independent benchmark."""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dialoguematch.text import normalize

VISUAL = [
"A masked hero hangs upside down in the rain while a woman rolls his mask partway up and kisses him.",
"During military training, a skinny recruit throws himself onto a grenade while all the bigger soldiers run away.",
"An unusually strong stranger enjoys a drink in a diner and smashes the empty cup on the floor because he wants another.",
"Dozens of empty metal superhero suits arrive at an industrial site and start fighting while their owner jumps between them.",
"A retired television actor takes a flamethrower from his shed and uses it against somebody in his swimming pool.",
"Two armored men battle remotely controlled robots together in a landscaped garden at night.",
"A desperate father holds a young suspect captive in an abandoned building and tortures him because he thinks he knows where his daughter is.",
"Some friends wake up after a party and discover a tiger in their hotel bathroom and a baby hidden in the room.",
"A group of dwarves takes over a nervous homeowner's dining room, singing and throwing plates around while washing up.",
"Two former allies fight at an airport while a teenage hero helps one side and another fighter grows much taller than the planes.",
"An elderly man in a wheelchair suffers a seizure in a hotel casino and everyone nearby becomes frozen and unable to move.",
"An enormous aircraft engine falls through the roof of a teenage boy's bedroom during the night.",
"Two children flee across rooftops and through a crowded slum while a policeman tries to catch them.",
"Two rivals fight for the throne on a cliff beside a huge waterfall while people from several tribes watch.",
"An astronaut spins helplessly away into black space after debris tears through the spacecraft she was working on.",
"A superhero runs across the surface of the ocean by freezing a path under his feet, then slides along a track of ice.",
"A giant green fighter is introduced in an arena, and his opponent is delighted because he recognizes him from work.",
"A young boy extends his hand toward a black dragon and waits until the dragon presses its nose against his palm.",
"A ballerina performs under stage lights while imagining black feathers growing from her skin and wings spreading from her arms.",
"Buildings bend and rotate around two men as they fight through a city whose streets seem to fold in on themselves.",
"A group of codebreakers celebrates when their huge machine finally stops and produces a useful result.",
"A lone man drives through deserted city streets hunting deer from his car while his dog accompanies him.",
"A man chooses to remain in the path of a tornado and signals his son to stay back rather than reveal his powers.",
"An elderly man stands unarmed in front of a gang house, reaches inside his jacket, and is shot in front of witnesses.",
"A tiny tree-like creature dances to music while a team fights a huge tentacled monster in the background.",
"A retired killer discovers that intruders have killed his puppy and stolen the vintage car he refused to sell.",
"Sailors duel on a giant wooden waterwheel that breaks free and rolls down a hill with the fighters still on it.",
"A heavily bandaged man keeps fighting his way through a violent city while remembering a murdered woman he spent one night with.",
"A college student sits alone at a computer repeatedly refreshing a page after sending his former girlfriend a friend request.",
"Three military aircraft fly over the sea with very little fuel left while soldiers wait for rescue on the beach."
]


def prepare():
    seeds = json.loads((ROOT/'research/fresh150_seeds.json').read_text(encoding='utf-8'))
    descriptions = json.loads((ROOT/'research/fresh150_descriptions.json').read_text(encoding='utf-8'))
    assert len(seeds) == len(descriptions) == 40
    cases = []
    introductions = [
        "I remember the events much better than the actors' names. I might have seen this on television, but I am not confident about when. Here is what I can still picture: ",
        "I am trying to track down a film from a conversation I remember. Some small details could be wrong, and I cannot give you the year or the name of the lead actor. The part I remember goes like this: ",
        "This has been stuck in my head and my previous searches have not helped. I remember the situation and the people arguing much better than the exact wording. Could you locate the scene from this description? ",
        "I cannot place the title, and I would rather not guess an actor or a year because I may be mixing those up with another film. The sequence that I remember most clearly is this one: "
    ]
    for i, (seed, description) in enumerate(zip(seeds, descriptions)):
        lines = json.loads(seed['lines'])
        selected = []
        for line in lines:
            selected.append(line)
            if len(' '.join(l['text'] for l in selected)) >= 650:
                break
        quote = ' '.join(l['text'] for l in selected)
        base = {'movie_id':seed['movie_id'], 'title':seed['title'], 'scene_id':seed['id'],
                'start':selected[0]['start'],'end':selected[-1]['end'], 'label_basis':'local original subtitle lines; not video verified'}
        cases.append({**base, 'query':quote, 'mode':'quote', 'category':'direct_dialogue'})
        # One character transposition in two longer words, including one late
        # in the excerpt. The source label is held fixed, not inferred by search.
        words = quote.split()
        positions = [n for n,w in enumerate(words) if re.fullmatch('[A-Za-z]{7,}', w)]
        for pos in list(dict.fromkeys(positions[:1]+positions[-1:])):
            word=words[pos];words[pos]=word[:2]+word[3]+word[2]+word[4:]
        noisy=' '.join(words)
        if normalize(noisy)==normalize(quote):
            noisy=quote.replace(' ', ' um ', 1)
        cases.append({**base,'query':noisy,'mode':'quote','category':'imperfect_dialogue'})
        cases.append({**base,'start':seed['start'],'end':seed['end'],
                      'query':description if i%2==0 else introductions[i%4]+description,
                      'mode':'auto','category':'natural_description' if i%2==0 else 'long_natural_description',
                      'label_basis':'manual paraphrase from local subtitle text and existing generated summary; summary may be inaccurate'})
    for seed, query in zip(seeds,VISUAL):
        cases.append({'query':query,'movie_id':seed['movie_id'],'title':seed['title'],'mode':'scene','category':'visual_memory',
                      'label_basis':'manually authored movie memory; no independently verified scene span; excluded from scene metrics'})
    assert len(cases)==150
    previous=set()
    for path in [ROOT/'preprocessing/evaluation_set.csv', ROOT/'research/long_query_cases.json', ROOT/'research/quote_pilot.json']:
        if path.suffix=='.json':previous.update(normalize(r['query']) for r in json.loads(path.read_text(encoding='utf-8')))
        else:
            import csv
            previous.update(normalize(r['query']) for r in csv.DictReader(path.open(encoding='utf-8-sig')))
    assert len({normalize(c['query']) for c in cases})==150
    assert not previous.intersection(normalize(c['query']) for c in cases)
    for i,c in enumerate(cases,1): c['id']=f'fresh-{i:03}'
    path=ROOT/'research/fresh150_queries.json'
    if path.exists():raise ValueError('Frozen query set already exists; do not overwrite it.')
    path.write_text(json.dumps(cases,indent=2,ensure_ascii=False),encoding='utf-8')
    print('Frozen 150 distinct new queries across 40 movies; 120 span-labeled variants and 30 movie-only visual memories.',flush=True)


def run(query_file='research/fresh150_queries.json', result_file='research/fresh150_results.json'):
    from dialoguematch.engine import SearchEngine
    path=ROOT/query_file
    cases=json.loads(path.read_text(encoding='utf-8'))
    fingerprint=hashlib.sha256(path.read_bytes()).hexdigest()
    output=ROOT/result_file
    report=json.loads(output.read_text()) if output.exists() else {'query_sha256':fingerprint,'rows':[]}
    assert report['query_sha256']==fingerprint
    current_code={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'dialoguematch').glob('*.py')}
    if report['rows']:
        for name in ['engine.py','neural.py','text.py','plots.py']:
            if report.get('code_sha256',{}).get(name)!=current_code[name]:
                raise ValueError('Search code changed since this checkpoint. Choose a new --output path for the comparison.')
    completed={r['id'] for r in report['rows']}
    engine=SearchEngine(ROOT/'data/dialoguematch.sqlite')
    report['status']=engine.status()
    report['code_sha256']=current_code
    try:
        for i,case in enumerate(cases,1):
            if case['id'] in completed:continue
            started=time.perf_counter()
            record={'id':case['id']}
            try:
                response=engine.search(case['query'],case['mode'],debug=True)
                hits=response['results']
                record['movie_rank']=next((n for n,r in enumerate(hits,1) if r['movie_id']==case['movie_id']),None)
                record['scene_rank']=next((n for n,r in enumerate(hits,1) if r['movie_id']==case['movie_id'] and r['start']<case.get('end',-1) and r['end']>case.get('start',1e9)),None)
                record['candidate_hit']=case.get('scene_id') in response['candidate_ids'] if case.get('scene_id') else None
                record['reranked_hit']=case.get('scene_id') in response.get('reranked_ids',[]) if case.get('scene_id') else None
                record['channels']={k: v.index(case['scene_id'])+1 if case.get('scene_id') in v else None for k,v in response['channels'].items()}
                record['top10']=[{k:r.get(k) for k in ['scene_id','movie_id','title','start','end','match']} for r in hits]
                record['expected_score']=response.get('reranker_scores',{}).get(case.get('scene_id'))
                record['elapsed_ms']=response['elapsed_ms']
                record['diagnosis']=('hit' if record['scene_rank'] else 'movie_only_unverified' if not case.get('scene_id') and record['movie_rank'] else 'visual_or_movie_miss' if not case.get('scene_id') else 'candidate_miss' if not record['candidate_hit'] else 'not_reranked_or_quote_rejected' if not record['reranked_hit'] else 'reranking_miss')
            except Exception as exc:
                record.update(error=f'{type(exc).__name__}: {exc}',diagnosis='error',elapsed_ms=round((time.perf_counter()-started)*1000))
            report['rows'].append(record)
            output.write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(f'{i}/{len(cases)} {case["category"]} {case["title"]}: movie={record.get("movie_rank")} scene={record.get("scene_rank")} {record["diagnosis"]} {record["elapsed_ms"]}ms',flush=True)
    finally:engine.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--queries', default='research/fresh150_queries.json')
    parser.add_argument('--output', default='research/fresh150_results.json')
    args=parser.parse_args()
    if args.prepare:prepare()
    run(args.queries, args.output)
