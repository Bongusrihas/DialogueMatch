import json
import math
import os

# ===== CONFIG =====
input_file = "1000_movie_dialogue.json"   # Your JSON file
output_folder = "split_json_parts"
num_parts = 8
# ==================

# Create output folder
os.makedirs(output_folder, exist_ok=True)

# Load JSON
with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Ensure the JSON is a list/array
if not isinstance(data, list):
    raise ValueError("Top-level JSON must be an array/list to split cleanly.")

# Calculate chunk size
total_items = len(data)
chunk_size = math.ceil(total_items / num_parts)

# Split and save
for i in range(num_parts):
    start = i * chunk_size
    end = start + chunk_size

    chunk = data[start:end]

    output_file = os.path.join(output_folder, f"part_{i+1}.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunk, f, indent=4, ensure_ascii=False)

    print(f"Saved: {output_file} ({len(chunk)} items)")

print("\nDone. JSON split into 8 ordered parts without jumbling data.")

