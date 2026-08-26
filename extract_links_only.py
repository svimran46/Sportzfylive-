import requests
import time

BASE_URL = "https://sports.highfly.dev"
MANIFEST_URL = f"{BASE_URL}/manifest.json"
OUTPUT_FILE = "m3u8_only.txt"

def extract_urls_only():
    print("Fetching manifest and extracting links...")
    try:
        manifest = requests.get(MANIFEST_URL).json()
    except Exception as e:
        print(f"Failed to fetch manifest: {e}")
        return

    catalogs = manifest.get('catalogs', [])
    count = 0

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for catalog in catalogs:
            cat_type = catalog.get('type')
            cat_id = catalog.get('id')
            catalog_url = f"{BASE_URL}/catalog/{cat_type}/{cat_id}.json"

            try:
                catalog_data = requests.get(catalog_url).json()
            except Exception:
                continue

            metas = catalog_data.get('metas', [])
            for item in metas:
                item_id = item.get('id')
                stream_url = f"{BASE_URL}/stream/{cat_type}/{item_id}.json"
                try:
                    stream_data = requests.get(stream_url).json()
                    streams = stream_data.get('streams', [])
                    for stream in streams:
                        link = stream.get('url', '')
                        if link:
                            f.write(f"{link}\n")
                            count += 1
                except Exception:
                    continue
                time.sleep(0.05)

    print(f"\nDone! Saved {count} direct stream URLs to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_urls_only()

