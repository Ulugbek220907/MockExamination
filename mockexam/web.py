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

import tornado.ioloop
import tornado.web

from . import accounts

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
    # Browsers ignore this over plain HTTP, so local development is unaffected. Over HTTPS
    # it lets returning visitors skip the http:// -> https:// redirect.
    "Strict-Transport-Security": "max-age=31536000",
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

    @property
    def auth(self):
        return self.application.settings["auth"]

    def prepare(self):
        # A signed-in browser only ever sends JSON with fetch(). Refusing other
        # content types on POST blocks cross-site form submissions (CSRF).
        if self.request.method == "POST" and not self.ACCEPTS_FORMS and self.request.body:
            ctype = self.request.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if ctype != "application/json":
                raise tornado.web.HTTPError(415, "Expected application/json")

    def send_json(self, payload, status=200):
        self.set_status(status)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.set_header("Cache-Control", "no-store")
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
        if status_code >= 500:
            message = "Internal server error"
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
                return forwarded.split(",")[-1].strip()
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
        self.clear_cookie(SESSION_COOKIE, path="/")

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
