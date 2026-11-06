"""
Sign in with Google (Google Identity Services): checking the ID token on the server.

The browser shows Google's own button. When the person picks an account, Google hands the page an ID token (a
signed JWT) and the page posts it to /api/auth/google. This module checks it the way Google's guide lists it
(https://developers.google.com/identity/gsi/web/guides/verify-google-id-token):

  - the signature is Google's (RS256, against the public keys Google publishes), so the token cannot be made up;
  - `iss` is accounts.google.com, `aud` is this site's client ID (a token made for another app is refused) and
    `exp` has not passed;
  - the email is verified, and Google is the authority for it (see `authoritative`).

Switched on by setting GOOGLE_CLIENT_ID (the *client ID* of an OAuth client of type "Web application"; it is
public and there is no client secret). Without it nothing here runs and the site is as it was.

Nothing is installed for this: checking an RS256 signature is one modular power and a comparison with the padded
hash that the signature must contain (RFC 8017, section 8.2.2), which `rs256_verify` does with Python integers.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
import urllib.request
import uuid

from . import pool
from .auth import AuthError, clean_email

log = logging.getLogger("mockexam.google")

CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ("accounts.google.com", "https://accounts.google.com")
GMAIL_DOMAINS = ("gmail.com", "googlemail.com")
MAX_TOKEN_CHARS = 8192
LEEWAY = 60                  # seconds of difference between this clock and Google's that we put up with
KEYS_MIN_AGE = 300           # Google's keys are kept for what its Cache-Control says (about 6 hours), between these
KEYS_MAX_AGE = 86400
KEYS_DEFAULT_AGE = 3600
KEYS_RETRY = 60              # a token that names a key we do not have makes us look again, but not more often than this
KEYS_TIMEOUT = 8

# What a SHA-256 signature wraps the hash in (RFC 8017, section 9.2, the DigestInfo for SHA-256).
_SHA256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
_B64URL = re.compile(r"^[A-Za-z0-9_-]+$")

BAD_TOKEN = "We could not check your Google sign-in. Please try again, or use your email."
UNAVAILABLE = "Google sign-in is temporarily unavailable. Please try again in a minute, or use your email."


def configured():
    """The client ID from the environment ('' when Google sign-in is off)."""
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def _b64d(text):
    """Base64url without padding, strictly: characters outside the alphabet are an error, not ignored."""
    if not isinstance(text, str) or not _B64URL.match(text):
        raise ValueError("not base64url")
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def rs256_verify(signing_input, signature, n, e):
    """True if `signature` is a valid RSASSA-PKCS1-v1_5 / SHA-256 signature of `signing_input` for the key (n, e)."""
    k = (n.bit_length() + 7) // 8
    if n < 3 or e < 3 or len(signature) != k:
        return False
    s = int.from_bytes(signature, "big")
    if s >= n:
        return False
    encoded = pow(s, e, n).to_bytes(k, "big")
    t = _SHA256_PREFIX + hashlib.sha256(signing_input).digest()
    if k < len(t) + 11:
        return False
    # The whole padded message is rebuilt and compared, so nothing in it can be bent (no parsing, no leftovers).
    return hmac.compare_digest(encoded, b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t)


def parse_keys(document):
    """{kid: (n, e)} from Google's key document (a JWK set). Entries that are not usable RSA keys are skipped."""
    keys = {}
    for k in (document.get("keys") or []) if isinstance(document, dict) else []:
        try:
            if k.get("kty") != "RSA" or k.get("alg", "RS256") != "RS256" or not k.get("kid"):
                continue
            keys[str(k["kid"])] = (int.from_bytes(_b64d(k["n"]), "big"), int.from_bytes(_b64d(k["e"]), "big"))
        except (AttributeError, KeyError, TypeError, ValueError):
            continue
    return keys


