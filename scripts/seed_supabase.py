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

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from mockexam import content, storage  # noqa: E402


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    secret = os.environ.get("SUPABASE_APP_SECRET")
    is_service_key = bool(key and (key.startswith("sb_secret_") or "service_role" in key or not secret))

    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY) first (see DEPLOY.md).")
    if not secret and not is_service_key:
        sys.exit("Set SUPABASE_APP_SECRET or use a Supabase service role key (see DEPLOY.md).")

    tests = storage.load_local_tests()
    problems = []
    for t in tests:
        problems += content.validate_test(t, public_dir=os.path.join(BASE_DIR, "public"))
    if problems:
        print("Refusing to upload invalid content:")
        for p in problems:
            print("  ✗", p)
        sys.exit(1)

    if secret:
        store = storage.SupabaseStore(url, key, secret)
        for t in tests:
            store.upsert_test(t)
            print(f"✓ uploaded {t['id']}  ({t['title']})")
    else:
        import urllib.request
        endpoint = url.rstrip("/") + "/rest/v1/tests"
        for t in tests:
            row = {
                "id": t["id"],
                "module": t["module"],
                "variant": t.get("variant", "academic"),
                "title": t["title"],
                "sort_order": t.get("sortOrder", 999),
                "is_published": True,
                "content": t,
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(row).encode("utf-8"),
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",
                },
                method="POST",
            )
            with urllib.request.urlopen(req) as resp:
                if resp.status not in (200, 201):
                    raise RuntimeError(f"Failed to upload {t['id']}: HTTP {resp.status}")
            print(f"✓ uploaded {t['id']}  ({t['title']})")

    print(f"\nDone: {len(tests)} tests are now in Supabase.")


if __name__ == "__main__":
    main()
