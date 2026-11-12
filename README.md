# Web Scraper with Video & Image Support

A comprehensive web scraper that extracts text content, images, and videos from websites with advanced timeout handling and **full website crawling** capabilities.

## Features

- **Web Content Scraping**: Extract text, metadata, and structured content
- **Image Scraping**: Download and deduplicate images from web pages
- **Video Scraping**: Extract and download videos from multiple sources
- **Full Website Crawling**: Crawl entire websites to extract ALL content
- **Anti-Freeze Protection**: Advanced timeout and error handling
- **User-Friendly GUI**: Easy-to-use graphical interface
- **Multiple Output Formats**: TXT, JSON, and HTML reports
- **Concurrent Processing**: Fast multi-threaded operations

## Full Website Crawling

The full crawl:
- **Follows all internal links** on the same domain/subdomain
- **Downloads every image** and lists every video on all discovered pages
- **Saves complete HTML** of each page with metadata
- **Avoids duplicates** and infinite loops
- **Respects robots.txt** and waits 1 second between pages
- **Generates detailed reports** of the entire crawl

### What Gets Extracted During Full Crawl:
- **All HTML pages** on the website
- **Every image downloaded** (jpg, png, gif, webp, etc.) with deduplication
- **All videos** (mp4, webm, embedded videos), listed in each page's metadata; tick "Include video scraping" to download them too
- **Complete site structure** and navigation
- **Metadata and analytics** for each page

## Video Content Detection

The scraper can detect and extract videos from:
- `<video>` HTML elements with source files
- Direct video file links (mp4, webm, avi, mov, etc.)
- Embedded videos (YouTube, Vimeo, Dailymotion, Twitch)
- Video metadata including platform detection

## Quick Start

### 1. Setup (First Time)
```bash
# Linux/macOS
chmod +x setup.sh
./setup.sh
```

```batch
# Windows
setup.bat
```

### 2. Launch Application
```bash
# Linux/macOS
./launch.sh
```

```batch
# Windows
launch.bat
```

## Project Layout

```
main.py               # Entry point, launches the GUI
crawl_website.py      # Command line crawler
setup.sh / setup.bat  # First-time setup
launch.sh             # Launcher (created by setup)
logo/                 # App icons
scraper/              # The application code
├── gui.py            # Main interface with image/video options
├── bs.py             # Core web scraper with content extraction
├── website_crawler.py  # Full website crawler
├── image_scraper.py  # Image extraction and deduplication
├── video_scraper.py  # Video detection and downloading
├── pinger.py         # Domain discovery and validation
└── report.py         # Results formatting and export
tests/                # Offline tests (python -m unittest)
```

## Output Structure

```
output_folder/
├── domain_name/           # Scraped content and report
│   ├── domain_name-com.txt
│   ├── domain_name-com.json
│   ├── domain_name-com.html
│   └── domain_name-report.txt
├── images/                # Downloaded images
│   └── domain.com/
└── videos/                # Downloaded videos
    └── domain.com/
```

## Configuration Options

### GUI Settings
- **Domain/URL Input**: Enter domain name or full URL
- **Thread Count**: Number of concurrent workers (1-100)
- **TLDs**: Target top-level domains (com, org, net, etc.)
- **Rate Limiting**: Delay between requests (seconds)
- **Content Tags**: Select specific HTML elements to scrape
- **Output Formats**: Choose TXT, JSON, and/or HTML
- **Media Options**: Enable image and/or video scraping

### Anti-Freeze Features
- **Request Timeouts**: 15s for content, 30s for videos
- **Connection Limits**: Prevents resource exhaustion
- **Exponential Backoff**: Smart retry mechanism
- **Semaphore Control**: Limits concurrent operations
- **Error Recovery**: Graceful failure handling

## Requirements

- Python 3.7+
- Dependencies: `aiohttp`, `beautifulsoup4`, `requests`, `pillow`, `textblob`

## Usage Examples

### Basic Web Scraping
1. Enter domain name (e.g., "example")
2. Select output formats
3. Click "Run Scraper"

### Full Website Crawling
1. Check "Crawl entire website" option
2. Set max pages limit (e.g., 50)
3. Enter URL or domain name
4. All pages and images are saved; videos are listed (and downloaded if video scraping is on)

### Video Scraping
1. Check "Include video scraping"
2. Enter URL or domain
3. Videos will be downloaded to `videos/` folder

### Advanced Options
- Use custom TLDs: "com,org,net"
- Set rate limiting: "1.0" (1 second between requests)
- Select specific tags: Check h1, h2, p, div boxes

## Command Line Interface

For advanced users, crawl websites directly from command line:

```bash
# Crawl a website with default settings (100 pages max)
python crawl_website.py https://example.com

# Crawl with custom settings
python crawl_website.py https://example.com --output my_crawl --max-pages 200 --verbose

# Get help
python crawl_website.py --help
```

The image and video scrapers also run on their own:

```bash
python -m scraper.image_scraper https://example.com --recursive --max-pages 20
python -m scraper.video_scraper https://example.com
```

## Troubleshooting

### Common Issues
- **Import errors**: Run setup script to install dependencies
- **Freezing**: The new version has timeout protection
- **No videos found**: Some sites may block video extraction
- **Large files**: Video downloads limited to 100MB by default

### Manual Dependency Installation
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Running Tests

```bash
python -m unittest discover tests
```

## License

Licensed under the original project license terms.
