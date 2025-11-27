from pinger import ping_domains
from bs import save_html_files
import tkinter as tk
from tkinter import messagebox, scrolledtext
import os

def write_report(base, stats):
    report_lines = [
        f"Scrape report for '{base}':",
        f"Total pinged: {stats['total_pinged']}",
        f"Saved: {stats['saved']}",
        f"Failed to scrape: {stats['failed']}",
        f"Not useful scrape: {stats['not_useful']}",
    ]
    report_path = os.path.join(base, f"{base}-scrape-report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    return report_path

def run_scraper(base, status_label, log_widget):
    base = base.strip()
    if not base:
        messagebox.showerror("Input Error", "Please enter a base domain name.")
        return
    status_label.config(text="Pinging domains, please wait...")
    log_widget.insert(tk.END, f"Starting scan for: {base}\n")
    log_widget.see(tk.END)
    log_widget.update()
    reachable_domains = ping_domains(base, timeout=5)
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

def main():
    root = tk.Tk()
    root.title("Domain Scraper")
    root.geometry("500x500")
    root.resizable(False, False)

    frame = tk.Frame(root, padx=15, pady=15)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="Base domain name (e.g., 'nrk'):", font=("Segoe UI", 11)).pack(anchor="w")
    base_entry = tk.Entry(frame, width=30, font=("Segoe UI", 11))
    base_entry.pack(fill=tk.X, pady=(0, 10))

    status_label = tk.Label(frame, text="", fg="blue", font=("Segoe UI", 10, "italic"))
    status_label.pack(anchor="w", pady=(0, 10))

    log_label = tk.Label(frame, text="App Log:", font=("Segoe UI", 10, "bold"))
    log_label.pack(anchor="w")

    log_widget = scrolledtext.ScrolledText(frame, width=60, height=18, font=("Consolas", 9))
    log_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    def on_run():
        log_widget.delete(1.0, tk.END)
        run_scraper(base_entry.get(), status_label, log_widget)

    run_button = tk.Button(frame, text="Run Scraper", command=on_run, font=("Segoe UI", 11, "bold"), bg="#4CAF50", fg="white")
    run_button.pack(pady=(5, 0), fill=tk.X)

    root.mainloop()

if __name__ == "__main__":
    main()