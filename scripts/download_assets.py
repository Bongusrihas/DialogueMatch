"""Asset downloader utility for DialogueMatch.

Downloads pre-trained FAISS indexes, embeddings, and full SQLite databases from
remote storage (e.g. Hugging Face Hub, GitHub Releases, or S3).
"""
import argparse
import hashlib
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

# Remote registry mapping filename to remote URL and expected SHA-256 (sample/template)
REMOTE_REGISTRY = {
    "dialoguematch.sample.sqlite": {
        "url": "https://raw.githubusercontent.com/user/DialogueMatch/main/data/sample/dialoguematch.sample.sqlite",
        "description": "5-movie lightweight demo database (~3.7MB)",
        "dest": DATA_DIR / "sample/dialoguematch.sample.sqlite",
        "sha256": None,
    },
    "dialoguematch.gap.npy": {
        "url": "https://huggingface.co/datasets/dialoguematch/corpus-v2/resolve/main/dialoguematch.gap.npy",
        "description": "Calibrated MiniLM gap vectors for 74 subtitle-recovered movies (~21MB)",
        "dest": DATA_DIR / "dialoguematch.gap.npy",
        "sha256": None,
    },
    "dialoguematch.movies.npy": {
        "url": "https://huggingface.co/datasets/dialoguematch/corpus-v2/resolve/main/dialoguematch.movies.npy",
        "description": "3-view narrative film vectors across 2,000 movies (~9MB)",
        "dest": DATA_DIR / "dialoguematch.movies.npy",
        "sha256": None,
    },
    "dialoguematch.sqlite": {
        "url": "https://huggingface.co/datasets/dialoguematch/corpus-v2/resolve/main/dialoguematch.sqlite",
        "description": "Full 2,000-movie enriched SQLite corpus with FTS5 search (~1.6GB)",
        "dest": DATA_DIR / "dialoguematch.sqlite",
        "sha256": None,
    },
}


def download_file(url: str, dest_path: Path, description: str = ""):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {dest_path.name} ({description})...")
    print(f"  Source: {url}")
    print(f"  Target: {dest_path}")

    def reporthook(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100.0, downloaded * 100.0 / total_size)
            mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            sys.stdout.write(f"\r  Progress: {mb:.1f} MB / {total_mb:.1f} MB ({percent:.1f}%)")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, dest_path, reporthook=reporthook)
        print("\n  [Success] Download complete.")
    except Exception as e:
        print(f"\n  [Error] Failed to download from {url}: {e}")
        print("  If using a custom Hugging Face repo or private mirror, set the URL or token.")


def download_assets(target: str = "sample"):
    if target == "sample":
        item = REMOTE_REGISTRY["dialoguematch.sample.sqlite"]
        if item["dest"].is_file():
            print(f"[Info] Sample corpus already exists at {item['dest']}")
            return
        download_file(item["url"], item["dest"], item["description"])
    elif target == "full":
        for name, item in REMOTE_REGISTRY.items():
            if item["dest"].is_file():
                print(f"[Info] {name} already exists. Skipping.")
                continue
            download_file(item["url"], item["dest"], item["description"])
    else:
        print(f"Unknown target: {target}. Choices: sample, full")


def main():
    parser = argparse.ArgumentParser(description="Download DialogueMatch data assets and model indexes")
    parser.add_argument("--target", choices=["sample", "full"], default="sample", help="Target assets to download")
    args = parser.parse_args()
    download_assets(args.target)


if __name__ == "__main__":
    main()
