import requests
import time
import re

BASE_URL = "https://sports.highfly.dev"
MANIFEST_URL = f"{BASE_URL}/manifest.json"
OUTPUT_FILE = "playlist.m3u"

def extract_all_m3u_playlist():
    print("Fetching manifest and extracting formatted titles...")
    try:
        manifest = requests.get(MANIFEST_URL).json()
    except Exception as e:
        print(f"Failed to fetch manifest: {e}")
        return

    catalogs = manifest.get('catalogs', [])
    channel_index = 1
    live_counter = 1  # Sequential counter for M3U8 replacements

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
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
                raw_name = item.get('name', f'Stream {channel_index}')

                # Replace -, _, and . with spaces, then capitalize every word
                clean_name = raw_name.replace('-', ' ').replace('_', ' ').replace('.', ' ')
                formatted_title = ' '.join(word.capitalize() for word in clean_name.split())

                # Replace variations of "Live M3u8" or "M3u8 Stream" with "Live 1", "Live 2"
                if 'M3u8' in formatted_title:
                    formatted_title = re.sub(r'(Live\s)?M3u8(\sStream)?', f'Live {live_counter}', formatted_title)
                    live_counter += 1

                stream_url = f"{BASE_URL}/stream/{cat_type}/{item_id}.json"
                try:
                    stream_data = requests.get(stream_url).json()
                    streams = stream_data.get('streams', [])
                    for stream in streams:
                        link = stream.get('url', '')

                        if link and "google.com" not in link:
                            f.write(f"#EXTINF:-1,{formatted_title}\n")
                            f.write(f"{link}\n")
                            channel_index += 1
                except Exception:
                    continue
                time.sleep(0.05)

    print(f"\nDone! Saved {channel_index - 1} channels with formatted titles to {OUTPUT_FILE}")

if __name__ == "__main__":
    extract_all_m3u_playlist()
