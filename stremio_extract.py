import requests

ADDON_BASE = "https://live-addon.vercel.app"
OUTPUT_FILE = "stremio_playlist.m3u"
KEYWORDS = ["today", "live", "football"]

def get_stremio_streams():
    streams_found = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        manifest_res = requests.get(f"{ADDON_BASE}/manifest.json", headers=headers, timeout=10)
        manifest = manifest_res.json()
        catalogs = manifest.get("catalogs", [])
        
        for cat in catalogs:
            cat_type = cat.get("type")
            cat_id = cat.get("id")
            
            catalog_url = f"{ADDON_BASE}/catalog/{cat_type}/{cat_id}.json"
            print(f"Fetching catalog: {catalog_url}")
            try:
                catalog_res = requests.get(catalog_url, headers=headers, timeout=10).json()
                metas = catalog_res.get("metas", [])
            except Exception as e:
                print(f"Failed catalog fetch for {cat_id}: {e}")
                continue
            
            for meta in metas:
                item_id = meta.get("id")
                name = meta.get("name", "Unknown Channel")
                
                stream_url = f"{ADDON_BASE}/stream/{cat_type}/{item_id}.json"
                try:
                    stream_res = requests.get(stream_url, headers=headers, timeout=5).json()
                    streams = stream_res.get("streams", [])
                    
                    for stream in streams:
                        title = stream.get("title", "")
                        url = stream.get("url")
                        
                        # Search channel name, catalog ID, and stream title
                        full_text = f"{name} {cat_id} {title}".lower()
                        
                        # Only keep if it contains "today", "live", or "football"
                        if url and any(kw in full_text for kw in KEYWORDS):
                            stream_name = f"{name} - {title}".strip(" -") if title else name
                            streams_found.append((stream_name, url))
                except Exception as e:
                    print(f"Failed stream fetch for {name}: {e}")
                        
    except Exception as e:
        print(f"Error parsing Stremio API: {e}")
        
    return streams_found

def main():
    print("Extracting streams filtered for 'Today', 'Live', and 'Football'...")
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
            
    print(f"Done! Saved {len(unique_entries)} matching streams to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
