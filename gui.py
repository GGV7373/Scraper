import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
from pinger import ping_domains, get_all_tlds
from bs import save_html_files
from report import write_report
import threading
import re
import os
import sys

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

def resource_path(relative_path):
    # Get absolute path to resource, works for dev and for PyInstaller .exe
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

def start_gui():
    from tkinter import ttk
    root = tk.Tk()
    root.title("Domain Scraper")
    root.geometry("560x770")
    root.resizable(True, True)
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


    # Set taskbar icon (Windows) using .ico (absolute path, with error handling)
    ico_path = resource_path(os.path.join("logo", "logo.ico"))
    if os.path.exists(ico_path):
        try:
            root.iconbitmap(ico_path)
            print(f"Taskbar icon set: {ico_path}")
        except Exception as e:
            print(f"Could not set .ico icon: {e}")
    else:
        print(f".ico file not found at: {ico_path}")

    # Set window icon and display logo (PNG, resized if needed)
    logo_path = resource_path(os.path.join("logo", "log.png"))
    logo_img = None
    try:
        if PIL_AVAILABLE:
            img = Image.open(logo_path)
            max_width = 128
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (max_width, int(img.height * ratio))
                img = img.resize(new_size, Image.ANTIALIAS)
            logo_img = ImageTk.PhotoImage(img)
            root.iconphoto(True, logo_img)
        else:
            logo_img = tk.PhotoImage(file=logo_path)
            root.iconphoto(True, logo_img)
    except Exception as e:
        print(f"Could not load logo image: {e}")
        logo_img = None

    frame = ttk.Frame(root, padding=20, style='TFrame')
    frame.pack(fill=tk.BOTH, expand=True)

    # Tags/elements to scrape - checkboxes
    ttk.Label(frame, text="Tags/elements to scrape (leave all unchecked to scrape all):", font=("Segoe UI", 10)).pack(anchor="w")
    tag_options = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'span', 'a', 'ul', 'li', 'img', 'table']
    tag_vars = {tag: tk.BooleanVar(value=False) for tag in tag_options}
    tags_frame = ttk.Frame(frame, style='TFrame')
    tags_frame.pack(anchor="w", pady=(0, 10))
    for i, tag in enumerate(tag_options):
        cb = ttk.Checkbutton(tags_frame, text=tag, variable=tag_vars[tag], style='TCheckbutton')
        cb.grid(row=i//7, column=i%7, sticky="w", padx=2, pady=2)

    # Display logo at the top if loaded
    if logo_img:
        logo_label = ttk.Label(frame, image=logo_img, style='TLabel')
        logo_label.image = logo_img  # Keep a reference!
        logo_label.pack(pady=(0, 10))
    elif not PIL_AVAILABLE:
        print("Pillow (PIL) is not installed. For best results, install it with 'pip install pillow'.")

    ttk.Label(frame, text="Domain Scraper", style='Header.TLabel').pack(pady=(0, 10))

    ttk.Label(frame, text="Base domain name (e.g., 'nrk', 'bbc'):").pack(anchor="w")
    base_entry = ttk.Entry(frame, width=30)
    base_entry.pack(fill=tk.X, pady=(0, 10))

    # Max workers
    ttk.Label(frame, text="Number of threads (default 20):", font=("Segoe UI", 10)).pack(anchor="w")
    max_workers_entry = ttk.Entry(frame, width=10)
    max_workers_entry.insert(0, "20")
    max_workers_entry.pack(fill=tk.X, pady=(0, 10))

    # TLDs
    ttk.Label(frame, text="TLDs to check (comma-separated, leave blank for all, e.g., '.com', '.org'):", font=("Segoe UI", 10)).pack(anchor="w")
    tlds_entry = ttk.Entry(frame, width=50)
    tlds_entry.pack(fill=tk.X, pady=(0, 10))

    # Output format checkboxes
    format_frame = ttk.Frame(frame, style='TFrame')
    format_frame.pack(anchor="w", pady=(0, 10))
    ttk.Label(format_frame, text="Report output formats:", font=("Segoe UI", 10)).pack(side=tk.LEFT)
    var_txt = tk.BooleanVar(value=True)
    var_json = tk.BooleanVar(value=False)
    var_html = tk.BooleanVar(value=False)
    cb_txt = ttk.Checkbutton(format_frame, text="TXT", variable=var_txt, style='TCheckbutton')
    cb_json = ttk.Checkbutton(format_frame, text="JSON", variable=var_json, style='TCheckbutton')
    cb_html = ttk.Checkbutton(format_frame, text="HTML", variable=var_html, style='TCheckbutton')
    cb_txt.pack(side=tk.LEFT, padx=2)
    cb_json.pack(side=tk.LEFT, padx=2)
    cb_html.pack(side=tk.LEFT, padx=2)


    status_label = ttk.Label(frame, text="", foreground="#2a3b4c", font=("Segoe UI", 10, "italic"), style='TLabel')
    status_label.pack(anchor="w", pady=(0, 5))

    # Progress bar
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100, style='TProgressbar')
    progress_bar.pack(fill=tk.X, pady=(0, 10))

    log_label = ttk.Label(frame, text="App Log:", font=("Segoe UI", 10, "bold"), style='TLabel')
    log_label.pack(anchor="w")

    log_widget = scrolledtext.ScrolledText(frame, width=60, height=18, font=("Consolas", 10), background="#f8fafc", borderwidth=1, relief="solid")
    log_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    def on_run():
        log_widget.delete(1.0, tk.END)
        base = base_entry.get()
        try:
            max_workers = int(max_workers_entry.get())
            if max_workers < 1 or max_workers > 100:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Number of threads must be an integer between 1 and 100.")
            return
        tlds_raw = tlds_entry.get().strip()
        if tlds_raw:
            tlds = [t.strip() if t.startswith('.') else f'.{t.strip()}' for t in tlds_raw.split(',') if t.strip()]
        else:
            tlds = None
        # Gather selected formats
        formats = []
        if var_txt.get():
            formats.append("txt")
        if var_json.get():
            formats.append("json")
        if var_html.get():
            formats.append("html")
        # Pass formats and tags to thread via function attribute
        run_scraper_thread.output_formats = formats
        # Gather checked tags; if none checked, scrape all
        checked_tags = [tag for tag, var in tag_vars.items() if var.get()]
        tags_to_scrape = checked_tags if checked_tags else None
        run_scraper_thread.tags_to_scrape = tags_to_scrape
        # Run in a background thread
        threading.Thread(target=run_scraper_thread, args=(base, status_label, log_widget, max_workers, tlds, progress_var, progress_bar), daemon=True).start()

    run_button = ttk.Button(frame, text="Run Scraper", command=on_run, style='TButton')
    run_button.pack(pady=(5, 0), fill=tk.X)

    root.mainloop()
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
from pinger import ping_domains, get_all_tlds
from bs import save_html_files
from report import write_report
import threading
import re
import os
import sys

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def is_valid_domain(domain):
    # Allow Norwegian characters å, ø, æ (both lower and upper case)
    return re.match(r'^[a-zA-Z0-9\-åøæÅØÆ]{1,63}$', domain) is not None

