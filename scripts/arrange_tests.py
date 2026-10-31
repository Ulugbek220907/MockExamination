#!/usr/bin/env python3
"""
Choose which tests of one module are free, and number the module's tests in that order.

    python scripts/arrange_tests.py reading --free academic-reading-01,academic-reading-02,...
    python scripts/arrange_tests.py reading --free ids.txt          # one id per line also works
    python scripts/arrange_tests.py reading --free ... --dry-run    # show the result, change nothing

What it does, for the module's files in content/<module>/:
  * the tests you list become free ("access": "free") and come first, in the order you give;
  * every other test becomes "premium" and follows, in its current order (the site shows "premium" tests as
    "Coming soon…" until COMMERCE_ENABLED is on; the launch keeps five tests free per module);
  * `sortOrder` is renumbered 1, 2, 3 ... in that order, and a trailing number in `title` and
    `shortTitle` ("Academic Reading Practice Test 12") is renumbered to match, so the list page
    ("Test 5") and the exam screen agree. Ids never change: attempts and payments refer to them.

Use it again after adding tests of your own: list the free ones, and the new files fall in after them
(give them a sortOrder larger than the others first). Then run scripts/validate_content.py and,
for production, scripts/seed_supabase.py.
"""

import argparse
import glob
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, "content")
TRAILING_NUMBER = re.compile(r"(\d+)$")


def load(module):
    tests = []
    for path in glob.glob(os.path.join(CONTENT_DIR, module, "*.json")):
        with open(path, encoding="utf-8") as f:
            tests.append((path, json.load(f)))
    tests.sort(key=lambda pt: (pt[1].get("sortOrder", 999), pt[1].get("id", "")))
    return tests


def read_ids(value):
    if os.path.isfile(value):
        with open(value, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return [x.strip() for x in value.split(",") if x.strip()]


def renumber(text, n):
    return TRAILING_NUMBER.sub(str(n), text) if isinstance(text, str) and TRAILING_NUMBER.search(text) else text


def arranged(test, access, n):
    """The test with access and numbering set, keys in their original order ("access" right after "sortOrder")."""
    out = {}
    for key, value in test.items():
        if key == "access":
            continue
        if key == "sortOrder":
            out[key] = n
            out["access"] = access
        elif key in ("title", "shortTitle"):
            out[key] = renumber(value, n)
        else:
            out[key] = value
    if "access" not in out:
        out["access"] = access
        out["sortOrder"] = n
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("module", choices=("reading", "listening", "writing", "speaking"))
    parser.add_argument("--free", required=True, help="comma-separated test ids (or a file with one per line), in the order they should appear")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tests = load(args.module)
    by_id = {t["id"]: (p, t) for p, t in tests}
    free_ids = read_ids(args.free)
    unknown = [i for i in free_ids if i not in by_id]
    if unknown:
        sys.exit(f"Not in content/{args.module}/: {', '.join(unknown)}")
    if len(set(free_ids)) != len(free_ids):
        sys.exit("A test is listed twice.")

    paid_ids = [t["id"] for _, t in tests if t["id"] not in set(free_ids)]
    order = [(i, "free") for i in free_ids] + [(i, "premium") for i in paid_ids]
    for n, (test_id, access) in enumerate(order, 1):
        path, test = by_id[test_id]
        new = arranged(test, access, n)
        if args.dry_run:
            print(f"{n:>3}  {access:<7}  {test_id}  {new.get('title', '')}")
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new, f, indent=2, ensure_ascii=False)
            f.write("\n")
    print(f"{len(free_ids)} free, {len(paid_ids)} premium in {args.module}" + (" (dry run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
