import requests
import concurrent.futures

SOURCE_URLS = [
    "https://tinyurl.com/livem3u8",
    "http://m3u4u.com/m3u/p87vnrjwd2b6mrvrn41j",
    "http://m3u4u.com/m3u/4z2xnjg1zkf3wx8pyv15"
]
OUTPUT_FILE = "playlist.m3u"
TIMEOUT = 4
MAX_WORKERS = 50

def fetch_playlist(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def parse_m3u(content):
    lines = content.splitlines()
    entries = []
    current_meta = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            current_meta = line
        elif line and not line.startswith("#"):
            if current_meta:
                entries.append((current_meta, line))
                current_meta = None
    return entries

def validate_stream(entry):
    meta, url = entry
    try:
        r = requests.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True, headers={'User-Agent': 'VLC'})
        if r.status_code in (200, 206, 301, 302):
            r.close()
            return (meta, url)
    except Exception:
        pass
    return None

def main():
    all_entries = []
    for url in SOURCE_URLS:
        print(f"Fetching playlist from {url}...")
        content = fetch_playlist(url)
        if content:
            entries = parse_m3u(content)
            print(f"Found {len(entries)} streams from {url}.")
            all_entries.extend(entries)

    print(f"Validating {len(all_entries)} streams using {MAX_WORKERS} threads...")
    
    valid_entries = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(validate_stream, all_entries)
        for result in results:
            if result:
                valid_entries.append(result)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for meta, url in valid_entries:
            f.write(f"{meta}\n{url}\n")
            
    print(f"Done! Saved {len(valid_entries)} working streams to {OUTPUT_FILE} in seconds.")

if __name__ == "__main__":
    main()
