"""
A read cache in front of the database.

The database (Supabase) can be far from the web server, so every query costs a
long round trip, and a signed-in page needs several: the profile, the plan,
the history, examiner counters. Most of these rows change rarely, and when they
change it is through this server.

CachedDb wraps a SqliteDb or RestDb and keeps the result of select() and count()
on the tables in CACHED_TABLES for a while. Any insert, update or delete on a
table through the wrapper drops that table's cached results at once, so the
server always sees its own writes. Writes that bypass the wrapper (the stores'
own SQL or RPC calls) call invalidate(table) themselves. Changes made outside
the server (for example in the Supabase dashboard) show up after at most the
table's lifetime below.

Tables used for payments, sign-in codes and analytics are never cached.
"""

import concurrent.futures
import copy
import json
import threading
import time

# Seconds a cached result may live, per table.
CACHED_TABLES = {
    "profiles": 600,
    "examiners": 600,
    "subscription_periods": 120,
    "checks": 300,
    "reading_attempts": 600,
    "listening_attempts": 600,
    "writing_submissions": 600,
    "speaking_submissions": 600,
    "recordings": 600,
}

MAX_ENTRIES = 20000

_READERS = concurrent.futures.ThreadPoolExecutor(max_workers=8, thread_name_prefix="db-read")


def gather(*calls):
    """Run independent reads side by side and return their results in order (errors are raised)."""
    if len(calls) <= 1:
        return [c() for c in calls]
    futures = [_READERS.submit(c) for c in calls]
    return [f.result() for f in futures]


class CachedDb:
    def __init__(self, db, tables=None):
        self.db = db
        self.tables = dict(CACHED_TABLES if tables is None else tables)
        self._lock = threading.Lock()
        self._entries = {}   # (table, key) -> (expires_at, value)
        self._generation = {}  # table -> number of writes seen; guards against storing a result older than a write

    def __getattr__(self, name):
        # Everything else (name, path, helpers) is the wrapped database's.
        return getattr(self.db, name)

    # -- cache ------------------------------------------------------------------
    def invalidate(self, *tables):
        with self._lock:
            for table in tables:
                self._generation[table] = self._generation.get(table, 0) + 1
                for key in [k for k in self._entries if k[0] == table]:
                    del self._entries[key]

    def clear(self):
        with self._lock:
            for table in {k[0] for k in self._entries}:
                self._generation[table] = self._generation.get(table, 0) + 1
            self._entries.clear()

    def _cached(self, table, key, load):
        ttl = self.tables.get(table)
        if not ttl:
            return load()
        cache_key = (table, key)
        now = time.monotonic()
        with self._lock:
            hit = self._entries.get(cache_key)
            generation = self._generation.get(table, 0)
            if hit and hit[0] > now:
                return copy.deepcopy(hit[1])
        value = load()
        with self._lock:
            # A write that happened while we were reading makes this result stale: do not keep it.
            if self._generation.get(table, 0) == generation:
                if len(self._entries) >= MAX_ENTRIES:
                    self._entries.clear()
                self._entries[cache_key] = (now + ttl, copy.deepcopy(value))
        return value

    @staticmethod
    def _key(*parts):
        return json.dumps(parts, sort_keys=True, default=str)

    # -- reads ------------------------------------------------------------------
    def select(self, table, where=None, order=None, limit=None):
        return self._cached(table, self._key("select", where, order, limit),
                            lambda: self.db.select(table, where, order=order, limit=limit))

    def count(self, table, where=None):
        return self._cached(table, self._key("count", where), lambda: self.db.count(table, where))

    # -- writes -----------------------------------------------------------------
    def insert(self, table, row, ignore_conflict=False):
        try:
            return self.db.insert(table, row, ignore_conflict=ignore_conflict)
        finally:
            self.invalidate(table)

    def update(self, table, where, values):
        try:
            return self.db.update(table, where, values)
        finally:
            self.invalidate(table)

    def delete(self, table, where):
        try:
            return self.db.delete(table, where)
        finally:
            self.invalidate(table)
