"""
Table access for accounts, payments, examiners and checks.

Two interchangeable backends expose the same four operations:

  select(table, where, order, limit)   -> list of rows (dicts)
  insert(table, row, ignore_conflict)  -> inserted row, or None if it already existed
  update(table, where, values)         -> list of updated rows
  delete(table, where)                 -> number of deleted rows

SqliteDb  – local development and the test suite (a file next to the attempts).
RestDb    – Supabase, through the normal REST table endpoints. Every request
            carries the server secret in the `x-app-key` header; Row Level
            Security only lets such requests through (see supabase/schema.sql).

`where` maps column -> value (equality; None means IS NULL) or column ->
(operator, value) with operator one of eq, neq, gt, gte, lt, lte, in, is,
ilike (case-insensitive "contains"). The business logic only uses these
operations, so it behaves the same on both backends.
"""

import datetime
import json
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request

from . import pool

# Column types that need converting in SQLite (Postgres/PostgREST return them natively).
JSON_COLUMNS = {
    "checks": {"result"},
    "reading_attempts": {"answers", "breakdown"},
    "listening_attempts": {"answers", "breakdown"},
    "writing_submissions": {"analysis", "assessment"},
}
BOOL_COLUMNS = {
    "examiners": {"does_writing", "does_speaking", "accepting", "approved"},
}
# Tables whose rows get `created_at` filled in by SQLite callers that omit it.
TIMESTAMPED = {"profiles", "orders", "subscription_periods", "click_transactions", "examiners", "checks",
               "speaking_submissions", "recordings"}

