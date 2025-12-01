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

def run_scraper_thread(base, status_label, log_widget, max_workers, tlds):
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
    reachable_domains = ping_domains(base, suffixes=tlds, timeout=5, max_workers=max_workers)
    if not reachable_domains:
        status_label.config(text="No reachable domain found.")
        log_widget.insert(tk.END, "No reachable domain found.\n")
        log_widget.see(tk.END)
        return
    log_widget.insert(tk.END, f"Found {len(reachable_domains)} reachable domains.\n")
    log_widget.see(tk.END)
    log_widget.update()
    def log_callback(msg):
        log_widget.insert(tk.END, msg + "\n")
        log_widget.see(tk.END)
        log_widget.update()
    stats = save_html_files(base, reachable_domains, log_callback=log_callback)
    report_path = write_report(base, stats)
    status_label.config(text=f"Done! {stats['saved']} domains saved.")
    log_widget.insert(tk.END, f"Done! {stats['saved']} domains saved.\n")
    log_widget.insert(tk.END, f"Report saved to {report_path}\n")
    log_widget.see(tk.END)
    messagebox.showinfo("Done", f"Done!\nReport saved to:\n{report_path}")

def resource_path(relative_path):
    # Get absolute path to resource, works for dev and for PyInstaller .exe
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

def start_gui():
    root = tk.Tk()
    root.title("Domain Scraper")
    root.geometry("520x600")
    root.resizable(True, True)

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

    frame = tk.Frame(root, padx=15, pady=15)
    frame.pack(fill=tk.BOTH, expand=True)

    # Display logo at the top if loaded
    if logo_img:
        logo_label = tk.Label(frame, image=logo_img)
        logo_label.image = logo_img  # Keep a reference!
        logo_label.pack(pady=(0, 10))
    elif not PIL_AVAILABLE:
        print("Pillow (PIL) is not installed. For best results, install it with 'pip install pillow'.")

    tk.Label(frame, text="Base domain name (e.g., 'nrk', 'bbc'):", font=("Segoe UI", 11)).pack(anchor="w")
    base_entry = tk.Entry(frame, width=30, font=("Segoe UI", 11))
    base_entry.pack(fill=tk.X, pady=(0, 10))

    # Max workers
    tk.Label(frame, text="Number of threads (default 20):", font=("Segoe UI", 10)).pack(anchor="w")
    max_workers_entry = tk.Entry(frame, width=10, font=("Segoe UI", 10))
    max_workers_entry.insert(0, "20")
    max_workers_entry.pack(fill=tk.X, pady=(0, 10))

    # TLDs
    tk.Label(frame, text="TLDs to check (comma-separated, leave blank for all):", font=("Segoe UI", 10)).pack(anchor="w")
    tlds_entry = tk.Entry(frame, width=50, font=("Segoe UI", 10))
    tlds_entry.pack(fill=tk.X, pady=(0, 10))

    status_label = tk.Label(frame, text="", fg="blue", font=("Segoe UI", 10, "italic"))
    status_label.pack(anchor="w", pady=(0, 10))

    log_label = tk.Label(frame, text="App Log:", font=("Segoe UI", 10, "bold"))
    log_label.pack(anchor="w")

    log_widget = scrolledtext.ScrolledText(frame, width=60, height=18, font=("Consolas", 9))
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
        # Run in a background thread
        threading.Thread(target=run_scraper_thread, args=(base, status_label, log_widget, max_workers, tlds), daemon=True).start()

    run_button = tk.Button(frame, text="Run Scraper", command=on_run, font=("Segoe UI", 11, "bold"), bg="#4CAF50", fg="white")
    run_button.pack(pady=(5, 0), fill=tk.X)

    root.mainloop()
