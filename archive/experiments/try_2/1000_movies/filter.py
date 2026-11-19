import csv
import json

# Load first 100 imdb_ids from CSV
with open("2000_movies.csv", newline='', encoding="utf-8") as f:
    reader = csv.DictReader(f)

    first_100_ids = [
        row["imdb_id"]
        for i, row in enumerate(reader)
        if i < 1000
    ]

# Convert to set for faster lookup
id_set = set(first_100_ids)

# Load JSON
with open("dialogue_2000_movies.json", encoding="utf-8") as f:
    json_movies = json.load(f)

# Keep ALL matching entries including duplicates
filtered_movies = [
    movie
    for movie in json_movies
    if movie.get("_id").split("_")[0] in id_set
]

# Save result
with open("filtered_movies.json", "w", encoding="utf-8") as f:
    json.dump(filtered_movies, f, indent=2, ensure_ascii=False)

print(f"Saved {len(filtered_movies)} matching records.")