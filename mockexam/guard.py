"""
Protection against people who try to take the site down or run up its bills. docs/SECURITY.md explains each one.

Most attacks on a small site are not clever: a script repeats one request many times, from many addresses. What it
can cost us, and the limit that stops it:

  sign-in emails     the email service allows ~100 a day on its free plan; a script asking for codes to random
                     addresses would use them up (and hurt the domain's reputation)
                       -> SIGNIN_EMAILS_PER_DAY for the whole site, plus the per-address limits in api.py, plus an
                          optional CAPTCHA (Cloudflare Turnstile) when TURNSTILE_SECRET_KEY is set
  database rows      tests can be submitted without an account; every submission is a row
                       -> SUBMITS_PER_USER_PER_HOUR (signed in), SUBMITS_PER_IP_PER_HOUR (signed out), and
                          ANON_SAVES_PER_DAY for signed-out visitors (over it the result is still shown, only not saved)
  bandwidth          the Listening audio is about 7 MB a test; the host charges for traffic over its allowance
                       -> AUDIO_MB_PER_IP_PER_HOUR per visitor (and Cloudflare's cache, which serves repeats for free)
  storage            Speaking recordings (about 2 MB a minute)
                       -> SPEAKING_UPLOAD_MB_PER_DAY per person (in speaking.py), SPEAKING_UPLOAD_GB_PER_DAY for the
                          whole site, and at most UPLOADS_AT_ONCE recordings being received at the same moment
  emails to the owner  each Feedback message notifies the owner -> FEEDBACK_PER_DAY
  analytics rows     -> EVENTS_PER_DAY (over it, events are dropped quietly)
  payment orders     -> ORDERS_PER_USER_PER_HOUR

The day counts live in memory: a restart starts them again, which is fine for a safety net.

Behind Cloudflare (recommended, free: it caches the audio files and absorbs floods) the address of the visitor comes
in the CF-Connecting-IP header, which is believed only when the request really comes from Cloudflare's network
(TRUST_CLOUDFLARE=1). With ORIGIN_SECRET set, requests that do not carry the header Cloudflare adds are refused, so
nobody can go around Cloudflare to the Render address.
"""

import hmac
import ipaddress
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .db import now

log = logging.getLogger("mockexam.guard")


def _int_env(name, default):
    try:
        return max(0, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Addresses
# --------------------------------------------------------------------------

# https://www.cloudflare.com/ips (checked 26 November 2026)
CLOUDFLARE_NETWORKS = [ipaddress.ip_network(n) for n in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22", "141.101.64.0/18", "108.162.192.0/18",
    "190.93.240.0/20", "188.114.96.0/20", "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32", "2405:8100::/32", "2a06:98c0::/29",
    "2c0f:f248::/32")]


def trust_cloudflare():
    return os.environ.get("TRUST_CLOUDFLARE", "").strip() in ("1", "true", "yes", "on")


def from_cloudflare(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in CLOUDFLARE_NETWORKS)


def visitor_key(ip):
    """
    The address limits are counted against. An IPv6 address is cut to its /64 network: one home or phone gets a whole
    /64 and can change the rest at will, so counting single addresses would let one person look like millions.
    """
    try:
        addr = ipaddress.ip_address(str(ip).strip())
    except ValueError:
        return str(ip)
    if addr.version == 6:
        if addr.ipv4_mapped:   # ::ffff:1.2.3.4 is the IPv4 address 1.2.3.4
            return str(addr.ipv4_mapped)
        return str(ipaddress.ip_network(f"{addr}/64", strict=False))
    return str(addr)


def origin_secret():
    return os.environ.get("ORIGIN_SECRET", "").strip()


def origin_allowed(headers, path):
    """With ORIGIN_SECRET set, only requests carrying it (added by Cloudflare) are served; Render's health check is let in."""
    secret = origin_secret()
    if not secret or path in ("/healthz", "/api/health"):
        return True
    return hmac.compare_digest(headers.get("X-Origin-Secret", ""), secret)


# --------------------------------------------------------------------------
# Counting
# --------------------------------------------------------------------------

class DayBudget:
    """How much of each thing the whole site has used today; take() says whether one more is allowed."""

    LIMITS = {   # name: (environment variable, default)
        "signin_email": ("SIGNIN_EMAILS_PER_DAY", 90),
        "anon_save": ("ANON_SAVES_PER_DAY", 2000),
        "feedback": ("FEEDBACK_PER_DAY", 100),
        "event": ("EVENTS_PER_DAY", 30000),
        "upload_mb": ("SPEAKING_UPLOAD_GB_PER_DAY", 3),   # counted in MB, set in GB
    }

    def __init__(self):
        self.lock = threading.Lock()
        self.day = None
        self.used = {}
        self.warned = set()

    def limit(self, name):
        env, default = self.LIMITS[name]
        value = _int_env(env, default)
        return value * 1024 if name == "upload_mb" else value

    def _roll(self):
        today = now().date()
        if today != self.day:
            self.day, self.used, self.warned = today, {}, set()

    def take(self, name, amount=1):
        with self.lock:
            self._roll()
            used = self.used.get(name, 0)
            if used + amount > self.limit(name):
                if name not in self.warned:
                    self.warned.add(name)
                    log.warning("Day budget used up: %s (%s of %s)", name, used, self.limit(name))
                return False
            self.used[name] = used + amount
            return True

    def snapshot(self):
        with self.lock:
            self._roll()
            return {name: {"used": self.used.get(name, 0), "limit": self.limit(name)} for name in self.LIMITS}