ALLOWED_TABLES = {
    "profiles", "orders", "subscription_periods", "payme_transactions", "click_transactions",
    "examiners", "checks", "reading_attempts", "listening_attempts", "writing_submissions",
    "speaking_submissions", "recordings",
}

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'student',
    created_at TEXT,
    last_login_at TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    provider TEXT,
    examiner_id TEXT,
    submission_id INTEGER,
    note TEXT,
    created_at TEXT,
    paid_at TEXT,
    cancelled_at TEXT
);
CREATE TABLE IF NOT EXISTS subscription_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    order_id INTEGER UNIQUE,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    source TEXT NOT NULL,
    note TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS payme_transactions (
    id TEXT PRIMARY KEY,
    order_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    state INTEGER NOT NULL,
    payme_time INTEGER NOT NULL,
    create_time INTEGER NOT NULL,
    perform_time INTEGER NOT NULL DEFAULT 0,
    cancel_time INTEGER NOT NULL DEFAULT 0,
    reason INTEGER
);
CREATE TABLE IF NOT EXISTS click_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    click_trans_id INTEGER NOT NULL UNIQUE,
    order_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS examiners (
    user_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    headline TEXT,
    bio TEXT,
    does_writing INTEGER NOT NULL DEFAULT 1,
    does_speaking INTEGER NOT NULL DEFAULT 1,
    accepting INTEGER NOT NULL DEFAULT 1,
    approved INTEGER NOT NULL DEFAULT 0,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    student_id TEXT NOT NULL,
    examiner_id TEXT NOT NULL,
    submission_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'waiting',
    result TEXT,
    overall_band REAL,
    created_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    rating INTEGER,
    review TEXT,
    reviewed_at TEXT
);
CREATE TABLE IF NOT EXISTS speaking_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    test_id TEXT NOT NULL,
    candidate_name TEXT,
    mode TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'recording',
    time_spent_seconds INTEGER,
    created_at TEXT,
    completed_at TEXT,
    recordings_deleted_at TEXT
);
CREATE TABLE IF NOT EXISTS recordings (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    submission_id INTEGER NOT NULL,
    question_key TEXT NOT NULL,
    mime TEXT NOT NULL,
    duration REAL,
    size INTEGER NOT NULL,
    path TEXT NOT NULL,
    created_at TEXT,
    UNIQUE (submission_id, question_key)
);
CREATE INDEX IF NOT EXISTS idx_speaking_user ON speaking_submissions(user_id, created_at);
"""

# Early development databases had placeholder Speaking tables with other columns.
_REPLACED_TABLES = {"speaking_submissions": "recordings_deleted_at", "recordings": "path"}


class DbError(Exception):
    pass


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def iso(dt):
    """Timestamps are stored as ISO 8601 UTC strings in the same shape Postgres returns."""
    return dt.astimezone(datetime.timezone.utc).isoformat(timespec="microseconds")


def parse_time(value):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    dt = datetime.datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)


def _check_table(table):
    if table not in ALLOWED_TABLES:
        raise DbError(f"unknown table {table!r}")


def _normalise_where(where):
    out = []
    for col, cond in (where or {}).items():
        if not col.replace("_", "").isalnum():
            raise DbError(f"bad column {col!r}")
        if isinstance(cond, tuple):
            op, value = cond
        elif cond is None:
            op, value = "is", None
        else:
            op, value = "eq", cond
        if op not in ("eq", "neq", "gt", "gte", "lt", "lte", "in", "is", "ilike"):
            raise DbError(f"bad operator {op!r}")
        out.append((col, op, value))
    return out


# --------------------------------------------------------------------------
# SQLite
# --------------------------------------------------------------------------

class SqliteDb:
    name = "sqlite"
    SQL_OPS = {"eq": "=", "neq": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}

    def __init__(self, path, lock=None):
        self.path = path
        self.lock = lock or threading.Lock()
        with self.lock, self._connect() as conn:
            for table, column in _REPLACED_TABLES.items():
                cols = {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')}
                if cols and column not in cols:
                    conn.execute(f'DROP TABLE "{table}"')
            conn.executescript(SQLITE_SCHEMA)

    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _encode(self, table, row):
        out = {}
        for k, v in row.items():
            if k in JSON_COLUMNS.get(table, ()) and v is not None:
                v = json.dumps(v, ensure_ascii=False)
            elif isinstance(v, bool):
                v = int(v)
            elif isinstance(v, datetime.datetime):
                v = iso(v)
            out[k] = v
        return out

    def _decode(self, table, row):
        d = dict(row)
        for k in JSON_COLUMNS.get(table, ()):
            if isinstance(d.get(k), str):
                d[k] = json.loads(d[k])
        for k in BOOL_COLUMNS.get(table, ()):
            if k in d and d[k] is not None:
                d[k] = bool(d[k])
        return d

    def _where_sql(self, table, where):
        parts, params = [], []
        for col, op, value in _normalise_where(where):
            if op == "is" or (op == "eq" and value is None):
                if value is None:
                    parts.append(f'"{col}" IS NULL')
                else:
                    parts.append(f'"{col}" = ?')
                    params.append(int(value) if isinstance(value, bool) else value)
            elif op == "in":
                values = list(value)
                if not values:
                    parts.append("0")
                    continue
                parts.append(f'"{col}" IN ({",".join("?" * len(values))})')
                params.extend(values)
            elif op == "ilike":
                parts.append(f'"{col}" LIKE ?')
                params.append(f"%{value}%")
            else:
                if isinstance(value, datetime.datetime):
                    value = iso(value)
                elif isinstance(value, bool):
                    value = int(value)
                parts.append(f'"{col}" {self.SQL_OPS[op]} ?')
                params.append(value)
        return (" WHERE " + " AND ".join(parts)) if parts else "", params

    def select(self, table, where=None, order=None, limit=None):
        _check_table(table)
        sql_where, params = self._where_sql(table, where)
        sql = f'SELECT * FROM "{table}"{sql_where}'
        if order:
            sql += " ORDER BY " + ", ".join(f'"{c}" {"DESC" if d == "desc" else "ASC"}' for c, d in order)
        if limit:
            sql += f" LIMIT {int(limit)}"
        with self.lock, self._connect() as conn:
            return [self._decode(table, r) for r in conn.execute(sql, params).fetchall()]

    def insert(self, table, row, ignore_conflict=False):
        _check_table(table)
        row = dict(row)
        if table in TIMESTAMPED and not row.get("created_at"):
            row["created_at"] = iso(now())
        row = self._encode(table, row)
        cols = list(row)
        sql = (f'INSERT {"OR IGNORE " if ignore_conflict else ""}INTO "{table}" '
               f'({",".join(chr(34) + c + chr(34) for c in cols)}) VALUES ({",".join("?" * len(cols))})')
        with self.lock, self._connect() as conn:
            try:
                cur = conn.execute(sql, [row[c] for c in cols])
            except sqlite3.IntegrityError as e:
                raise DbError(str(e)) from e
            if cur.rowcount == 0:
                return None
            got = conn.execute(f'SELECT * FROM "{table}" WHERE rowid = ?', (cur.lastrowid,)).fetchone()
            return self._decode(table, got)

    def update(self, table, where, values):
        _check_table(table)
        if not where:
            raise DbError("update without a filter")
        values = self._encode(table, values)
        sql_where, params = self._where_sql(table, where)
        sets = ", ".join(f'"{c}" = ?' for c in values)
        with self.lock, self._connect() as conn:
            rowids = [r[0] for r in conn.execute(f'SELECT rowid FROM "{table}"{sql_where}', params).fetchall()]
            if not rowids:
                return []
            marks = ",".join("?" * len(rowids))
            conn.execute(f'UPDATE "{table}" SET {sets} WHERE rowid IN ({marks})', list(values.values()) + rowids)
            rows = conn.execute(f'SELECT * FROM "{table}" WHERE rowid IN ({marks})', rowids).fetchall()
            return [self._decode(table, r) for r in rows]

    def delete(self, table, where):
        _check_table(table)
        if not where:
            raise DbError("delete without a filter")
        sql_where, params = self._where_sql(table, where)
        with self.lock, self._connect() as conn:
            return conn.execute(f'DELETE FROM "{table}"{sql_where}', params).rowcount


# --------------------------------------------------------------------------
# Supabase (PostgREST)
# --------------------------------------------------------------------------

def _rest_value(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime.datetime):
        return iso(value)
    return str(value)


def _rest_list_item(value):
    text = _rest_value(value)
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


class RestDb:
    name = "supabase"

    def __init__(self, url, api_key, app_secret, timeout=15):
        self.rest = url.rstrip("/") + "/rest/v1"
        self.key = api_key
        self.secret = app_secret
        self.timeout = timeout

    def _headers(self, prefer=None):
        h = {
            "apikey": self.key,
            "x-app-key": self.secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.key.startswith("eyJ"):
            h["Authorization"] = f"Bearer {self.key}"
        if prefer:
            h["Prefer"] = prefer
        return h

    def _query(self, where=None, order=None, limit=None, extra=None):
        params = []
        for col, op, value in _normalise_where(where):
            if op == "in":
                params.append((col, "in.(" + ",".join(_rest_list_item(v) for v in value) + ")"))
            elif op == "is" or (op == "eq" and value is None):
                params.append((col, "is." + _rest_value(value)))
            elif op == "ilike":
                params.append((col, "ilike.*" + str(value).replace("*", "") + "*"))
            else:
                params.append((col, f"{op}.{_rest_value(value)}"))
        if order:
            params.append(("order", ",".join(f"{c}.{'desc' if d == 'desc' else 'asc'}" for c, d in order)))
        if limit:
            params.append(("limit", str(int(limit))))
        params.extend(extra or [])
        return urllib.parse.urlencode(params)

    def _request(self, method, table, query="", body=None, prefer=None):
        _check_table(table)
        url = f"{self.rest}/{table}" + (f"?{query}" if query else "")
        data = json.dumps(body, ensure_ascii=False, default=_rest_value).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(prefer), method=method)
        try:
            with pool.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else []
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            raise DbError(f"{method} {table} failed ({e.code}): {detail}") from e
        except urllib.error.URLError as e:
            raise DbError(f"{method} {table} failed: {e.reason}") from e

    def select(self, table, where=None, order=None, limit=None):
        return self._request("GET", table, self._query(where, order, limit, [("select", "*")]))

    def insert(self, table, row, ignore_conflict=False):
        prefer = "return=representation"
        query = ""
        if ignore_conflict:
            prefer += ",resolution=ignore-duplicates"
            if isinstance(ignore_conflict, str):
                query = urllib.parse.urlencode([("on_conflict", ignore_conflict)])
        rows = self._request("POST", table, query, body=row, prefer=prefer)
        return rows[0] if rows else None

    def update(self, table, where, values):
        if not where:
            raise DbError("update without a filter")
        return self._request("PATCH", table, self._query(where), body=values, prefer="return=representation")

    def delete(self, table, where):
        if not where:
            raise DbError("delete without a filter")
        return len(self._request("DELETE", table, self._query(where), prefer="return=representation"))
