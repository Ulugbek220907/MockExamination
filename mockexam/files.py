"""
Private file storage for Speaking recordings.

LocalFiles     – a folder on disk (development and the test suite).
SupabaseFiles  – a private Supabase Storage bucket. Like the tables, the bucket
                 only accepts requests that carry the server secret in the
                 `x-app-key` header (see the storage policies in supabase/schema.sql),
                 so the public key alone can neither read nor list recordings.

Both expose put(path, data, mime), get(path) -> bytes or None, and delete(paths).
Paths look like "<user-id>/<submission-id>/<question-key>-<recording-id>.webm".
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

PATH_RE = re.compile(r"^[a-z0-9\-]+(/[a-z0-9\-]+)*\.[a-z0-9]+$")


class FileError(Exception):
    pass


def _check_path(path):
    if not PATH_RE.match(path) or ".." in path:
        raise FileError(f"bad file path {path!r}")
    return path


class LocalFiles:
    name = "local"

    def __init__(self, root):
        self.root = root

    def _full(self, path):
        return os.path.join(self.root, *_check_path(path).split("/"))

    def put(self, path, data, mime):
        full = self._full(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        tmp = full + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, full)

    def get(self, path):
        try:
            with open(self._full(path), "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def delete(self, paths):
        for path in paths:
            try:
                os.remove(self._full(path))
            except FileNotFoundError:
                pass


class SupabaseFiles:
    name = "supabase"

    def __init__(self, url, api_key, app_secret, bucket="speaking", timeout=30):
        self.base = url.rstrip("/") + "/storage/v1"
        self.key = api_key
        self.secret = app_secret
        self.bucket = bucket
        self.timeout = timeout

    def _headers(self, extra=None):
        h = {"apikey": self.key, "x-app-key": self.secret}
        if self.key.startswith("eyJ"):
            h["Authorization"] = f"Bearer {self.key}"
        h.update(extra or {})
        return h

    def _request(self, method, path, data=None, headers=None):
        req = urllib.request.Request(self.base + path, data=data, headers=self._headers(headers), method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if method == "GET" and e.code in (400, 404) and ("not_found" in detail.lower() or "not found" in detail.lower()):
                return None
            raise FileError(f"storage {method} failed ({e.code}): {detail}") from e
        except urllib.error.URLError as e:
            raise FileError(f"storage {method} failed: {e.reason}") from e

    def _object(self, path):
        return f"/object/{self.bucket}/" + urllib.parse.quote(_check_path(path))

    def put(self, path, data, mime):
        self._request("POST", self._object(path), data=data,
                      headers={"Content-Type": mime.split(";")[0], "x-upsert": "true", "Cache-Control": "no-cache"})

    def get(self, path):
        return self._request("GET", f"/object/authenticated/{self.bucket}/" + urllib.parse.quote(_check_path(path)))

    def delete(self, paths):
        paths = [_check_path(p) for p in paths]
        for i in range(0, len(paths), 100):
            self._request("DELETE", f"/object/{self.bucket}", data=json.dumps({"prefixes": paths[i:i + 100]}).encode(),
                          headers={"Content-Type": "application/json"})
