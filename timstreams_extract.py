import requests
import time
import re

BASE_URLS = [
    "https://stra.viaplus.site",
    "https://api.timstreams.site"
]
OUTPUT_FILE = "timstreams.m3u"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://timstreams.st/live-tv"
}

def extract_live_tv():
    base_url = None
    manifest = None
    for url in BASE_URLS:
        try:
            res = requests.get(f"{url}/manifest.json", headers=HEADERS, timeout=10)
            if res.status_code == 200:
                manifest = res.json()
                base_url = url
                break
        except Exception:
            continue

    if not base_url or not manifest:
        print("Failed to reach Timstreams API.")
        return

    catalogs = manifest.get('catalogs', [])
    live_tv_catalogs = [
        c for c in catalogs 
        if 'tv' in c.get('type', '').lower() or 'live' in c.get('id', '').lower() or 'tv' in c.get('id', '').lower()
    ]

    if not live_tv_catalogs:
        live_tv_catalogs = catalogs

    channel_index = 1
    live_counter = 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for catalog in live_tv_catalogs:
            cat_type = catalog.get('type', 'tv')
            cat_id = catalog.get('id', '')

            catalog_url = f"{base_url}/catalog/{cat_type}/{cat_id}.json"
            try:
                catalog_data = requests.get(catalog_url, headers=HEADERS, timeout=10).json()
            except Exception:
                continue

            metas = catalog_data.get('metas', [])
            for item in metas:
                item_id = item.get('id')
                raw_name = item.get('name', f'Live TV {channel_index}')

                clean_name = raw_name.replace('-', ' ').replace('_', ' ').replace('.', ' ')
                formatted_title = ' '.join(word.capitalize() for word in clean_name.split())

                if 'M3u8' in formatted_title:
                    formatted_title = re.sub(r'(Live\s)?M3u8(\sStream)?', f'Live {live_counter}', formatted_title)
                    live_counter += 1

                stream_url = f"{base_url}/stream/{cat_type}/{item_id}.json"
                try:
                    stream_data = requests.get(stream_url, headers=HEADERS, timeout=10).json()
                    streams = stream_data.get('streams', [])
                    for stream in streams:
                        link = stream.get('url', '') if isinstance(stream, dict) else ''

                        if link and "google.com" not in link:
                            f.write(f"#EXTINF:-1,{formatted_title}\n")
                            f.write(f"{link}\n")
                            channel_index += 1
                except Exception:
                    continue
                time.sleep(0.05)

if __name__ == "__main__":
    extract_live_tv()
