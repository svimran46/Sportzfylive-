import requests
import concurrent.futures

ADDON_BASE = "https://nuvio.moaqeel6679.my.id"
OUTPUT_FILE = "nuvio_playlist.m3u"
MAX_WORKERS = 30
HEADERS = {'User-Agent': 'Mozilla/5.0'}

# Standard exclusions to keep the list focused on channels/sports
EXCLUDE_KEYWORDS = [
    "news", "movie", "adult", "politic", "music", 
    "kids", "family", "trailer", "smutt", "gore", 
    "crime", "crazyshit", "worldstar", "ync", "kaotic"
]

def is_excluded(text):
    text_lower = text.lower()
    return any(ex in text_lower for ex in EXCLUDE_KEYWORDS)

def process_meta_task(task):
    cat_type, item_id, name, cat_name = task
    found = []
    
    if is_excluded(name):
        return found

    stream_url = f"{ADDON_BASE}/stream/{cat_type}/{item_id}.json"
    try:
        res = requests.get(stream_url, headers=HEADERS, timeout=5).json()
        streams = res.get("streams", [])
        for stream in streams:
            url = stream.get("url")
            raw_title = stream.get("title", "")
            if url:
                title_clean = raw_title.replace("\n", " ").strip() if raw_title else ""
                
                if is_excluded(title_clean):
                    continue

                # Deduplicate channel name and stream title
                if not title_clean or name.lower() == title_clean.lower():
                    channel_label = name
                elif name.lower() in title_clean.lower():
                    channel_label = title_clean
                elif title_clean.lower() in name.lower():
                    channel_label = name
                else:
                    channel_label = f"{name} - {title_clean}"

                found.append((channel_label, url))
    except Exception:
        pass
    return found

def get_stremio_streams():
    tasks = []
    clean_base = ADDON_BASE.replace("/manifest.json", "").rstrip("/")
    try:
        print(f"Connecting to manifest: {clean_base}...")
        manifest = requests.get(f"{clean_base}/manifest.json", headers=HEADERS, timeout=10).json()
        catalogs = manifest.get("catalogs", [])
        
        for cat in catalogs:
            cat_type = cat.get("type")
            cat_id = cat.get("id")
            cat_name = cat.get("name", cat_id)
            
            if is_excluded(f"{cat_name} {cat_id}"):
                print(f"Skipping excluded catalog: {cat_name}")
                continue

            catalog_url = f"{clean_base}/catalog/{cat_type}/{cat_id}.json"
            print(f"Fetching catalog: {cat_name}...")
            try:
                cat_res = requests.get(catalog_url, headers=HEADERS, timeout=10).json()
                metas = cat_res.get("metas", [])
                for meta in metas:
                    item_id = meta.get("id")
                    name = meta.get("name", "Unknown Channel").strip()
                    tasks.append((cat_type, item_id, name, cat_name))
            except Exception as e:
                print(f"Failed catalog fetch for {cat_id}: {e}")
    except Exception as e:
        print(f"Error connecting to source {clean_base}: {e}")

    print(f"\nConcurrently extracting channels using {MAX_WORKERS} threads...")
    streams_found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(process_meta_task, tasks)
        for stream_list in results:
            streams_found.extend(stream_list)

    return streams_found

def main():
    print("Starting Nuvio Stremio channel extraction...")
    valid_entries = get_stremio_streams()
    
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
            
    print(f"Done! Saved {len(unique_entries)} clean channels to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
