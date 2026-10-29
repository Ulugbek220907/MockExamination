"""YouTube Shorts, through the YouTube Data API v3 (videos.insert, resumable upload)."""

import json
import os

from .. import http
from ..http import AmbiguousError, PlatformError
from .base import Platform, Result

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"


class YouTube(Platform):
    name = "youtube"
    label = "YouTube"
    media = "video"

    def env_token(self, cfg):
        return {"refresh_token": cfg.env_value("YOUTUBE_REFRESH_TOKEN")}

    def configured(self, ctx):
        return bool(ctx.token(self.name, self.env_token(ctx.cfg)).get("refresh_token") and ctx.cfg.google_client_id and ctx.cfg.google_client_secret)

    def account(self, ctx):
        return "channel connected" if self.configured(ctx) else ""

    def access_token(self, ctx):
        data = ctx.token(self.name, self.env_token(ctx.cfg))
        if data.get("access_token") and float(data.get("expires_at") or 0) > ctx.now() + 120:
            return data["access_token"]
        response = http.call("POST", TOKEN_URL, data={
            "client_id": ctx.cfg.google_client_id, "client_secret": ctx.cfg.google_client_secret,
            "refresh_token": data["refresh_token"], "grant_type": "refresh_token"})
        body = http.json_of(response, "YouTube token refresh")
        token = body.get("access_token")
        if not token:
            raise PlatformError("YouTube token refresh gave no access token.", retryable=False)
        ctx.save_token(self.name, {"access_token": token, "expires_at": ctx.now() + int(body.get("expires_in") or 3000)})
        return token

    def publish(self, post, files, caption, ctx):
        from .. import bank
        token = self.access_token(ctx)
        size = os.path.getsize(files["video"])
        tags = [t for t in post.hashtags if len(t) < 30][:12] + ["Shorts"]
        metadata = {
            "snippet": {"title": bank.youtube_title(post), "description": caption, "tags": tags, "categoryId": "27",
                        "defaultLanguage": "en"},
            "status": {"privacyStatus": ctx.cfg.youtube_privacy, "selfDeclaredMadeForKids": False},
        }
        start = http.call("POST", UPLOAD_URL, headers={
            "Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}, data=json.dumps(metadata))
        if start.status_code != 200 or not start.headers.get("Location"):
            retry = start.status_code >= 500 or start.status_code == 429
            raise PlatformError(f"YouTube upload could not start: HTTP {start.status_code} {start.text[:300]}", retryable=retry)
        with open(files["video"], "rb") as f:
            body = f.read()
        try:
            upload = http.client.send("PUT", start.headers["Location"], headers={
                "Authorization": f"Bearer {token}", "Content-Type": "video/mp4", "Content-Length": str(size)}, data=body)
        except Exception as e:  # the video may have arrived: do not upload it again
            raise AmbiguousError(f"YouTube upload was interrupted ({e.__class__.__name__}); check the channel.") from e
        if upload.status_code not in (200, 201):
            raise AmbiguousError(f"YouTube upload answered HTTP {upload.status_code}: {upload.text[:300]}")
        video_id = (upload.json() or {}).get("id", "")
        return Result(video_id, f"https://www.youtube.com/shorts/{video_id}" if video_id else "")
