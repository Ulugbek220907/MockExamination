"""Instagram Reels and Facebook Page Reels, through the Graph API. Both use the Page's access token."""

import os

from .. import http
from ..http import AmbiguousError, PlatformError
from .base import Platform, Result, check_graph


def graph(cfg):
    return f"{cfg.meta_graph_base}/{cfg.meta_graph_version}"


def meta_token(ctx):
    """{"page_id", "page_token", "ig_user_id"} from the connected account, over the environment's values."""
    cfg = ctx.cfg
    return ctx.token("meta", {"page_token": cfg.env_value("META_PAGE_TOKEN"), "page_id": cfg.env_value("FACEBOOK_PAGE_ID"),
                              "ig_user_id": cfg.env_value("INSTAGRAM_USER_ID")})


class Instagram(Platform):
    name = "instagram"
    label = "Instagram"
    media = "video"
    caption_limit = 2200

    def configured(self, ctx):
        data = meta_token(ctx)
        return bool(data.get("page_token") and data.get("ig_user_id"))

    def account(self, ctx):
        data = meta_token(ctx)
        return f"@{data['ig_username']}" if data.get("ig_username") else ("account connected" if self.configured(ctx) else "")

    def publish(self, post, files, caption, ctx):
        data = meta_token(ctx)
        base, ig, token = graph(ctx.cfg), data["ig_user_id"], data["page_token"]
        container = check_graph(http.call("POST", f"{base}/{ig}/media", data={
            "media_type": "REELS", "video_url": ctx.media_url("video.mp4"), "caption": caption,
            "share_to_feed": "true", "access_token": token}), "Instagram media container").get("id")
        if not container:
            raise PlatformError("Instagram gave no media container.")

        def check():
            status = check_graph(http.call("GET", f"{base}/{container}", params={"fields": "status_code", "access_token": token}),
                                 "Instagram container status")
            code = status.get("status_code")
            if code in ("FINISHED", "PUBLISHED"):
                return code
            if code in ("ERROR", "EXPIRED"):
                raise PlatformError(f"Instagram could not process the video ({code}).", retryable=False)
            return None

        ctx.wait_until(check, "Instagram processing")
        try:
            published = check_graph(http.client.send("POST", f"{base}/{ig}/media_publish", data={"creation_id": container, "access_token": token}),
                                    "Instagram publish")
        except PlatformError as e:
            if e.retryable:
                raise AmbiguousError(str(e)) from e
            raise
        except Exception as e:
            raise AmbiguousError(f"Instagram publish was interrupted ({e.__class__.__name__}); check the account.") from e
        media_id = published.get("id", "")
        link = ""
        try:
            link = check_graph(http.call("GET", f"{base}/{media_id}", params={"fields": "permalink", "access_token": token}), "permalink").get("permalink", "")
        except PlatformError:
            pass  # the post is live; the link is only for the admin page
        return Result(media_id, link)


class Facebook(Platform):
    name = "facebook"
    label = "Facebook"
    media = "video"
    caption_limit = 2200

    def configured(self, ctx):
        data = meta_token(ctx)
        return bool(data.get("page_token") and data.get("page_id"))

    def account(self, ctx):
        data = meta_token(ctx)
        return data.get("page_name") or ("Page connected" if self.configured(ctx) else "")

    def publish(self, post, files, caption, ctx):
        data = meta_token(ctx)
        base, page, token = graph(ctx.cfg), data["page_id"], data["page_token"]
        start = check_graph(http.call("POST", f"{base}/{page}/video_reels", data={"upload_phase": "start", "access_token": token}),
                            "Facebook Reel start")
        video_id = start.get("video_id")
        if not video_id:
            raise PlatformError("Facebook gave no video id.")
        size = os.path.getsize(files["video"])
        with open(files["video"], "rb") as f:
            body = f.read()
        upload = http.call("POST", f"{ctx.cfg.meta_upload_base}/video-upload/{ctx.cfg.meta_graph_version}/{video_id}", headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(size), "Content-Type": "application/octet-stream"}, data=body)
        if upload.status_code != 200 or not (upload.json() or {}).get("success"):
            raise PlatformError(f"Facebook Reel upload failed: HTTP {upload.status_code} {upload.text[:300]}", retryable=upload.status_code >= 500)

        def check():
            status = check_graph(http.call("GET", f"{base}/{video_id}", params={"fields": "status", "access_token": token}),
                                 "Facebook Reel status").get("status") or {}
            state = status.get("video_status")
            if state in ("ready", "upload_complete"):
                return state
            if state == "error":
                raise PlatformError("Facebook could not process the video.", retryable=False)
            return None

        ctx.wait_until(check, "Facebook processing")
        try:
            finished = check_graph(http.client.send("POST", f"{base}/{page}/video_reels", data={
                "upload_phase": "finish", "video_id": video_id, "video_state": "PUBLISHED", "description": caption,
                "title": post.title[:100], "access_token": token}), "Facebook Reel publish")
        except PlatformError as e:
            if e.retryable:
                raise AmbiguousError(str(e)) from e
            raise
        except Exception as e:
            raise AmbiguousError(f"Facebook publish was interrupted ({e.__class__.__name__}); check the Page.") from e
        if finished.get("success") is False:
            raise PlatformError("Facebook did not publish the Reel.", retryable=False)
        return Result(video_id, f"https://www.facebook.com/reel/{video_id}")
