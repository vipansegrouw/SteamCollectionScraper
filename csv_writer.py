import json
import csv
from main import CACHE_FILE

CSV_FILE = "steam_app_data.csv"

# Load JSON data
with open(CACHE_FILE, "r") as f:
    app_cache = json.load(f)

# Define CSV headers
headers = [
    "appid",
    "name",
    "type",
    "release_date",
    "developers",
    "publishers",
    "genres",
    "is_free",
    "header_image",
    "collection"
]

with open(CSV_FILE, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=headers)
    writer.writeheader()

    for appid_str, app_info in app_cache.items():
        if app_info.get("status") == "unavailable":
            continue

        row = {
            "appid": app_info.get("appid", ""),
            "name": app_info.get("name", ""),
            "type": app_info.get("type", ""),
            "release_date": app_info.get("release_date", ""),
            "developers": ", ".join(app_info.get("developers", [])),
            "publishers": ", ".join(app_info.get("publishers", [])),
            "genres": ", ".join(app_info.get("genres", [])),
            "is_free": app_info.get("is_free", ""),
            "header_image": app_info.get("header_image", ""),
            "collection": app_info.get("collection", "")
        }
        writer.writerow(row)

print(f"CSV data saved to {CSV_FILE}")
