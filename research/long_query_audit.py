"""Source-derived development probes; not an independent accuracy benchmark."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dialoguematch.engine import SearchEngine


def prepare():
    con = sqlite3.connect(ROOT / 'data/dialoguematch.sqlite')
    con.row_factory = sqlite3.Row
    cases = []
    for sid in ['tt0816692_77', 'tt0468569_23', 'tt2582802_13', 'tt0172495_9', 'tt0371746_36', 'tt4154796_108']:
        row = con.execute('SELECT * FROM scenes WHERE id=?', (sid,)).fetchone()
        lines = {}
        for r in con.execute('SELECT lines FROM scenes WHERE movie_id=? AND start>=? ORDER BY start LIMIT 5', (row['movie_id'], row['start'])):
            for line in json.loads(r['lines']):
                lines[(line['start'], line['end'], line['text'])] = line
        selected, size = [], 0
        for line in sorted(lines.values(), key=lambda l: l['start']):
            selected.append(line)
            size += len(line['text'])
            if size >= 1100:
                break
        assert selected
        cases.append({'query': ' '.join(l['text'] for l in selected), 'movie_id': row['movie_id'], 'scene_id': sid,
                      'start': selected[0]['start'], 'end': selected[-1]['end'], 'mode': 'quote', 'category': 'long_direct_dialogue'})
    memories = [
        ('tt0816692_77', 'I cannot remember the title. A dad has been away for ages, and when he finally sits down to watch recorded messages from his children, they have grown up and had families without him. He breaks down as he realizes how much of their lives he has missed.'),
        ('tt0468569_23', 'I remember a criminal interrupting a meeting of gangsters. He promises to show them a magic trick involving a pencil, and the trick is much more violent than anybody expects. Which movie and scene was that?'),
        ('tt2582802_13', 'There is a young drummer in a rehearsal room and an incredibly angry music teacher. The teacher throws a chair at him, then makes him count the beat and keeps demanding whether he was playing too fast or too slowly.'),
        ('tt0371746_36', 'At a press conference a wealthy man is supposed to read prepared cards and deny being a superhero. He starts joking, goes off the script, and finally admits that he is the man inside the metal suit.'),
        ('tt0172495_9', 'Before a battle, a general talks to his soldiers about harvesting crops and green fields. He tells them not to be afraid if they find themselves in paradise because that would mean they are already dead.'),
        ('tt4154796_108', 'The hero with a shield is facing an overwhelming army on his own. Then he hears his friend on the radio telling him to look to his left. Reinforcements arrive and he gives the team the order to assemble.'),
    ]
    for sid, query in memories:
        row = con.execute('SELECT * FROM scenes WHERE id=?', (sid,)).fetchone()
        cases.append({'query': query, 'movie_id': row['movie_id'], 'scene_id': sid, 'start': row['start'], 'end': row['end'], 'mode': 'auto', 'category': 'humanized'})
    for sid, quote in [('tt0816692_77','Messages span 23 years. Play from the beginning.'), ('tt0468569_23','I am going to make this pencil disappear'), ('tt2582802_13','Were you rushing or dragging'), ('tt0371746_36','The truth is I am Iron Man')]:
        row = con.execute('SELECT * FROM scenes WHERE id=?', (sid,)).fetchone()
        cases.append({'query': f'I watched this years ago and cannot remember its name. Someone says "{quote}". Can you find the moment and tell me the movie?', 'movie_id': row['movie_id'], 'scene_id': sid, 'start': row['start'], 'end': row['end'], 'mode': 'auto', 'category': 'embedded_quote'})
    for mid, query in [('tt1375666','A man in a suit is fighting people in a hotel corridor, but the floor turns into the wall and the fighters start floating. I remember gravity changing as another vehicle rolls over. I cannot remember any dialogue.'), ('tt0468569','I remember a villain in a nurse costume walking out of a hospital, fiddling with a detonator as the building explodes behind him. I want that exact scene, not another conversation about hospitals.'), ('tt0120737','An old wizard stands on a narrow bridge facing a huge fiery monster and tells it that it shall not pass.'), ('tt0133093','A man in a black coat leans backwards in slow motion while bullets pass over him on a rooftop.')]:
        cases.append({'query': query, 'movie_id': mid, 'mode': 'scene', 'category': 'visual_or_source_limit'})
    prefix = ('I have been trying to remember this movie for a while and I only remember one part clearly. '
              'I watched it at home a long time ago, so I am unsure about the release year, the actors, and whether I saw the whole thing. '
              'I do not remember the title or who directed it. The images are much clearer in my head than the names of the people. '
              'I searched a few times without finding it, and I would appreciate a match based on the events I describe. '
              'I cannot give an exact line of dialogue, but here is the specific part that has stayed with me. ')
    for item in [c for c in cases if c['category'] == 'humanized']:
        cases.append({**item, 'query': prefix + item['query'], 'category': 'long_humanized'})
    con.close()
    (ROOT / 'research/long_query_cases.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')


def run(output, indices=None):
    cases = json.loads((ROOT / 'research/long_query_cases.json').read_text(encoding='utf-8'))
    engine = SearchEngine(ROOT / 'data/dialoguematch.sqlite')
    rows = []
    try:
        for i, case in enumerate(cases):
            if indices and i+1 not in indices:
                continue
            record = {**case, 'characters': len(case['query'])}
            present = engine.con.execute('SELECT 1 FROM movies WHERE id=?', (case['movie_id'],)).fetchone()
            try:
                result = engine.search(case['query'], case['mode'], debug=True)
                hits = result['results']
                record['movie_rank'] = next((n for n,r in enumerate(hits,1) if r['movie_id']==case['movie_id']), None)
                record['scene_rank'] = next((n for n,r in enumerate(hits,1) if r['movie_id']==case['movie_id'] and r['start'] < case.get('end',-1) and r['end'] > case.get('start',1e9)), None)
                record['full_span_rank'] = next((n for n,r in enumerate(hits,1) if r['movie_id']==case['movie_id'] and r['start'] <= case.get('start',-1)+.1 and r['end'] >= case.get('end',1e9)-.1), None)
                candidate = case.get('scene_id') in result.get('candidate_ids', [])
                record['candidate_hit'] = candidate
                record['reranked_hit'] = case.get('scene_id') in result.get('reranked_ids', [])
                record['expected_reranker_score'] = result.get('reranker_scores', {}).get(case.get('scene_id'))
                record['retrieval_query'] = result.get('retrieval_query', case['query'])
                record['channels'] = {k: v.index(case['scene_id'])+1 if case.get('scene_id') in v else None for k,v in result.get('channels',{}).items()}
                record['top'] = [{k:r[k] for k in ['scene_id','title','start','end','match']} for r in hits[:5]]
                record['elapsed_ms'] = result['elapsed_ms']
                record['diagnosis'] = ('movie_missing' if not present else 'hit' if record['scene_rank'] else 'movie_only_unverified' if not case.get('scene_id') and record['movie_rank'] else 'ranking_or_localization_miss' if candidate else 'candidate_or_source_miss')
            except ValueError as exc:
                record.update(diagnosis='input_rejected', error=str(exc))
            rows.append(record)
            (ROOT / output).write_text(json.dumps(rows, indent=2), encoding='utf-8')
            print(i+1,case['category'],record['diagnosis'],record.get('movie_rank'),record.get('scene_rank'),flush=True)
    finally:
        engine.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--output',default='research/long_query_baseline.json')
    parser.add_argument('--indices', help='Comma-separated one-based case numbers')
    args = parser.parse_args()
    if args.prepare: prepare()
    run(args.output, {int(n) for n in args.indices.split(',')} if args.indices else None)
