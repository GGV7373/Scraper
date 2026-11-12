#!/usr/bin/env python3
"""
Command line interface for the comprehensive website crawler
"""

import argparse
import asyncio
from scraper.website_crawler import crawl_full_website

def main():
    parser = argparse.ArgumentParser(description='Crawl entire website and extract all images, videos, and HTML files')
    parser.add_argument('url', help='Starting URL to crawl')
    parser.add_argument('--output', '-o', default='output', help='Output directory (default: output)')
    parser.add_argument('--max-pages', '-p', type=int, default=100, help='Maximum pages to crawl (default: 100)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    def log_callback(msg):
        if args.verbose:
            print(f"[LOG] {msg}")

    print(f"Starting full website crawl: {args.url}")
    print(f"Max pages: {args.max_pages}")
    print(f"Output directory: {args.output}")
    print("")

    try:
        stats = asyncio.run(crawl_full_website(
            start_url=args.url,
            output_dir=args.output,
            max_pages=args.max_pages,
            log_callback=log_callback
        ))

        print("\n" + "="*50)
        print("CRAWL COMPLETED SUCCESSFULLY!")
        print("="*50)
        print(f"Pages crawled: {stats['pages_crawled']}")
        print(f"Images found: {stats['images_found']}")
        print(f"Images downloaded: {stats['images_downloaded']}")
        print(f"Videos found: {stats['videos_found']}")
        print(f"HTML files saved: {stats['html_files_saved']}")
        print(f"Errors: {stats['errors']}")
        print(f"\nResults saved to: {args.output}/")

    except Exception as e:
        print(f"Crawl failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())