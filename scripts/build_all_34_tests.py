import os
import sys
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from book_extractor_common import open_pdf, clean_text, load_answer_keys
from test_parser_engine import TOC_TITLES, split_test_into_sections, find_section_groups, extract_paragraphs, parse_group, build_parsed_test
from test_parser_foundation import get_test_raw_text

def get_test_1_to_10(test_num):
    file_num = test_num + 6
    path = os.path.join(BASE_DIR, "content", "reading", f"academic-reading-{file_num:02d}.json")
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    
    # Use exact TOC titles
    for p in d.get("passages", []):
        p_num = p.get("passageNumber")
        toc_t = TOC_TITLES.get((test_num, p_num))
        if toc_t:
            p["title"] = toc_t

    test_obj = {
        "id": f"book-reading-{test_num:02d}",
        "module": "reading",
        "variant": "academic",
        "testNumber": test_num,
        "title": f"Academic Reading Test {test_num}",
        "shortTitle": f"Book Test {test_num}",
        "durationMinutes": 60,
        "totalQuestions": 40,
        "sortOrder": test_num,
        "passages": d["passages"]
    }
    return test_obj

def build_all_tests():
    doc = open_pdf()
    all_keys = load_answer_keys(doc)
    all_tests = []
    
    print("Loading Tests 1 to 10...")
    for t in range(1, 11):
        test_dict = get_test_1_to_10(t)
        all_tests.append(test_dict)
        print(f"  ✓ Test {t:2d}: {test_dict['title']} (40 questions)")
        
    print("\nBuilding Tests 11 to 34 from PDF...")
    for t in range(11, 35):
        test_dict = build_parsed_test(t, doc, all_keys)
        # Validate question count
        q_count = sum(len(g["questions"]) for p in test_dict["passages"] for g in p["groups"])
        if q_count != 40:
            print(f"  ⚠ Test {t:2d} has {q_count} questions, adjusting...")
            # Check question numbers
            q_nums = [q["number"] for p in test_dict["passages"] for g in p["groups"] for q in g["questions"]]
            print(f"    Existing Qs: min={min(q_nums)}, max={max(q_nums)}, total={len(q_nums)}")
        else:
            print(f"  ✓ Test {t:2d}: {test_dict['title']} (40 questions)")
        all_tests.append(test_dict)

    # Verification of all 34 tests
    print("\n--- Verifying all 34 tests ---")
    assert len(all_tests) == 34, f"Expected 34 tests, got {len(all_tests)}"
    for idx, t in enumerate(all_tests, 1):
        assert t["testNumber"] == idx, f"Test number mismatch at index {idx}"
        assert len(t["passages"]) == 3, f"Test {idx} does not have 3 passages"
        q_nums = [q["number"] for p in t["passages"] for g in p["groups"] for q in g["questions"]]
        expected_qs = list(range(1, 41))
        assert sorted(q_nums) == expected_qs, f"Test {idx} questions mismatch: {sorted(q_nums)}"
        # Check every question has an answer
        for p in t["passages"]:
            for g in p["groups"]:
                if g["type"] == "choose_multiple":
                    assert g.get("answer"), f"Test {idx} choose_multiple missing answer"
                else:
                    for q in g["questions"]:
                        assert q.get("answer"), f"Test {idx} Q{q['number']} missing answer"
    print("✓ All 34 tests verified: 3 passages each, exactly 40 questions (1-40) with answers!")

    # Write to content/reading/book_34_tests.json
    out_content = os.path.join(BASE_DIR, "content", "reading", "book_34_tests.json")
    with open(out_content, "w", encoding="utf-8") as f:
        json.dump(all_tests, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved to {out_content} ({os.path.getsize(out_content):,} bytes)")

    # Also write to data/book_34_tests.json
    out_data = os.path.join(BASE_DIR, "data", "book_34_tests.json")
    os.makedirs(os.path.dirname(out_data), exist_ok=True)
    with open(out_data, "w", encoding="utf-8") as f:
        json.dump(all_tests, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved to {out_data} ({os.path.getsize(out_data):,} bytes)")

    return all_tests

if __name__ == "__main__":
    build_all_tests()
