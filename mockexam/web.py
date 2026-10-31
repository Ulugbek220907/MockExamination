"""
Shared pieces for the HTTP handlers: security headers, JSON helpers, the
signed session cookie, and role checks.

The application settings carry the shared services, so handlers never import
the server module:
  settings["store"]   – LocalStore or SupabaseStore (store.db for tables)
  settings["auth"]    – SupabaseAuth or DevAuth
"""

import hmac
import json
import os
import time
from urllib.parse import urlparse

import tornado.ioloop
import tornado.web

from . import accounts, analytics

TRUST_PROXY = os.environ.get("TRUST_PROXY", "1") != "0"
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
MAX_BODY_BYTES = 256 * 1024
SESSION_COOKIE = "mx_session"
SESSION_DAYS = 30

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(self), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    # Browsers ignore this over plain HTTP, so local development is unaffected. Over HTTPS
    # it lets returning visitors skip the http:// -> https:// redirect.
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; font-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
}


async def in_thread(fn, *args):
    return await tornado.ioloop.IOLoop.current().run_in_executor(None, fn, *args)


class BaseHandler(tornado.web.RequestHandler):
    # Payment providers post forms and have no session; they are exempt from the JSON-only rule.
    ACCEPTS_FORMS = False

    def set_default_headers(self):
        for k, v in SECURITY_HEADERS.items():
            self.set_header(k, v)

    @property
    def store(self):
        return self.application.settings["store"]

    @property
    def db(self):
        return self.application.settings["store"].db

    def track(self, name, **fields):
        """Record a funnel event in the background: it never delays or fails the response."""
        return tornado.ioloop.IOLoop.current().run_in_executor(None, lambda: analytics.record(self.db, name, **fields))

    @property
    def auth(self):
        return self.application.settings["auth"]

    def _is_same_origin(self, origin):
        if not origin:
            return True
        origin_parsed = urlparse(origin)
        req_host = self.request.host.split(":")[0].lower()
        origin_host = (origin_parsed.hostname or "").lower()
        expected = {req_host, "localhost", "127.0.0.1"}
        if SITE_URL:
            sh = urlparse(SITE_URL).hostname
            if sh:
                expected.add(sh.lower())
        return origin_host in expected

    def prepare(self):
        # Defend against cross-site request forgery:
        # 1. Fetch Metadata (Sec-Fetch-Site): allow same-origin, same-site, and top-level navigation.
        #    Reject cross-site API fetches, subresource requests, and cross-site state-changing requests.
        # 2. Origin verification: reject cross-origin state-changing requests.
        # 3. Content-Type: require application/json for state-changing requests so standard HTML
        #    forms (which cannot send application/json) are refused.
        if not self.ACCEPTS_FORMS:
            sec_site = self.request.headers.get("Sec-Fetch-Site")
            if sec_site == "cross-site":
                is_top_nav = self.request.method in ("GET", "HEAD") and self.request.headers.get("Sec-Fetch-Mode") == "navigate"
                if not is_top_nav:
                    raise tornado.web.HTTPError(403, "Cross-site request blocked")
            if self.request.method in ("POST", "PUT", "PATCH", "DELETE"):
                origin = self.request.headers.get("Origin")
                if origin and not self._is_same_origin(origin):
                    raise tornado.web.HTTPError(403, "Cross-origin state change blocked")
                ctype = self.request.headers.get("Content-Type", "").split(";")[0].strip().lower()
                is_bearer = bool(self.request.headers.get("Authorization", "").startswith("Bearer "))
                if ctype != "application/json" and not (is_bearer and not self.request.body):
                    raise tornado.web.HTTPError(415, "Expected application/json")

    def send_json(self, payload, status=200):
        self.set_status(status)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.set_header("Cache-Control", "no-store")
        # How long the server took (visible in the browser's network panel), to spot slow requests.
        self.set_header("Server-Timing", f"app;dur={self.request.request_time() * 1000:.0f}")
        self.finish(json.dumps(payload, ensure_ascii=False, default=str))

    def send_error_json(self, status, message, code=None):
        body = {"error": message}
        if code:
            body["code"] = code
        self.send_json(body, status)

    def body_json(self):
        if len(self.request.body or b"") > MAX_BODY_BYTES:
            raise tornado.web.HTTPError(413)
        try:
            data = json.loads(self.request.body or b"{}")
        except (ValueError, UnicodeDecodeError):
            raise tornado.web.HTTPError(400, "Invalid JSON")
        if not isinstance(data, dict):
            raise tornado.web.HTTPError(400, "Expected a JSON object")
        return data

    def write_error(self, status_code, **kwargs):
        message = self._reason
        exc = (kwargs.get("exc_info") or (None, None, None))[1]
        if isinstance(exc, tornado.web.HTTPError) and exc.log_message:
            message = exc.log_message % exc.args if exc.args else exc.log_message
        if status_code >= 500 and not getattr(exc, "public", False):
            message = "Internal server error"  # never leak internals; ApiError messages are written for users
        body = {"error": message}
        if getattr(exc, "code", None):
            body["code"] = exc.code
        self.send_json(body, status_code)

    def client_ip(self):
        """
        Real client IP for rate limiting. Behind a proxy (Render, Docker ingress) the
        proxy appends the address it saw as the LAST X-Forwarded-For entry, which a
        client cannot forge. Set TRUST_PROXY=0 when the server is exposed directly.
        """
        if TRUST_PROXY:
            forwarded = self.request.headers.get("X-Forwarded-For", "")
            if forwarded:
                parts = [p.strip() for p in forwarded.split(",") if p.strip()]
                if parts:
                    return parts[-1]
        return self.request.remote_ip

    def site_url(self):
        if SITE_URL:
            return SITE_URL
        proto = self.request.protocol
        if TRUST_PROXY and self.request.headers.get("X-Forwarded-Proto"):
            proto = self.request.headers["X-Forwarded-Proto"].split(",")[-1].strip()
        return f"{proto}://{self.request.host}"

    def require_admin_token(self):
        supplied = self.request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return bool(ADMIN_TOKEN) and hmac.compare_digest(supplied, ADMIN_TOKEN)

    # -- session ---------------------------------------------------------------
    def get_current_user(self):
        raw = self.get_signed_cookie(SESSION_COOKIE, max_age_days=SESSION_DAYS)
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        return data.get("uid") if isinstance(data, dict) else None

    def start_session(self, user_id):
        secure = self.site_url().startswith("https://")
        self.set_signed_cookie(SESSION_COOKIE, json.dumps({"uid": user_id, "iat": int(time.time())}),
                               expires_days=SESSION_DAYS, httponly=True, secure=secure, samesite="Lax", path="/")

    def end_session(self):
        secure = self.site_url().startswith("https://")
        self.clear_cookie(SESSION_COOKIE, path="/", secure=secure, samesite="Lax")

    async def load_profile(self):
        """The signed-in user's profile (cached for this request), or None."""
        if not hasattr(self, "_profile"):
            uid = self.current_user
            self._profile = await in_thread(accounts.get_profile, self.db, uid) if uid else None
        return self._profile

    async def require_profile(self):
        profile = await self.load_profile()
        if not profile:
            raise tornado.web.HTTPError(401, "Please sign in first.")
        return profile

    async def require_role(self, *roles):
        profile = await self.require_profile()
        if profile["role"] not in roles and profile["role"] != "admin":
            raise tornado.web.HTTPError(403, "You do not have access to this page.")
        return profile
