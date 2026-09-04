import requests
import time
import re

MANIFEST_URL = "https://premium.highfly.dev/352560f7-07b9-476f-8c12-4f4b609df881/manifest.json"
BASE_URL = MANIFEST_URL.rsplit("/manifest.json", 1)[0]
OUTPUT_FILE = "playlist.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def clean_title(raw_name, live_counter):
    if not raw_name:
        return f"Live {live_counter}", live_counter + 1
    
    clean_name = raw_name.replace('-', ' ').replace('_', ' ').replace('.', ' ')
    formatted_title = ' '.join(word.capitalize() for word in clean_name.split())

    if 'M3u8' in formatted_title or not formatted_title.strip():
        formatted_title = f"Live {live_counter}"
        live_counter += 1

    return formatted_title, live_counter

def extract_premium_highfly():
    print(f"Fetching manifest from {MANIFEST_URL}...")
    try:
        res = requests.get(MANIFEST_URL, headers=HEADERS, timeout=12)
        if res.status_code != 200:
            print(f"Failed to fetch manifest. Status code: {res.status_code}")
            return
        manifest = res.json()
    except Exception as e:
        print(f"Error loading manifest: {e}")
        return

    catalogs = manifest.get('catalogs', [])
    if not catalogs:
        print("No catalogs found in manifest.")
        return

    channels = []
    live_counter = 1

    for catalog in catalogs:
        cat_type = catalog.get('type')
        cat_id = catalog.get('id')
        
        catalog_url = f"{BASE_URL}/catalog/{cat_type}/{cat_id}.json"
        print(f"Fetching catalog: {cat_id} ({cat_type})...")

        try:
            cat_res = requests.get(catalog_url, headers=HEADERS, timeout=12)
            if cat_res.status_code != 200:
                continue
            cat_data = cat_res.json()
        except Exception:
            continue

        metas = cat_data.get('metas', [])
        print(f"Found {len(metas)} items in catalog.")

        for item in metas:
            item_id = item.get('id')
            raw_title = item.get('name', '')
            
            title, live_counter = clean_title(raw_title, live_counter)

            stream_url = f"{BASE_URL}/stream/{cat_type}/{item_id}.json"
            try:
                stream_res = requests.get(stream_url, headers=HEADERS, timeout=10)
                if stream_res.status_code != 200:
                    continue
                
                stream_data = stream_res.json()
                streams = stream_data.get('streams', [])
                
                for stream in streams:
                    link = ""
                    if isinstance(stream, dict):
                        link = stream.get('url') or stream.get('externalUrl') or ""
                    
                    if link:
                        channels.append((title, link))
            except Exception:
                continue
            
            time.sleep(0.05)

    print(f"\nExtracted {len(channels)} stream links.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in channels:
            f.write(f"#EXTINF:-1,{title}\n")
            f.write(f"{link}\n")

    print(f"Successfully generated {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_premium_highfly()
