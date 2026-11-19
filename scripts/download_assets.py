"""Asset downloader utility for DialogueMatch.

Downloads pre-trained embeddings, context dossiers, and the full 2,000-movie SQLite database
directly from the official Hugging Face repository (nithingodugu/DialogueMatch).
"""
import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
HF_REPO = "nithingodugu/DialogueMatch"

DATASET_FILES = [
    "data/dialoguematch.gap.json",
    "data/dialoguematch.gap.npy",
    "data/dialoguematch.movies.json",
    "data/dialoguematch.movies.npy",
    "data/dialoguematch.coverage.json",
    "data/dialoguematch.vectors.json",
    "data/dialoguematch.plots.sqlite",
    "data/dialoguematch.context.sqlite",
    "data/dialoguematch.sqlite",
]


def download_assets(target: str = "full", repo_id: str = HF_REPO):
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[Error] huggingface_hub is required. Install via: pip install huggingface_hub")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if target == "sample":
        sample_path = DATA_DIR / "sample/dialoguematch.sample.sqlite"
        if sample_path.is_file():
            print(f"[Info] Sample corpus already present: {sample_path}")
            return
        print(f"[Info] Generating local sample corpus...")
        from scripts.create_sample_corpus import create_sample_corpus
        create_sample_corpus()
        return

    print(f"================================================================================")
    print(f"             DOWNLOADING DIALOGUEMATCH ASSETS FROM HUGGING FACE")
    print(f"================================================================================")
    print(f"Repository: https://huggingface.co/datasets/{repo_id}")
    print(f"Destination: {DATA_DIR}")
    print(f"================================================================================\n")

    for file_rel in DATASET_FILES:
        dest_file = ROOT / file_rel
        if dest_file.is_file() and dest_file.stat().st_size > 0:
            print(f"[Exists] {file_rel} already exists ({dest_file.stat().st_size / (1024*1024):.2f} MB). Skipping.")
            continue

        print(f"--> Downloading {file_rel} from {repo_id}...")
        try:
            downloaded = hf_hub_download(
                repo_id=repo_id,
                filename=file_rel,
                repo_type="dataset",
            )
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(downloaded, dest_file)
            print(f"    [Done] Saved to {dest_file}")
        except Exception as e:
            print(f"    [Warning] Could not download {file_rel}: {e}")

    print("\n[Complete] Asset download finished. Run 'python -m dialoguematch doctor' to verify health.")


def main():
    parser = argparse.ArgumentParser(description="Download DialogueMatch data assets and model indexes")
    parser.add_argument("--target", choices=["sample", "full"], default="full", help="Target assets to download")
    parser.add_argument("--repo-id", default=HF_REPO, help="Hugging Face Dataset repo ID")
    args = parser.parse_args()
    download_assets(args.target, args.repo_id)


if __name__ == "__main__":
    main()
