"""
The service's small database (SQLite): what was posted where, and the platform tokens it was connected with.

Put DATA_DIR on a persistent disk. Without one, a redeploy forgets what has been posted, and the daily run
could post the same day twice.
"""

import json
import os
import sqlite3
import threading
import time

SCHEMA = """
create table if not exists deliveries (
  day text not null, platform text not null, status text not null,
  attempts integer not null default 0, started_at real, finished_at real,
  external_id text, url text, error text,
  primary key (day, platform));
create table if not exists tokens (platform text primary key, data text not null, updated_at real not null);
create table if not exists media (day text primary key, key text not null, created_at real not null);
"""

# posting: the request is in flight. posted: done. failed: not posted, may be tried again.
# needs_review: it may have been posted, so nothing retries it; look at the platform, then retry or dismiss it here.
STATUSES = ("posting", "posted", "failed", "needs_review")


class Store:
    def __init__(self, path, clock=time.time):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.clock = clock
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        with self.lock:
            self.db.executescript(SCHEMA)

    def _run(self, sql, args=()):
        with self.lock:
            return self.db.execute(sql, args)

    # -- deliveries ----------------------------------------------------------
    def delivery(self, day, platform):
        row = self._run("select * from deliveries where day=? and platform=?", (day, platform)).fetchone()
        return dict(row) if row else None

    def deliveries(self, day=None, limit=200):
        if day:
            rows = self._run("select * from deliveries where day=? order by platform", (day,)).fetchall()
        else:
            rows = self._run("select * from deliveries order by day desc, platform limit ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def begin(self, day, platform):
        """Mark a post as in flight (counting the attempt). False if one is already in flight or posted."""
        with self.lock:
            row = self.delivery(day, platform)
            if row and row["status"] in ("posting", "posted", "needs_review"):
                return False
            attempts = (row["attempts"] if row else 0) + 1
            self._run("insert into deliveries(day, platform, status, attempts, started_at) values(?,?,?,?,?) "
                      "on conflict(day, platform) do update set status='posting', attempts=?, started_at=?, error=null",
                      (day, platform, "posting", attempts, self.clock(), attempts, self.clock()))
            return True

    def finish(self, day, platform, status, external_id=None, url=None, error=None):
        self._run("update deliveries set status=?, finished_at=?, external_id=?, url=?, error=? where day=? and platform=?",
                  (status, self.clock(), external_id, url, (error or "")[:500] or None, day, platform))

    def give_up(self, day, platform, attempts):
        """Count the attempts as used, so a failure that trying again cannot fix is not retried by the schedule."""
        self._run("update deliveries set attempts=? where day=? and platform=?", (attempts, day, platform))

    def reset(self, day, platform):
        """Forget a delivery that needs review so it can be tried again (the owner has checked the platform)."""
        self._run("delete from deliveries where day=? and platform=? and status in ('needs_review','failed')", (day, platform))

    # -- tokens --------------------------------------------------------------
    def token(self, platform):
        row = self._run("select data from tokens where platform=?", (platform,)).fetchone()
        return json.loads(row["data"]) if row else {}

    def save_token(self, platform, data):
        self._run("insert into tokens(platform, data, updated_at) values(?,?,?) "
                  "on conflict(platform) do update set data=excluded.data, updated_at=excluded.updated_at",
                  (platform, json.dumps(data), self.clock()))

    def delete_token(self, platform):
        self._run("delete from tokens where platform=?", (platform,))

    # -- media ---------------------------------------------------------------
    def media_key(self, day):
        """The unguessable address part under which the platforms may fetch the day's files."""
        import secrets
        with self.lock:
            row = self._run("select key from media where day=?", (day,)).fetchone()
            if row:
                return row["key"]
            key = secrets.token_urlsafe(18)
            self._run("insert into media(day, key, created_at) values(?,?,?)", (day, key, self.clock()))
            return key

    def day_for_media_key(self, key):
        row = self._run("select day from media where key=?", (key,)).fetchone()
        return row["day"] if row else None
