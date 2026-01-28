import json
import os
import time
import requests


# -----------------------------
# input your info below here
# -----------------------------

# this'll be what the path is in steam/userdata/
userid = "123456789"
# this is the path to your steam base directory (the one that contains stuff like "common" and "userdata")
path_base = os.path.join("/home/foo/.steam/steam")

# -----------------------------
# input your info above here
# -----------------------------

path = os.path.join(path_base, "userdata", userid, "config", "cloudstorage")
files = os.listdir(path)
match = "cloud-storage-namespace-"
collections = []

# -----------------------------
# Cache setup
# -----------------------------
CACHE_FILE = "steam_app_cache.json"
SAVE_EVERY = 5  # Save cache every 5 new fetched entries

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        try:
            app_cache = json.load(f)
            # JSON keys are strings → convert back to int
            app_cache = {int(k): v for k, v in app_cache.items()}
        except json.JSONDecodeError:
            app_cache = {}
else:
    app_cache = {}

new_entries_since_save = 0

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(app_cache, f, indent=2)

# -----------------------------
# Steam API w/ recursive backoff
# -----------------------------
def fetch_app_info(appid, collection_name, attempt=1, max_attempts=5, base_delay=0.5):
    global new_entries_since_save

    # ✅ Cache hit
    if appid in app_cache:
        printstring = f"🗂️ Cache hit: {app_cache[appid].get('name', 'Unknown')} ({appid})"
        app_info = app_cache[appid]

        # Ensure 'collection' is a list
        collections = app_info.get("collection")
        if not collections:
            app_info["collection"] = [collection_name]
            printstring += " - Added collection info"
        else:
            if isinstance(collections, str):
                collections = [collections]

            if collection_name not in collections:
                collections.append(collection_name)
                app_info["collection"] = collections
                printstring += " - Added additional collection info"

        print(printstring)
        return app_info

    if attempt > max_attempts:
        print(f"❌ Giving up on app {appid}")
        return None

    # Wait before making a network request (not for cache hits)
    delay = base_delay * (2 ** (attempt - 1))
    if attempt > 1 or attempt == 1:
        time.sleep(delay)

    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": appid, "l": "en"}

    try:
        r = requests.get(url, params=params, timeout=10)

        if r.status_code == 429:
            raise requests.HTTPError("Rate limited", response=r)

        r.raise_for_status()
        data = r.json()

        app_data = data.get(str(appid), {})
        if not app_data.get("success"):
            # Cache failures so we don’t retry forever
            app_cache[appid] = {"appid": appid, "status": "unavailable"}
            new_entries_since_save += 1
            if new_entries_since_save >= SAVE_EVERY:
                save_cache()
                new_entries_since_save = 0
            return None

        info = app_data["data"]
        result = {
            "appid": appid,
            "name": info.get("name"),
            "type": info.get("type"),
            "release_date": info.get("release_date", {}).get("date"),
            "developers": info.get("developers", []),
            "publishers": info.get("publishers", []),
            "genres": [g["description"] for g in info.get("genres", [])],
            "is_free": info.get("is_free"),
            "header_image": info.get("header_image"),
            "collection": collection_name
        }

        print(f"✅ Fetched: {result['name']} ({appid})")

        # Cache & conditionally save
        app_cache[appid] = result
        new_entries_since_save += 1
        if new_entries_since_save >= SAVE_EVERY:
            save_cache()
            new_entries_since_save = 0

        return result

    except (requests.RequestException, ValueError):
        print(f"⚠️  App {appid} failed (attempt {attempt}), retrying in {delay:.1f}s")
        return fetch_app_info(appid, collection_name, attempt + 1, max_attempts, base_delay)

# -----------------------------
# Load collections
# -----------------------------
for file in files:
    if file.startswith(match):
        file_path = os.path.join(path, file)
        with open(file_path, "r") as f:
            json_data = json.loads(f.read())

            for entry_name, entry in json_data:
                if entry.get("is_deleted"):
                    continue

                if not entry_name.startswith("user-collections.uc-"):
                    continue

                value = entry.get("value")
                if not value:
                    continue

                try:
                    value_data = json.loads(value)
                except json.JSONDecodeError:
                    continue

                added = value_data.get("added", [])
                if not added:
                    continue

                collections.append({
                    "id": value_data.get("id"),
                    "name": value_data.get("name"),
                    "added": added,
                })

# -----------------------------
# Fetch Steam metadata
# -----------------------------
for collection in collections:
    for appid in collection["added"]:
        fetch_app_info(appid, collection["name"])

# Save cache at the end just in case
save_cache()

# -----------------------------
# Attach metadata to collections
# -----------------------------
for collection in collections:
    collection["games"] = [
        app_cache[appid]
        for appid in collection["added"]
        if appid in app_cache and app_cache[appid].get("status") != "unavailable"
    ]
