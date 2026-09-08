import re
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from difflib import get_close_matches

IPTV_ORG_API = "https://iptv-org.github.io/api/channels.json"
LYNGSAT_BASE = "https://www.lyngsat.com/logo/"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def clean_channel_name(raw_name):
    if not raw_name:
        return ""
    # Remove emojis
    text = re.sub(r'[\U00010000-\U0010ffff\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', '', raw_name)
    # Remove text in brackets like [Live], (UK), (Backup)
    text = re.sub(r'\[.*?\]|\(.*?\)', '', text)
    # Remove common IPTV clutter & resolutions
    text = re.sub(r'\b(4k|1080p|720p|fhd|hd|sd|hevc|vip|raw|backup|live|stream|tv|us|uk|ca)\b', '', text, flags=re.IGNORECASE)
    # Keep only letters, numbers, and spaces
    text = re.sub(r'[^\w\s]', '', text)
    return ' '.join(text.split()).lower()

def build_iptv_org_database():
    print("Loading IPTV-Org global channel & logo database...")
    logo_map = {}
    try:
        res = requests.get(IPTV_ORG_API, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            channels = res.json()
            for ch in channels:
                logo = ch.get('logo')
                if not logo:
                    continue
                
                # Index main name
                name = ch.get('name', '')
                clean_n = clean_channel_name(name)
                if clean_n and clean_n not in logo_map:
                    logo_map[clean_n] = logo
                
                # Index all alternative name aliases
                for alt in ch.get('alt_names', []):
                    clean_alt = clean_channel_name(alt)
                    if clean_alt and clean_alt not in logo_map:
                        logo_map[clean_alt] = logo
                        
        print(f"Indexed {len(logo_map)} clean channel names & aliases from IPTV-Org.")
    except Exception as e:
        print(f"Error fetching IPTV-Org database: {e}")
    return logo_map

def fetch_lyngsat_letter(char):
    dict_out = {}
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
                    clean_n = clean_channel_name(text)
                    if clean_n and '/logo/' in full_url:
                        dict_out[clean_n] = full_url
    except Exception:
        pass
    return dict_out

def build_lyngsat_database():
    print("Fetching supplemental logos from LyngSat...")
    letters = [chr(i) for i in range(ord('A'), ord('Z')+1)] + ['0-9']
    lyngsat_map = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_lyngsat_letter, letters)
        for d in results:
            lyngsat_map.update(d)
    return lyngsat_map

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
            
            # Clean up existing logo if broken or empty
            if 'tvg-logo=""' in meta:
                meta = meta.replace('tvg-logo=""', '')

            if 'tvg-logo=' not in meta and name:
                cleaned = clean_channel_name(name)
                logo_url = logo_map.get(cleaned)
                
                # Fallback: Fuzzy matching against indexed names
                if not logo_url and cleaned:
                    matches = get_close_matches(cleaned, logo_map.keys(), n=1, cutoff=0.70)
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
    # 1. Primary DB: IPTV-Org
    logo_map = build_iptv_org_database()
    
    # 2. Secondary DB: LyngSat
    lyngsat_map = build_lyngsat_database()
    for k, v in lyngsat_map.items():
        if k not in logo_map:
            logo_map[k] = v

    # 3. Enrich both M3U files
    enrich_playlist("stremio_playlist.m3u", logo_map)
    enrich_playlist("playlist.m3u", logo_map)

if __name__ == "__main__":
    main()
