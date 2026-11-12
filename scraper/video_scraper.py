import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Deque, Dict, List, Set, Tuple
from urllib.parse import urljoin, urlparse
from collections import deque

import aiohttp
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VideoScraper/1.0)"
}

# Video file extensions and MIME types
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.m4v', '.3gp', '.ogv', '.f4v'}
VIDEO_MIME_TYPES = {
    'video/mp4', 'video/webm', 'video/avi', 'video/quicktime',
    'video/x-msvideo', 'video/x-flv', 'video/x-matroska',
    'video/3gpp', 'video/ogg', 'video/x-f4v'
}

def load_hash_index(index_path: Path) -> Dict[str, str]:
    """Load video hash index to avoid duplicates"""
    if index_path.exists():
        try:
            with index_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_hash_index(index_path: Path, index: Dict[str, str]) -> None:
    """Save video hash index"""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

def sanitize_filename(name: str) -> str:
    """Create safe filename from string"""
    safe = [c if c.isalnum() or c in ("-", "_") else "-" for c in name]
    return "".join(safe).strip("-") or "video"

def folder_from_url(page_url: str) -> Path:
    """Create folder structure from URL"""
    parsed = urlparse(page_url)
    domain = sanitize_filename(parsed.netloc)
    path_parts = [p for p in parsed.path.split("/") if p]
    if not path_parts or path_parts == [""]:
        path_parts = ["index"]
    path_parts = [sanitize_filename(p) for p in path_parts]
    return Path(domain) / "/".join(path_parts)

def extension_from_content_type(content_type: str) -> str:
    """Get file extension from content type"""
    if not content_type:
        return ""
    mapping = {
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/avi": ".avi",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "video/x-flv": ".flv",
        "video/x-matroska": ".mkv",
        "video/3gpp": ".3gp",
        "video/ogg": ".ogv",
        "video/x-f4v": ".f4v",
    }
    return mapping.get(content_type.split(";")[0].lower(), "")

def collect_video_urls(html: str, base_url: str) -> Set[str]:
    """Extract video URLs from HTML"""
    soup = BeautifulSoup(html, "html.parser")
    urls: Set[str] = set()

    # Extract from video tags
    for video in soup.find_all("video"):
        # Direct src attribute
        src = video.get("src")
        if src:
            urls.add(urljoin(base_url, src))

        # Source elements within video
        for source in video.find_all("source"):
            src = source.get("src")
            if src:
                urls.add(urljoin(base_url, src))

    # Extract from links pointing to video files
    for link in soup.find_all("a", href=True):
        href = link["href"]
        parsed_url = urlparse(href)
        extension = os.path.splitext(parsed_url.path)[1].lower()

        if extension in VIDEO_EXTENSIONS:
            urls.add(urljoin(base_url, href))

    # Extract from any element with video-related attributes
    for elem in soup.find_all(attrs={"data-src": True}):
        data_src = elem.get("data-src")
        if data_src:
            parsed_url = urlparse(data_src)
            extension = os.path.splitext(parsed_url.path)[1].lower()
            if extension in VIDEO_EXTENSIONS:
                urls.add(urljoin(base_url, data_src))

    return urls

def collect_video_metadata(html: str, base_url: str) -> List[Dict]:
    """Extract video metadata including embed information"""
    soup = BeautifulSoup(html, "html.parser")
    videos = []

    # Extract video tags with metadata
    for video in soup.find_all("video"):
        video_info = {
            'type': 'video_element',
            'sources': [],
            'poster': '',
            'controls': video.get('controls') is not None,
            'autoplay': video.get('autoplay') is not None,
            'loop': video.get('loop') is not None,
            'width': video.get('width'),
            'height': video.get('height')
        }

        # Get poster image
        if video.get('poster'):
            video_info['poster'] = urljoin(base_url, video['poster'])

        # Get direct src
        if video.get('src'):
            video_info['sources'].append({
                'url': urljoin(base_url, video['src']),
                'type': video.get('type', 'unknown')
            })

        # Get source elements
        for source in video.find_all('source'):
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
                'platform': _detect_video_platform(src),
                'width': iframe.get('width'),
                'height': iframe.get('height'),
                'title': iframe.get('title', '')
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
                'text': link.get_text(strip=True),
                'download_url': urljoin(base_url, href)
            })

    return videos

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

async def fetch_html(session: aiohttp.ClientSession, url: str, timeout: int) -> str:
    """Fetch HTML content from URL"""
    async with session.get(url, headers=DEFAULT_HEADERS, timeout=timeout) as resp:
        resp.raise_for_status()
        return await resp.text()

