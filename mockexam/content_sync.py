"""
Bring the tests stored in Supabase up to date with the test files in content/.

Only needed when the site reads its tests from Supabase (TESTS_SOURCE=supabase). By default it does not:
the tests are the files that ship with each deploy, so there is nothing to upload. In the Supabase mode a
test added to content/ (or a change to its free/paid flag) is invisible on the live site until it is
uploaded. scripts/seed_supabase.py does that from a laptop; this does it from the running site, with the
credentials it already has (Admin -> Tests, or POST /api/admin/sync-content). Only tests that differ from
what Supabase holds are uploaded, and nothing is uploaded at all if any test file is invalid.

All of it runs in a background thread, never inside the request: reading the tests back from Supabase is a
download of several megabytes from a far-away database, and the upload is one request per test. `status()`
reports the phase and the progress, so the Admin page answers at once and shows what is happening.
"""

import json
import logging
import os
import threading

from . import content, storage

log = logging.getLogger("mockexam.content_sync")

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")

_lock = threading.Lock()
_state = {"running": False, "phase": "", "total": 0, "done": 0, "failed": [], "problems": [], "message": "Not run yet."}
FILES_MESSAGE = ("This site reads its tests from the files that ship with each deploy, so there is nothing to upload. "
                 "Supabase keeps accounts, results and recordings only.")


def reads_tests_from_supabase(store):
    """True when the live tests are the copy in Supabase (TESTS_SOURCE=supabase); a fake or older store counts as yes."""
    return getattr(store, "name", "") == "supabase" and getattr(store, "tests_source", "supabase") == "supabase"


def _same(a, b):
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


def plan(store, local_tests=None, public_dir=PUBLIC_DIR):
    """(problems, changed): what is wrong with the files, and which tests Supabase lacks or holds differently."""
    local = local_tests if local_tests is not None else storage.load_local_tests()
    problems = []
    for t in local:
        problems += content.validate_test(t, public_dir=public_dir)
    remote = {t["id"]: t for t in store.list_tests()}
    changed = [t for t in local if t["id"] not in remote or not _same(t, remote[t["id"]])]
    return problems, changed


def status():
    with _lock:
        return dict(_state, failed=list(_state["failed"]), problems=list(_state["problems"]))


def _snapshot():
    return dict(_state, failed=list(_state["failed"]), problems=list(_state["problems"]))


def _finish(message, **fields):
    with _lock:
        _state.update(running=False, phase="", message=message, **fields)


def _upload(store, changed):
    for t in changed:
        try:
            store.upsert_test(t)
        except Exception as e:  # noqa: BLE001 - keep going; the failure is reported
            log.error("Could not upload %s: %s", t["id"], e)
            with _lock:
                _state["failed"].append(t["id"])
        with _lock:
            _state["done"] += 1
    store.refresh()
    with _lock:
        failed = len(_state["failed"])
        done = _state["done"]
    _finish(f"Uploaded {done - failed} of {done} tests; {failed} failed. See the server log." if failed
            else f"Done: {done} tests uploaded and the site reloaded them.")


def _work(store, local_tests, public_dir, only_new):
    """Check the files, compare them with Supabase, and upload what differs. Runs in its own thread."""
    try:
        with _lock:
            _state.update(phase="checking", message="Checking the test files…")
        local = local_tests if local_tests is not None else storage.load_local_tests()
        problems = []
        for t in local:
            problems += content.validate_test(t, public_dir=public_dir)
        if problems:
            return _finish(f"Nothing was uploaded: {len(problems)} problem(s) in the test files.", problems=problems[:20])
        with _lock:
            _state.update(phase="reading", message="Reading which tests Supabase already holds…")
        store.refresh()  # compare with what Supabase holds now, not with a cache up to five minutes old
        remote = {t["id"]: t for t in store.list_tests()}
        changed = [t for t in local if t["id"] not in remote or (not only_new and not _same(t, remote[t["id"]]))]
    except Exception as e:  # noqa: BLE001
        log.exception("Could not compare the tests")
        return _finish(f"Could not read the tests from Supabase: {e}")
    if not changed:
        return _finish("Supabase already has every test; nothing to upload.")
    with _lock:
        _state.update(phase="uploading", total=len(changed), done=0, message=f"Uploading {len(changed)} tests…")
    _upload(store, changed)


def start(store, local_tests=None, public_dir=PUBLIC_DIR, only_new=False):
    """
    Start checking and uploading, and answer at once with the status (it never raises, and never waits for Supabase).
    `only_new` uploads only tests Supabase does not have yet; tests that exist are left as they are there.
    """
    if not reads_tests_from_supabase(store):
        message = FILES_MESSAGE if getattr(store, "name", "") == "supabase" else \
            "This site reads its tests from the files in content/, so there is nothing to upload."
        with _lock:
            _state.update(running=False, phase="", total=0, done=0, failed=[], problems=[], message=message)
            return _snapshot()
    with _lock:
        if _state["running"]:
            return _snapshot()
        _state.update(running=True, phase="checking", total=0, done=0, failed=[], problems=[], message="Starting…")
    threading.Thread(target=_work, args=(store, local_tests, public_dir, only_new), daemon=True, name="content-sync").start()
    return status()