DAY = DayBudget()


class Window:
    """At most `limit` events per key in `seconds` (sliding), with memory kept bounded."""

    def __init__(self, env, default, seconds):
        self.env, self.default, self.seconds = env, default, seconds
        self.hits = {}
        self.lock = threading.Lock()

    def allow(self, key):
        limit = _int_env(self.env, self.default)
        t = time.monotonic()
        with self.lock:
            q = [x for x in self.hits.get(key, ()) if t - x < self.seconds]
            if len(q) >= limit:
                self.hits[key] = q
                return False
            q.append(t)
            self.hits[key] = q
            if len(self.hits) > 20000:
                for k in list(self.hits)[:10000]:
                    del self.hits[k]
            return True


# Reading, Listening and Writing answers sent: per account when signed in, per address when not (an address can be a
# whole school class behind one router, so its limit is higher).
SUBMITS_USER = Window("SUBMITS_PER_USER_PER_HOUR", 30, 3600)
SUBMITS_IP = Window("SUBMITS_PER_IP_PER_HOUR", 120, 3600)
ORDERS = Window("ORDERS_PER_USER_PER_HOUR", 12, 3600)
# Audio files (Listening recordings) sent to one visitor in an hour, in MB: a test is about 7 MB.
AUDIO_MB = {}
AUDIO_LOCK = threading.Lock()


def audio_allowed(key):
    limit = _int_env("AUDIO_MB_PER_IP_PER_HOUR", 400)
    t = time.monotonic()
    with AUDIO_LOCK:
        used = [(x, mb) for x, mb in AUDIO_MB.get(key, ()) if t - x < 3600]
        AUDIO_MB[key] = used
        if len(AUDIO_MB) > 20000:
            for k in list(AUDIO_MB)[:10000]:
                del AUDIO_MB[k]
        return sum(mb for _, mb in used) < limit


def audio_sent(key, size):
    if size:
        with AUDIO_LOCK:
            AUDIO_MB.setdefault(key, []).append((time.monotonic(), size / (1024 * 1024)))


class Gate:
    """At most N of something at the same moment (recordings being received)."""

    def __init__(self, env, default):
        self.env, self.default = env, default
        self.count = 0
        self.lock = threading.Lock()

    def enter(self):
        with self.lock:
            if self.count >= _int_env(self.env, self.default):
                return False
            self.count += 1
            return True

    def leave(self):
        with self.lock:
            self.count = max(0, self.count - 1)


UPLOADS = Gate("UPLOADS_AT_ONCE", 24)

# Recordings played back: a browser asks for each one in a few pieces while it plays and seeks.
RECORDING_FETCHES = Window("RECORDING_FETCHES_PER_USER_PER_HOUR", 600, 3600)


class SmallCache:
    """The last recordings played, kept in memory (at most `megabytes`), so playing and seeking do not fetch the whole
    file from storage again for every piece the browser asks for: storage charges for what is downloaded."""

    def __init__(self, megabytes=48):
        self.limit = megabytes * 1024 * 1024
        self.items = {}
        self.size = 0
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            value = self.items.pop(key, None)
            if value is not None:
                self.items[key] = value   # most recently used last
            return value

    def put(self, key, value):
        if value is None or len(value) > self.limit // 4:
            return
        with self.lock:
            old = self.items.pop(key, None)
            if old is not None:
                self.size -= len(old)
            self.items[key] = value
            self.size += len(value)
            while self.size > self.limit and self.items:
                first = next(iter(self.items))
                self.size -= len(self.items.pop(first))


RECORDINGS = SmallCache()


# --------------------------------------------------------------------------
# Cloudflare Turnstile (a CAPTCHA without puzzles), for sign-in codes
# --------------------------------------------------------------------------

TURNSTILE_VERIFY = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def turnstile_site_key():
    return os.environ.get("TURNSTILE_SITE_KEY", "").strip()


def turnstile_on():
    return bool(turnstile_site_key() and os.environ.get("TURNSTILE_SECRET_KEY", "").strip())


def turnstile_ok(token, ip=None):
    """True when Cloudflare confirms the browser passed the check (or when Turnstile is not set up)."""
    if not turnstile_on():
        return True
    token = str(token or "").strip()
    if not token or len(token) > 4096:
        return False
    form = {"secret": os.environ.get("TURNSTILE_SECRET_KEY", "").strip(), "response": token}
    if ip:
        form["remoteip"] = ip
    req = urllib.request.Request(TURNSTILE_VERIFY, data=urllib.parse.urlencode(form).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read() or b"{}")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        # Cloudflare unreachable: let the person in rather than lock everyone out; the other limits still apply.
        log.warning("Turnstile check could not be made: %s", e)
        return True
    return bool(data.get("success"))
