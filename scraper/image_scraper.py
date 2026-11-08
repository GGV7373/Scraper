import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Deque, Dict, List, Set
from urllib.parse import urljoin, urlparse
from collections import deque

import aiohttp
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ImageScraper/1.0)"
}


def load_hash_index(index_path: Path) -> Dict[str, str]:
    if index_path.exists():
        try:
            with index_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_hash_index(index_path: Path, index: Dict[str, str]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def sanitize_filename(name: str) -> str:
    safe = [c if c.isalnum() or c in ("-", "_") else "-" for c in name]
    return "".join(safe).strip("-") or "image"


def folder_from_url(page_url: str) -> Path:
    parsed = urlparse(page_url)
    domain = sanitize_filename(parsed.netloc)
    path_parts = [p for p in parsed.path.split("/") if p]
    if not path_parts or path_parts == [""]:
        path_parts = ["index"]
    path_parts = [sanitize_filename(p) for p in path_parts]
    return Path(domain) / "/".join(path_parts)


def extension_from_content_type(content_type: str) -> str:
    if not content_type:
        return ""
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/svg+xml": ".svg",
        "image/avif": ".avif",
    }
    return mapping.get(content_type.split(";")[0].lower(), "")


def collect_image_urls(html: str, base_url: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: Set[str] = set()
    for img in soup.find_all("img"):
        src = img.get("src")
        if src:
            urls.add(urljoin(base_url, src))
        srcset = img.get("srcset")
        if srcset:
            for part in srcset.split(","):
                candidate = part.strip().split(" ")[0]
                if candidate:
                    urls.add(urljoin(base_url, candidate))
    return urls


def extract_links(html: str, base_url: str, seed_host: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        candidate = urljoin(base_url, href)
        if not candidate.startswith(("http://", "https://")):
            continue
        host = urlparse(candidate).netloc
        if host.endswith(seed_host):
            links.append(candidate)
    return links


async def fetch_html(session: aiohttp.ClientSession, url: str, timeout: int) -> str:
    async with session.get(url, headers=DEFAULT_HEADERS, timeout=timeout) as resp:
        resp.raise_for_status()
        return await resp.text()


async def download_image(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    img_url: str,
    dest_dir: Path,
    hash_index: Dict[str, str],
    seen_urls: Set[str],
    timeout: int,
) -> bool:
    if img_url in seen_urls:
        return False
    seen_urls.add(img_url)

    async with sem:
        try:
            async with session.get(img_url, headers=DEFAULT_HEADERS, timeout=timeout) as resp:
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "")
                if not content_type.startswith("image"):
                    return False
                data = await resp.read()
        except Exception:
            return False

    digest = hashlib.sha256(data).hexdigest()
    if digest in hash_index:
        return False

    ext = extension_from_content_type(content_type)
    parsed = urlparse(img_url)
    name_part = sanitize_filename(Path(parsed.path).name.split(".")[0]) or digest[:12]
    filename = f"{name_part or 'image'}-{digest[:8]}{ext or ''}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    file_path = dest_dir / filename
    with file_path.open("wb") as f:
        f.write(data)

    hash_index[digest] = str(file_path)
    return True


async def scrape_page_images(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    page_url: str,
    output_root: Path,
    hash_index: Dict[str, str],
    seen_urls: Set[str],
    timeout: int,
) -> int:
    try:
        html = await fetch_html(session, page_url, timeout)
    except Exception:
        return 0

    dest_dir = output_root / folder_from_url(page_url)
    img_urls = collect_image_urls(html, page_url)

    tasks = [
        download_image(session, sem, img_url, dest_dir, hash_index, seen_urls, timeout)
        for img_url in img_urls
    ]
    results = await asyncio.gather(*tasks)
    return sum(1 for r in results if r)


async def crawl_seed(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    seed_url: str,
    output_root: Path,
    hash_index: Dict[str, str],
    seen_urls: Set[str],
    timeout: int,
    recursive: bool,
    max_pages: int,
) -> int:
    visited: Set[str] = set()
    queue: Deque[str] = deque([seed_url])
    seed_host = urlparse(seed_url).netloc
    total_new = 0

    while queue and len(visited) < max_pages:
        page_url = queue.popleft()
        if page_url in visited:
            continue
        visited.add(page_url)
        try:
            html = await fetch_html(session, page_url, timeout)
        except Exception:
            continue

        # Save images on this page
        dest_dir = output_root / folder_from_url(page_url)
        img_urls = collect_image_urls(html, page_url)
        tasks = [
            download_image(session, sem, img_url, dest_dir, hash_index, seen_urls, timeout)
            for img_url in img_urls
        ]
        results = await asyncio.gather(*tasks)
        total_new += sum(1 for r in results if r)

        if recursive and len(visited) < max_pages:
            for link in extract_links(html, page_url, seed_host):
                if link not in visited:
                    queue.append(link)
    return total_new


async def scrape_images(
    urls: List[str],
    output_root: Path,
    concurrency: int,
    timeout: int,
    recursive: bool = False,
    max_pages: int = 1,
) -> int:
    output_root.mkdir(parents=True, exist_ok=True)
    index_path = output_root / ".hash_index.json"
    hash_index = load_hash_index(index_path)
    seen_urls: Set[str] = set()

    connector = aiohttp.TCPConnector(limit=concurrency)
    sem = asyncio.Semaphore(concurrency)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            crawl_seed(session, sem, url, output_root, hash_index, seen_urls, timeout, recursive, max_pages)
            for url in urls
        ]
        results = await asyncio.gather(*tasks)

    save_hash_index(index_path, hash_index)
    total_new = sum(results)
    print(f"Downloaded {total_new} new images (deduplicated). Saved under: {output_root}")
    return total_new


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download images from one or more web pages.")
    parser.add_argument("urls", nargs="*", help="Page URLs to scrape for images.")
    parser.add_argument(
        "--url-file",
        dest="url_file",
        help="Path to a text file with one URL per line.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default="output/images",
        help="Root folder to save images (default: output/images).",
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
        default=15,
        help="Per-request timeout in seconds (default: 15).",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Follow same-domain and subdomain links from the seed URL(s) up to --max-pages.",
    )
    parser.add_argument(
        "--max-pages",
        dest="max_pages",
        type=int,
        default=50,
        help="Maximum pages to visit per seed when --recursive is set (default: 50).",
    )
    return parser.parse_args()


def gather_urls(args: argparse.Namespace) -> List[str]:
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
    args = parse_args()
    urls = gather_urls(args)
    if not urls:
        print("No URLs provided. Supply URLs as arguments or via --url-file.")
        return
    output_root = Path(args.output).resolve()
    asyncio.run(
        scrape_images(
            urls,
            output_root,
            concurrency=args.concurrency,
            timeout=args.timeout,
            recursive=args.recursive,
            max_pages=args.max_pages,
        )
    )


if __name__ == "__main__":
    main()