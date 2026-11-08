import asyncio
import os
import queue
import re
import sys
import threading
import tkinter as tk
import tkinter.filedialog as fd
from collections import Counter
from pathlib import Path
from tkinter import ttk, messagebox, scrolledtext
from urllib.parse import urlparse

from .bs import save_html_files
from .image_scraper import scrape_images
from .pinger import ping_domains
from .report import write_report
from .video_scraper import scrape_videos
from .website_crawler import crawl_website_sync

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def resource_path(relative_path):
    # Get absolute path to resource, works for dev and for PyInstaller .exe
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # logo/ lives in the project root, one level above this package
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)

def start_gui():
    # Root window
    root = tk.Tk()
    root.title("Web Scraper")
    root.geometry("560x620")
    root.resizable(True, True)

    # Styling
    style = ttk.Style()
    try:
        style.theme_use('clam')
    except Exception:
        pass
    style.configure('TFrame', background='#f4f6fa')
    style.configure('TLabel', background='#f4f6fa', font=("Segoe UI", 11))
    style.configure('Header.TLabel', font=("Segoe UI", 16, 'bold'), foreground='#2a3b4c', background='#f4f6fa')
    style.configure('TButton', font=("Segoe UI", 13, 'bold'), padding=10, foreground='white', background='#43a047')
    style.map('TButton', background=[('active', '#388e3c'), ('!active', '#43a047')], foreground=[('active', 'white'), ('!active', 'white')])
    style.configure('TCheckbutton', background='#f4f6fa', font=("Segoe UI", 10))
    style.configure('TEntry', font=("Segoe UI", 11))

    # Set taskbar icon
    ico_path = resource_path(os.path.join("logo", "logo.ico"))
    if os.path.exists(ico_path):
        try:
            root.iconbitmap(ico_path)
        except Exception:
            pass

    # Set window icon/logo
    logo_img = None
    logo_path = resource_path(os.path.join("logo", "logo.png"))
    try:
        if PIL_AVAILABLE:
            img = Image.open(logo_path)
            max_width = 128
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)), Image.BICUBIC)
            logo_img = ImageTk.PhotoImage(img)
            root.iconphoto(True, logo_img)
    except Exception:
        logo_img = None

    # Main frame
    frame = ttk.Frame(root, padding=20, style='TFrame')
    frame.pack(fill=tk.BOTH, expand=True)

    # Show logo if loaded
    if logo_img:
        lbl_logo = ttk.Label(frame, image=logo_img)
        lbl_logo.image = logo_img
        lbl_logo.pack(pady=(0, 10))

    ttk.Label(frame, text="Web Scraper", style='Header.TLabel').pack(pady=(0, 10))

    # Input field for domain or URL
    ttk.Label(frame, text="Domain name (e.g., 'nrk') or full URL (e.g., 'https://www.nrk.no/'):").pack(anchor="w")
    base_entry = ttk.Entry(frame, width=30)
    base_entry.pack(fill=tk.X, pady=(0, 10))

    # Threads
    ttk.Label(frame, text="Number of threads (default 20):", font=("Segoe UI", 10)).pack(anchor="w")
    max_workers_entry = ttk.Entry(frame, width=10)
    max_workers_entry.insert(0, "20")
    max_workers_entry.pack(fill=tk.X, pady=(0, 10))

    # TLDs
    ttk.Label(frame, text="TLDs to check (comma-separated, leave blank for all):", font=("Segoe UI", 10)).pack(anchor="w")
    tlds_entry = ttk.Entry(frame, width=50)
    tlds_entry.pack(fill=tk.X, pady=(0, 10))

    # Output folder selection
    output_dir_var = tk.StringVar(value=os.path.abspath(os.getcwd()))
    def browse_output_dir():
        folder = fd.askdirectory(initialdir=output_dir_var.get(), title="Select Output Folder")
        if folder:
            output_dir_var.set(folder)
    output_frame = ttk.Frame(frame, style='TFrame')
    output_frame.pack(fill=tk.X, pady=(0, 10))
    ttk.Label(output_frame, text="Output folder:", font=("Segoe UI", 10)).pack(side=tk.LEFT)
    output_entry = ttk.Entry(output_frame, textvariable=output_dir_var, width=40)
    output_entry.pack(side=tk.LEFT, padx=(5, 5), fill=tk.X, expand=True)
    ttk.Button(output_frame, text="Browse", command=browse_output_dir).pack(side=tk.LEFT)

    # Delay between requests
    ttk.Label(frame, text="Delay between requests (seconds, e.g. 0.5):", font=("Segoe UI", 10)).pack(anchor="w")
    delay_entry = ttk.Entry(frame, width=10)
    delay_entry.insert(0, "0.5")
    delay_entry.pack(fill=tk.X, pady=(0, 10))

    # Tag checkboxes
    ttk.Label(frame, text="Tags/elements to scrape (leave all unchecked to scrape all):", font=("Segoe UI", 10)).pack(anchor="w")
    tag_options = ['h1','h2','h3','h4','h5','h6','p','div','span','a','ul','li','img','table']
    tag_vars = {tag: tk.BooleanVar(value=False) for tag in tag_options}
    tags_frame = ttk.Frame(frame, style='TFrame')
    tags_frame.pack(anchor="w", pady=(0, 10))
    for i, tag in enumerate(tag_options):
        ttk.Checkbutton(tags_frame, text=tag, variable=tag_vars[tag], style='TCheckbutton').grid(row=i//7, column=i%7, sticky="w", padx=2, pady=2)

    # Output formats
    format_frame = ttk.Frame(frame, style='TFrame')
    format_frame.pack(anchor="w", pady=(0, 10))
    ttk.Label(format_frame, text="Report output formats:", font=("Segoe UI", 10)).pack(side=tk.LEFT)
    var_txt = tk.BooleanVar(value=True)
    var_json = tk.BooleanVar(value=False)
    var_html = tk.BooleanVar(value=False)
    ttk.Checkbutton(format_frame, text="TXT", variable=var_txt, style='TCheckbutton').pack(side=tk.LEFT, padx=2)
    ttk.Checkbutton(format_frame, text="JSON", variable=var_json, style='TCheckbutton').pack(side=tk.LEFT, padx=2)
    ttk.Checkbutton(format_frame, text="HTML", variable=var_html, style='TCheckbutton').pack(side=tk.LEFT, padx=2)

    # Image scraping option
    image_frame = ttk.Frame(frame, style='TFrame')
    image_frame.pack(anchor="w", pady=(0, 10))
    var_images = tk.BooleanVar(value=False)
    ttk.Checkbutton(image_frame, text="Include image scraping", variable=var_images, style='TCheckbutton').pack(side=tk.LEFT)

    # Video scraping option
    video_frame = ttk.Frame(frame, style='TFrame')
    video_frame.pack(anchor="w", pady=(0, 10))
    var_videos = tk.BooleanVar(value=False)
    ttk.Checkbutton(video_frame, text="Include video scraping", variable=var_videos, style='TCheckbutton').pack(side=tk.LEFT)

    # Full website crawling option
    crawl_frame = ttk.Frame(frame, style='TFrame')
    crawl_frame.pack(anchor="w", pady=(0, 10))
    var_crawl_full = tk.BooleanVar(value=False)
    ttk.Checkbutton(crawl_frame, text="Crawl entire website (extracts ALL images, videos, and HTML)", variable=var_crawl_full, style='TCheckbutton').pack(side=tk.LEFT)

    # Max pages for crawling
    crawl_limit_frame = ttk.Frame(frame, style='TFrame')
    crawl_limit_frame.pack(anchor="w", pady=(0, 10))
    ttk.Label(crawl_limit_frame, text="Max pages to crawl (if crawling entire website):", font=("Segoe UI", 10)).pack(side=tk.LEFT)
    max_pages_entry = ttk.Entry(crawl_limit_frame, width=10)
    max_pages_entry.insert(0, "50")
    max_pages_entry.pack(side=tk.LEFT, padx=(5, 0))

    # Status + progress
    status_label = ttk.Label(frame, text="", foreground="#2a3b4c", font=("Segoe UI", 10, "italic"), style='TLabel')
    status_label.pack(anchor="w", pady=(0, 5))
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100, style='TProgressbar')
    progress_bar.pack(fill=tk.X, pady=(0, 10))

    # Log (collapsible)
    log_visible = tk.BooleanVar(value=False)
    
    def toggle_log():
        if log_visible.get():
            log_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        else:
            log_widget.pack_forget()
    
    log_header_frame = ttk.Frame(frame, style='TFrame')
    log_header_frame.pack(fill=tk.X, anchor="w")
    log_toggle_btn = ttk.Checkbutton(log_header_frame, text="App Log", variable=log_visible, command=toggle_log, style='TCheckbutton')
    log_toggle_btn.pack(side=tk.LEFT)
    
    log_widget = scrolledtext.ScrolledText(frame, width=60, height=18, font=("Consolas", 10), background="#f8fafc", borderwidth=1, relief="solid")
    # Initially hidden


    # Tk is not thread-safe: the worker thread queues UI updates, the main loop runs them
    ui_queue = queue.Queue()

    def drain_ui_queue():
        while True:
            try:
                ui_queue.get_nowait()()
            except queue.Empty:
                break
        root.after(100, drain_ui_queue)

    def log(msg):
        ui_queue.put(lambda: (log_widget.insert(tk.END, msg + "\n"), log_widget.see(tk.END)))

    def set_status(text):
        ui_queue.put(lambda: status_label.config(text=text))

    def set_progress(percent):
        ui_queue.put(lambda: progress_var.set(percent))

    def finished(title, message):
        ui_queue.put(lambda: (run_btn.state(["!disabled"]), messagebox.showinfo(title, message) if title else None))

    # Run handler: validate input on the main thread, then hand off to a worker
    def on_run():
        base = base_entry.get().strip()
        if not base:
            messagebox.showerror("Input Error", "Please enter a domain name or URL.")
            return
        is_url = base.startswith(("http://", "https://"))
        if not is_url and not is_valid_domain(base):
            messagebox.showerror("Input Error", "Invalid domain name. Only letters, numbers, and hyphens allowed.")
            return
        try:
            max_workers = int(max_workers_entry.get())
            if max_workers < 1 or max_workers > 100:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Number of threads must be an integer between 1 and 100.")
            return
        try:
            rate_limit = float(delay_entry.get())
            if rate_limit < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Delay must be a non-negative number.")
            return
        try:
            max_pages = int(max_pages_entry.get())
            if max_pages < 1 or max_pages > 1000:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Max pages must be an integer between 1 and 1000.")
            return
        formats = [name for name, var in (("txt", var_txt), ("json", var_json), ("html", var_html)) if var.get()]
        if not formats:
            messagebox.showerror("Input Error", "Pick at least one output format.")
            return
        tlds_raw = tlds_entry.get().strip()
        opts = {
            "base": base,
            "is_url": is_url,
            "max_workers": max_workers,
            "tlds": ['.' + t.strip().lstrip('.') for t in tlds_raw.split(',') if t.strip()] or None,
            "formats": formats,
            "tags": [tag for tag, var in tag_vars.items() if var.get()] or None,
            "rate_limit": rate_limit,
            "output_dir": output_dir_var.get(),
            "images": var_images.get(),
            "videos": var_videos.get(),
            "crawl": var_crawl_full.get(),
            "max_pages": max_pages,
        }
        log_widget.delete(1.0, tk.END)
        progress_var.set(0)
        run_btn.state(["disabled"])  # one run at a time, so two runs never write the same files

        def worker():
            try:
                run_scraper(opts, log, set_status, set_progress, finished)
            except Exception as e:
                log(f"Unexpected error: {e}")
                set_status("Failed, see App Log.")
                finished("Error", f"Scraper stopped with an error:\n{e}")

        threading.Thread(target=worker, daemon=True).start()

    run_btn = ttk.Button(frame, text="Run Scraper", command=on_run, style='TButton')
    run_btn.pack(pady=(5, 0), fill=tk.X)
    drain_ui_queue()
    root.mainloop()


