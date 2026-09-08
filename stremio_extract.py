import requests
import concurrent.futures

ADDON_BASE = "https://live-addon.vercel.app"
OUTPUT_FILE = "stremio_playlist.m3u"
KEYWORDS = ["live now", "today", "football"]
MAX_WORKERS = 30
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def process_meta_task(task):
    cat_type, item_id, name, cat_name, cat_id = task
    found = []
    stream_url = f"{ADDON_BASE}/stream/{cat_type}/{item_id}.json"
    try:
        stream_res = requests.get(stream_url, headers=HEADERS, timeout=5).json()
        streams = stream_res.get("streams", [])
        
        for stream in streams:
            title = stream.get("title", "")
            url = stream.get("url")
            
            # Check catalog name, catalog ID, channel name, and stream title
            full_text = f"{cat_name} {cat_id} {name} {title}".lower()
            
            if url and any(kw in full_text for kw in KEYWORDS):
                stream_name = f"{name} - {title}".strip(" -") if title else name
                found.append((stream_name, url))
    except Exception:
        pass
    return found

def get_stremio_streams():
    tasks = []
    try:
        manifest_res = requests.get(f"{ADDON_BASE}/manifest.json", headers=HEADERS, timeout=10)
        manifest = manifest_res.json()
        catalogs = manifest.get("catalogs", [])
        
        # Build list of items across catalogs first
        for cat in catalogs:
            cat_type = cat.get("type")
            cat_id = cat.get("id")
            cat_name = cat.get("name", "")
            
            catalog_url = f"{ADDON_BASE}/catalog/{cat_type}/{cat_id}.json"
            print(f"Fetching catalog metadata: {cat_name or cat_id}...")
            try:
                catalog_res = requests.get(catalog_url, headers=HEADERS, timeout=10).json()
                metas = catalog_res.get("metas", [])
                for meta in metas:
                    item_id = meta.get("id")
                    name = meta.get("name", "Unknown Channel")
                    tasks.append((cat_type, item_id, name, cat_name, cat_id))
            except Exception as e:
                print(f"Failed catalog fetch for {cat_id}: {e}")
                
    except Exception as e:
        print(f"Error parsing Stremio API: {e}")
        return []

    print(f"Concurrently checking {len(tasks)} channels using {MAX_WORKERS} threads...")
    streams_found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(process_meta_task, tasks)
        for stream_list in results:
            streams_found.extend(stream_list)

    return streams_found

def main():
    print("Starting high-speed multithreaded extraction...")
    valid_entries = get_stremio_streams()
    
    # Deduplicate entries by URL
    seen = set()
    unique_entries = []
    for name, url in valid_entries:
        if url not in seen:
            seen.add(url)
            unique_entries.append((name, url))
            
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in unique_entries:
            f.write(f"#EXTINF:-1,{name}\n{url}\n")
            
    print(f"Done! Saved {len(unique_entries)} matching streams to {OUTPUT_FILE} in seconds.")

if __name__ == "__main__":
    main()
