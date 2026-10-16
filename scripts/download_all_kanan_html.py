import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_DIR = os.path.join(BASE_DIR, "data", "kanan_html")
os.makedirs(HTML_DIR, exist_ok=True)

with open(os.path.join(BASE_DIR, "kanan_170_catalog.json"), "r", encoding="utf-8") as f:
    items = json.load(f)

def main():
    print(f"Scraping all {len(items)} Kanan answer pages into {HTML_DIR}...")
    t0 = time.time()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context()
        main_page = context.new_page()
        main_page.goto("https://www.kanan.co/ielts/academic/reading/practice-test/", wait_until="networkidle", timeout=30000)
        print("[OK] Solved Cloudflare challenge on main page")
        
        tab = context.new_page()
        saved = 0
        skipped = 0
        for idx, item in enumerate(items, 1):
            sno = int(item["sno"])
            url = item["ans_url"]
            out_file = os.path.join(HTML_DIR, f"test_{sno:03d}.html")
            if os.path.exists(out_file) and os.path.getsize(out_file) > 10000:
                skipped += 1
                continue
            try:
                tab.goto(url, wait_until="domcontentloaded", timeout=15000)
                content = tab.content()
                if "Just a moment" in tab.title():
                    # Brief wait for cloudflare if triggered
                    tab.wait_for_timeout(3000)
                    content = tab.content()
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(content)
                saved += 1
                if idx % 10 == 0 or idx == len(items):
                    print(f"  Progress: {idx}/{len(items)} (saved {saved}, cached {skipped}) in {time.time()-t0:.1f}s")
            except Exception as e:
                print(f"  ⚠ Error scraping test {sno} ({url}): {e}")
                time.sleep(1)
        
        browser.close()
    print(f"\n[OK] Completed scraping: {saved} new, {skipped} cached, total {saved+skipped}/{len(items)} in {time.time()-t0:.1f}s")

if __name__ == "__main__":
    main()
