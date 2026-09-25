#!/usr/bin/env python3
"""
Upload (insert or update) every test in content/ to the Supabase `tests` table.

Run supabase/schema.sql first, then:

    SUPABASE_URL=https://xxxx.supabase.co \
    SUPABASE_SERVICE_ROLE_KEY=eyJ... \
    python scripts/seed_supabase.py

Content is validated before upload; nothing is sent if any test is invalid.
Re-running the script updates existing tests in place.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from mockexam import content, storage  # noqa: E402


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY first (see DEPLOY.md).")

    tests = storage.load_local_tests()
    problems = []
    for t in tests:
        if t["module"] == "reading":
            problems += content.validate_reading_test(t)
        else:
            problems += content.validate_writing_test(t)
    if problems:
        print("Refusing to upload invalid content:")
        for p in problems:
            print("  ✗", p)
        sys.exit(1)

    store = storage.SupabaseStore(url, key)
    for t in tests:
        store.upsert_test(t)
        print(f"✓ uploaded {t['id']}  ({t['title']})")
    print(f"\nDone: {len(tests)} tests are now in Supabase.")


if __name__ == "__main__":
    main()
