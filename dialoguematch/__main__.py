import argparse
import json
import os
from pathlib import Path
import sys

from .build import DEFAULT_DB

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DB = ROOT / "data/sample/dialoguematch.sample.sqlite"


def _print_pretty_results(payload: dict):
    print(f"\nQuery: {payload['query']}")
    print(f"Status: {payload['status']} | Mode: {payload['mode']} | Time: {payload.get('elapsed_ms', 0)} ms")
    qc = payload.get('query_context') or {}
    if qc.get('is_decomposed'):
        print(f"  [Global Film Clue] : {qc.get('global_context')}")
        print(f"  [Target Scene Clue]: {qc.get('scene_target')}")
    if qc.get('temporal_label'):
        print(f"  [Narrative Timing] : {qc.get('temporal_label')}")
    if qc.get('matched_movies'):
        worlds = ', '.join(f"{m['title']} ({m.get('year') or ''})" for m in qc['matched_movies'][:3])
        print(f"  [Film Worlds]      : {worlds}")
    print(payload.get('message', ''))
    print('-' * 78)
    for idx, r in enumerate(payload.get('results', []), 1):
        yr = f" ({r['year']})" if r.get('year') else ''
        rt = f" ★ {r['rating']:.1f}" if r.get('rating') else ''
        act = f" · {r['act_label']} ({round(r.get('progress', 0) * 100)}%)" if r.get('act_label') else ''
        print(f"{idx}. {r['title']}{yr}{rt} [{r['movie_id']}]  {r['start_label']} – {r['end_label']}{act}")
        if r.get('why_matched'):
            print(f"   Why:      {r['why_matched']}")
        if r.get('prev_beat'):
            print(f"   Before:   {r['prev_beat']}")
        if r.get('summary'):
            print(f"   Scene:    {r['summary']}")
        snippet = ' '.join(str(r.get('dialogue', '')).split())[:220]
        print(f"   Dialogue: {snippet}")
        print()


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='DialogueMatch: local quote and scene search engine')
    parser.add_argument('--db', default=None, help='Path to SQLite database')
    parser.add_argument('--sample', action='store_true', help='Use lightweight sample corpus (5 iconic movies) for instant offline demo')
    commands = parser.add_subparsers(dest='command', required=True)

    build_cmd = commands.add_parser('build', help='Build lexical corpus, sequence windows, and recover local subtitles')
    build_cmd.add_argument('--source')
    build_cmd.add_argument('--subtitles')
    build_cmd.add_argument('--metadata')
    build_cmd.add_argument('--all-subtitles', action='store_true')

    embed_cmd = commands.add_parser('embed', help='Build verified semantic vectors')
    embed_cmd.add_argument('--model', default='sentence-transformers/all-MiniLM-L6-v2')
    embed_cmd.add_argument('--batch-size', type=int, default=64)

    gap_cmd = commands.add_parser('build-gap', help='Rebind manifest and build calibrated semantic vectors for recovered movies')
    gap_cmd.add_argument('--model', default='sentence-transformers/all-MiniLM-L6-v2')
    gap_cmd.add_argument('--batch-size', type=int, default=128)

    legacy_cmd = commands.add_parser('import-legacy', help='Verify and import the existing local BGE index')
    legacy_cmd.add_argument('--index', default='V3/files/1606text.index')
    legacy_cmd.add_argument('--ids', default='V3/files/1606text_chunk_ids.npy')
    legacy_cmd.add_argument('--source', default='V3/scene-finder.chunks_paraphrase.json')

    plots_cmd = commands.add_parser('build-plots', help='Build optional movie-level plot search')
    plots_cmd.add_argument('--archive', default='data/MovieSummaries.tar.gz')
    plots_cmd.add_argument('--metadata')

    ctx_cmd = commands.add_parser('build-context', help='Synthesize global movie dossiers, scene flow, and movie vectors')
    ctx_cmd.add_argument('--model', default='sentence-transformers/all-MiniLM-L6-v2')
    ctx_cmd.add_argument('--batch-size', type=int, default=128)

    doctor_cmd = commands.add_parser('doctor', help='Verify database, semantic indexes, plot index, and models')
    doctor_cmd.add_argument('--lexical-only', action='store_true')
    doctor_cmd.add_argument('--sample', action='store_true', help='Use sample corpus')
    doctor_cmd.add_argument('--db', help='Path to SQLite database')

    test_cmd = commands.add_parser('test', help='Run automated test suite')
    test_cmd.add_argument('pytest_args', nargs='*', default=['tests', '-q'])

    bench_cmd = commands.add_parser('benchmark', help='Run ablation benchmark suite (Hit@k, MRR, NDCG, latency)')
    bench_cmd.add_argument('--sample', action='store_true', help='Use sample corpus')
    bench_cmd.add_argument('--db', help='Path to SQLite database')
    bench_cmd.add_argument('--dataset', default=str(ROOT / 'benchmarks/datasets/curated_benchmark.json'))
    bench_cmd.add_argument('--output-dir', default=str(ROOT / 'benchmarks/results'))

    sample_cmd = commands.add_parser('sample', help='Generate lightweight 5-movie sample corpus for instant offline testing')
    sample_cmd.add_argument('--target', default=str(SAMPLE_DB))

    dl_cmd = commands.add_parser('download', help='Download pre-trained weights and indexes from cloud repository')
    dl_cmd.add_argument('--target', choices=['sample', 'full'], default='sample')

    for name in ['search', 'serve', 'evaluate']:
        command = commands.add_parser(name)
        command.add_argument('--lexical-only', action='store_true')
        command.add_argument('--no-rerank', action='store_true')
        command.add_argument('--sample', action='store_true', help='Use sample corpus')
        command.add_argument('--db', help='Path to SQLite database')
        if name == 'search':
            command.add_argument('query')
            command.add_argument('--mode', choices=['auto', 'quote', 'scene'], default='auto')
            command.add_argument('--movie', help='IMDb ID (e.g. tt0816692) or movie title (e.g. "Interstellar")')
            command.add_argument('--limit', type=int, default=10)
            command.add_argument('--pretty', action='store_true', help='Format output as readable terminal cards')
        elif name == 'serve':
            command.add_argument('--port', type=int, default=8765)
        else:
            command.add_argument('queries')
            command.add_argument('--output', default='research/retrieval_evaluation.json')

    args = parser.parse_args()

    # Database resolution
    use_sample = getattr(args, 'sample', False)
    explicit_db = getattr(args, 'db', None)
    if use_sample:
        active_db = SAMPLE_DB
    elif explicit_db:
        active_db = Path(explicit_db)
    elif DEFAULT_DB.is_file():
        active_db = DEFAULT_DB
    elif SAMPLE_DB.is_file():
        active_db = SAMPLE_DB
    else:
        active_db = DEFAULT_DB

    if args.command == 'build':
        from .build import build
        build(active_db, args.source, args.subtitles, args.metadata, args.all_subtitles)
    elif args.command == 'embed':
        from .neural import build_vectors
        build_vectors(active_db, args.model, args.batch_size)
    elif args.command == 'build-gap':
        from .neural import build_gap_vectors, rebind_vector_manifest
        if Path(active_db).with_suffix('.vectors.json').is_file():
            rebind_vector_manifest(active_db)
        build_gap_vectors(active_db, args.model, args.batch_size)
    elif args.command == 'import-legacy':
        from .neural import import_legacy_vectors
        import_legacy_vectors(active_db, args.index, args.ids, args.source)
    elif args.command == 'build-plots':
        from .plots import build_plot_index
        build_plot_index(active_db, args.archive, args.metadata)
    elif args.command == 'build-context':
        from .context import build_context_index
        build_context_index(active_db, args.model, args.batch_size)
    elif args.command == 'test':
        os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        import pytest
        raise SystemExit(pytest.main(args.pytest_args))
    elif args.command == 'benchmark':
        from benchmarks.run_benchmark import run_benchmarks
        run_benchmarks(active_db, Path(args.dataset), Path(args.output_dir))
    elif args.command == 'sample':
        from scripts.create_sample_corpus import create_sample_corpus
        create_sample_corpus(target_path=Path(args.target))
    elif args.command == 'download':
        from scripts.download_assets import download_assets
        download_assets(args.target)
    elif args.command == 'doctor':
        from .artwork import MovieArtwork
        from .engine import SearchEngine
        from .indexes import IndexSelector
        engine = SearchEngine(active_db, neural=not args.lexical_only, rerank=not args.lexical_only)
        try:
            info = engine.status()
            info['database_path'] = str(active_db)
            info['artwork_configured'] = MovieArtwork().enabled
            info['available_lab_indexes'] = len(IndexSelector(engine).options()) - 1
            print(json.dumps(info, indent=2))
        finally:
            engine.close()
    else:
        from .engine import SearchEngine
        engine = SearchEngine(active_db, neural=not args.lexical_only, rerank=not (args.no_rerank or args.lexical_only))
        try:
            if args.command == 'search':
                res = engine.search(args.query, args.mode, args.limit, args.movie)
                if args.pretty:
                    _print_pretty_results(res)
                else:
                    print(json.dumps(res, indent=2, ensure_ascii=False))
            elif args.command == 'serve':
                from .server import serve
                serve(engine, args.port)
            else:
                from .evaluate import evaluate
                evaluate(engine, args.queries, args.output)
        finally:
            engine.close()


if __name__ == '__main__':
    main()
