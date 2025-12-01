

import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import time



async def fetch_and_save(session, sem, base, suffix, url, log_callback, stats, headers, retries=3, rate_limit=0.5):
    # Only log successful fetches/saves, not every attempt
    attempt = 0
    while attempt < retries:
        try:
            async with sem:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        raise aiohttp.ClientError(f"Status {response.status}")
                    text = await response.text()
                    soup = BeautifulSoup(text, "html.parser")

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

                    # Structured data: JSON-LD (schema.org)
                    for script in soup.find_all('script', type='application/ld+json'):
                        try:
                            import json
                            data = json.loads(script.string)
                            lines.append(f"[json-ld] {json.dumps(data, ensure_ascii=False, indent=2)}")
                        except Exception as e:
                            pass

                    # h1-h6 and p tags
                    all_text = []
                    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                        text = tag.get_text(strip=True)
                        if text:
                            lines.append(f"[{tag.name}] {text}")
                            all_text.append(text)

                    # Keyword extraction (simple)
                    try:
                        from collections import Counter
                        import re
                        words = re.findall(r'\b\w{4,}\b', ' '.join(all_text).lower())
                        common = Counter(words).most_common(10)
                        if common:
                            lines.append("[keywords] " + ', '.join([w for w, _ in common]))
                    except Exception:
                        pass

                    # Sentiment analysis (optional, simple)
                    try:
                        from textblob import TextBlob
                        blob = TextBlob(' '.join(all_text))
                        sentiment = blob.sentiment
                        lines.append(f"[sentiment] polarity={sentiment.polarity:.2f}, subjectivity={sentiment.subjectivity:.2f}")
                    except Exception:
                        pass
                    if not lines:
                        stats["not_useful"] += 1
                        return
                    filename = f"{base}-{suffix.lstrip('.')}.txt"
                    folder = base
                    os.makedirs(folder, exist_ok=True)
                    filepath = os.path.join(folder, filename)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))
                    msg = f"Saved important content to {filepath}"
                    print(msg)
                    if log_callback:
                        log_callback(msg)
                    stats["saved"] += 1
                    return
        except Exception as e:
            attempt += 1
            if attempt >= retries:
                stats["failed"] += 1
            else:
                await asyncio.sleep(1)  # Wait before retry
        await asyncio.sleep(rate_limit)

async def save_html_files_async(base, domains, log_callback=None, max_concurrent=10, rate_limit=0.5, retries=3):
    """
    Async version: For each (suffix, url) in domains, fetch HTML and save important elements to base/base-suffix.txt.
    Uses aiohttp for efficiency. Supports rate limiting and retries.
    Returns a dict with scrape statistics for reporting.
    """
    stats = {
        "total_pinged": len(domains),
        "saved": 0,
        "failed": 0,
        "not_useful": 0
    }
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DomainScraper/1.0)"}
    sem = asyncio.Semaphore(max_concurrent)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_save(session, sem, base, suffix, url, log_callback, stats, headers, retries, rate_limit) for suffix, url in domains]
        await asyncio.gather(*tasks)
    return stats

# Synchronous wrapper for GUI compatibility
def save_html_files(base, domains, log_callback=None, max_concurrent=10, rate_limit=0.5, retries=3):
    return asyncio.run(save_html_files_async(base, domains, log_callback, max_concurrent, rate_limit, retries))