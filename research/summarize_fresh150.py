"""Summarize all completed probes, including every failure and label caveats."""
import hashlib
import json
import math
import sqlite3
import statistics
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    query_path=ROOT/'research/fresh150_queries.json'
    cases=json.loads(query_path.read_text(encoding='utf-8'))
    run=json.loads((ROOT/'research/fresh150_results.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(query_path.read_bytes()).hexdigest()==run['query_sha256']
    by_id={q['id']:q for q in cases}
    rows=[{**by_id[r['id']],**r} for r in run['rows']]
    for row in rows:
        if row['diagnosis']=='not_reranked_or_quote_rejected':
            row['diagnosis']='quote_rejected' if row['mode']=='quote' else 'shortlist_excluded'
    summary={'completed':len(rows),'planned':len(cases),'query_sha256':run['query_sha256'],'categories':{},'diagnoses':dict(Counter(r['diagnosis'] for r in rows))}
    for category in dict.fromkeys(q['category'] for q in cases):
        members=[r for r in rows if r['category']==category]
        times=sorted(r['elapsed_ms'] for r in members)
        result={'count':len(members),'errors':sum('error' in r for r in members)}
        for key in ['movie','scene']:
            if key=='scene' and not any('scene_id' in r for r in members):continue
            result.update({f'{key}_hit{k}':sum(bool(r.get(f'{key}_rank') and r[f'{key}_rank']<=k) for r in members) for k in [1,5,10]})
        if times:result.update(median_ms=statistics.median(times),p95_ms=times[math.ceil(.95*len(times))-1])
        summary['categories'][category]=result
    con=sqlite3.connect(ROOT/'data/dialoguematch.sqlite');con.row_factory=sqlite3.Row
    failures=[]
    for row in rows:
        key='scene_rank' if row.get('scene_id') else 'movie_rank'
        if row.get(key) and row[key]<=5:continue
        expected=con.execute('SELECT id,start,end,text,summary FROM scenes WHERE id=?',(row.get('scene_id'),)).fetchone()
        top=row.get('top10',[])[:3]
        examples=[]
        for hit in top:
            source=con.execute('SELECT text,summary FROM scenes WHERE id=?',(hit['scene_id'],)).fetchone()
            examples.append({**hit,'dialogue_excerpt':source['text'][:500] if source else '', 'summary':source['summary'] if source else ''})
        failures.append({**row,'failure_at':'ranked_below_top5' if row.get(key) else row['diagnosis'],
                         'expected_source':dict(expected) if expected else None,'retrieved_examples':examples})
    con.close()
    summary['failed_top5']=len(failures)
    descriptions=[r for r in rows if r['category'] in {'natural_description','long_natural_description'}]
    summary['description_pipeline']={
        'count':len(descriptions),
        'labeled_passage_in_candidates':sum(bool(r.get('candidate_hit')) for r in descriptions),
        'labeled_passage_reranked':sum(bool(r.get('reranked_hit')) for r in descriptions),
        'span_hit5':sum(bool(r.get('scene_rank') and r['scene_rank']<=5) for r in descriptions),
        'movie_hit5_but_span_miss':sum(bool(r.get('movie_rank') and r['movie_rank']<=5) and not bool(r.get('scene_rank') and r['scene_rank']<=5) for r in descriptions)}
    pair_path=ROOT/'research/fresh150_paired20_results.json'
    paired_rows=[]
    if pair_path.exists():
        paired_cases=json.loads((ROOT/'research/fresh150_paired20_queries.json').read_text(encoding='utf-8'))
        pair_run=json.loads(pair_path.read_text(encoding='utf-8'))
        for name in ['engine.py','neural.py','text.py','plots.py']:
            assert pair_run['code_sha256'][name]==run['code_sha256'][name], 'Paired control used different search code'
        assert pair_run['query_sha256']==hashlib.sha256((ROOT/'research/fresh150_paired20_queries.json').read_bytes()).hexdigest()
        pair_labels={x['id']:x for x in paired_cases}
        originals={r['id']:r for r in rows}
        paired_rows=[{**pair_labels[r['id']],**r} for r in pair_run['rows']]
        summary['paired_controls']={'completed':len(paired_rows),'scene_hit5':0,'movie_hit5':0,'concise_gains':0,'concise_losses':0,'comparisons':[]}
        for r in paired_rows:
            original=originals[r['paired_with']]
            old=bool(original.get('scene_rank') and original['scene_rank']<=5)
            new=bool(r.get('scene_rank') and r['scene_rank']<=5)
            summary['paired_controls']['scene_hit5']+=new
            summary['paired_controls']['movie_hit5']+=bool(r.get('movie_rank') and r['movie_rank']<=5)
            summary['paired_controls']['concise_gains']+=new and not old
            summary['paired_controls']['concise_losses']+=old and not new
            summary['paired_controls']['comparisons'].append({'title':r['title'],'long_id':r['paired_with'],'concise_id':r['id'],'long_scene_rank':original.get('scene_rank'),'concise_scene_rank':r.get('scene_rank')})
        summary['total_completed_including_controls']=len(rows)+len(paired_rows)
    (ROOT/'research/fresh150_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (ROOT/'research/fresh150_failures.json').write_text(json.dumps(failures,indent=2,ensure_ascii=False),encoding='utf-8')
    lines=['# Fresh 150-query audit','',f'Completed: {len(rows)}/150. Query set SHA-256: `{run["query_sha256"]}`.','',
      'The query set was fixed before running. No search changes were made during this run. These are newly authored development probes across 40 movies excluded from the older 310-query evaluation. They are not independently collected human requests. The first 120 queries are three variants of 40 scene seeds, so they are correlated rather than 120 independent events. The 30 visual queries have manually supplied movie labels, no verified time labels, and are excluded from scene metrics. Natural descriptions were written using local subtitle text and generated summaries; summaries can be wrong. Timing labels follow local subtitles and have not been checked against movie video.','',
      '| Category | Queries | Movie @1 / @5 / @10 | Scene @1 / @5 / @10 | Median seconds |',
      '|---|---:|---|---|---:|']
    for cat,result in summary['categories'].items():
        movie=' / '.join(str(result[f'movie_hit{k}']) for k in [1,5,10])
        scene=' / '.join(str(result[f'scene_hit{k}']) for k in [1,5,10]) if 'scene_hit1' in result else 'No span labels'
        lines.append(f'| {cat} | {result["count"]} | {movie} | {scene} | {result.get("median_ms",0)/1000:.2f} |')
    pipeline=summary['description_pipeline']
    lines+=['',f'For the {pipeline["count"]} description probes, the labeled passage ID entered the candidate pool in {pipeline["labeled_passage_in_candidates"]} cases and reached reranking in {pipeline["labeled_passage_reranked"]}. Accepted span Hit@5 was {pipeline["span_hit5"]}. In {pipeline["movie_hit5_but_span_miss"]} cases the expected movie appeared in the first five but its labeled span did not. Retrieval, shortlist selection, and ranking therefore have separate measurable failure modes.']
    lines+=['','Search received only each query and its mode: expected movie IDs and scene labels were used only for scoring, with no movie filter. Counts above are hits, not percentages. A scene hit means temporal overlap with the labeled interval; broad passages can pass without precise localization. Some generic memories may fit multiple films or nearby passages: a miss of the single expected label does not establish that every returned alternative is irrelevant. Latencies exclude startup and were recorded under the machine’s current load.','',
            '## Every result','', '| ID | Movie | Category | Movie rank | Scene rank | Diagnosis |','|---|---|---|---:|---:|---|']
    for row in rows:lines.append(f'| {row["id"]} | {row["title"]} | {row["category"]} | {row.get("movie_rank") or "—"} | {row.get("scene_rank") or "—"} | {row["diagnosis"]} |')
    lines+=['','## Every top-five miss','', 'Full query text, expected dialogue, retrieval-channel ranks, and the first three returned passages are preserved in `fresh150_failures.json`. Missing ranks mean absent from the returned top ten, not proof that the movie is absent from the corpus.','']
    for row in failures:
        lines += [f'### {row["id"]}: {row["title"]} ({row["category"]})','',row['query'],'',
                  f'Movie rank: {row.get("movie_rank")}; scene rank: {row.get("scene_rank")}; diagnosis: {row["failure_at"]}. Candidate retained: {row.get("candidate_hit")}; reranked: {row.get("reranked_hit")}.',
                  '',f'Expected-scene channel ranks: `{json.dumps(row.get("channels",{}))}`.','']
    if paired_rows:
        result=summary['paired_controls']
        lines+=['## Twenty additional paired controls','',
                f'The same twenty long-description events were also tested as concise descriptions, with no search changes. Completed: {len(paired_rows)}/20; scene Hit@5: {result["scene_hit5"]}; movie Hit@5: {result["movie_hit5"]}. Removing the preamble gained {result["concise_gains"]} scene hits and lost {result["concise_losses"]}. These comparisons isolate the supplied preamble on these selected examples; they do not prove a universal effect of query length.','',
                '| Movie | Long scene rank | Concise scene rank |','|---|---:|---:|']
        for r in result['comparisons']:lines.append(f'| {r["title"]} | {r["long_scene_rank"] or "—"} | {r["concise_scene_rank"] or "—"} |')
        (ROOT/'research/fresh170_complete_records.json').write_text(json.dumps(rows+paired_rows,indent=2,ensure_ascii=False),encoding='utf-8')
    review_path=ROOT/'research/fresh150_label_review.json'
    if review_path.exists():
        review=json.loads(review_path.read_text(encoding='utf-8'))
        summary['label_review']=review
        lines+=['','## Label review','', 'Visual-memory labels are exploratory and were not verified against video. Raw scores retain all frozen labels, including the following uncertain example; no query was removed or relabeled to improve the result.','']
        for key,note in review.items():
            links=', '.join(f'[Official source {i+1}]({url})' for i,url in enumerate(note.get('sources',[])))
            lines += [f'- {key}: {note["reason"]} {links}']
    (ROOT/'research/fresh150_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (ROOT/'research/fresh150_report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
