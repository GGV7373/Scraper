import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
import time
import json
import os
from pathlib import Path
from typing import Set, Dict, List, Optional
import hashlib
import re

class WebsiteCrawler:
    """Comprehensive website crawler that extracts and downloads all content"""

    def __init__(self, start_url: str, output_dir: str = "output", max_pages: int = 100):
        self.start_url = start_url
        self.output_dir = Path(output_dir)
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.queued_urls: Set[str] = set()
        self.downloaded_images: Set[str] = set()
        self.image_hash_index: Dict[str, str] = {}
        self.crawl_stats = {
            "pages_crawled": 0,
            "images_found": 0,
            "images_downloaded": 0,
            "videos_found": 0,
            "html_files_saved": 0,
            "errors": 0
        }

        # Get domain for crawling limits
        parsed = urlparse(start_url)
        self.base_domain = parsed.netloc
        self.allowed_domains = {self.base_domain}

        # Add common subdomain patterns
        if self.base_domain.startswith('www.'):
            self.allowed_domains.add(self.base_domain[4:])
        else:
            self.allowed_domains.add(f'www.{self.base_domain}')

        # Create images directory
        self.images_dir = self.output_dir / self.base_domain / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Load existing image hash index
        self.hash_index_file = self.images_dir / ".hash_index.json"
        self._load_image_hash_index()

    def _load_image_hash_index(self):
        """Load existing image hash index to avoid re-downloading"""
        if self.hash_index_file.exists():
            try:
                with open(self.hash_index_file, 'r') as f:
                    self.image_hash_index = json.load(f)
            except:
                self.image_hash_index = {}

    def _save_image_hash_index(self):
        """Save image hash index"""
        try:
            with open(self.hash_index_file, 'w') as f:
                json.dump(self.image_hash_index, f, indent=2)
        except Exception as e:
            print(f"Error saving image hash index: {e}")

    def is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled"""
        try:
            parsed = urlparse(url)

            # Must be HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False

            # Must be same domain or subdomain
            if not any(parsed.netloc.endswith(domain) or parsed.netloc == domain for domain in self.allowed_domains):
                return False

            # Skip common non-content files
            skip_extensions = {'.css', '.js', '.ico', '.svg', '.woff', '.woff2', '.ttf', '.eot', '.map', '.xml', '.rss'}
            if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
                return False

            # Skip common admin/system paths
            skip_paths = {'/wp-admin', '/admin', '/api/', '/ajax/', '/feed/', '/login', '/logout'}
            if any(skip_path in parsed.path.lower() for skip_path in skip_paths):
                return False

            return True
        except:
            return False

    def is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image"""
        try:
            parsed = urlparse(url)
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.avif', '.tiff', '.tif'}
            return any(parsed.path.lower().endswith(ext) for ext in image_extensions)
        except:
            return False

    def clean_url(self, url: str) -> str:
        """Clean URL by removing fragments and normalizing"""
        # Remove fragments (#section)
        url_clean, _ = urldefrag(url)

        # Remove common tracking parameters
        parsed = urlparse(url_clean)
        if parsed.query:
            # Keep only essential parameters, remove tracking
            query_params = []
            skip_params = {'utm_', 'fb_', 'gclid', 'ref', 'source', 'campaign'}
            for param in parsed.query.split('&'):
                if '=' in param:
                    key = param.split('=')[0].lower()
                    if not any(key.startswith(skip) for skip in skip_params):
                        query_params.append(param)

            new_query = '&'.join(query_params) if query_params else ''
            url_clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if new_query:
                url_clean += f"?{new_query}"

        return url_clean

    def sanitize_filename(self, name: str) -> str:
        """Create safe filename"""
        safe = [c if c.isalnum() or c in ("-", "_", ".") else "-" for c in name]
        return "".join(safe).strip("-") or "image"

    def get_image_extension(self, url: str, content_type: str = "") -> str:
        """Get appropriate file extension for image"""
        # Try to get from URL first
        parsed = urlparse(url)
        url_ext = os.path.splitext(parsed.path)[1].lower()
        if url_ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.avif'}:
            return url_ext

        # Try to get from content type
        if content_type:
            type_mapping = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'image/bmp': '.bmp',
                'image/svg+xml': '.svg',
                'image/avif': '.avif'
            }
            return type_mapping.get(content_type.split(';')[0].lower(), '.jpg')

        return '.jpg'  # Default fallback

    async def download_image(self, session: aiohttp.ClientSession, img_url: str, page_url: str) -> bool:
        """Download a single image"""
        if img_url in self.downloaded_images:
            return False

        self.downloaded_images.add(img_url)

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; ImageCrawler/1.0)'}
            async with session.get(img_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    return False

                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    # Still try if URL suggests it's an image
                    if not self.is_valid_image_url(img_url):
                        return False

                data = await response.read()

                # Check for duplicates using hash
                img_hash = hashlib.sha256(data).hexdigest()
                if img_hash in self.image_hash_index:
                    return False

                # Generate filename
                parsed_img = urlparse(img_url)
                parsed_page = urlparse(page_url)

                # Create subdirectory based on page path
                page_path_parts = [p for p in parsed_page.path.split('/') if p]
                if page_path_parts:
                    img_subdir = self.images_dir / '/'.join(page_path_parts[:-1]) if len(page_path_parts) > 1 else self.images_dir
                else:
                    img_subdir = self.images_dir
                img_subdir.mkdir(parents=True, exist_ok=True)

                # Create filename
                img_name = os.path.basename(parsed_img.path)
                if not img_name or '.' not in img_name:
                    img_name = f"image_{img_hash[:8]}"

                img_name_clean = self.sanitize_filename(os.path.splitext(img_name)[0])
                extension = self.get_image_extension(img_url, content_type)
                filename = f"{img_name_clean}_{img_hash[:8]}{extension}"

                # Save image
                img_path = img_subdir / filename
                with open(img_path, 'wb') as f:
                    f.write(data)

                # Update hash index
                self.image_hash_index[img_hash] = str(img_path)

                print(f"Downloaded image: {img_path.name}")
                return True

        except Exception as e:
            print(f"Failed to download image {img_url}: {e}")
            return False

    def extract_links(self, html: str, base_url: str) -> Set[str]:
        """Extract all valid links from HTML"""
        links = set()
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Get links from <a> tags
            for link in soup.find_all('a', href=True):
                href = link.get('href', '').strip()
                if href:
                    full_url = urljoin(base_url, href)
                    clean_url = self.clean_url(full_url)
                    if self.is_valid_url(clean_url):
                        links.add(clean_url)

            # Get links from navigation elements
            for nav in soup.find_all(['nav', 'menu']):
                for link in nav.find_all('a', href=True):
                    href = link.get('href', '').strip()
                    if href:
                        full_url = urljoin(base_url, href)
                        clean_url = self.clean_url(full_url)
                        if self.is_valid_url(clean_url):
                            links.add(clean_url)

        except Exception as e:
            print(f"Error extracting links from {base_url}: {e}")

        return links

    async def extract_and_download_images(self, session: aiohttp.ClientSession, html: str, base_url: str) -> List[Dict]:
        """Extract and download all images from HTML"""
        images = []
        download_tasks = []

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Extract from <img> tags
            for img in soup.find_all('img'):
                # Get src
                if img.get('src'):
                    img_url = urljoin(base_url, img['src'])
                    img_data = {
                        'url': img_url,
                        'alt': img.get('alt', ''),
                        'title': img.get('title', ''),
                        'width': img.get('width', ''),
                        'height': img.get('height', ''),
                        'type': 'img_src'
                    }
                    images.append(img_data)
                    download_tasks.append(self.download_image(session, img_url, base_url))

                # Get srcset
                if img.get('srcset'):
                    srcset = img['srcset']
                    for src_entry in srcset.split(','):
                        src_url = src_entry.strip().split(' ')[0]
                        if src_url:
                            img_url = urljoin(base_url, src_url)
                            img_data = {
                                'url': img_url,
                                'alt': img.get('alt', ''),
                                'title': img.get('title', ''),
                                'type': 'img_srcset'
                            }
                            images.append(img_data)
                            download_tasks.append(self.download_image(session, img_url, base_url))

            # Extract from CSS background images
            for element in soup.find_all(style=True):
                style = element['style']
                bg_match = re.search(r'background-image:\s*url\(["\']?([^"\']+)["\']?\)', style)
                if bg_match:
                    bg_url = urljoin(base_url, bg_match.group(1))
                    images.append({
                        'url': bg_url,
                        'alt': '',
                        'title': '',
                        'type': 'css_background'
                    })
                    download_tasks.append(self.download_image(session, bg_url, base_url))

            # Extract from <picture> elements
            for picture in soup.find_all('picture'):
                for source in picture.find_all('source'):
                    if source.get('srcset'):
                        srcset = source['srcset']
                        for src_entry in srcset.split(','):
                            src_url = src_entry.strip().split(' ')[0]
                            if src_url:
                                img_url = urljoin(base_url, src_url)
                                images.append({
                                    'url': img_url,
                                    'alt': '',
                                    'title': '',
                                    'type': 'picture_source'
                                })
                                download_tasks.append(self.download_image(session, img_url, base_url))

            # Download all images concurrently
            if download_tasks:
                results = await asyncio.gather(*download_tasks, return_exceptions=True)
                successful_downloads = sum(1 for r in results if r is True)
                self.crawl_stats['images_downloaded'] += successful_downloads

        except Exception as e:
            print(f"Error extracting images from {base_url}: {e}")

        return images

    def extract_videos(self, html: str, base_url: str) -> List[Dict]:
        """Extract all videos from HTML"""
        videos = []
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Extract <video> elements
            for video in soup.find_all('video'):
                video_data = {
                    'type': 'video_element',
                    'sources': [],
                    'poster': video.get('poster', ''),
                    'controls': video.get('controls') is not None,
                    'autoplay': video.get('autoplay') is not None,
                    'loop': video.get('loop') is not None,
                }

                # Direct src
                if video.get('src'):
                    video_data['sources'].append({
                        'url': urljoin(base_url, video['src']),
                        'type': video.get('type', 'unknown')
                    })

                # Source elements
                for source in video.find_all('source'):
                    if source.get('src'):
                        video_data['sources'].append({
                            'url': urljoin(base_url, source['src']),
                            'type': source.get('type', 'unknown')
                        })

                if video_data['sources']:
                    videos.append(video_data)

            # Extract iframe videos (YouTube, Vimeo, etc.)
            for iframe in soup.find_all('iframe'):
                src = iframe.get('src', '')
                if any(platform in src.lower() for platform in ['youtube', 'vimeo', 'dailymotion', 'twitch', 'player']):
                    videos.append({
                        'type': 'iframe_embed',
                        'url': src,
                        'platform': self._detect_platform(src),
                        'width': iframe.get('width'),
                        'height': iframe.get('height'),
                        'title': iframe.get('title', '')
                    })

            # Extract video file links
            video_extensions = {'.mp4', '.webm', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.m4v', '.3gp', '.ogv'}
            for link in soup.find_all('a', href=True):
                href = link['href']
                parsed_url = urlparse(href)
                if any(parsed_url.path.lower().endswith(ext) for ext in video_extensions):
                    videos.append({
                        'type': 'video_link',
                        'url': urljoin(base_url, href),
                        'extension': os.path.splitext(parsed_url.path)[1].lower(),
                        'text': link.get_text(strip=True)
                    })

        except Exception as e:
            print(f"Error extracting videos from {base_url}: {e}")

        return videos

    def _detect_platform(self, url: str) -> str:
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

    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Fetch a single page"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
            timeout = aiohttp.ClientTimeout(total=30)

            async with session.get(url, headers=headers, timeout=timeout) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"HTTP {response.status} for {url}")
                    return None
        except asyncio.TimeoutError:
            print(f"Timeout for {url}")
            return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def save_page_content(self, url: str, html: str, images: List[Dict], videos: List[Dict]) -> None:
        """Save page content to files"""
        try:
            # Create safe filename from URL
            parsed = urlparse(url)
            path_parts = [part for part in parsed.path.split('/') if part]
            if not path_parts:
                path_parts = ['index']

            # Create directory structure
            page_dir = self.output_dir / self.base_domain / '/'.join(path_parts[:-1]) if len(path_parts) > 1 else self.output_dir / self.base_domain
            page_dir.mkdir(parents=True, exist_ok=True)

            filename_base = path_parts[-1] if path_parts else 'index'
            filename_base = re.sub(r'[^\w\-_.]', '_', filename_base)
            if not filename_base:
                filename_base = 'page'

            # Save HTML
            html_file = page_dir / f"{filename_base}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html)
            self.crawl_stats['html_files_saved'] += 1

            # Save metadata
            metadata = {
                'url': url,
                'timestamp': time.time(),
                'formatted_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'images': images,
                'videos': videos,
                'image_count': len(images),
                'video_count': len(videos),
                'images_downloaded': sum(1 for img in images if img['url'] not in self.downloaded_images)
            }

            metadata_file = page_dir / f"{filename_base}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            self.crawl_stats['images_found'] += len(images)
            self.crawl_stats['videos_found'] += len(videos)

            print(f"Saved: {html_file.name} ({len(images)} images, {len(videos)} videos)")

        except Exception as e:
            print(f"Error saving content for {url}: {e}")
            self.crawl_stats['errors'] += 1

    async def crawl_page(self, session: aiohttp.ClientSession, url: str) -> None:
        """Crawl a single page and extract all content"""
        if url in self.visited_urls or len(self.visited_urls) >= self.max_pages:
            return

        self.visited_urls.add(url)
        print(f"Crawling [{len(self.visited_urls)}/{self.max_pages}]: {url}")

        # Fetch page content
        html = await self.fetch_page(session, url)
        if not html:
            self.crawl_stats['errors'] += 1
            return

        self.crawl_stats['pages_crawled'] += 1

        # Extract and download images, extract videos
        images = await self.extract_and_download_images(session, html, url)
        videos = self.extract_videos(html, url)

        # Save content
        self.save_page_content(url, html, images, videos)

        # Extract new links for crawling
        new_links = self.extract_links(html, url)
        for link in new_links:
            if link not in self.visited_urls and link not in self.queued_urls:
                self.queued_urls.add(link)

    async def crawl_website(self, log_callback=None) -> Dict:
        """Main crawling function"""
        print(f"🕷️ Starting comprehensive crawl of: {self.start_url}")
        print(f"📊 Max pages: {self.max_pages}")
        print(f"🏠 Base domain: {self.base_domain}")
        print(f"🖼️ Images will be downloaded to: {self.images_dir}")

        # Initialize
        self.queued_urls.add(self.start_url)

        # Setup session
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)

        async with aiohttp.ClientSession(connector=connector) as session:
            while self.queued_urls and len(self.visited_urls) < self.max_pages:
                # Get next URL
                current_url = self.queued_urls.pop()

                # Crawl page
                await self.crawl_page(session, current_url)

                # Save image hash index periodically
                if len(self.visited_urls) % 10 == 0:
                    self._save_image_hash_index()

                # Rate limiting
                await asyncio.sleep(1)

                # Log progress
                if log_callback:
                    progress_msg = f"Crawled {self.crawl_stats['pages_crawled']} pages, found {self.crawl_stats['images_found']} images, downloaded {self.crawl_stats['images_downloaded']}, found {self.crawl_stats['videos_found']} videos"
                    log_callback(progress_msg)

        # Save final image hash index
        self._save_image_hash_index()

        # Save final statistics
        self.save_crawl_report()

        print(f"\n🎉 Crawl complete!")
        print(f"📄 Pages crawled: {self.crawl_stats['pages_crawled']}")
        print(f"🖼️ Images found: {self.crawl_stats['images_found']}")
        print(f"📥 Images downloaded: {self.crawl_stats['images_downloaded']}")
        print(f"🎥 Videos found: {self.crawl_stats['videos_found']}")
        print(f"💾 HTML files saved: {self.crawl_stats['html_files_saved']}")
        print(f"❌ Errors: {self.crawl_stats['errors']}")

        return self.crawl_stats

    def save_crawl_report(self) -> None:
        """Save comprehensive crawl report"""
        try:
            report_dir = self.output_dir / self.base_domain
            report_dir.mkdir(parents=True, exist_ok=True)

            report = {
                'crawl_info': {
                    'start_url': self.start_url,
                    'base_domain': self.base_domain,
                    'start_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'max_pages': self.max_pages,
                    'images_directory': str(self.images_dir)
                },
                'statistics': self.crawl_stats,
                'crawled_urls': list(self.visited_urls)
            }

            report_file = report_dir / 'crawl_report.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)

            # Save simple text report
            text_report = report_dir / 'crawl_summary.txt'
            with open(text_report, 'w', encoding='utf-8') as f:
                f.write(f"Website Crawl Report\n")
                f.write(f"==================\n\n")
                f.write(f"Start URL: {self.start_url}\n")
                f.write(f"Base Domain: {self.base_domain}\n")
                f.write(f"Crawl Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Images Directory: {self.images_dir}\n\n")
                f.write(f"Statistics:\n")
                f.write(f"-----------\n")
                f.write(f"Pages crawled: {self.crawl_stats['pages_crawled']}\n")
                f.write(f"Images found: {self.crawl_stats['images_found']}\n")
                f.write(f"Images downloaded: {self.crawl_stats['images_downloaded']}\n")
                f.write(f"Videos found: {self.crawl_stats['videos_found']}\n")
                f.write(f"HTML files saved: {self.crawl_stats['html_files_saved']}\n")
                f.write(f"Errors: {self.crawl_stats['errors']}\n\n")
                f.write(f"Crawled URLs:\n")
                f.write(f"-------------\n")
                for url in sorted(self.visited_urls):
                    f.write(f"- {url}\n")

            print(f"📊 Crawl report saved: {report_file}")

        except Exception as e:
            print(f"Error saving crawl report: {e}")

# Integration function for existing GUI
async def crawl_full_website(start_url: str, output_dir: str = "output", max_pages: int = 100, log_callback=None) -> Dict:
    """Main function to crawl entire website and download all images"""
    crawler = WebsiteCrawler(start_url, output_dir, max_pages)
    return await crawler.crawl_website(log_callback)

def crawl_website_sync(start_url: str, output_dir: str = "output", max_pages: int = 100, log_callback=None) -> Dict:
    """Synchronous wrapper for GUI integration"""
    return asyncio.run(crawl_full_website(start_url, output_dir, max_pages, log_callback))