"""
Sign-in: email one-time codes and Google, through Supabase Auth.

The server talks to Supabase Auth's REST API with the public key. Once Supabase
confirms who the person is (a correct code, or a valid access token from the
Google / magic-link redirect), the server creates its own signed session
cookie. Supabase tokens are never stored.

SupabaseAuth  – production. Needs SUPABASE_URL and SUPABASE_KEY.
DevAuth       – local development and tests: codes are printed to the server
                log (and returned by the API when AUTH_DEV_CODES=1), no email
                is sent, Google is unavailable.
"""

import hmac
import json
import logging
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from . import pool

log = logging.getLogger("mockexam.auth")

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[A-Za-z]{2,}$")
CODE_RE = re.compile(r"^\d{6}$")


class AuthError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def clean_email(value):
    email = str(value or "").strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise AuthError("Please enter a valid email address.")
    return email


def clean_code(value):
    code = re.sub(r"\s+", "", str(value or ""))
    if not CODE_RE.match(code):
        raise AuthError("The code has 6 digits.")
    return code


def _identity(user):
    """Reduce a Supabase user object to what the site needs."""
    meta = user.get("user_metadata") or {}
    email = (user.get("email") or "").lower()
    if not user.get("id") or not email:
        raise AuthError("This account has no email address.", 400)
    return {"id": user["id"], "email": email, "name": meta.get("full_name") or meta.get("name") or ""}


class SupabaseAuth:
    name = "supabase"
    SETTINGS_TTL = 600

    def __init__(self, url, api_key, timeout=15):
        self.base = url.rstrip("/") + "/auth/v1"
        self.key = api_key
        self.timeout = timeout
        self._google = (False, 0.0)

    def google_enabled(self):
        """Whether the Google provider is switched on in Supabase (checked every 10 minutes)."""
        value, checked = self._google
        if time.time() - checked < self.SETTINGS_TTL:
            return value
        try:
            settings = self._call("GET", "/settings")
            value = bool((settings.get("external") or {}).get("google"))
        except AuthError:
            pass  # keep the last known value
        self._google = (value, time.time())
        return value

    def _call(self, method, path, body=None, token=None, query=None, action="verify"):
        headers = {"apikey": self.key, "Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = self.base + path + (f"?{urllib.parse.urlencode(query)}" if query else "")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with pool.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read() or b"{}")
            except ValueError:
                detail = {}
            message = str(detail.get("msg") or detail.get("message") or detail.get("error_description") or "")
            code = str(detail.get("error_code") or detail.get("code") or "")
            log.warning("Supabase Auth %s %s -> %s %s %s", method, path, e.code, code, message)
            raise self._friendly(e.code, code, message, action) from e
        except urllib.error.URLError as e:
            log.error("Supabase Auth unreachable: %s", e.reason)
            raise AuthError("Sign-in is temporarily unavailable. Please try again in a minute.", 503) from e

    @staticmethod
    def _friendly(status, code, message, action):
        """Turn a Supabase Auth error into a message a student can act on."""
        text = f"{code} {message}".lower()
        if status == 429 or "rate_limit" in text or "security purposes" in text:
            return AuthError("Too many requests. Please wait a minute and try again.", 429)
        if code == "email_address_invalid" or (action == "send" and code == "validation_failed"):
            return AuthError("Please enter a valid email address.", 400)
        if "not authorized" in text or code == "email_address_not_authorized":
            return AuthError("We could not send an email to this address yet. Please try another address or try later.", 503)
        if code in ("otp_disabled", "signup_disabled", "email_provider_disabled"):
            return AuthError("Sign-in by email is not available right now. Please try Google or come back later.", 503)
        if action == "verify" and (code in ("otp_expired", "invalid_credentials") or status in (400, 401, 403)):
            return AuthError("That code is wrong or has expired. Request a new code.", 400)
        if action == "token":
            return AuthError("Your sign-in link has expired. Please sign in again.", 400)
        return AuthError("We could not send the code. Please try again in a minute.", 503 if status >= 500 else 400)

    def send_code(self, email, redirect_to):
        self._call("POST", "/otp", {"email": email, "create_user": True}, query={"redirect_to": redirect_to}, action="send")
        return None  # the code goes by email

    def verify_code(self, email, code):
        data = self._call("POST", "/verify", {"type": "email", "email": email, "token": code})
        return _identity(data.get("user") or {})

    def user_from_token(self, access_token):
        if not access_token or len(access_token) > 4096:
            raise AuthError("Missing sign-in token.")
        return _identity(self._call("GET", "/user", token=access_token, action="token"))

    def google_url(self, redirect_to):
        return f"{self.base}/authorize?" + urllib.parse.urlencode({"provider": "google", "redirect_to": redirect_to})


class DevAuth:
    """Local sign-in without email: the code is logged (and optionally returned to the browser)."""

    name = "dev"
    TTL = 600

    def google_enabled(self):
        return False

    def __init__(self):
        self.codes = {}
        self.lock = threading.Lock()

    def send_code(self, email, redirect_to):
        code = f"{secrets.randbelow(1_000_000):06d}"
        with self.lock:
            self.codes[email] = (code, time.time() + self.TTL)
        log.info("Development sign-in code for %s: %s", email, code)
        return code

    def verify_code(self, email, code):
        with self.lock:
            expected, expires = self.codes.get(email, (None, 0))
            if not expected or time.time() > expires or not hmac.compare_digest(expected, code):
                raise AuthError("That code is wrong or has expired. Request a new code.", 400)
            del self.codes[email]
        return {"id": str(uuid.uuid5(uuid.NAMESPACE_URL, "mockexam:" + email)), "email": email, "name": ""}

    def user_from_token(self, access_token):
        raise AuthError("Google sign-in is not configured on this server.", 400)

    def google_url(self, redirect_to):
        return None


class AttemptLimiter:
    """Sliding-window limits for code requests and code checks (per IP and per email)."""

    def __init__(self, limit, window):
        self.limit = limit
        self.window = window
        self.hits = {}
        self.lock = threading.Lock()

    def allow(self, key):
        now = time.time()
        with self.lock:
            q = [t for t in self.hits.get(key, []) if now - t < self.window]
            if len(q) >= self.limit:
                self.hits[key] = q
                return False
            q.append(now)
            self.hits[key] = q
            if len(self.hits) > 10000:  # keep memory bounded
                for k in list(self.hits)[:5000]:
                    del self.hits[k]
            return True
