import requests
import time

BASE_URL = "https://sports.highfly.dev"
MANIFEST_URL = f"{BASE_URL}/manifest.json"
OUTPUT_FILE = "playlist.m3u"

def extract_all_m3u_playlist():
    print("Fetching manifest and generating complete M3U playlist...")
    try:
        manifest = requests.get(MANIFEST_URL).json()
    except Exception as e:
        print(f"Failed to fetch manifest: {e}")
        return

    catalogs = manifest.get('catalogs', [])
    channel_index = 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # Mandatory M3U header
        f.write("#EXTM3U\n")

        for catalog in catalogs:
            cat_type = catalog.get('type', '')
            cat_id = catalog.get('id', '')

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

                        # Strictly skip empty links and google.com placeholders
                        if link and "google.com" not in link:
                            f.write(f"#EXTINF:-1,CH{channel_index}\n")
                            f.write(f"{link}\n")
                            channel_index += 1
                except Exception:
                    continue
                time.sleep(0.05)

    print(f"\nDone! Saved {channel_index - 1} channels to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_all_m3u_playlist()
