
import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import time
import json



async def fetch_and_save(session, sem, base, suffix, url, log_callback, stats, headers, formats, retries=3, rate_limit=0.5):
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

                    # Prepare data for all formats
                    folder = base
                    os.makedirs(folder, exist_ok=True)
                    base_filename = f"{base}-{suffix.lstrip('.')}"

                    # Extracted data for JSON
                    title = soup.title.string.strip() if soup.title and soup.title.string else ""
                    meta_desc = soup.find("meta", attrs={"name": "description"})
                    meta_desc_val = meta_desc['content'].strip() if meta_desc and meta_desc.get("content") else ""
                    og_desc = soup.find("meta", attrs={"property": "og:description"})
                    og_desc_val = og_desc['content'].strip() if og_desc and og_desc.get("content") else ""
                    json_ld = []
                    for script in soup.find_all('script', type='application/ld+json'):
                        try:
                            data = json.loads(script.string)
                            json_ld.append(data)
                        except Exception:
                            pass
                    all_text = []
                    h_tags = []
                    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                        t = tag.get_text(strip=True)
                        if t:
                            h_tags.append({"tag": tag.name, "text": t})
                            all_text.append(t)
                    # Keyword extraction
                    keywords = []
                    try:
                        from collections import Counter
                        import re
                        words = re.findall(r'\b\w{4,}\b', ' '.join(all_text).lower())
                        common = Counter(words).most_common(10)
                        keywords = [w for w, _ in common]
                    except Exception:
                        pass
                    # Sentiment analysis
                    sentiment = None
                    try:
                        from textblob import TextBlob
                        blob = TextBlob(' '.join(all_text))
                        sentiment = {
                            "polarity": round(blob.sentiment.polarity, 2),
                            "subjectivity": round(blob.sentiment.subjectivity, 2)
                        }
                    except Exception:
                        pass

                    # Save TXT (summary)
                    if 'txt' in formats:
                        lines = []
                        if title:
                            lines.append(f"[title] {title}")
                        if meta_desc_val:
                            lines.append(f"[meta description] {meta_desc_val}")
                        if og_desc_val:
                            lines.append(f"[og:description] {og_desc_val}")
                        for item in json_ld:
                            lines.append(f"[json-ld] {json.dumps(item, ensure_ascii=False, indent=2)}")
                        for h in h_tags:
                            lines.append(f"[{h['tag']}] {h['text']}")
                        if keywords:
                            lines.append("[keywords] " + ', '.join(keywords))
                        if sentiment:
                            lines.append(f"[sentiment] polarity={sentiment['polarity']:.2f}, subjectivity={sentiment['subjectivity']:.2f}")
                        if not lines:
                            stats["not_useful"] += 1
                        else:
                            txt_path = os.path.join(folder, base_filename + ".txt")
                            with open(txt_path, "w", encoding="utf-8") as f:
                                f.write("\n".join(lines))
                            msg = f"Saved summary TXT to {txt_path}"
                            if log_callback:
                                log_callback(msg)
                            stats["saved"] += 1

                    # Save JSON (full structured data)
                    if 'json' in formats:
                        data = {
                            "url": url,
                            "title": title,
                            "meta_description": meta_desc_val,
                            "og_description": og_desc_val,
                            "json_ld": json_ld,
                            "tags": h_tags,
                            "keywords": keywords,
                            "sentiment": sentiment,
                            "raw_html": text
                        }
                        json_path = os.path.join(folder, base_filename + ".json")
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        msg = f"Saved JSON to {json_path}"
                        if log_callback:
                            log_callback(msg)
                        stats["saved"] += 1

                    # Save HTML (raw HTML)
                    if 'html' in formats:
                        html_path = os.path.join(folder, base_filename + ".html")
                        with open(html_path, "w", encoding="utf-8") as f:
                            f.write(text)
                        msg = f"Saved raw HTML to {html_path}"
                        if log_callback:
                            log_callback(msg)
                        stats["saved"] += 1

                    # If nothing was saved, count as not useful
                    if not any(fmt in formats for fmt in ['txt', 'json', 'html']):
                        stats["not_useful"] += 1
                    return
        except Exception as e:
            attempt += 1
            if attempt >= retries:
                stats["failed"] += 1
            else:
                await asyncio.sleep(1)  # Wait before retry
        await asyncio.sleep(rate_limit)

async def save_html_files_async(base, domains, formats=None, log_callback=None, max_concurrent=10, rate_limit=0.5, retries=3):
    """
    Async version: For each (suffix, url) in domains, fetch HTML and save important elements to base/base-suffix.txt.
    Uses aiohttp for efficiency. Supports rate limiting and retries.
    Returns a dict with scrape statistics for reporting.
    """
    if formats is None:
        formats = ['txt']
    stats = {
        "total_pinged": len(domains),
        "saved": 0,
        "failed": 0,
        "not_useful": 0
    }
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DomainScraper/1.0)"}
    sem = asyncio.Semaphore(max_concurrent)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_save(session, sem, base, suffix, url, log_callback, stats, headers, formats, retries, rate_limit) for suffix, url in domains]
        await asyncio.gather(*tasks)
    return stats

# Synchronous wrapper for GUI compatibility
def save_html_files(base, domains, formats=None, log_callback=None, max_concurrent=10, rate_limit=0.5, retries=3):
    return asyncio.run(save_html_files_async(base, domains, formats, log_callback, max_concurrent, rate_limit, retries))