def is_valid_domain(domain):
    # Allow Norwegian characters å, ø, æ (both lower and upper case)
    return re.match(r'^[a-zA-Z0-9\-åøæÅØÆ]{1,63}$', domain) is not None


def run_scraper(opts, log, set_status, set_progress, finished):
    """Runs on a worker thread. Talks to the window only through the callbacks."""
    base, out = opts["base"], opts["output_dir"]

    if opts["is_url"]:
        netloc = urlparse(base).netloc
        folder_name = netloc[4:] if netloc.startswith("www.") else netloc
        domains = [(folder_name, base)]
        log(f"Processing URL: {base}")
    else:
        folder_name = base
        set_status("Pinging domains, please wait...")
        log(f"Starting scan for: {base}")
        domains = ping_domains(base, suffixes=opts["tlds"], timeout=5, max_workers=opts["max_workers"])
        if not domains:
            set_status("No reachable domain found.")
            log("No reachable domain found.")
            finished(None, None)
            return
        log(f"Found {len(domains)} reachable domains.")
    urls = [url for _, url in domains]

    # The full crawl downloads images itself, so the separate image step is only for normal runs
    if opts["images"] and not opts["crawl"]:
        set_status("Downloading images...")
        log(f"Starting image scraping for {len(urls)} site(s)...")
        try:
            n = asyncio.run(scrape_images(urls, Path(out) / "images", concurrency=8, timeout=15))
            log(f"Downloaded {n} new images")
        except Exception as e:
            log(f"Image scraping failed: {e}")

    if opts["videos"]:
        set_status("Downloading videos...")
        log(f"Starting video scraping for {len(urls)} site(s)...")
        try:
            n = asyncio.run(scrape_videos(urls, Path(out) / "videos", concurrency=4, timeout=30, max_size_mb=100))
            log(f"Downloaded {n} new videos")
        except Exception as e:
            log(f"Video scraping failed: {e}")

    if opts["crawl"]:
        set_status("Crawling entire websites...")
        log(f"Full website crawl of {len(urls)} site(s), max {opts['max_pages']} pages each")
        total = Counter()
        for i, url in enumerate(urls, 1):
            log(f"\nCrawling website {i}/{len(urls)}: {url}")
            try:
                stats = crawl_website_sync(url, out, opts["max_pages"], log)
                total.update(stats)
                log(f"Completed {url}: {stats['pages_crawled']} pages, {stats['images_found']} images, {stats['videos_found']} videos")
            except Exception as e:
                log(f"Failed to crawl {url}: {e}")
                total["errors"] += 1
            set_progress(i / len(urls) * 100)
        summary = (
            f"Sites crawled: {len(urls)}\n"
            f"Pages crawled: {total['pages_crawled']}\n"
            f"Images found: {total['images_found']}\n"
            f"Images downloaded: {total['images_downloaded']}\n"
            f"Videos found: {total['videos_found']}\n"
            f"HTML files saved: {total['html_files_saved']}\n"
            f"Errors: {total['errors']}"
        )
        log("\nFull crawl completed!\n" + summary)
        set_status(f"Full crawl complete! {total['pages_crawled']} pages total")
        finished("Full Crawl Complete", summary + "\n\nCheck output folder for results.")
        return

    set_status("Scraping content...")
    set_progress(0)
    done = [0]

    def scrape_log(msg):
        # save_html_files logs once per domain, so this also drives the progress bar
        log(msg)
        done[0] += 1
        set_progress(done[0] / len(domains) * 100)

    stats = save_html_files(folder_name, domains, formats=opts["formats"], log_callback=scrape_log,
                            tags_to_scrape=opts["tags"], rate_limit=opts["rate_limit"], output_dir=out)
    report_path = write_report(folder_name, stats, formats=opts["formats"], output_dir=out)
    set_progress(100)
    set_status(f"Done! {stats['saved']} domains saved.")
    log(f"Done! {stats['saved']} domains saved.\nReport saved to {report_path}")
    finished("Done", f"Done!\nReport saved to:\n{report_path}")
