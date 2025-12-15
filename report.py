import os
import csv
import json
from datetime import datetime

def write_report(base, stats, formats=("txt","csv","json","html")):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [
        f"Scrape report for '{base}':",
        f"Timestamp: {timestamp}",
        f"Total pinged: {stats['total_pinged']}",
        f"Saved: {stats['saved']}",
        f"Failed to scrape: {stats['failed']}",
        f"Not useful scrape: {stats['not_useful']}",
    ]
    report_dir = base
    os.makedirs(report_dir, exist_ok=True)
    report_paths = {}
    if "txt" in formats:
        txt_path = os.path.join(report_dir, f"{base}-report.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
        report_paths["txt"] = txt_path
    if "csv" in formats:
        csv_path = os.path.join(report_dir, f"{base}-report.csv")
        with open(csv_path, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["base", "timestamp", "total_pinged", "saved", "failed", "not_useful"])
            writer.writerow([
                base,
                timestamp,
                stats["total_pinged"],
                stats["saved"],
                stats["failed"],
                stats["not_useful"]
            ])
        report_paths["csv"] = csv_path
    if "json" in formats:
        json_path = os.path.join(report_dir, f"{base}-report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "base": base,
                "timestamp": timestamp,
                **stats
            }, f, indent=2)
        report_paths["json"] = json_path
    if "html" in formats:
        html_path = os.path.join(report_dir, f"{base}-report.html")
        html_content = f"""
        <html><head><meta charset='utf-8'><title>Scrape report for '{base}'</title></head><body>
        <h2>Scrape report for '{base}'</h2>
        <ul>
        <li><b>Timestamp:</b> {timestamp}</li>
        <li><b>Total pinged:</b> {stats['total_pinged']}</li>
        <li><b>Saved:</b> {stats['saved']}</li>
        <li><b>Failed to scrape:</b> {stats['failed']}</li>
        <li><b>Not useful scrape:</b> {stats['not_useful']}</li>
        </ul>
        </body></html>
        """
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        report_paths["html"] = html_path
    # Return the text report path for backward compatibility
    return report_paths.get("txt")
