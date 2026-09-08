import requests
import re
import json
import os
import hashlib
import argparse
import time
from urllib.parse import urljoin

# --- Configuration ---
CHANNELS_API = "https://timst.cfd/api/channels"
EMBED_BASE = "https://epiembeds.online/embed/"
OUTPUT_PLAYLIST = "timstreams.st.m3u"
SUCCESS_CACHE = "successes.json"
FAILURES_LOG = "failures.json"
FAILURES_HTML_DIR = "failures/html"

# Standard headers to mimic a real browser and bypass basic bot-protection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://timst.cfd/"
}

# --- Regex Patterns ---
ARRAY_RE = re.compile(r'var\s+(_[a-z]{2}\d)\s*=\s*\[\s*([0-9,\s]+)\s*\]')
INT_ASSIGN_RE = re.compile(r'(_[a-z]{2}\d)\s*=\s*(\d{1,3})\s*[,;]')
# Broadened: Matches ANY quoted URL containing .m3u8 in the decoded text
M3U8_RE = re.compile(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', re.IGNORECASE)

def ensure_dirs():
    os.makedirs(FAILURES_HTML_DIR, exist_ok=True)

def fetch_channels():
    print("[*] Fetching channel list...")
    try:
        resp = requests.get(CHANNELS_API, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get('channels', data) if isinstance(data, dict) else data
    except Exception as e:
        print(f"[!] Failed to fetch channels API: {e}")
        return []

def resolve_embed_url(base_id):
    candidates = [base_id]
    for suf in ["usa", "uk", "ca", "au", "live", "hd", "fhd", "1"]:
        if not base_id.endswith(suf):
            candidates.append(f"{base_id}-{suf}")
            
    for cid in candidates:
        url = f"{EMBED_BASE}{cid}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
            if resp.status_code == 200 and len(resp.text) > 1000:
                return url, resp.text
            elif resp.status_code == 404:
                continue
        except requests.RequestException:
            continue
            
    return None, None

def decode_payload(arr_data, bx, ys):
    try:
        return "".join([chr(((_val ^ bx) - ys + 256) & 255) for _val in arr_data])
    except Exception:
        return None

def extract_m3u8_from_html(html):
    arrays = ARRAY_RE.findall(html)
    if not arrays:
        return None, "NO_ARRAY_MATCH"
        
    int_vars = INT_ASSIGN_RE.findall(html)
    keys = {k: int(v) for k, v in int_vars}
    
    for arr_name, arr_str in arrays:
        arr_data = [int(x.strip()) for x in arr_str.split(',') if x.strip().isdigit()]
        if len(arr_data) < 100:
            continue
            
        for k_name, k_val in keys.items():
            if k_name == arr_name: 
                continue
                
            for y_name, y_val in keys.items():
                if y_name == arr_name or y_name == k_name:
                    continue
                    
                decoded = decode_payload(arr_data, k_val, y_val)
                if not decoded:
                    continue
                    
                printable_ratio = sum(32 <= ord(c) <= 126 or c in '\n\r\t' for c in decoded) / len(decoded)
                if printable_ratio > 0.85 and "jwplayer" in decoded.lower():
                    m3u8_match = M3U8_RE.search(decoded)
                    if m3u8_match:
                        return m3u8_match.group(1), "SUCCESS"
                    else:
                        # Print a snippet of decoded text for debugging if it matched jwplayer but no m3u8
                        return None, f"NO_M3U8_IN_DECODE (Snippet: {decoded[:150].strip()})"
                        
    return None, "DECODE_FAILURE"

def write_playlist(successes):
    print(f"\n[*] Writing playlist to {OUTPUT_PLAYLIST}...")
    with open(OUTPUT_PLAYLIST, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for ch_name, data in successes.items():
            logo = data.get('logo', '')
            url = data.get('m3u8_url')
            if url:
                f.write(f'#EXTINF:-1 tvg-logo="{logo}",{ch_name}\n')
                f.write(f"{url}\n")
    print(f"[*] Playlist written with {len(successes)} channels.")

def main():
    parser = argparse.ArgumentParser(description="Timstreams IPTV Extractor")
    parser.add_argument("--only-failures", action="store_true", help="Re-run only channels from failures.json")
    args = parser.parse_args()
    
    ensure_dirs()
    
    successes = {}
    if os.path.exists(SUCCESS_CACHE):
        try:
            with open(SUCCESS_CACHE, 'r', encoding='utf-8') as f:
                successes = json.load(f)
        except Exception:
            successes = {}
    
    failures = []
    if os.path.exists(FAILURES_LOG):
        try:
            with open(FAILURES_LOG, 'r', encoding='utf-8') as f:
                failures = json.load(f)
        except Exception:
            failures = []
            
    channels_json = fetch_channels()
    if not channels_json:
        print("[!] No channels found or API error.")
        return
    
    if args.only_failures:
        failed_names = {f['channel_name'] for f in failures}
        channels_to_process = [ch for ch in channels_json if ch.get('name') in failed_names]
        print(f"[*] Resume mode: Processing {len(channels_to_process)} previously failed channels.")
    else:
        channels_to_process = channels_json
        failures = []
        print(f"[*] Full run: Processing {len(channels_to_process)} channels.")

    for i, ch in enumerate(channels_to_process, 1):
        ch_name = ch.get('name', f'Unknown_{i}')
        base_id = ch.get('id', ch_name.lower().replace(' ', '-'))
        logo = ch.get('logo', '')
        
        print(f"[{i}/{len(channels_to_process)}] {ch_name}...", end=" ")
        
        embed_url, html = resolve_embed_url(base_id)
        
        if not html:
            print("FAIL: HTTP_ERROR")
            failures.append({
                "channel_name": ch_name,
                "base_id": base_id,
                "final_url": f"{EMBED_BASE}{base_id}",
                "failure_category": "HTTP_ERROR"
            })
            continue
            
        html_sha1 = hashlib.sha1(html.encode('utf-8')).hexdigest()[:10]
        m3u8_url, status = extract_m3u8_from_html(html)
        
        if m3u8_url:
            print("SUCCESS")
            successes[ch_name] = {
                "m3u8_url": m3u8_url,
                "logo": logo,
                "html_sha1": html_sha1,
                "extracted_at": time.time()
            }
            failures = [f for f in failures if f['channel_name'] != ch_name]
        else:
            print(f"FAIL: {status}")
            html_path = os.path.join(FAILURES_HTML_DIR, f"{base_id}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
                
            failures.append({
                "channel_name": ch_name,
                "base_id": base_id,
                "embed_url": embed_url,
                "html_length": len(html),
                "html_sha1": html_sha1,
                "html_dump": html_path,
                "failure_category": status
            })
            
        if i % 10 == 0:
            with open(SUCCESS_CACHE, 'w', encoding='utf-8') as f: json.dump(successes, f, indent=2)
            with open(FAILURES_LOG, 'w', encoding='utf-8') as f: json.dump(failures, f, indent=2)

    with open(SUCCESS_CACHE, 'w', encoding='utf-8') as f: json.dump(successes, f, indent=2)
    with open(FAILURES_LOG, 'w', encoding='utf-8') as f: json.dump(failures, f, indent=2)
    
    write_playlist(successes)
    
    print("\n=== Failure Summary ===")
    from collections import Counter
    counts = Counter(f['failure_category'] for f in failures)
    for cat, count in counts.items():
        print(f"{cat:<25}: {count}")
        
    if failures:
        print(f"\n[*] Dumped HTML for failed channels in {FAILURES_HTML_DIR}/")
        print("[*] To retry only failed channels, run: python generate_final_playlist.py --only-failures")

if __name__ == "__main__":
    main()
