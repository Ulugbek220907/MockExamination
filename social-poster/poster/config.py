"""
Settings, all from environment variables (see README.md and render.yaml).

Nothing here is secret by default: a platform whose keys are missing is simply "not connected" and is skipped.
"""

import os
import secrets
from dataclasses import dataclass, field

PLATFORM_NAMES = ("youtube", "tiktok", "instagram", "threads", "facebook")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _flag(name, default=False):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _text(name, default=""):
    return (os.environ.get(name) or default).strip()


def _number(name, default):
    try:
        return int(_text(name, str(default)))
    except ValueError:
        return default


@dataclass
class Config:
    # where
    public_url: str = ""            # this service's public address; platforms fetch the media from it
    site_url: str = "https://www.testday.uz"
    data_dir: str = os.path.join(BASE_DIR, "runtime")
    port: int = 10000
    # when
    timezone: str = "Asia/Tashkent"
    post_time: str = "10:00"        # HH:MM in `timezone`
    posting_enabled: bool = False   # the daily run posts for real only when this is on
    platforms: tuple = PLATFORM_NAMES
    # who may use the admin page and the cron endpoint
    admin_password: str = ""
    cron_token: str = ""
    secret_key: str = ""
    # the apps registered with each platform (for the "Connect" buttons)
    google_client_id: str = ""
    google_client_secret: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    threads_app_id: str = ""
    threads_app_secret: str = ""
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_graph_version: str = "v26.0"
    meta_graph_base: str = "https://graph.facebook.com"
    meta_upload_base: str = "https://rupload.facebook.com"
    threads_api_base: str = "https://graph.threads.com"
    # how to post
    youtube_privacy: str = "public"
    tiktok_privacy: str = "SELF_ONLY"   # until TikTok has audited the app only SELF_ONLY is allowed
    extra_hashtags: tuple = ("Uzbekistan",)
    keep_media_days: int = 7
    max_attempts: int = 3
    retry_minutes: int = 20
    env: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_env(cls):
        platforms = tuple(p for p in (x.strip().lower() for x in _text("PLATFORMS", ",".join(PLATFORM_NAMES)).split(","))
                          if p in PLATFORM_NAMES)
        return cls(
            public_url=_text("PUBLIC_URL").rstrip("/"),
            site_url=_text("SITE_URL", "https://www.testday.uz").rstrip("/"),
            data_dir=_text("DATA_DIR", os.path.join(BASE_DIR, "runtime")),
            port=_number("PORT", 10000),
            timezone=_text("TIMEZONE", "Asia/Tashkent"),
            post_time=_text("POST_TIME", "10:00"),
            posting_enabled=_flag("POSTING_ENABLED"),
            platforms=platforms or PLATFORM_NAMES,
            admin_password=_text("ADMIN_PASSWORD"),
            cron_token=_text("CRON_TOKEN"),
            secret_key=_text("SECRET_KEY") or secrets.token_hex(32),
            google_client_id=_text("GOOGLE_CLIENT_ID"),
            google_client_secret=_text("GOOGLE_CLIENT_SECRET"),
            tiktok_client_key=_text("TIKTOK_CLIENT_KEY"),
            tiktok_client_secret=_text("TIKTOK_CLIENT_SECRET"),
            threads_app_id=_text("THREADS_APP_ID"),
            threads_app_secret=_text("THREADS_APP_SECRET"),
            meta_app_id=_text("META_APP_ID"),
            meta_app_secret=_text("META_APP_SECRET"),
            meta_graph_version=_text("META_GRAPH_VERSION", "v26.0"),
            meta_graph_base=_text("META_GRAPH_BASE", "https://graph.facebook.com").rstrip("/"),
            meta_upload_base=_text("META_UPLOAD_BASE", "https://rupload.facebook.com").rstrip("/"),
            threads_api_base=_text("THREADS_API_BASE", "https://graph.threads.com").rstrip("/"),
            youtube_privacy=_text("YOUTUBE_PRIVACY", "public"),
            tiktok_privacy=_text("TIKTOK_PRIVACY", "SELF_ONLY"),
            extra_hashtags=tuple(h.strip().lstrip("#") for h in _text("EXTRA_HASHTAGS", "Uzbekistan").split(",") if h.strip()),
            keep_media_days=_number("KEEP_MEDIA_DAYS", 7),
            max_attempts=_number("MAX_ATTEMPTS", 3),
            retry_minutes=_number("RETRY_MINUTES", 20),
            env=dict(os.environ),
        )

    # -- helpers ---------------------------------------------------------
    def env_value(self, name):
        return (self.env.get(name) or "").strip()

    @property
    def db_path(self):
        return os.path.join(self.data_dir, "poster.sqlite3")

    @property
    def media_dir(self):
        return os.path.join(self.data_dir, "media")

    def redirect_uri(self, platform):
        return f"{self.public_url}/oauth/{platform}/callback"

    def link(self, platform):
        """The TestDay address to put in a post, tagged so that the site's visits show where they came from."""
        return f"{self.site_url}/?utm_source={platform}&utm_medium=social&utm_campaign=daily"
