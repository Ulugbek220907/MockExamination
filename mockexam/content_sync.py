"""
Bring the tests stored in Supabase up to date with the test files in content/.

Production reads its tests from Supabase, so a test added to content/ (or a change to its free/paid
flag) is invisible on the live site until it is uploaded. scripts/seed_supabase.py does that from a
laptop; this does it from the running site, with the credentials it already has (Admin → Tests, or
POST /api/admin/sync-content). Only tests that differ from what Supabase holds are uploaded, and
nothing is uploaded at all if any test file is invalid.

The upload runs in a background thread: a full sync can take a minute or two, longer than a browser
request should wait. `status()` reports its progress.
"""

import json
import logging
import os
import threading

from . import content, storage

log = logging.getLogger("mockexam.content_sync")

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")

_lock = threading.Lock()
_state = {"running": False, "total": 0, "done": 0, "failed": [], "problems": [], "message": "Not run yet."}


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


def _run(store, changed):
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
        _state["running"] = False
        failed = len(_state["failed"])
        _state["message"] = (f"Uploaded {_state['done'] - failed} of {_state['total']} tests; {failed} failed. See the server log."
                             if failed else f"Done: {_state['total']} tests uploaded and the site reloaded them.")


def start(store, local_tests=None, public_dir=PUBLIC_DIR):
    """Check the files and start the upload. Returns the status; never raises."""
    if getattr(store, "name", "") != "supabase":
        with _lock:
            _state.update(running=False, total=0, done=0, failed=[], problems=[],
                          message="This site reads its tests from the files in content/, so there is nothing to upload.")
        return status()
    with _lock:
        if _state["running"]:
            return dict(_state, failed=list(_state["failed"]), problems=list(_state["problems"]))
    try:
        store.refresh()  # compare with what Supabase holds now, not with a cache up to five minutes old
        problems, changed = plan(store, local_tests, public_dir)
    except Exception as e:  # noqa: BLE001
        log.exception("Could not compare the tests")
        with _lock:
            _state.update(running=False, total=0, done=0, failed=[], problems=[], message=f"Could not read the tests from Supabase: {e}")
        return status()
    with _lock:
        if problems:
            _state.update(running=False, total=0, done=0, failed=[], problems=problems[:20],
                          message=f"Nothing was uploaded: {len(problems)} problem(s) in the test files.")
            return dict(_state, failed=[], problems=list(_state["problems"]))
        if not changed:
            _state.update(running=False, total=0, done=0, failed=[], problems=[], message="Supabase already has every test; nothing to upload.")
            return status()
        _state.update(running=True, total=len(changed), done=0, failed=[], problems=[], message=f"Uploading {len(changed)} tests…")
    threading.Thread(target=_run, args=(store, changed), daemon=True).start()
    return status()
