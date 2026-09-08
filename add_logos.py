import re
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from difflib import get_close_matches

LYNGSAT_BASE = "https://www.lyngsat.com/logo/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
MAX_WORKERS = 10

def fetch_letter_logos(char):
    logo_dict = {}
    url = f"{LYNGSAT_BASE}tvchannel/{char}.html"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            for td in soup.find_all('td'):
                img = td.find('img')
                text = td.get_text(strip=True)
                if img and img.get('src'):
                    src = img['src']
                    full_url = requests.compat.urljoin(url, src)
                    clean_name = re.sub(r'[^\w\s]', '', text).strip().lower()
                    if clean_name and '/logo/' in full_url:
                        logo_dict[clean_name] = full_url
    except Exception:
        pass
    return logo_dict

def build_lyngsat_database():
    print("Crawling LyngSat logo directory...")
    letters = [chr(i) for i in range(ord('A'), ord('Z')+1)] + ['0-9']
    logo_map = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(fetch_letter_logos, letters)
        for d in results:
            logo_map.update(d)
            
    print(f"Successfully indexed {len(logo_map)} total logos from LyngSat.")
    return logo_map

def enrich_playlist(m3u_file, logo_map):
    try:
        with open(m3u_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Skipping {m3u_file} (file not found)")
        return

    updated_lines = []
    added_count = 0

    for line in lines:
        if line.startswith("#EXTINF:"):
            parts = line.split(",", 1)
            meta = parts[0]
            name = parts[1].strip() if len(parts) > 1 else ""
            
            # Inject logo if not already present
            if 'tvg-logo=' not in meta and name:
                clean_name = re.sub(r'[^\w\s]', '', name).strip().lower()
                logo_url = logo_map.get(clean_name)
                
                # Fuzzy fallback if exact match fails
                if not logo_url:
                    matches = get_close_matches(clean_name, logo_map.keys(), n=1, cutoff=0.75)
                    if matches:
                        logo_url = logo_map[matches[0]]
                        
                if logo_url:
                    meta = meta.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{logo_url}"')
                    added_count += 1
            
            updated_lines.append(f"{meta},{name}\n" if len(parts) > 1 else line)
        else:
            updated_lines.append(line)

    with open(m3u_file, 'w', encoding='utf-8') as f:
        f.writelines(updated_lines)

    print(f"Updated {m3u_file}: Injected TV logos into {added_count} channels.")

def main():
    logo_map = build_lyngsat_database()
    enrich_playlist("stremio_playlist.m3u", logo_map)
    enrich_playlist("playlist.m3u", logo_map)

if __name__ == "__main__":
    main()
