from bs4 import BeautifulSoup
import re
import json

with open("kanan_main_page.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

print("Title:", soup.title.string if soup.title else None)

# Find all links
links = soup.find_all("a", href=True)
print(f"Total links: {len(links)}")

reading_test_links = []
pdf_links = []
for a in links:
    href = a["href"]
    text = a.get_text(strip=True)
    if "reading" in href.lower() or "practice-test" in href.lower() or "test" in href.lower():
        reading_test_links.append((text, href))
    if href.endswith(".pdf") or ".pdf" in href:
        pdf_links.append((text, href))

print(f"Reading/test related links: {len(reading_test_links)}")
print(f"PDF links: {len(pdf_links)}")

for t, h in reading_test_links[:30]:
    print(f"  {t} -> {h}")

# Check tables or list items
tables = soup.find_all("table")
print(f"Tables: {len(tables)}")
for i, tab in enumerate(tables):
    rows = tab.find_all("tr")
    print(f"Table {i}: {len(rows)} rows")
    for r in rows[:5]:
        print("   ", [c.get_text(strip=True) for c in r.find_all(["th", "td"])])
