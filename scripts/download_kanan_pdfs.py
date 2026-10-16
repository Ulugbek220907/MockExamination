import os
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "data", "kanan_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

with open(os.path.join(BASE_DIR, "kanan_170_catalog.json"), "r", encoding="utf-8") as f:
    items = json.load(f)

def download_one(item):
    sno = int(item["sno"])
    url = item["pdf_url"]
    out_file = os.path.join(PDF_DIR, f"test_{sno:03d}.pdf")
    if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
        return sno, True, os.path.getsize(out_file), "cached"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            with open(out_file, "wb") as f:
                f.write(data)
            return sno, True, len(data), "downloaded"
    except Exception as e:
        return sno, False, 0, str(e)

def main():
    print(f"Downloading {len(items)} PDFs to {PDF_DIR}...")
    t0 = time.time()
    success = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(download_one, it): it for it in items}
        for fut in as_completed(futures):
            sno, ok, size, msg = fut.result()
            if ok:
                success += 1
            else:
                print(f"  ✗ Failed test {sno}: {msg}")
    print(f"\nDone: {success}/{len(items)} PDFs ready in {time.time()-t0:.2f}s")

if __name__ == "__main__":
    main()
