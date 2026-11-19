"""Create a lightweight sample SQLite corpus (~3MB) for instant offline demo and CI testing."""
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT / "data/dialoguematch.sqlite"
TARGET_DIR = ROOT / "data/sample"
TARGET_DB = TARGET_DIR / "dialoguematch.sample.sqlite"

SAMPLE_MOVIES = (
    "tt0816692",  # Interstellar (2014)
    "tt0468569",  # The Dark Knight (2008)
    "tt0172495",  # Gladiator (2000)
    "tt2582802",  # Whiplash (2014)
    "tt1375666",  # Inception (2010)
)


def create_sample_corpus(source_path: Path = SOURCE_DB, target_path: Path = TARGET_DB):
    if not source_path.is_file():
        raise FileNotFoundError(f"Source database not found at {source_path}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.is_file():
        target_path.unlink()

    src = sqlite3.connect(f"file:{source_path.resolve()}?mode=ro", uri=True)
    dst = sqlite3.connect(target_path)

    try:
        # Create schema matching production exactly
        dst.executescript("""
            CREATE TABLE scenes(
                id TEXT PRIMARY KEY,
                movie_id TEXT,
                start REAL,
                end REAL,
                text TEXT,
                summary TEXT,
                queries TEXT,
                keywords TEXT,
                lines TEXT,
                source TEXT,
                paraphrase TEXT,
                relationship TEXT,
                emotion TEXT
            );
            CREATE INDEX by_movie_time ON scenes(movie_id, start);

            CREATE TABLE movies(
                id TEXT PRIMARY KEY,
                title TEXT,
                status TEXT,
                details TEXT,
                year INTEGER DEFAULT 0,
                rating REAL DEFAULT 0.0,
                votes INTEGER DEFAULT 0
            );

            CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);

            CREATE VIRTUAL TABLE search USING fts5(
                id UNINDEXED,
                dialogue,
                description,
                keywords,
                tokenize='porter unicode61'
            );

            CREATE VIRTUAL TABLE quotes USING fts5(
                scene_id UNINDEXED,
                start UNINDEXED,
                end UNINDEXED,
                raw UNINDEXED,
                dialogue,
                tokenize='unicode61'
            );

            CREATE VIRTUAL TABLE sequences USING fts5(
                movie_id UNINDEXED,
                scene_ids UNINDEXED,
                start UNINDEXED,
                end UNINDEXED,
                narrative,
                tokenize='porter unicode61'
            );
        """)

        # Copy movies
        placeholders = ",".join("?" for _ in SAMPLE_MOVIES)
        movie_rows = src.execute(
            f"SELECT id, title, status, details, year, rating, votes FROM movies WHERE id IN ({placeholders})",
            SAMPLE_MOVIES,
        ).fetchall()
        dst.executemany("INSERT INTO movies VALUES (?, ?, ?, ?, ?, ?, ?)", movie_rows)

        # Copy scenes
        scene_rows = src.execute(
            f"SELECT id, movie_id, start, end, text, summary, queries, keywords, lines, source, "
            f"paraphrase, relationship, emotion FROM scenes WHERE movie_id IN ({placeholders})",
            SAMPLE_MOVIES,
        ).fetchall()
        dst.executemany(
            "INSERT INTO scenes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            scene_rows,
        )

        # Copy meta
        meta_rows = src.execute("SELECT key, value FROM meta").fetchall()
        dst.executemany("INSERT INTO meta VALUES (?, ?)", meta_rows)

        # Populate search FTS from copied scenes directly (fast)
        dst.execute("""
            INSERT INTO search(id, dialogue, description, keywords)
            SELECT id, text, summary, keywords FROM scenes;
        """)

        # Populate quotes FTS by joining scenes with source quotes table
        scene_ids = [r[0] for r in scene_rows]
        scene_id_set = set(scene_ids)
        # Fetch matching quotes in batches of 500
        for i in range(0, len(scene_ids), 500):
            batch = scene_ids[i:i + 500]
            batch_ph = ",".join("?" for _ in batch)
            q_rows = src.execute(
                f"SELECT scene_id, start, end, raw, dialogue FROM quotes WHERE scene_id IN ({batch_ph})",
                batch,
            ).fetchall()
            dst.executemany("INSERT INTO quotes VALUES (?, ?, ?, ?, ?)", q_rows)

        # Populate sequences FTS
        seq_rows = src.execute(
            f"SELECT movie_id, scene_ids, start, end, narrative FROM sequences WHERE movie_id IN ({placeholders})",
            SAMPLE_MOVIES,
        ).fetchall()
        dst.executemany("INSERT INTO sequences VALUES (?, ?, ?, ?, ?)", seq_rows)

        dst.commit()
        size_mb = target_path.stat().st_size / (1024 * 1024)
        print(f"Created sample corpus at: {target_path}")
        print(f"  Movies: {len(movie_rows)}")
        print(f"  Scenes: {len(scene_rows)}")
        print(f"  Sequences: {len(seq_rows)}")
        print(f"  Size: {size_mb:.2f} MB")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    create_sample_corpus()
