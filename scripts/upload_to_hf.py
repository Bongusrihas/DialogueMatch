"""Upload DialogueMatch production data assets and model indexes to Hugging Face Hub."""
import argparse
from pathlib import Path
import sys
import time

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "nithingodugu/DialogueMatch"

# Priority 1: Core metadata, vector indexes, and auxiliary sqlite databases
CORE_ASSETS = [
    ("data/dialoguematch.gap.json", "data/dialoguematch.gap.json"),
    ("data/dialoguematch.gap.npy", "data/dialoguematch.gap.npy"),
    ("data/dialoguematch.movies.json", "data/dialoguematch.movies.json"),
    ("data/dialoguematch.movies.npy", "data/dialoguematch.movies.npy"),
    ("data/dialoguematch.coverage.json", "data/dialoguematch.coverage.json"),
    ("data/dialoguematch.vectors.json", "data/dialoguematch.vectors.json"),
    ("data/dialoguematch.plots.sqlite", "data/dialoguematch.plots.sqlite"),
    ("data/dialoguematch.context.sqlite", "data/dialoguematch.context.sqlite"),
]

# Priority 2: Primary SQLite corpus (1.67 GB)
PRIMARY_DATABASE = [
    ("data/dialoguematch.sqlite", "data/dialoguematch.sqlite"),
]

# Priority 3: Fallback single-vector embeddings
SINGLE_VECTORS = [
    ("data/dialoguematch.vectors.npy", "data/dialoguematch.vectors.npy"),
]

# Priority 4: Verified Multi-Index FAISS ensemble and fine-tuned model
ENSEMBLE_INDEXES = [
    ("index_lab/catalog.json", "index_lab/catalog.json"),
    ("index_lab/shared/fine_model/model.safetensors", "index_lab/shared/fine_model/model.safetensors"),
    ("index_lab/shared/fine_model/config.json", "index_lab/shared/fine_model/config.json"),
    ("index_lab/shared/fine_model/tokenizer.json", "index_lab/shared/fine_model/tokenizer.json"),
    ("index_lab/shared/fine_model/vocab.txt", "index_lab/shared/fine_model/vocab.txt"),
    ("index_lab/shared/fine_model/modules.json", "index_lab/shared/fine_model/modules.json"),
    ("index_lab/02_preprocessing_finetuned_model_dialogue/index.faiss", "index_lab/02_preprocessing_finetuned_model_dialogue/index.faiss"),
    ("index_lab/02_preprocessing_finetuned_model_dialogue/config.json", "index_lab/02_preprocessing_finetuned_model_dialogue/config.json"),
    ("index_lab/04_preprocessing_finetuned_model_summary/index.faiss", "index_lab/04_preprocessing_finetuned_model_summary/index.faiss"),
    ("index_lab/04_preprocessing_finetuned_model_summary/config.json", "index_lab/04_preprocessing_finetuned_model_summary/config.json"),
    ("index_lab/18_preprocessing_indexes_movies_t_e_baai/index.faiss", "index_lab/18_preprocessing_indexes_movies_t_e_baai/index.faiss"),
    ("index_lab/18_preprocessing_indexes_movies_t_e_baai/config.json", "index_lab/18_preprocessing_indexes_movies_t_e_baai/config.json"),
    ("index_lab/12_preprocessing_indexes_chunk_embeddings_ctx_combined/index.faiss", "index_lab/12_preprocessing_indexes_chunk_embeddings_ctx_combined/index.faiss"),
    ("index_lab/12_preprocessing_indexes_chunk_embeddings_ctx_combined/config.json", "index_lab/12_preprocessing_indexes_chunk_embeddings_ctx_combined/config.json"),
]


def upload_batch(api: HfApi, repo_id: str, file_pairs: list[tuple[str, str]], existing_files: set[str], overwrite: bool = False):
    for local_rel, repo_path in file_pairs:
        local_path = ROOT / local_rel
        if not local_path.is_file():
            print(f"[Skip] Local file not found: {local_rel}")
            continue

        if repo_path in existing_files and not overwrite:
            print(f"[Exists] Already in HF repo: {repo_path}")
            continue

        size_mb = local_path.stat().st_size / (1024 * 1024)
        print(f"\n--> Uploading {repo_path} ({size_mb:.2f} MB)...")
        t0 = time.time()
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=repo_path,
            repo_id=repo_id,
            repo_type="dataset",
        )
        elapsed = time.time() - t0
        speed = size_mb / elapsed if elapsed > 0 else 0
        print(f"    Done in {elapsed:.1f}s ({speed:.2f} MB/s)")


def main():
    parser = argparse.ArgumentParser(description="Upload DialogueMatch assets to Hugging Face Hub")
    parser.add_argument("--repo-id", default=DEFAULT_REPO, help="Hugging Face repo ID")
    parser.add_argument("--tier", choices=["core", "database", "all"], default="core",
                        help="Upload tier: core (metadata/vectors/context/plots), database (full 1.67GB sqlite), all")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files in HF repo")
    args = parser.parse_args()

    api = HfApi()
    who = api.whoami()
    print(f"Authenticated on Hugging Face as: {who.get('name', who.get('user', 'unknown'))}")
    print(f"Target Repository: {args.repo_id} (dataset)")

    existing = set(api.list_repo_files(repo_id=args.repo_id, repo_type="dataset"))
    print(f"Existing files in repository: {len(existing)}")

    if args.tier in {"core", "all"}:
        print("\n=== UPLOADING CORE ASSETS ===")
        upload_batch(api, args.repo_id, CORE_ASSETS, existing, args.overwrite)

    if args.tier in {"database", "all"}:
        print("\n=== UPLOADING PRIMARY DATABASE (1.67 GB) ===")
        upload_batch(api, args.repo_id, PRIMARY_DATABASE, existing, args.overwrite)
        upload_batch(api, args.repo_id, SINGLE_VECTORS, existing, args.overwrite)

    if args.tier == "all":
        print("\n=== UPLOADING ENSEMBLE INDEXES & MODEL ===")
        upload_batch(api, args.repo_id, ENSEMBLE_INDEXES, existing, args.overwrite)

    print("\n[Complete] All requested assets checked and synced to Hugging Face Hub.")


if __name__ == "__main__":
    main()