async def download_video(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    video_url: str,
    dest_dir: Path,
    hash_index: Dict[str, str],
    seen_urls: Set[str],
    timeout: int,
    max_size_mb: int = 100
) -> bool:
    """Download a single video file"""
    if video_url in seen_urls:
        return False
    seen_urls.add(video_url)

    async with sem:
        try:
            # First, get headers to check content type and size
            async with session.head(video_url, headers=DEFAULT_HEADERS, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "").lower()
                content_length = resp.headers.get("Content-Length")

                # Check if it's actually a video
                if not (content_type.startswith("video") or
                       any(mime in content_type for mime in VIDEO_MIME_TYPES)):
                    # Still try if the URL extension suggests it's a video
                    parsed_url = urlparse(video_url)
                    extension = os.path.splitext(parsed_url.path)[1].lower()
                    if extension not in VIDEO_EXTENSIONS:
                        return False

                # Check file size (convert to MB)
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > max_size_mb:
                        print(f"Skipping {video_url}: too large ({size_mb:.1f}MB)")
                        return False

            # Download the video
            async with session.get(video_url, headers=DEFAULT_HEADERS, timeout=timeout) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "")
                # Enforce the size limit while reading: HEAD may lie or omit Content-Length
                limit = max_size_mb * 1024 * 1024
                data = bytearray()
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    data.extend(chunk)
                    if len(data) > limit:
                        print(f"Skipping {video_url}: larger than {max_size_mb}MB")
                        return False
                data = bytes(data)

        except Exception as e:
            print(f"Failed to download {video_url}: {e}")
            return False

    # Check for duplicates using hash
    digest = hashlib.sha256(data).hexdigest()
    if digest in hash_index:
        return False

    # Generate filename
    ext = extension_from_content_type(content_type)
    parsed = urlparse(video_url)
    name_part = sanitize_filename(Path(parsed.path).name.split(".")[0]) or digest[:12]
    filename = f"{name_part}-{digest[:8]}{ext or '.mp4'}"

    # Save file
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_path = dest_dir / filename
    with file_path.open("wb") as f:
        f.write(data)

    hash_index[digest] = str(file_path)
    print(f"Downloaded: {file_path}")
    return True

async def scrape_page_videos(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    page_url: str,
    output_root: Path,
    hash_index: Dict[str, str],
    seen_urls: Set[str],
    timeout: int,
    max_size_mb: int = 100
) -> int:
    """Scrape videos from a single page"""
    try:
        html = await fetch_html(session, page_url, timeout)
    except Exception as e:
        print(f"Failed to fetch {page_url}: {e}")
        return 0

    # Save video metadata
    dest_dir = output_root / folder_from_url(page_url)
    video_metadata = collect_video_metadata(html, page_url)

    if video_metadata:
        metadata_path = dest_dir / "video_metadata.json"
        dest_dir.mkdir(parents=True, exist_ok=True)
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(video_metadata, f, indent=2)

    # Collect downloadable video URLs
    video_urls = collect_video_urls(html, page_url)

    # Download videos
    tasks = [
        download_video(session, sem, video_url, dest_dir, hash_index, seen_urls, timeout, max_size_mb)
        for video_url in video_urls
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successful_downloads = sum(1 for r in results if r is True)

    print(f"Page {page_url}: Found {len(video_metadata)} video elements, downloaded {successful_downloads} files")
    return successful_downloads

async def scrape_videos(
    urls: List[str],
    output_root: Path,
    concurrency: int,
    timeout: int,
    max_size_mb: int = 100
) -> int:
    """Main video scraping function"""
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / ".video_hash_index.json"
    hash_index = load_hash_index(index_path)
    seen_urls: Set[str] = set()

    connector = aiohttp.TCPConnector(limit=concurrency)
    sem = asyncio.Semaphore(concurrency)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            scrape_page_videos(session, sem, url, output_root, hash_index, seen_urls, timeout, max_size_mb)
            for url in urls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    save_hash_index(index_path, hash_index)
    total_new = sum(r for r in results if isinstance(r, int))
    print(f"Downloaded {total_new} new videos (deduplicated). Saved under: {output_root}")
    return total_new

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Download videos from one or more web pages.")
    parser.add_argument("urls", nargs="*", help="Page URLs to scrape for videos.")
    parser.add_argument(
        "--url-file",
        dest="url_file",
        help="Path to a text file with one URL per line.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default="output/videos",
        help="Root folder to save videos (default: output/videos).",
    )
    parser.add_argument(
        "--concurrency",
        dest="concurrency",
        type=int,
        default=8,
        help="Number of concurrent downloads (default: 8).",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=int,
        default=30,
        help="Per-request timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--max-size",
        dest="max_size_mb",
        type=int,
        default=100,
        help="Maximum video size in MB to download (default: 100).",
    )
    return parser.parse_args()

def gather_urls(args: argparse.Namespace) -> List[str]:
    """Gather URLs from arguments and file"""
    urls: List[str] = []
    if args.url_file:
        path = Path(args.url_file)
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    url = line.strip()
                    if url:
                        urls.append(url)
    urls.extend(args.urls)
    return [u for u in urls if u.startswith("http://") or u.startswith("https://")]

def main() -> None:
    """Main entry point"""
    args = parse_args()
    urls = gather_urls(args)
    if not urls:
        print("No URLs provided. Supply URLs as arguments or via --url-file.")
        return
    output_root = Path(args.output).resolve()
    asyncio.run(
        scrape_videos(
            urls,
            output_root,
            concurrency=args.concurrency,
            timeout=args.timeout,
            max_size_mb=args.max_size_mb,
        )
    )

if __name__ == "__main__":
    main()