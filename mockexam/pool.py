"""
Keep-alive HTTP(S) for the Supabase clients.

`urlopen(request, timeout)` is a drop-in for urllib.request.urlopen: it takes a
urllib.request.Request, returns a response with .status, .headers and .read(),
and raises urllib.error.HTTPError / URLError like urllib does. The difference
is that each worker thread keeps its connection to a host open between calls,
so a call costs one round trip instead of a new TCP + TLS handshake (three or
more round trips) every time.

When a proxy is configured for the URL, the call goes through urllib itself,
since http.client does not read proxy settings.
"""

import http.client
import io
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# Reuse a connection only while it is fresh; servers close idle ones after a while.
MAX_IDLE_SECONDS = 30

_local = threading.local()
_STALE_ERRORS = (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError)


class _Response:
    def __init__(self, status, headers, body):
        self.status = self.code = status
        self.headers = headers
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _connections():
    if not hasattr(_local, "conns"):
        _local.conns = {}
    return _local.conns


def _drop(key):
    entry = _connections().pop(key, None)
    if entry:
        entry[0].close()


def _proxied(parts):
    return bool(urllib.request.getproxies().get(parts.scheme)) and not urllib.request.proxy_bypass(parts.hostname or "")


def urlopen(req, timeout=15):
    parts = urllib.parse.urlsplit(req.full_url)
    if parts.scheme not in ("http", "https") or _proxied(parts):
        return urllib.request.urlopen(req, timeout=timeout)

    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    headers = dict(req.header_items())
    key = (parts.scheme, parts.netloc, timeout)
    conns = _connections()
    for attempt in (1, 2):
        entry = conns.get(key)
        if entry and time.monotonic() - entry[1] > MAX_IDLE_SECONDS:
            _drop(key)
            entry = None
        reused = entry is not None
        if entry:
            conn = entry[0]
        else:
            cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
            conn = cls(parts.netloc, timeout=timeout)
        try:
            conn.request(req.get_method(), path, body=req.data, headers=headers)
            resp = conn.getresponse()
            body = resp.read()
        except (http.client.HTTPException, OSError) as e:
            if reused:
                _drop(key)
            else:
                conn.close()
            # A kept-alive connection the server has just closed fails before the
            # request is handled: retry once on a new connection.
            if reused and attempt == 1 and isinstance(e, _STALE_ERRORS):
                continue
            raise urllib.error.URLError(e) from e
        if resp.will_close:
            if reused:
                _drop(key)
            else:
                conn.close()
        else:
            conns[key] = (conn, time.monotonic())
        if resp.status >= 400:
            raise urllib.error.HTTPError(req.full_url, resp.status, resp.reason, resp.msg, io.BytesIO(body))
        return _Response(resp.status, resp.msg, body)
