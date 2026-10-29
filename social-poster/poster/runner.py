"""
The daily run: make the day's post, then post it to every connected platform that has not had it yet.

Safe to run as often as you like. Each (day, platform) is posted at most once: a delivery is marked "posting"
before the request is sent, and a request that may have gone through but whose answer was lost is marked
"needs_review" and never retried by itself, so a crash or a retry cannot post the same day twice.
"""

import logging
import threading
import time
import traceback
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import bank, media
from .http import AmbiguousError, PlatformError
from .platforms import PLATFORMS
from .platforms.base import Context

log = logging.getLogger("poster.runner")
STALE_POSTING_SECONDS = 30 * 60


class Runner:
    def __init__(self, cfg, store, platforms=None, now=None, sleep=time.sleep, clock=time.time):
        self.cfg = cfg
        self.store = store
        self.platforms = platforms or PLATFORMS
        self._now = now
        self.sleep = sleep
        self.clock = clock
        self.lock = threading.RLock()
        self.zone = ZoneInfo(cfg.timezone)

    # -- time ---------------------------------------------------------------
    def now(self):
        return self._now() if self._now else datetime.now(self.zone)

    def today(self):
        return self.now().date()

    def due_at(self, day):
        hour, minute = (int(x) for x in self.cfg.post_time.split(":"))
        return datetime(day.year, day.month, day.day, hour, minute, tzinfo=self.zone)

    # -- the post and its files ---------------------------------------------
    def post_for(self, day):
        return bank.post_for(day, self.cfg.extra_hashtags)

    def files_for(self, day, post=None):
        """The day's card and video (made once, kept in DATA_DIR/media/<day>)."""
        with self.lock:
            post = post or self.post_for(day)
            return media.render_day(post, f"{self.cfg.media_dir}/{day.isoformat()}")

    def context(self, day):
        return Context(self.cfg, self.store, media_key=self.store.media_key(day.isoformat()), sleep=self.sleep, now=self.clock)

    def media_path(self, key, filename):
        """The file a platform asked for at /media/<key>/<filename>, or None."""
        day = self.store.day_for_media_key(key)
        if not day or filename not in ("card.jpg", "video.mp4"):
            return None
        return f"{self.cfg.media_dir}/{day}/{filename}"

    # -- one run -------------------------------------------------------------
    def run_day(self, day, only=None, dry_run=False, manual=False):
        """Post `day` to each connected platform that still needs it. Returns one result per platform."""
        if isinstance(day, str):
            day = date.fromisoformat(day)
        results = []
        with self.lock:
            post = self.post_for(day)
            ctx = self.context(day)
            files = None
            for name in self.cfg.platforms:
                if only and name != only:
                    continue
                platform = self.platforms[name]
                if not platform.configured(ctx):
                    results.append({"platform": name, "state": "not_connected"})
                    continue
                skip = None if dry_run else self.skip_reason(day, name, manual)
                if skip:
                    results.append({"platform": name, "state": skip})
                    continue
                if files is None:
                    files = self.files_for(day, post)
                caption = bank.caption(post, name, self.cfg.link(name))
                if dry_run:
                    results.append({"platform": name, "state": "dry_run", "caption": caption, "media": platform.media})
                    continue
                results.append(self.deliver(day, name, platform, post, files, caption, ctx))
            if not dry_run:
                media.cleanup(self.cfg.media_dir, self.cfg.keep_media_days)
        return results

    def skip_reason(self, day, name, manual):
        row = self.store.delivery(day.isoformat(), name)
        if not row:
            return None
        status = row["status"]
        if status == "posted":
            return "already_posted"
        if status == "needs_review":
            return "needs_review"
        if status == "posting":
            if self.clock() - float(row["started_at"] or 0) < STALE_POSTING_SECONDS:
                return "in_progress"
            # It was in flight long ago and never finished (the service stopped): it may have gone out.
            self.store.finish(day.isoformat(), name, "needs_review", error="The service stopped while posting; check the platform.")
            return "needs_review"
        if status == "failed" and not manual:
            if row["attempts"] >= self.cfg.max_attempts:
                return "gave_up"
            if self.clock() - float(row["finished_at"] or 0) < self.cfg.retry_minutes * 60:
                return "waiting"
        return None

    def deliver(self, day, name, platform, post, files, caption, ctx):
        key = day.isoformat()
        if not self.store.begin(key, name):
            return {"platform": name, "state": "in_progress"}
        try:
            result = platform.publish(post, files, caption, ctx)
        except AmbiguousError as e:
            log.error("%s %s: may have posted: %s", key, name, e)
            self.store.finish(key, name, "needs_review", error=str(e))
            return {"platform": name, "state": "needs_review", "error": str(e)}
        except PlatformError as e:
            log.warning("%s %s failed: %s", key, name, e)
            self.store.finish(key, name, "failed", error=str(e))
            if not e.retryable:
                self.store.give_up(key, name, self.cfg.max_attempts)
            return {"platform": name, "state": "failed", "error": str(e), "retryable": e.retryable}
        except Exception as e:  # noqa: BLE001 - one platform's bug must not stop the others
            log.error("%s %s crashed:\n%s", key, name, traceback.format_exc())
            self.store.finish(key, name, "failed", error=f"Unexpected error: {e.__class__.__name__}: {e}")
            return {"platform": name, "state": "failed", "error": f"{e.__class__.__name__}: {e}", "retryable": True}
        self.store.finish(key, name, "posted", external_id=result.external_id, url=result.url, error=result.note or None)
        log.info("%s %s posted %s", key, name, result.external_id)
        return {"platform": name, "state": "posted", "id": result.external_id, "url": result.url, "note": result.note}

    # -- the schedule --------------------------------------------------------
    def pending(self, day):
        """Connected platforms that could still be posted to today (not posted, not waiting for review)."""
        ctx = self.context(day)
        out = []
        for name in self.cfg.platforms:
            if self.platforms[name].configured(ctx) and not self.skip_reason(day, name, manual=False):
                out.append(name)
        return out

    def tick(self):
        """Called every minute: once the posting time has passed, post whatever is still missing today."""
        if not self.cfg.posting_enabled:
            return None
        now = self.now()
        day = now.date()
        if now < self.due_at(day):
            return None
        with self.lock:
            if not self.pending(day):
                return None
            return self.run_day(day)

    def upcoming(self, days=14):
        start = self.today()
        return [self.post_for(start + timedelta(days=i)) for i in range(days)]

    def status(self):
        day = self.today()
        ctx = self.context(day)
        return {
            "day": day.isoformat(), "now": self.now().isoformat(timespec="minutes"), "timezone": self.cfg.timezone,
            "postTime": self.cfg.post_time, "postingEnabled": self.cfg.posting_enabled,
            "platforms": [{"name": n, "label": p.label, "media": p.media, "connected": p.configured(ctx), "account": p.account(ctx)}
                          for n, p in self.platforms.items() if n in self.cfg.platforms],
            "deliveries": self.store.deliveries(day.isoformat()),
        }
