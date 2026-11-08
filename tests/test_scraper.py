"""Offline tests: every request goes to a small local web server."""
import asyncio
import functools
import http.server
import tempfile
import threading
import unittest
from pathlib import Path

from scraper.bs import save_html_files
from scraper.image_scraper import scrape_images
from scraper.report import write_report
from scraper.video_scraper import scrape_videos
from scraper.website_crawler import WebsiteCrawler, crawl_website_sync

PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                    "1f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")

SITE = {
    "index.html": '<html><title>Home</title><h1>Hello world</h1><p>some text</p>'
                  '<img src="/pic.png"><a href="/about.html">about</a><a href="/secret/x.html">x</a>'
                  '<a href="/big.mp4">video</a></html>',
    "about.html": "<html><title>About</title><p>about page</p></html>",
    "secret/x.html": "<html><p>hidden</p></html>",
    "robots.txt": "User-agent: *\nDisallow: /secret/\n",
}


class ScraperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = tempfile.TemporaryDirectory()
        root = Path(cls.site.name)
        for name, body in SITE.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(body)
        (root / "pic.png").write_bytes(PNG)
        (root / "big.mp4").write_bytes(b"\0" * (2 * 1024 * 1024))  # 2 MB
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        handler = functools.partial(Quiet, directory=cls.site.name)
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.site.cleanup()

    def setUp(self):
        self.out = tempfile.TemporaryDirectory()
        self.addCleanup(self.out.cleanup)

    def test_scrape_counts_each_domain_once_and_report_lands_in_output_dir(self):
        log = []
        stats = save_html_files("t", [(".ok", self.url), (".bad", "http://127.0.0.1:1/")],
                                formats=["txt", "json", "html"], log_callback=log.append,
                                rate_limit=0, retries=1, output_dir=self.out.name)
        self.assertEqual(stats, {"total_pinged": 2, "saved": 1, "failed": 1, "not_useful": 0})
        self.assertEqual(len(log), 2)  # one line per domain drives the GUI progress bar
        report = write_report("t", stats, formats=["json"], output_dir=self.out.name)
        self.assertEqual(Path(report), Path(self.out.name) / "t" / "t-report.json")

    def test_image_scraper_works_with_gui_arguments(self):
        n = asyncio.run(scrape_images([self.url], Path(self.out.name) / "images", concurrency=2, timeout=5))
        self.assertEqual(n, 1)

    def test_video_over_size_limit_is_skipped(self):
        n = asyncio.run(scrape_videos([self.url], Path(self.out.name) / "videos", concurrency=2, timeout=5, max_size_mb=1))
        self.assertEqual(n, 0)

    def test_crawler_respects_robots_and_follows_links(self):
        stats = crawl_website_sync(self.url, self.out.name, max_pages=5)
        self.assertEqual(stats["pages_crawled"], 2)  # index + about, not /secret/
        self.assertEqual(stats["images_downloaded"], 1)

    def test_crawler_rejects_lookalike_domains(self):
        c = WebsiteCrawler("https://nrk.no/", self.out.name)
        self.assertTrue(c.is_valid_url("https://tv.nrk.no/page"))
        self.assertFalse(c.is_valid_url("https://evilnrk.no/page"))


if __name__ == "__main__":
    unittest.main()
