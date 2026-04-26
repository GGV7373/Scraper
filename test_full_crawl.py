#!/usr/bin/env python3
"""
Test the new full website crawling functionality
"""

import os

def test_new_features():
    print("🧪 Testing Full Website Crawling Integration")
    print("=" * 50)

    # Test file existence
    required_files = [
        'website_crawler.py',
        'crawl_website.py',
        'gui.py',
        'main.py'
    ]

    print("📁 Checking new files...")
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} (MISSING)")
            return False

    # Check GUI integration
    print("\n🔗 Checking GUI integration...")
    try:
        with open('gui.py', 'r') as f:
            gui_content = f.read()

            checks = [
                ('from website_crawler import crawl_website_sync', 'Website crawler import'),
                ('var_crawl_full = tk.BooleanVar', 'Full crawl checkbox variable'),
                ('Crawl entire website', 'Full crawl checkbox text'),
                ('max_pages_entry = ttk.Entry', 'Max pages entry field'),
                ('crawl_full_website = getattr', 'Full crawl option handling'),
                ('crawl_website_sync(', 'Full crawl function call')
            ]

            for check, description in checks:
                if check in gui_content:
                    print(f"  ✓ {description}")
                else:
                    print(f"  ✗ {description} (MISSING)")
                    return False
    except FileNotFoundError:
        print("  ✗ gui.py not found")
        return False

    # Check website crawler features
    print("\n🕷️ Checking website crawler features...")
    try:
        with open('website_crawler.py', 'r') as f:
            crawler_content = f.read()

            features = [
                ('class WebsiteCrawler', 'Main crawler class'),
                ('extract_links', 'Link extraction'),
                ('extract_images', 'Image extraction'),
                ('extract_videos', 'Video extraction'),
                ('crawl_page', 'Page crawling'),
                ('save_page_content', 'Content saving'),
                ('async def crawl_website', 'Main crawl function'),
                ('crawl_website_sync', 'Sync wrapper function')
            ]

            for feature, description in features:
                if feature in crawler_content:
                    print(f"  ✓ {description}")
                else:
                    print(f"  ✗ {description} (MISSING)")
                    return False
    except FileNotFoundError:
        print("  ✗ website_crawler.py not found")
        return False

    # Check command-line interface
    print("\n💻 Checking command-line interface...")
    try:
        with open('crawl_website.py', 'r') as f:
            cli_content = f.read()

            cli_features = [
                ('argparse', 'Argument parsing'),
                ('crawl_full_website', 'Main crawler import'),
                ('--max-pages', 'Max pages option'),
                ('--output', 'Output directory option'),
                ('--verbose', 'Verbose logging option')
            ]

            for feature, description in cli_features:
                if feature in cli_content:
                    print(f"  ✓ {description}")
                else:
                    print(f"  ✗ {description} (MISSING)")
                    return False
    except FileNotFoundError:
        print("  ✗ crawl_website.py not found")
        return False

    return True

def show_usage_examples():
    print("\n" + "="*60)
    print("🎉 FULL WEBSITE CRAWLING READY!")
    print("="*60)

    print("\n🖥️ GUI Usage:")
    print("  1. Run: ./launch.sh")
    print("  2. Check 'Crawl entire website' option")
    print("  3. Set max pages (e.g., 50)")
    print("  4. Enter URL or domain")
    print("  5. Click 'Run Scraper'")
    print("  → Extracts ALL images, videos, and HTML from entire website!")

    print("\n💻 Command Line Usage:")
    print("  # Basic crawl")
    print("  python crawl_website.py https://example.com")
    print("")
    print("  # Advanced crawl")
    print("  python crawl_website.py https://example.com \\")
    print("    --output my_crawl \\")
    print("    --max-pages 200 \\")
    print("    --verbose")

    print("\n📁 What Gets Extracted:")
    print("  🌐 Complete HTML pages with metadata")
    print("  🖼️ All images (jpg, png, gif, webp, svg)")
    print("  🎥 All videos (mp4, webm, avi, embedded)")
    print("  🔗 Site structure and navigation")
    print("  📊 Comprehensive crawl reports")

    print("\n💾 Output Structure:")
    print("  output/")
    print("  └── domain.com/")
    print("      ├── page1.html")
    print("      ├── page1_metadata.json")
    print("      ├── subfolder/")
    print("      │   ├── page2.html")
    print("      │   └── page2_metadata.json")
    print("      ├── crawl_report.json")
    print("      └── crawl_summary.txt")

def main():
    success = test_new_features()

    if success:
        show_usage_examples()
    else:
        print("\n❌ Some features are missing. Please check the errors above.")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())