"""Threads: the day's card as an image post, through the Threads API."""

from .. import http
from ..http import AmbiguousError, PlatformError
from .base import Platform, Result, check_graph

REFRESH_WHEN_DAYS_LEFT = 10


class Threads(Platform):
    name = "threads"
    label = "Threads"
    media = "card"
    caption_limit = 500

    def env_token(self, cfg):
        return {"access_token": cfg.env_value("THREADS_ACCESS_TOKEN"), "user_id": cfg.env_value("THREADS_USER_ID")}

    def configured(self, ctx):
        data = ctx.token(self.name, self.env_token(ctx.cfg))
        return bool(data.get("access_token") and data.get("user_id"))

    def account(self, ctx):
        data = ctx.token(self.name, self.env_token(ctx.cfg))
        return f"@{data['username']}" if data.get("username") else ("account connected" if self.configured(ctx) else "")

    def access_token(self, ctx):
        """The long-lived token, refreshed when it is within ten days of its 60-day end (it must be a day old)."""
        data = ctx.token(self.name, self.env_token(ctx.cfg))
        expires_at = float(data.get("expires_at") or 0)
        if expires_at and expires_at - ctx.now() < REFRESH_WHEN_DAYS_LEFT * 86400 and ctx.now() - float(data.get("issued_at") or 0) > 86400:
            response = http.call("GET", f"{ctx.cfg.threads_api_base}/refresh_access_token",
                                 params={"grant_type": "th_refresh_token", "access_token": data["access_token"]})
            body = check_graph(response, "Threads token refresh")
            if body.get("access_token"):
                ctx.save_token(self.name, {"access_token": body["access_token"], "issued_at": ctx.now(),
                                           "expires_at": ctx.now() + int(body.get("expires_in") or 5184000)})
                return body["access_token"]
        return data["access_token"]

    def publish(self, post, files, caption, ctx):
        data = ctx.token(self.name, self.env_token(ctx.cfg))
        token, user = self.access_token(ctx), data["user_id"]
        base = f"{ctx.cfg.threads_api_base}/v1.0"
        container = check_graph(http.call("POST", f"{base}/{user}/threads", data={
            "media_type": "IMAGE", "image_url": ctx.media_url("card.jpg"), "text": caption, "access_token": token}),
            "Threads container").get("id")
        if not container:
            raise PlatformError("Threads gave no media container.")

        def check():
            status = check_graph(http.call("GET", f"{base}/{container}", params={"fields": "status,error_message", "access_token": token}),
                                 "Threads container status")
            state = status.get("status")
            if state in ("FINISHED", "PUBLISHED"):
                return state
            if state in ("ERROR", "EXPIRED"):
                raise PlatformError(f"Threads could not process the post: {status.get('error_message') or state}", retryable=False)
            return None

        ctx.wait_until(check, "Threads processing")
        try:
            published = check_graph(http.client.send("POST", f"{base}/{user}/threads_publish", data={"creation_id": container, "access_token": token}),
                                    "Threads publish")
        except PlatformError as e:
            if e.retryable:
                raise AmbiguousError(str(e)) from e
            raise
        except Exception as e:
            raise AmbiguousError(f"Threads publish was interrupted ({e.__class__.__name__}); check the account.") from e
        media_id = published.get("id", "")
        link = ""
        try:
            link = check_graph(http.call("GET", f"{base}/{media_id}", params={"fields": "permalink", "access_token": token}), "permalink").get("permalink", "")
        except PlatformError:
            pass
        return Result(media_id, link)
