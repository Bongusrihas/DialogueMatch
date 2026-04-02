from config import Config
from pathlib import Path
import requests
import json
import csv


Path("Subtitles").mkdir(exist_ok=True)
API_KEY=Config.API_KEY
BASE_URL=Config.BASE_URL


def download_subtitles(id):
    URL=BASE_URL+API_KEY+f"&id={id}"
    r=requests.get(URL).text
    data=json.loads(r)
    if not(isinstance(data, dict) and data.get("code") == 400):
        urls=[]
        for item in data:
            url=item.get("url")
            if url is None:
                break
            urls.append(url)

        for url in urls:
            subtitles=requests.get(url).text
            if not(subtitles is None):
                with open(f"Subtitles/{id}.srt","w+") as file:
                    file.write(subtitles)
                print("done",id)
                break

def cleaner(csv_file="movies_2000_2025.csv"):
    subtitles_folder = Path("Subtitles")
    with open(csv_file, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = reader.fieldnames
    rows_with_subtitles = [
        row for row in rows if (subtitles_folder / f"{row['id']}.srt").exists()
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_with_subtitles)


def get_ids(csv_file="movies_2000_2025.csv"):
    with open(csv_file,newline="",encoding="utf-8") as file:
        reader=csv.DictReader(file)
        for row in reader:
            id=row["id"]
            download_subtitles(id)
    cleaner(csv_file)
    

if __name__=="__main__":
    get_ids()
