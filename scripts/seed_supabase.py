#!/usr/bin/env python3
"""
Upload (insert or update) every test in content/ to the Supabase `tests` table.

Run supabase/schema.sql first (and store the hash of your server secret, see
the comment in that file), then:

    SUPABASE_URL=https://xxxx.supabase.co \
    SUPABASE_KEY=sb_publishable_... \
    SUPABASE_APP_SECRET=your-server-secret \
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
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    secret = os.environ.get("SUPABASE_APP_SECRET")
    if not url or not key or not secret:
        sys.exit("Set SUPABASE_URL, SUPABASE_KEY and SUPABASE_APP_SECRET first (see DEPLOY.md).")

    tests = storage.load_local_tests()
    problems = []
    for t in tests:
        problems += content.validate_test(t, public_dir=os.path.join(BASE_DIR, "public"))
    if problems:
        print("Refusing to upload invalid content:")
        for p in problems:
            print("  ✗", p)
        sys.exit(1)

    store = storage.SupabaseStore(url, key, secret)
    for t in tests:
        store.upsert_test(t)
        print(f"✓ uploaded {t['id']}  ({t['title']})")
    print(f"\nDone: {len(tests)} tests are now in Supabase.")


if __name__ == "__main__":
    main()
