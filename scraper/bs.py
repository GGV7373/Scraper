import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import time
import json
import random
from collections import Counter
import re
from typing import List, Dict, Set, Tuple, Optional
from urllib.parse import urljoin, urlparse

# Simple user agent rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# Video file extensions and MIME types
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.m4v', '.3gp', '.ogv'}
VIDEO_MIME_TYPES = {
    'video/mp4', 'video/webm', 'video/avi', 'video/quicktime',
    'video/x-msvideo', 'video/x-flv', 'video/x-matroska',
    'video/3gpp', 'video/ogg'
}

class EnhancedContentExtractor:
    """Enhanced content extraction with support for videos and rich metadata"""

    @staticmethod
    def extract_metadata(soup: BeautifulSoup, url: str) -> Dict:
        """Extract comprehensive metadata from the page"""
        metadata = {
            'title': '',
            'meta_description': '',
            'og_title': '',
            'og_description': '',
            'og_image': '',
            'author': '',
            'published_date': '',
            'canonical_url': '',
            'schema_org': [],
            'videos': []
        }

        # Title
        if soup.title and soup.title.string:
            metadata['title'] = soup.title.string.strip()

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            metadata['meta_description'] = meta_desc['content'].strip()

        # Open Graph tags
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and og_title.get("content"):
            metadata['og_title'] = og_title['content'].strip()

        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            metadata['og_description'] = og_desc['content'].strip()

        og_image = soup.find("meta", attrs={"property": "og:image"})
        if og_image and og_image.get("content"):
            metadata['og_image'] = og_image['content'].strip()

        # Author
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            metadata['author'] = author_meta['content'].strip()

        # Published date
        for selector in ['meta[name="date"]', 'meta[property="article:published_time"]', 'time']:
            elem = soup.select_one(selector)
            if elem:
                content = elem.get('content') or elem.get('datetime') or elem.get_text()
                if content:
                    metadata['published_date'] = content.strip()
                    break

        # Canonical URL
        canonical = soup.find("link", attrs={"rel": "canonical"})
        if canonical and canonical.get("href"):
            metadata['canonical_url'] = canonical['href'].strip()

        # Video extraction
        metadata['videos'] = EnhancedContentExtractor.extract_videos(soup, url)

        return metadata

    @staticmethod
    def extract_videos(soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract video information from the page"""
        videos = []

        # Extract video tags
        for video_tag in soup.find_all('video'):
            video_info = {
                'type': 'video_element',
                'sources': [],
                'poster': '',
                'controls': video_tag.get('controls') is not None,
                'autoplay': video_tag.get('autoplay') is not None,
                'loop': video_tag.get('loop') is not None,
            }

            # Get poster image
            if video_tag.get('poster'):
                video_info['poster'] = urljoin(base_url, video_tag['poster'])

            # Get direct src
            if video_tag.get('src'):
                video_info['sources'].append({
                    'url': urljoin(base_url, video_tag['src']),
                    'type': video_tag.get('type', 'unknown')
                })

            # Get source elements
            for source in video_tag.find_all('source'):
                if source.get('src'):
                    video_info['sources'].append({
                        'url': urljoin(base_url, source['src']),
                        'type': source.get('type', 'unknown')
                    })

            if video_info['sources']:
                videos.append(video_info)

        # Extract iframe videos (YouTube, Vimeo, etc.)
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if any(platform in src.lower() for platform in ['youtube', 'vimeo', 'dailymotion', 'twitch']):
                videos.append({
                    'type': 'iframe_embed',
                    'url': src,
                    'platform': EnhancedContentExtractor._detect_video_platform(src),
                    'width': iframe.get('width'),
                    'height': iframe.get('height')
                })

        # Extract links to video files
        for link in soup.find_all('a', href=True):
            href = link['href']
            parsed_url = urlparse(href)
            extension = os.path.splitext(parsed_url.path)[1].lower()

            if extension in VIDEO_EXTENSIONS:
                videos.append({
                    'type': 'video_link',
                    'url': urljoin(base_url, href),
                    'extension': extension,
                    'text': link.get_text(strip=True)
                })

        return videos

    @staticmethod
    def _detect_video_platform(url: str) -> str:
        """Detect video platform from URL"""
        url_lower = url.lower()
        if 'youtube' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'vimeo' in url_lower:
            return 'vimeo'
        elif 'dailymotion' in url_lower:
            return 'dailymotion'
        elif 'twitch' in url_lower:
            return 'twitch'
        else:
            return 'unknown'

    @staticmethod
    def extract_content(soup: BeautifulSoup, tags_to_scrape: Optional[List[str]] = None) -> Dict:
        """Extract text content and structure from the page"""
        content = {
            'headings': [],
            'paragraphs': [],
            'text_content': '',
            'word_count': 0,
            'links': [],
            'images': []
        }

        # Default tags if none specified
        if not tags_to_scrape:
            tags_to_scrape = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'article', 'section']

        # Extract headings
        for level in range(1, 7):
            for h_tag in soup.find_all(f'h{level}'):
                text = h_tag.get_text(strip=True)
                if text:
                    content['headings'].append({
                        'level': level,
                        'text': text
                    })

        # Extract paragraphs and text
        all_text = []
        for tag_name in tags_to_scrape:
            for tag in soup.find_all(tag_name):
                text = tag.get_text(strip=True)
                if text:
                    all_text.append(text)
                    if tag_name == 'p':
                        content['paragraphs'].append(text)

        content['text_content'] = ' '.join(all_text)
        content['word_count'] = len(content['text_content'].split())

        # Extract links
        for link in soup.find_all('a', href=True):
            content['links'].append({
                'url': link['href'],
                'text': link.get_text(strip=True)
            })

        # Extract images
        for img in soup.find_all('img', src=True):
            content['images'].append({
                'src': img['src'],
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            })

        return content

async def fetch_and_save(session, sem, base, suffix, url, log_callback, stats, formats, tags_to_scrape=None, retries=3, rate_limit=0.5, output_dir=None):
    """Enhanced fetch and save function with video support and timeout handling"""
    attempt = 0

    while attempt < retries:
        try:
            async with sem:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}")
                    text = await response.text()

                soup = BeautifulSoup(text, "html.parser")

                # Prepare folder structure
                folder = os.path.join(output_dir or "", base)
                os.makedirs(folder, exist_ok=True)
                base_filename = f"{base}-{suffix.lstrip('.')}"

                # Use enhanced content extraction
                metadata = EnhancedContentExtractor.extract_metadata(soup, url)
                content = EnhancedContentExtractor.extract_content(soup, tags_to_scrape)

                # Enhanced keyword extraction
                keywords = []
                try:
                    text_for_keywords = content['text_content']
                    if text_for_keywords:
                        # Remove common stop words and extract meaningful keywords
                        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were', 'been', 'have', 'has', 'had'}
                        words = re.findall(r'\b\w{4,}\b', text_for_keywords.lower())
                        filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
                        common = Counter(filtered_words).most_common(15)
                        keywords = [w for w, count in common if count > 1]
                except Exception:
                    pass

                # Enhanced sentiment analysis (optional)
                sentiment = None
                try:
                    from textblob import TextBlob
                    text_for_sentiment = content['text_content'][:1000]  # Limit text length for performance
                    if text_for_sentiment:
                        blob = TextBlob(text_for_sentiment)
                        sentiment = {
                            "polarity": round(blob.sentiment.polarity, 3),
                            "subjectivity": round(blob.sentiment.subjectivity, 3),
                            "word_count": content['word_count']
                        }
                except Exception:
                    pass

                saved = []  # one log line per file written

                # Save TXT (enhanced summary)
                if 'txt' in formats:
                    lines = []
                    if metadata['title']:
                        lines.append(f"[title] {metadata['title']}")
                    if metadata['meta_description']:
                        lines.append(f"[meta description] {metadata['meta_description']}")
                    if metadata['og_title'] and metadata['og_title'] != metadata['title']:
                        lines.append(f"[og:title] {metadata['og_title']}")
                    if metadata['og_description']:
                        lines.append(f"[og:description] {metadata['og_description']}")
                    if metadata['author']:
                        lines.append(f"[author] {metadata['author']}")
                    if metadata['published_date']:
                        lines.append(f"[published] {metadata['published_date']}")
                    if metadata['canonical_url']:
                        lines.append(f"[canonical] {metadata['canonical_url']}")

                    # Add headings
                    for heading in content['headings'][:10]:  # Limit to first 10 headings
                        lines.append(f"[h{heading['level']}] {heading['text']}")

                    # Add key paragraphs (longer ones)
                    key_paragraphs = [p for p in content['paragraphs'] if len(p) > 100][:5]
                    for para in key_paragraphs:
                        lines.append(f"[paragraph] {para[:200]}{'...' if len(para) > 200 else ''}")

                    # Add video information
                    for video in metadata['videos']:
                        if video['type'] == 'video_element':
                            for source in video['sources']:
                                lines.append(f"[video] {source['url']} ({source['type']})")
                        elif video['type'] == 'iframe_embed':
                            lines.append(f"[video_embed] {video['url']} (platform: {video['platform']})")
                        elif video['type'] == 'video_link':
                            lines.append(f"[video_link] {video['url']} ({video['extension']}) - {video['text']}")

                    if keywords:
                        lines.append("[keywords] " + ', '.join(keywords))
                    if sentiment:
                        lines.append(f"[sentiment] polarity={sentiment['polarity']:.3f}, subjectivity={sentiment['subjectivity']:.3f}, words={sentiment['word_count']}")

                    if lines:
                        txt_path = os.path.join(folder, base_filename + ".txt")
                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write("\n".join(lines))
                        saved.append(f"Saved enhanced TXT to {txt_path}")

                # Save JSON (comprehensive structured data)
                if 'json' in formats:
                    data = {
                        "url": url,
                        "metadata": metadata,
                        "content": content,
                        "keywords": keywords,
                        "sentiment": sentiment,
                        "scrape_info": {
                            "timestamp": time.time(),
                            "formatted_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                            "method": "enhanced_scraper",
                            "javascript_used": False,
                            "videos_found": len(metadata['videos'])
                        }
                    }
                    json_path = os.path.join(folder, base_filename + ".json")
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    saved.append(f"Saved enhanced JSON to {json_path}")

                # Save HTML (raw HTML with metadata comments)
                if 'html' in formats:
                    html_content = f"""<!-- Scraped with Enhanced Scraper at {time.strftime('%Y-%m-%d %H:%M:%S')} -->
<!-- Original URL: {url} -->
<!-- Method: HTTP (Enhanced) -->
<!-- Word Count: {content.get('word_count', 0)} -->
<!-- Videos Found: {len(metadata['videos'])} -->
{text}"""
                    html_path = os.path.join(folder, base_filename + ".html")
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    saved.append(f"Saved enhanced HTML to {html_path}")

                # Count each domain once and log once, so the GUI progress bar counts domains
                if saved:
                    stats["saved"] += 1
                    msg = "\n".join(saved)
                else:
                    stats["not_useful"] += 1
                    msg = f"Nothing useful on {url}"
                if log_callback:
                    log_callback(msg)
                return

        except asyncio.TimeoutError:
            attempt += 1
            if attempt >= retries:
                if log_callback:
                    log_callback(f"Timeout error for {url} after {retries} attempts")
                stats["failed"] += 1
                return
            else:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        except Exception as e:
            attempt += 1
            if attempt >= retries:
                if log_callback:
                    log_callback(f"Failed to scrape {url} after {retries} attempts: {str(e)}")
                stats["failed"] += 1
                return
            else:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # Add rate limiting between attempts
        await asyncio.sleep(rate_limit)

async def save_html_files_async(base, domains, formats=None, log_callback=None, max_concurrent=10, rate_limit=0.5, retries=3, tags_to_scrape=None, output_dir=None):
    """Async function to save HTML files with enhanced error handling"""
    if formats is None:
        formats = ['txt']

    stats = {
        "total_pinged": len(domains),
        "saved": 0,
        "failed": 0,
        "not_useful": 0
    }

    # Create semaphore to limit concurrent requests and prevent overwhelming
    sem = asyncio.Semaphore(max_concurrent)

    # Use connector with limits to prevent resource exhaustion
    connector = aiohttp.TCPConnector(
        limit=max_concurrent * 2,
        limit_per_host=5,
        ttl_dns_cache=300,
        use_dns_cache=True,
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_and_save(session, sem, base, suffix, url, log_callback, stats, formats, tags_to_scrape, retries, rate_limit, output_dir)
            for suffix, url in domains
        ]
        # Use asyncio.gather with return_exceptions=True to handle failures gracefully
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            if log_callback:
                log_callback(f"Critical error in batch processing: {str(e)}")

    return stats

def save_html_files(base, domains, formats=None, log_callback=None, max_concurrent=10, rate_limit=0.5, retries=3, tags_to_scrape=None, output_dir=None):
    """Main entry point for saving HTML files with video support"""
    try:
        return asyncio.run(save_html_files_async(base, domains, formats, log_callback, max_concurrent, rate_limit, retries, tags_to_scrape, output_dir))
    except Exception as e:
        if log_callback:
            log_callback(f"Critical error in scraper: {str(e)}")
        return {
            "total_pinged": len(domains),
            "saved": 0,
            "failed": len(domains),
            "not_useful": 0
        }