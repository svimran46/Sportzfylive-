import requests
import time
import re
import string

MANIFEST_URL = "https://premium.highfly.dev/352560f7-07b9-476f-8c12-4f4b609df881/manifest.json"
BASE_URL = MANIFEST_URL.rsplit("/manifest.json", 1)[0]
OUTPUT_FILE = "playlist.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json"
}

def clean_title(item, live_counter):
    raw_name = item.get('name', '')
    item_id = item.get('id', '')

    # Fallback to ID if name is missing or is just a raw m3u8 string
    if not raw_name or 'm3u8' in str(raw_name).lower() or str(raw_name).lower() == 'none':
        raw_name = item_id
        # Clean Stremio artifacts from ID
        raw_name = re.sub(r'^streamed_', '', raw_name)
        raw_name = re.sub(r'_[0-9]+$', '', raw_name)

    if not raw_name:
        return f"Live Stream {live_counter}", live_counter + 1

    # Remove requested symbols (-, _, .) plus pipes and colons
    clean_name = re.sub(r'[-_.|:]', ' ', raw_name)
    
    # Remove ugly stream tags like (fhd) and RAW
    clean_name = re.sub(r'\b(?:fhd|raw)\b', '', clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r'[()]', '', clean_name)

    # Convert to strict Title Case and clear extra spaces
    formatted_title = string.capwords(clean_name.strip())

    if not formatted_title:
        return f"Live Stream {live_counter}", live_counter + 1

    return formatted_title, live_counter

def extract_premium_highfly():
    print(f"Fetching manifest from {MANIFEST_URL}...")
    try:
        res = requests.get(MANIFEST_URL, headers=HEADERS, timeout=12)
        if res.status_code != 200:
            return
        manifest = res.json()
    except Exception as e:
        print(f"Error loading manifest: {e}")
        return

    catalogs = manifest.get('catalogs', [])
    channels = []
    live_counter = 1

    for catalog in catalogs:
        cat_type = catalog.get('type')
        cat_id = catalog.get('id')
        catalog_url = f"{BASE_URL}/catalog/{cat_type}/{cat_id}.json"

        try:
            cat_res = requests.get(catalog_url, headers=HEADERS, timeout=12)
            if cat_res.status_code != 200:
                continue
            cat_data = cat_res.json()
        except Exception:
            continue

        for item in cat_data.get('metas', []):
            title, live_counter = clean_title(item, live_counter)
            item_id = item.get('id')
            stream_url = f"{BASE_URL}/stream/{cat_type}/{item_id}.json"
            
            try:
                stream_res = requests.get(stream_url, headers=HEADERS, timeout=10)
                if stream_res.status_code != 200:
                    continue
                
                for stream in stream_res.json().get('streams', []):
                    link = stream.get('url') or stream.get('externalUrl') or ""
                    
                    # Filter out useless Google placeholders
                    if link and "google.com" not in link:
                        channels.append((title, link))
            except Exception:
                continue
            
            time.sleep(0.05)

    print(f"\nExtracted {len(channels)} valid stream links.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in channels:
            f.write(f"#EXTINF:-1,{title}\n")
            f.write(f"{link}\n")

if __name__ == "__main__":
    extract_premium_highfly()