def fetch_google_keys(url=CERTS_URL):
    """(keys, seconds to keep them) from Google."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with pool.urlopen(req, timeout=KEYS_TIMEOUT) as resp:
        body = resp.read()
        cache_control = resp.headers.get("Cache-Control", "") if resp.headers else ""
    keys = parse_keys(json.loads(body))
    if not keys:
        raise ValueError("Google's key document has no usable keys")
    m = re.search(r"max-age=(\d+)", cache_control or "")
    age = int(m.group(1)) if m else KEYS_DEFAULT_AGE
    return keys, max(KEYS_MIN_AGE, min(KEYS_MAX_AGE, age))


def authoritative(email, claims):
    """
    Whether Google decides who may use this address (so a Google sign-in is as good as proof of the mailbox).
    Google's guide: yes for a Gmail address, and for a Google Workspace account (a verified email with `hd`);
    no for a Google account that was made with someone else's address (Yahoo, Mail.ru ...), because that address
    was verified once when the account was made, and the mailbox may belong to somebody else since.
    """
    return email.rsplit("@", 1)[1] in GMAIL_DOMAINS or bool(claims.get("hd"))


class GoogleSignIn:
    def __init__(self, client_id="", fetch_keys=None, clock=time.time):
        self.client_id = (client_id or "").strip()
        self._fetch = fetch_keys or fetch_google_keys
        self._clock = clock
        self._lock = threading.Lock()
        self._keys = None      # {kid: (n, e)}
        self._fetched = 0.0    # when they were fetched
        self._expires = 0.0    # until when they are good

    @property
    def enabled(self):
        return bool(self.client_id)

    # -- Google's keys -------------------------------------------------------------------------
    def _key(self, kid):
        """The (n, e) for this key ID, looking at Google's keys again when they are old or the ID is new to us."""
        now = self._clock()
        with self._lock:
            have = self._keys is not None
            if have and kid in self._keys and now < self._expires:
                return self._keys[kid]
            if have and now < self._expires and now - self._fetched < KEYS_RETRY:
                return None  # we looked a moment ago, and Google does not have this key: stop garbage tokens costing a fetch each
            try:
                keys, age = self._fetch()
            except Exception:
                log.warning("Could not fetch Google's sign-in keys", exc_info=True)
                if have:  # keep going on the old ones; try again in a minute
                    self._fetched, self._expires = now, now + KEYS_RETRY
                    return self._keys.get(kid)
                raise AuthError(UNAVAILABLE, 503)
            self._keys, self._fetched, self._expires = keys, now, now + age
            return keys.get(kid)

    # -- the token -----------------------------------------------------------------------------
    def _parse(self, token):
        """(header, claims, signing input, signature) of a well-formed token; ValueError otherwise."""
        if not token or len(token) > MAX_TOKEN_CHARS:
            raise ValueError("size")
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("parts")
        header, claims = json.loads(_b64d(parts[0])), json.loads(_b64d(parts[1]))
        signature = _b64d(parts[2])
        if not isinstance(header, dict) or not isinstance(claims, dict) or not signature:
            raise ValueError("shape")
        # Only RS256, and only a key Google published: "none", or HS256 keyed with a public key, never gets as far as a check.
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise ValueError("alg")
        return header, claims, f"{parts[0]}.{parts[1]}".encode("ascii"), signature

    def verify(self, credential):
        """
        The identity {id, email, name} that a Google ID token proves, or an AuthError a student can act on.
        The id is for a new account only: an existing account is found by its email, as for the emailed codes.
        """
        if not self.enabled:
            raise AuthError("Google sign-in is not available on this server.", 400)
        bad = AuthError(BAD_TOKEN, 400)
        try:
            header, claims, signing_input, signature = self._parse(str(credential or ""))
        except (ValueError, UnicodeError, RecursionError):  # RecursionError: JSON nested thousands deep
            raise bad from None
        key = self._key(header["kid"])  # may raise "unavailable" (503)
        if not key or not rs256_verify(signing_input, signature, *key):
            raise bad

        now = self._clock()
        exp = claims.get("exp")
        if (claims.get("iss") not in ISSUERS or claims.get("aud") != self.client_id
                or isinstance(exp, bool) or not isinstance(exp, (int, float)) or not now <= exp + LEEWAY
                or not isinstance(claims.get("sub"), str) or not claims.get("sub")):
            raise bad
        verified = claims.get("email_verified")
        if verified is not True and verified != "true":  # not `in (True, ...)`: 1 == True in Python
            raise AuthError("Your Google account has not confirmed its email address, so we cannot use it. "
                            "Please use the email option instead.", 400)
        try:
            email = clean_email(claims.get("email"))
        except AuthError:
            raise bad from None
        if not authoritative(email, claims):
            raise AuthError("We cannot confirm this address through Google. Press \u201cSend me a code\u201d and "
                            "we will email you a 6-digit code instead.", 400, code="google_use_code", extra={"email": email})
        name = str(claims.get("name") or "").strip() or " ".join(
            str(claims.get(k) or "").strip() for k in ("given_name", "family_name")).strip()
        return {"id": str(uuid.uuid4()), "email": email, "name": re.sub(r"\s+", " ", name)[:80]}
