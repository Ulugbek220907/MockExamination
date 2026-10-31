"""
Keep-alive HTTP(S) for the Supabase clients.

`urlopen(request, timeout)` is a drop-in for urllib.request.urlopen: it takes a
urllib.request.Request, returns a response with .status, .headers and .read(),
and raises urllib.error.HTTPError / URLError like urllib does. The difference
is that connections stay open between calls, shared by all threads, so a call
costs one round trip instead of a new TCP + TLS handshake (three or more round
trips) every time. With the database on another continent that is the
difference between about a quarter of a second and most of a second per query.

`keep_warm(make_request)` starts a background thread that sends a tiny request
on the idle connections now and then, so they are still open (and nobody waits
for a handshake) when the next visitor arrives.

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
MAX_IDLE_SECONDS = 50
MAX_IDLE_PER_HOST = 24

_lock = threading.Lock()
_idle = {}  # (scheme, netloc, timeout) -> [(connection, last used)], most recent last
_STALE_ERRORS = (http.client.RemoteDisconnected, ConnectionError)


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
    """The idle connections, by host (for tests and diagnostics)."""
    return _idle


def _take(key):
    """A fresh idle connection to this host, or None."""
    now = time.monotonic()
    stale = []
    conn = None
    with _lock:
        stack = _idle.get(key) or []
        while stack:
            candidate, used = stack.pop()
            if now - used <= MAX_IDLE_SECONDS:
                conn = candidate
                break
            stale.append(candidate)
        if not stack:
            _idle.pop(key, None)
    for c in stale:
        c.close()
    return conn


def _give(key, conn):
    with _lock:
        stack = _idle.setdefault(key, [])
        stack.append((conn, time.monotonic()))
        extra = stack[:-MAX_IDLE_PER_HOST] if len(stack) > MAX_IDLE_PER_HOST else []
        del stack[:len(extra)]
    for c, _ in extra:
        c.close()


def _proxied(parts):
    return bool(urllib.request.getproxies().get(parts.scheme)) and not urllib.request.proxy_bypass(parts.hostname or "")


def _key(parts, timeout):
    return (parts.scheme, parts.netloc, timeout)


def _new_connection(parts, timeout):
    cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
    return cls(parts.netloc, timeout=timeout)


def urlopen(req, timeout=15):
    parts = urllib.parse.urlsplit(req.full_url)
    if parts.scheme not in ("http", "https") or _proxied(parts):
        return urllib.request.urlopen(req, timeout=timeout)

    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    headers = dict(req.header_items())
    key = _key(parts, timeout)
    for attempt in (1, 2):
        conn = _take(key) if attempt == 1 else None
        reused = conn is not None
        if conn is None:
            conn = _new_connection(parts, timeout)
        try:
            conn.request(req.get_method(), path, body=req.data, headers=headers)
            resp = conn.getresponse()
            body = resp.read()
        except (http.client.HTTPException, OSError) as e:
            conn.close()
            # A kept-alive connection the server has just closed fails before the
            # request is handled: retry once on a new connection.
            if reused and attempt == 1 and isinstance(e, _STALE_ERRORS):
                continue
            raise urllib.error.URLError(e) from e
        if resp.will_close:
            conn.close()
        else:
            _give(key, conn)
        if resp.status >= 400:
            raise urllib.error.HTTPError(req.full_url, resp.status, resp.reason, resp.msg, io.BytesIO(body))
        return _Response(resp.status, resp.msg, body)


def keep_warm(make_request, every=25, spare=3):
    """
    Keep `spare` connections to make_request()'s host open: every `every` seconds,
    send make_request() (a cheap GET) on each idle connection, opening new ones
    when there are fewer than `spare`. Runs in a daemon thread; errors are ignored.
    Returns the thread (None if the host goes through a proxy); thread.stop() ends it.
    """
    sample = make_request()
    parts = urllib.parse.urlsplit(sample.full_url)
    if parts.scheme not in ("http", "https") or _proxied(parts):
        return None

    def ping(conn):
        req = make_request()
        p = urllib.parse.urlsplit(req.full_url)
        conn.request("GET", (p.path or "/") + (f"?{p.query}" if p.query else ""), headers=dict(req.header_items()))
        resp = conn.getresponse()
        resp.read()
        return not resp.will_close

    stopped = threading.Event()

    def loop():
        import concurrent.futures
        workers = concurrent.futures.ThreadPoolExecutor(max_workers=spare, thread_name_prefix="keepwarm")
        while not stopped.is_set():
            with _lock:
                timeouts = {k[2] for k in _idle if k[:2] == (parts.scheme, parts.netloc)} | {15}
            for timeout in sorted(timeouts):
                key = (parts.scheme, parts.netloc, timeout)
                conns = []
                while len(conns) < spare:
                    c = _take(key)
                    if c is None:
                        break
                    conns.append(c)
                if timeout == 15:
                    conns += [_new_connection(parts, timeout) for _ in range(spare - len(conns))]

                def refresh(c, key=key):
                    try:
                        if ping(c):
                            _give(key, c)
                            return
                    except (http.client.HTTPException, OSError):
                        pass
                    c.close()

                list(workers.map(refresh, conns))
            stopped.wait(every)
        workers.shutdown(wait=False)

    thread = threading.Thread(target=loop, daemon=True, name="db-keep-warm")
    thread.stop = stopped.set
    thread.start()
    return thread
