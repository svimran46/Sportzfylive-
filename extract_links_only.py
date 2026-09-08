import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

PLAYLIST_URL = "https://tinyurl.com/livem3u8"
OUTPUT_FILE = "playlist.m3u"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def test_stream(item):
    title, url = item
    try:
        with requests.get(url, headers=HEADERS, timeout=5, allow_redirects=True, stream=True) as res:
            if res.status_code in [200, 206]:
                return (title, url, True)
    except Exception:
        pass
    return (title, url, False)

def main():
    print(f"Downloading external playlist from {PLAYLIST_URL}...")
    try:
        res = requests.get(PLAYLIST_URL, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            print(f"Failed to download playlist. Status code: {res.status_code}")
            return
        content = res.text
    except Exception as e:
        print(f"Error downloading playlist: {e}")
        return

    lines = content.splitlines()
    channels = []
    current_title = "Live Stream"
    
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            if "," in line:
                current_title = line.split(",", 1)[1]
        elif line and not line.startswith("#"):
            url = line
            channels.append((current_title, url))
            current_title = "Live Stream"

    print(f"Parsed {len(channels)} total links. Testing in parallel (will finish in under a minute)...")
    
    working_channels = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {executor.submit(test_stream, ch): ch for ch in channels}
        for future in as_completed(futures):
            title, url, is_working = future.result()
            if is_working:
                print(f"✔ [WORKING] {title}")
                working_channels.append((title, url))
            else:
                print(f"✖ [DEAD] {title}")

    print(f"\nTotal working streams found: {len(working_channels)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, link in working_channels:
            f.write(f"#EXTINF:-1,{title}\n")
            f.write(f"{link}\n")
    print(f"Successfully saved to {OUTPUT_FILE}!")

if __name__ == "__main__":
    main()
