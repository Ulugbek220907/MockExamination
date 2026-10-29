"""
"Connect" buttons: sign in to a platform once and the service keeps the tokens (in its database).

YouTube (Google), TikTok and Threads each have their own sign-in; Facebook and Instagram share Meta's, so
one connection covers both. Register the redirect address shown on the admin page in each app.
"""

import base64
import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode

from . import http
from .http import PlatformError
from .platforms.base import check_graph
from .platforms.tiktok import SCOPES as TIKTOK_SCOPES
from .platforms.youtube import SCOPE as YOUTUBE_SCOPE, TOKEN_URL as GOOGLE_TOKEN_URL

STATE_SECONDS = 900
THREADS_SCOPES = "threads_basic,threads_content_publish"
META_SCOPES = "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish,business_management"

# connection name -> (label, the platforms it connects, the settings its app needs)
CONNECTIONS = {
    "youtube": ("YouTube", ("youtube",), ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET")),
    "tiktok": ("TikTok", ("tiktok",), ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET")),
    "threads": ("Threads", ("threads",), ("THREADS_APP_ID", "THREADS_APP_SECRET")),
    "meta": ("Facebook and Instagram", ("facebook", "instagram"), ("META_APP_ID", "META_APP_SECRET")),
}


def app_ready(cfg, name):
    keys = {"youtube": (cfg.google_client_id, cfg.google_client_secret), "tiktok": (cfg.tiktok_client_key, cfg.tiktok_client_secret),
            "threads": (cfg.threads_app_id, cfg.threads_app_secret), "meta": (cfg.meta_app_id, cfg.meta_app_secret)}[name]
    return all(keys) and bool(cfg.public_url)


def sign_state(cfg, name, now=None):
    payload = f"{name}.{int(now or time.time())}.{secrets.token_urlsafe(8)}"
    sig = hmac.new(cfg.secret_key.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=") + "." + base64.urlsafe_b64encode(sig).decode().rstrip("=")


def check_state(cfg, state, now=None):
    """The connection name inside a state we signed less than 15 minutes ago, or None."""
    try:
        body, sig = state.split(".")
        pad = lambda s: s + "=" * (-len(s) % 4)  # noqa: E731
        payload = base64.urlsafe_b64decode(pad(body)).decode()
        expected = hmac.new(cfg.secret_key.encode(), payload.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, base64.urlsafe_b64decode(pad(sig))):
            return None
        name, issued, _ = payload.split(".")
        if (now or time.time()) - int(issued) > STATE_SECONDS or name not in CONNECTIONS:
            return None
        return name
    except (ValueError, TypeError):
        return None


def authorize_url(cfg, name, state):
    redirect = cfg.redirect_uri(name)
    if name == "youtube":
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
            "client_id": cfg.google_client_id, "redirect_uri": redirect, "response_type": "code", "scope": YOUTUBE_SCOPE,
            "access_type": "offline", "prompt": "consent", "state": state})
    if name == "tiktok":
        return "https://www.tiktok.com/v2/auth/authorize/?" + urlencode({
            "client_key": cfg.tiktok_client_key, "scope": TIKTOK_SCOPES, "response_type": "code", "redirect_uri": redirect, "state": state})
    if name == "threads":
        return "https://threads.com/oauth/authorize?" + urlencode({
            "client_id": cfg.threads_app_id, "redirect_uri": redirect, "scope": THREADS_SCOPES, "response_type": "code", "state": state})
    if name == "meta":
        return f"https://www.facebook.com/{cfg.meta_graph_version}/dialog/oauth?" + urlencode({
            "client_id": cfg.meta_app_id, "redirect_uri": redirect, "state": state,
            "scope": cfg.env_value("META_SCOPES") or META_SCOPES, "response_type": "code"})
    raise ValueError(name)


def finish(cfg, store, name, code, now=None):
    """Swap the code for tokens, save them, and return a sentence describing what was connected."""
    now = now or time.time()
    redirect = cfg.redirect_uri(name)
    if name == "youtube":
        body = http.json_of(http.call("POST", GOOGLE_TOKEN_URL, data={
            "code": code, "client_id": cfg.google_client_id, "client_secret": cfg.google_client_secret,
            "redirect_uri": redirect, "grant_type": "authorization_code"}), "Google sign-in")
        if not body.get("refresh_token"):
            raise PlatformError("Google gave no refresh token. Remove TestDay's access at myaccount.google.com/permissions and connect again.", False)
        store.save_token("youtube", {"refresh_token": body["refresh_token"], "access_token": body.get("access_token"),
                                     "expires_at": now + int(body.get("expires_in") or 3000)})
        return "YouTube is connected."
    if name == "tiktok":
        body = http.json_of(http.call("POST", "https://open.tiktokapis.com/v2/oauth/token/", data={
            "client_key": cfg.tiktok_client_key, "client_secret": cfg.tiktok_client_secret, "code": code,
            "grant_type": "authorization_code", "redirect_uri": redirect}), "TikTok sign-in")
        if not body.get("access_token"):
            raise PlatformError(f"TikTok sign-in failed: {body.get('error_description') or body.get('error')}", False)
        store.save_token("tiktok", {"access_token": body["access_token"], "refresh_token": body.get("refresh_token"),
                                    "open_id": body.get("open_id"), "expires_at": now + int(body.get("expires_in") or 86400)})
        return "TikTok is connected. Until TikTok audits the app, posts can only be private (SELF_ONLY)."
    if name == "threads":
        base = cfg.threads_api_base
        short = check_graph(http.call("POST", f"{base}/oauth/access_token", data={
            "client_id": cfg.threads_app_id, "client_secret": cfg.threads_app_secret, "code": code,
            "grant_type": "authorization_code", "redirect_uri": redirect}), "Threads sign-in")
        long = check_graph(http.call("GET", f"{base}/access_token", params={
            "grant_type": "th_exchange_token", "client_secret": cfg.threads_app_secret, "access_token": short.get("access_token")}),
            "Threads long-lived token")
        username = ""
        try:
            username = check_graph(http.call("GET", f"{base}/v1.0/me", params={"fields": "username", "access_token": long["access_token"]}),
                                   "Threads profile").get("username", "")
        except PlatformError:
            pass
        store.save_token("threads", {"access_token": long["access_token"], "user_id": str(short.get("user_id")), "username": username,
                                     "issued_at": now, "expires_at": now + int(long.get("expires_in") or 5184000)})
        return f"Threads is connected{' as @' + username if username else ''}."
    if name == "meta":
        graph = f"{cfg.meta_graph_base}/{cfg.meta_graph_version}"
        short = check_graph(http.call("GET", f"{graph}/oauth/access_token", params={
            "client_id": cfg.meta_app_id, "client_secret": cfg.meta_app_secret, "redirect_uri": redirect, "code": code}), "Facebook sign-in")
        long = check_graph(http.call("GET", f"{graph}/oauth/access_token", params={
            "grant_type": "fb_exchange_token", "client_id": cfg.meta_app_id, "client_secret": cfg.meta_app_secret,
            "fb_exchange_token": short["access_token"]}), "Facebook long-lived token")
        pages = check_graph(http.call("GET", f"{graph}/me/accounts", params={
            "fields": "id,name,access_token,instagram_business_account{id,username}", "access_token": long["access_token"]}), "Facebook Pages").get("data") or []
        if not pages:
            raise PlatformError("This Facebook account manages no Pages. Create one, or sign in as someone who does.", False)
        wanted = cfg.env_value("FACEBOOK_PAGE_ID")
        page = next((p for p in pages if p["id"] == wanted), None) or next((p for p in pages if p.get("instagram_business_account")), pages[0])
        ig = page.get("instagram_business_account") or {}
        store.save_token("meta", {"page_id": page["id"], "page_name": page.get("name", ""), "page_token": page["access_token"],
                                  "ig_user_id": ig.get("id", ""), "ig_username": ig.get("username", "")})
        extra = f" and Instagram @{ig['username']}" if ig.get("username") else ". No Instagram professional account is linked to this Page, so Instagram is not connected"
        return f"Facebook Page “{page.get('name', page['id'])}” is connected{extra}."
    raise ValueError(name)
