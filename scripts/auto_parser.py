import re
import json
import pymupdf
from book_extractor_common import open_pdf, clean_text, TEST_PAGE_STARTS, load_answer_keys, save_and_validate_test

def extract_section_blocks(raw_text):
    """Split test text into 3 sections."""
    # Split on Section 1, 2, 3 or READING PASSAGE 1, 2, 3
    pattern = r'(?:SECTION|READING PASSAGE)\s*([123])'
    splits = re.split(pattern, raw_text, flags=re.IGNORECASE)
    sections = {}
    for i in range(1, len(splits), 2):
        s_num = int(splits[i])
        content = splits[i+1].strip()
        sections[s_num] = content
    return sections

def extract_paragraphs_from_section(sec_text):
    """Extract paragraphs and question text from a section."""
    # Find where the question block begins.
    # Usually marked by 'Questions 1-' or 'Questions 14-' or 'Questions 27-' or 'Q ụest' or 'Questions'
    # Wait: if matching_headings is present, questions may be at the very top!
    has_top_headings = False
    m_top = re.search(r'^\s*(?:Questions?\s*\d+\s*[-–]\s*\d+|List of Headings)', sec_text, re.I | re.M)
    if m_top and m_top.start() < 200:
        has_top_headings = True

    # Find lettered paragraphs: lines starting with A. or A\n or [A]
    # Let's inspect
    return sec_text

if __name__ == "__main__":
    doc = open_pdf()
    keys = load_answer_keys(doc)
    print("Auto parser initialized.")