def run_scraper_thread(base, status_label, log_widget, max_workers, tlds, progress_var, progress_bar):
    base = base.strip()
    if not base:
        messagebox.showerror("Input Error", "Please enter a base domain name.")
        return
    if not is_valid_domain(base):
        messagebox.showerror("Input Error", "Invalid base domain name. Only letters, numbers, and hyphens allowed.")
        return
    status_label.config(text="Pinging domains, please wait...")
    log_widget.insert(tk.END, f"Starting scan for: {base}\n")
    log_widget.see(tk.END)
    log_widget.update()
    progress_var.set(0)
    progress_bar.update()
    reachable_domains = ping_domains(base, suffixes=tlds, timeout=5, max_workers=max_workers)
    if not reachable_domains:
        status_label.config(text="No reachable domain found.")
        log_widget.insert(tk.END, "No reachable domain found.\n")
        log_widget.see(tk.END)
        return
    log_widget.insert(tk.END, f"Found {len(reachable_domains)} reachable domains.\n")
    log_widget.see(tk.END)
    log_widget.update()
    status_label.config(text="Scraping domains...")
    total = len(reachable_domains)
    progress_var.set(0)
    progress_bar.update()
    completed = [0]
    def log_callback(msg):
        log_widget.insert(tk.END, msg + "\n")
        log_widget.see(tk.END)
        log_widget.update()
        # Progress update
        completed[0] += 1
        percent = (completed[0] / total) * 100
        progress_var.set(percent)
        progress_bar.update()
    # Get selected formats and tags from global variable set in start_gui
    formats = getattr(run_scraper_thread, 'output_formats', ["txt"])
    tags_to_scrape = getattr(run_scraper_thread, 'tags_to_scrape', None)
    stats = save_html_files(base, reachable_domains, formats=formats, log_callback=log_callback, tags_to_scrape=tags_to_scrape)
    report_path = write_report(base, stats, formats=formats)
    status_label.config(text=f"Done! {stats['saved']} domains saved.")
    progress_var.set(100)
    progress_bar.update()
    log_widget.insert(tk.END, f"Done! {stats['saved']} domains saved.\n")
    log_widget.insert(tk.END, f"Report saved to {report_path}\n")
    log_widget.see(tk.END)
    messagebox.showinfo("Done", f"Done!\nReport saved to:\n{report_path}")
