import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_all_tlds():
    """
    Returns a list of all active top-level domains (TLDs) fetched from a public source.
    """
    url = "https://raw.githubusercontent.com/incognico/list-of-top-level-domains/master/tlds.csv"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        tlds = [line.split(",")[0].strip() for line in lines if line.strip() and not line.startswith("#")]
        return tlds
    except requests.RequestException as e:
        print("Error fetching TLD list:", e)
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
