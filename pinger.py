import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time

_TLD_CACHE_FILE = os.path.join(os.path.dirname(__file__), "tlds_cache.txt")
_TLD_CACHE_TTL = 60 * 60 * 24  # 1 day

def get_all_tlds():
    """
    Returns a list of all active top-level domains (TLDs), using a local cache if available and fresh.
    """
    url = "https://raw.githubusercontent.com/incognico/list-of-top-level-domains/master/tlds.csv"
    # Check cache
    if os.path.exists(_TLD_CACHE_FILE):
        mtime = os.path.getmtime(_TLD_CACHE_FILE)
        if time.time() - mtime < _TLD_CACHE_TTL:
            try:
                with open(_TLD_CACHE_FILE, "r", encoding="utf-8") as f:
                    tlds = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                return tlds
            except Exception as e:
                print("Error reading TLD cache:", e)
    # Download and cache
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        tlds = [line.split(",")[0].strip() for line in lines if line.strip() and not line.startswith("#")]
        try:
            with open(_TLD_CACHE_FILE, "w", encoding="utf-8") as f:
                for tld in tlds:
                    f.write(tld + "\n")
        except Exception as e:
            print("Error writing TLD cache:", e)
        return tlds
    except requests.RequestException as e:
        print("Error fetching TLD list:", e)
        # Try to use cache even if stale
        if os.path.exists(_TLD_CACHE_FILE):
            try:
                with open(_TLD_CACHE_FILE, "r", encoding="utf-8") as f:
                    tlds = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                return tlds
            except Exception as e:
                print("Error reading TLD cache:", e)
        return []

def ping_website(url, timeout=5):
    """
    Returns True if the given URL responds with HTTP 200, otherwise False.
    """
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False

def ping_domains(base, suffixes=None, timeout=5, max_workers=20):
    """
    Tries each suffix in `suffixes` for the given `base` domain name in parallel.
    If suffixes is None, fetches all TLDs using get_all_tlds().
    Returns a list of tuples (suffix, url) for all reachable domains.
    """
    if suffixes is None:
        suffixes = get_all_tlds()
        # Add a dot to each TLD if not already present
        suffixes = [s if s.startswith('.') else f'.{s}' for s in suffixes]

    reachable = []
    urls = [(suffix, f"https://{base}{suffix}") for suffix in suffixes]

    def check(suffix_url):
        suffix, url = suffix_url
        if ping_website(url, timeout=timeout):
            print(f"Domain {url} is reachable.")
            return (suffix, url)
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(check, su) for su in urls]
        for future in as_completed(futures):
            result = future.result()
            if result:
                reachable.append(result)

    if not reachable:
        print("No reachable domains found.")
    return reachable
