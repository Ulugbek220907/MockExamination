"""TikTok, through the Content Posting API (Direct Post, uploading the file in one piece)."""

import os

from .. import http
from ..http import AmbiguousError, PlatformError
from .base import Platform, Result

API = "https://open.tiktokapis.com"
SCOPES = "user.info.basic,video.publish"


class TikTok(Platform):
    name = "tiktok"
    label = "TikTok"
    media = "video"
    caption_limit = 2200

    def env_token(self, cfg):
        return {"refresh_token": cfg.env_value("TIKTOK_REFRESH_TOKEN")}

    def configured(self, ctx):
        return bool(ctx.token(self.name, self.env_token(ctx.cfg)).get("refresh_token") and ctx.cfg.tiktok_client_key and ctx.cfg.tiktok_client_secret)

    def account(self, ctx):
        return "account connected" if self.configured(ctx) else ""

    def access_token(self, ctx):
        data = ctx.token(self.name, self.env_token(ctx.cfg))
        if data.get("access_token") and float(data.get("expires_at") or 0) > ctx.now() + 300:
            return data["access_token"]
        response = http.call("POST", f"{API}/v2/oauth/token/", data={
            "client_key": ctx.cfg.tiktok_client_key, "client_secret": ctx.cfg.tiktok_client_secret,
            "grant_type": "refresh_token", "refresh_token": data["refresh_token"]})
        body = http.json_of(response, "TikTok token refresh")
        if not body.get("access_token"):
            raise PlatformError(f"TikTok token refresh failed: {body.get('error_description') or body.get('error') or body}", retryable=False)
        # TikTok may hand back a new refresh token: keep the newest, or the next refresh fails
        ctx.save_token(self.name, {"access_token": body["access_token"], "refresh_token": body.get("refresh_token") or data["refresh_token"],
                                   "expires_at": ctx.now() + int(body.get("expires_in") or 86400), "open_id": body.get("open_id")})
        return body["access_token"]

    def _api(self, ctx, token, path, payload, what):
        response = http.call("POST", f"{API}{path}", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}, json=payload)
        body = http.json_of(response, what)
        error = body.get("error") or {}
        if error.get("code") not in (None, "ok"):
            retry = error.get("code") in ("internal_error", "rate_limit_exceeded")
            raise PlatformError(f"{what}: {error.get('code')}: {error.get('message')}", retryable=retry)
        return body.get("data") or {}

    def publish(self, post, files, caption, ctx):
        token = self.access_token(ctx)
        creator = self._api(ctx, token, "/v2/post/publish/creator_info/query/", {}, "TikTok creator info")
        options = creator.get("privacy_level_options") or ["SELF_ONLY"]
        wanted = ctx.cfg.tiktok_privacy
        privacy = wanted if wanted in options else ("SELF_ONLY" if "SELF_ONLY" in options else options[0])
        size = os.path.getsize(files["video"])
        init = self._api(ctx, token, "/v2/post/publish/video/init/", {
            "post_info": {"title": caption[:2200], "privacy_level": privacy, "disable_duet": False, "disable_comment": False,
                          "disable_stitch": False, "video_cover_timestamp_ms": 1000},
            "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}},
            "TikTok post init")
        publish_id, upload_url = init.get("publish_id"), init.get("upload_url")
        if not publish_id or not upload_url:
            raise PlatformError("TikTok gave no upload address.")
        with open(files["video"], "rb") as f:
            body = f.read()
        try:
            upload = http.client.send("PUT", upload_url, headers={
                "Content-Type": "video/mp4", "Content-Length": str(size), "Content-Range": f"bytes 0-{size - 1}/{size}"}, data=body)
        except Exception as e:
            raise AmbiguousError(f"TikTok upload was interrupted ({e.__class__.__name__}); check the account.") from e
        if upload.status_code not in (200, 201, 206):
            raise PlatformError(f"TikTok upload answered HTTP {upload.status_code}: {upload.text[:300]}", retryable=upload.status_code >= 500)

        def check():
            data = self._api(ctx, token, "/v2/post/publish/status/fetch/", {"publish_id": publish_id}, "TikTok post status")
            status = data.get("status")
            if status == "PUBLISH_COMPLETE":
                return data
            if status == "FAILED":
                raise PlatformError(f"TikTok could not publish the video: {data.get('fail_reason')}", retryable=data.get("fail_reason") == "internal")
            return None

        try:
            data = ctx.wait_until(check, "TikTok processing")
        except PlatformError as e:
            if "did not finish" in str(e):  # uploaded, but TikTok has not said it is done: it may still appear
                raise AmbiguousError(str(e)) from e
            raise
        posted = (data.get("publicaly_available_post_id") or [None])[0]
        note = f"posted as {privacy}" + (" (TikTok limits unaudited apps to private posts)" if privacy == "SELF_ONLY" else "")
        return Result(str(posted or publish_id), "", note)
