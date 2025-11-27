import os
import requests
from bs4 import BeautifulSoup

def save_html_files(base, domains, log_callback=None):
    """
    For each (suffix, url) in domains, fetch HTML and save important elements to base/base-suffix.txt.
    Returns a dict with scrape statistics for reporting.
    """
    folder = base
    os.makedirs(folder, exist_ok=True)

    stats = {
        "total_pinged": len(domains),
        "saved": 0,
        "failed": 0,
        "not_useful": 0
    }

    for suffix, url in domains:
        msg = f"Fetching HTML from: {url}"
        print(msg)
        if log_callback:
            log_callback(msg)
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            lines = []

            # Title
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            if title:
                lines.append(f"[title] {title}")

            # Meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                lines.append(f"[meta description] {meta_desc['content'].strip()}")

            # Open Graph description
            og_desc = soup.find("meta", attrs={"property": "og:description"})
            if og_desc and og_desc.get("content"):
                lines.append(f"[og:description] {og_desc['content'].strip()}")

            # h1-h6 and p tags
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                text = tag.get_text(strip=True)
                if text:
                    lines.append(f"[{tag.name}] {text}")

            if not lines:
                msg = f"No important content found for {url}, skipping file."
                print(msg)
                if log_callback:
                    log_callback(msg)
                stats["not_useful"] += 1
                continue

            filename = f"{base}-{suffix.lstrip('.')}.txt"
            filepath = os.path.join(folder, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            msg = f"Saved important content to {filepath}"
            print(msg)
            if log_callback:
                log_callback(msg)
            stats["saved"] += 1

        except Exception as e:
            msg = f"Failed to fetch or save {url}: {e}"
            print(msg)
            if log_callback:
                log_callback(msg)
            stats["failed"] += 1

    return stats
