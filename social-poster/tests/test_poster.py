#!/usr/bin/env python3
"""
Tests for the social poster. Nothing here talks to a real platform: every call goes through a fake.

    cd social-poster && python -m unittest discover -s tests -t .
"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from tornado.testing import AsyncHTTPTestCase  # noqa: E402

from poster import bank, http, media, oauth  # noqa: E402
from poster.config import Config  # noqa: E402
from poster.http import AmbiguousError, PlatformError  # noqa: E402
from poster.platforms import PLATFORMS  # noqa: E402
from poster.platforms.base import Context, Platform, Result  # noqa: E402
from poster.runner import Runner  # noqa: E402
from poster.store import Store  # noqa: E402
from poster.web import make_app  # noqa: E402


class FakeResponse:
    def __init__(self, status=200, body=None, headers=None, text=None):
        self.status_code = status
        self._body = body
        self.headers = headers or {}
        self.text = text if text is not None else json.dumps(body if body is not None else {})
        self.content = self.text.encode()

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeClient:
    """Answers requests from a list of (method, url fragment, response) rules and records every request."""

    def __init__(self, rules=()):
        self.rules = list(rules)
        self.calls = []

    def add(self, method, fragment, response):
        self.rules.append((method, fragment, response))

    def send(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        matches = [rule for rule in self.rules if rule[0] == method and rule[1] in url]
        if not matches:
            raise AssertionError(f"unexpected request {method} {url}")
        path = url.split("?")[0]
        _, _, response = max(matches, key=lambda rule: (path.endswith(rule[1]), len(rule[1])))  # the most specific rule wins
        if isinstance(response, Exception):
            raise response
        if isinstance(response, list):  # a sequence of answers, the last repeats
            return response.pop(0) if len(response) > 1 else response[0]
        return response

    def urls(self):
        return [(c["method"], c["url"].split("?")[0]) for c in self.calls]


def make_cfg(tmp, **overrides):
    cfg = Config(public_url="https://social.example.com", data_dir=tmp, admin_password="pw", cron_token="cron", secret_key="s3cret",
                 google_client_id="gid", google_client_secret="gsecret", tiktok_client_key="tk", tiktok_client_secret="ts",
                 threads_app_id="th", threads_app_secret="ths", meta_app_id="meta", meta_app_secret="metas",
                 posting_enabled=True, env={})
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


class BankTests(unittest.TestCase):
    def test_every_day_for_two_years_has_a_valid_post(self):
        start = date(2026, 11, 1)
        seen = {}
        for i in range(730):
            day = start + timedelta(days=i)
            post = bank.post_for(day, ("Uzbekistan",))
            self.assertEqual(post.kind, bank.WEEK[day.weekday()])
            self.assertTrue(post.headline and post.title and post.scenes and post.text)
            for scene in post.scenes:
                self.assertGreaterEqual(scene.seconds, 2.5)
                self.assertTrue(scene.headline)
            self.assertLessEqual(sum(s.seconds for s in post.scenes), 45)  # short enough for every platform
            for platform in ("youtube", "tiktok", "instagram", "threads", "facebook"):
                text = bank.caption(post, platform, "https://www.testday.uz/?utm_source=x")
                limit = {"threads": 500, "youtube": 5000}.get(platform, 2200)
                self.assertLessEqual(len(text), limit, (post.day, platform))
                self.assertIn("testday", text.lower())
            self.assertLessEqual(len(bank.youtube_title(post)), 100)
            self.assertLessEqual(len(post.hashtags), 12)
            seen.setdefault(post.kind, []).append(post.item_id)
        # an item comes round again only after its whole pool has been used
        for kind, ids in seen.items():
            pool = len(bank.load_bank()[bank.POOLS[kind]])
            for i in range(0, len(ids) - pool):
                self.assertNotIn(ids[i], ids[i + 1:i + pool], kind)

    def test_the_same_day_always_gives_the_same_post(self):
        a = bank.post_for(date(2027, 3, 4)).to_dict()
        b = bank.post_for("2027-03-04").to_dict()
        self.assertEqual(a, b)

    def test_the_bank_has_content_to_spare(self):
        data = bank.load_bank()
        self.assertGreaterEqual(len(data["vocab"]), 50)
        self.assertGreaterEqual(len(data["tips"]), 30)
        self.assertGreaterEqual(len(data["speaking"]), 30)
        self.assertGreaterEqual(len(data["writing"]), 30)
        for item in data["vocab"]:
            self.assertTrue(item["meaning"] and item["example"].endswith("."), item["word"])

    def test_threads_text_keeps_the_link_whole(self):
        for i in range(60):
            post = bank.post_for(date(2026, 11, 1) + timedelta(days=i))
            link = "https://www.testday.uz/?utm_source=threads&utm_medium=social&utm_campaign=daily"
            text = bank.caption(post, "threads", link)
            self.assertTrue(text.endswith(link))
            self.assertLessEqual(len(text), 500)


class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.files = {}
        for d in (date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 5)):
            cls.files[d] = media.render_day(bank.post_for(d), os.path.join(cls.tmp, d.isoformat()))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_card_is_a_4_by_5_jpeg_under_8_mb(self):
        from PIL import Image
        for files in self.files.values():
            with Image.open(files["card"]) as img:
                self.assertEqual((img.format, img.size), ("JPEG", (1080, 1350)))
            self.assertLess(os.path.getsize(files["card"]), 8_000_000)

    def test_the_video_is_vertical_h264_with_audio(self):
        import subprocess
        for files in self.files.values():
            out = subprocess.run([media.ffmpeg_exe(), "-hide_banner", "-i", files["video"]], capture_output=True, text=True).stderr
            self.assertIn("1080x1920", out)
            self.assertIn("h264", out)
            self.assertIn("Audio: aac", out)
            seconds = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
            total = int(seconds.group(2)) * 60 + float(seconds.group(3))
            self.assertTrue(8 <= total <= 40, total)

    def test_rendering_again_keeps_the_files(self):
        day = date(2026, 11, 2)
        before = os.path.getmtime(self.files[day]["video"])
        media.render_day(bank.post_for(day), os.path.join(self.tmp, day.isoformat()))
        self.assertEqual(os.path.getmtime(self.files[day]["video"]), before)


class AdapterBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = make_cfg(self.tmp)
        self.store = Store(self.cfg.db_path)
        self.client = FakeClient()
        patcher = mock.patch.object(http, "client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.now = 1_800_000_000.0
        self.ctx = Context(self.cfg, self.store, media_key="KEY123", sleep=lambda s: None, now=lambda: self.now)
        self.post = bank.post_for(date(2026, 11, 3))
        self.video = os.path.join(self.tmp, "video.mp4")
        self.card = os.path.join(self.tmp, "card.jpg")
        for path in (self.video, self.card):
            with open(path, "wb") as f:
                f.write(b"x" * 2048)
        self.files = {"video": self.video, "card": self.card}


class YouTubeTests(AdapterBase):
    def test_uploads_through_the_resumable_protocol(self):
        self.store.save_token("youtube", {"refresh_token": "RT"})
        self.client.add("POST", "oauth2.googleapis.com/token", FakeResponse(200, {"access_token": "AT", "expires_in": 3600}))
        self.client.add("POST", "upload/youtube/v3/videos", FakeResponse(200, {}, headers={"Location": "https://upload.example/session1"}))
        self.client.add("PUT", "upload.example/session1", FakeResponse(201, {"id": "VID1"}))
        platform = PLATFORMS["youtube"]
        self.assertTrue(platform.configured(self.ctx))
        result = platform.publish(self.post, self.files, "the caption", self.ctx)
        self.assertEqual((result.external_id, result.url), ("VID1", "https://www.youtube.com/shorts/VID1"))
        refresh, start, put = self.client.calls
        self.assertEqual(refresh["data"]["grant_type"], "refresh_token")
        self.assertEqual(start["headers"]["X-Upload-Content-Length"], "2048")
        self.assertEqual(start["headers"]["Authorization"], "Bearer AT")
        meta = json.loads(start["data"])
        self.assertEqual(meta["status"]["privacyStatus"], "public")
        self.assertFalse(meta["status"]["selfDeclaredMadeForKids"])
        self.assertIn("#Shorts", meta["snippet"]["title"])
        self.assertEqual(meta["snippet"]["description"], "the caption")
        self.assertEqual(put["headers"]["Content-Length"], "2048")
        self.assertEqual(self.store.token("youtube")["access_token"], "AT")

    def test_a_saved_access_token_is_reused_until_it_expires(self):
        self.store.save_token("youtube", {"refresh_token": "RT", "access_token": "OLD", "expires_at": self.now + 1000})
        self.assertEqual(PLATFORMS["youtube"].access_token(self.ctx), "OLD")
        self.assertEqual(self.client.calls, [])

    def test_a_dropped_upload_is_ambiguous_and_a_refused_start_is_not(self):
        self.store.save_token("youtube", {"refresh_token": "RT", "access_token": "AT", "expires_at": self.now + 1000})
        self.client.add("POST", "upload/youtube/v3/videos", FakeResponse(200, {}, headers={"Location": "https://u.example/s"}))
        self.client.add("PUT", "u.example/s", ConnectionError("reset"))
        with self.assertRaises(AmbiguousError):
            PLATFORMS["youtube"].publish(self.post, self.files, "c", self.ctx)
        self.client.rules.clear()
        self.client.add("POST", "upload/youtube/v3/videos", FakeResponse(403, {"error": "quota"}))
        with self.assertRaises(PlatformError) as caught:
            PLATFORMS["youtube"].publish(self.post, self.files, "c", self.ctx)
        self.assertNotIsInstance(caught.exception, AmbiguousError)

    def test_not_configured_without_the_app_keys(self):
        self.store.save_token("youtube", {"refresh_token": "RT"})
        self.cfg.google_client_id = ""
        self.assertFalse(PLATFORMS["youtube"].configured(self.ctx))


class TikTokTests(AdapterBase):
    def setUp(self):
        super().setUp()
        self.store.save_token("tiktok", {"refresh_token": "RT", "access_token": "AT", "expires_at": self.now + 5000})

    def rules(self, status="PUBLISH_COMPLETE", options=("SELF_ONLY", "PUBLIC_TO_EVERYONE")):
        self.client.add("POST", "creator_info/query", FakeResponse(200, {"data": {"privacy_level_options": list(options)}, "error": {"code": "ok"}}))
        self.client.add("POST", "video/init", FakeResponse(200, {"data": {"publish_id": "P1", "upload_url": "https://up.tiktok.example/u?x=1"}, "error": {"code": "ok"}}))
        self.client.add("PUT", "up.tiktok.example", FakeResponse(201, {}))
        self.client.add("POST", "status/fetch", FakeResponse(200, {"data": {"status": status, "publicaly_available_post_id": [777]}, "error": {"code": "ok"}}))

    def test_direct_post_uploads_one_chunk_and_waits_for_the_result(self):
        self.rules()
        result = PLATFORMS["tiktok"].publish(self.post, self.files, "cap #tag", self.ctx)
        self.assertEqual(result.external_id, "777")
        init = next(c for c in self.client.calls if "video/init" in c["url"])
        self.assertEqual(init["json"]["source_info"], {"source": "FILE_UPLOAD", "video_size": 2048, "chunk_size": 2048, "total_chunk_count": 1})
        self.assertEqual(init["json"]["post_info"]["privacy_level"], "SELF_ONLY")  # the safe default
        self.assertEqual(init["json"]["post_info"]["title"], "cap #tag")
        put = next(c for c in self.client.calls if c["method"] == "PUT")
        self.assertEqual(put["headers"]["Content-Range"], "bytes 0-2047/2048")

    def test_public_posting_is_used_only_when_asked_for_and_allowed(self):
        self.cfg.tiktok_privacy = "PUBLIC_TO_EVERYONE"
        self.rules()
        PLATFORMS["tiktok"].publish(self.post, self.files, "c", self.ctx)
        init = next(c for c in self.client.calls if "video/init" in c["url"])
        self.assertEqual(init["json"]["post_info"]["privacy_level"], "PUBLIC_TO_EVERYONE")
        self.client.calls.clear()
        self.client.rules.clear()
        self.rules(options=("SELF_ONLY",))
        PLATFORMS["tiktok"].publish(self.post, self.files, "c", self.ctx)
        init = next(c for c in self.client.calls if "video/init" in c["url"])
        self.assertEqual(init["json"]["post_info"]["privacy_level"], "SELF_ONLY")

    def test_failure_and_slow_processing(self):
        self.rules(status="FAILED")
        with self.assertRaises(PlatformError):
            PLATFORMS["tiktok"].publish(self.post, self.files, "c", self.ctx)
        self.client.rules.clear()
        self.rules(status="PROCESSING_UPLOAD")
        with self.assertRaises(AmbiguousError):
            PLATFORMS["tiktok"].publish(self.post, self.files, "c", self.ctx)

    def test_refreshing_keeps_the_newest_refresh_token(self):
        self.store.save_token("tiktok", {"refresh_token": "RT", "access_token": "OLD", "expires_at": self.now - 10})
        self.client.add("POST", "oauth/token", FakeResponse(200, {"access_token": "NEW", "refresh_token": "RT2", "expires_in": 86400, "open_id": "o"}))
        self.assertEqual(PLATFORMS["tiktok"].access_token(self.ctx), "NEW")
        self.assertEqual(self.store.token("tiktok")["refresh_token"], "RT2")


class MetaTests(AdapterBase):
    def setUp(self):
        super().setUp()
        self.store.save_token("meta", {"page_id": "PAGE", "page_token": "PT", "ig_user_id": "IG", "ig_username": "testday"})

    def test_instagram_reel_creates_waits_then_publishes(self):
        self.client.add("POST", "/IG/media", FakeResponse(200, {"id": "C1"}))
        self.client.add("GET", "/C1", [FakeResponse(200, {"status_code": "IN_PROGRESS"}), FakeResponse(200, {"status_code": "FINISHED"})])
        self.client.add("POST", "/IG/media_publish", FakeResponse(200, {"id": "M1"}))
        self.client.add("GET", "/M1", FakeResponse(200, {"permalink": "https://www.instagram.com/reel/abc/"}))
        result = PLATFORMS["instagram"].publish(self.post, self.files, "cap", self.ctx)
        self.assertEqual((result.external_id, result.url), ("M1", "https://www.instagram.com/reel/abc/"))
        create = self.client.calls[0]
        self.assertEqual(create["data"]["media_type"], "REELS")
        self.assertEqual(create["data"]["video_url"], "https://social.example.com/media/KEY123/video.mp4")
        self.assertEqual(create["data"]["caption"], "cap")
        self.assertEqual(create["data"]["access_token"], "PT")

    def test_instagram_error_while_processing_is_not_retried_and_publish_loss_is_ambiguous(self):
        self.client.add("POST", "/IG/media", FakeResponse(200, {"id": "C1"}))
        self.client.add("GET", "/C1", FakeResponse(200, {"status_code": "ERROR"}))
        with self.assertRaises(PlatformError) as caught:
            PLATFORMS["instagram"].publish(self.post, self.files, "c", self.ctx)
        self.assertFalse(caught.exception.retryable)
        self.client.rules.clear()
        self.client.add("POST", "/IG/media", FakeResponse(200, {"id": "C1"}))
        self.client.add("GET", "/C1", FakeResponse(200, {"status_code": "FINISHED"}))
        self.client.add("POST", "/IG/media_publish", ConnectionError("timeout"))
        with self.assertRaises(AmbiguousError):
            PLATFORMS["instagram"].publish(self.post, self.files, "c", self.ctx)

    def test_the_public_address_is_needed_for_instagram(self):
        self.cfg.public_url = ""
        with self.assertRaises(PlatformError) as caught:
            PLATFORMS["instagram"].publish(self.post, self.files, "c", self.ctx)
        self.assertFalse(caught.exception.retryable)

    def test_facebook_reel_has_three_phases(self):
        self.client.add("POST", "/PAGE/video_reels", [FakeResponse(200, {"video_id": "V1", "upload_url": "u"}), FakeResponse(200, {"success": True})])
        self.client.add("POST", "rupload.facebook.com/video-upload/v26.0/V1", FakeResponse(200, {"success": True}))
        self.client.add("GET", "/V1", FakeResponse(200, {"status": {"video_status": "ready"}}))
        result = PLATFORMS["facebook"].publish(self.post, self.files, "cap", self.ctx)
        self.assertEqual((result.external_id, result.url), ("V1", "https://www.facebook.com/reel/V1"))
        start, upload, status, finish = self.client.calls
        self.assertEqual(start["data"]["upload_phase"], "start")
        self.assertEqual(upload["headers"]["Authorization"], "OAuth PT")
        self.assertEqual(upload["headers"]["file_size"], "2048")
        self.assertEqual((finish["data"]["upload_phase"], finish["data"]["video_state"]), ("finish", "PUBLISHED"))
        self.assertEqual(finish["data"]["description"], "cap")

    def test_each_needs_its_own_part_of_the_connection(self):
        self.store.save_token("meta", {"page_id": "PAGE", "page_token": "PT", "ig_user_id": ""})
        self.assertTrue(PLATFORMS["facebook"].configured(self.ctx))
        self.assertFalse(PLATFORMS["instagram"].configured(self.ctx))


class ThreadsTests(AdapterBase):
    def setUp(self):
        super().setUp()
        self.store.save_token("threads", {"user_id": "U1", "access_token": "TT", "issued_at": self.now - 86400 * 5, "expires_at": self.now + 86400 * 50})

    def test_posts_the_card_as_an_image_with_text(self):
        self.client.add("POST", "/v1.0/U1/threads", FakeResponse(200, {"id": "C9"}))
        self.client.add("GET", "/v1.0/C9", FakeResponse(200, {"status": "FINISHED"}))
        self.client.add("POST", "threads_publish", FakeResponse(200, {"id": "T1"}))
        self.client.add("GET", "/v1.0/T1", FakeResponse(200, {"permalink": "https://www.threads.com/@testday/post/x"}))
        result = PLATFORMS["threads"].publish(self.post, self.files, "short text", self.ctx)
        self.assertEqual(result.external_id, "T1")
        create = self.client.calls[0]
        self.assertTrue(create["url"].startswith("https://graph.threads.com/v1.0/U1/threads"))
        self.assertEqual((create["data"]["media_type"], create["data"]["text"]), ("IMAGE", "short text"))
        self.assertEqual(create["data"]["image_url"], "https://social.example.com/media/KEY123/card.jpg")

    def test_a_token_near_its_end_is_refreshed_and_saved(self):
        self.store.save_token("threads", {"expires_at": self.now + 86400 * 3, "issued_at": self.now - 86400 * 57})
        self.client.add("GET", "refresh_access_token", FakeResponse(200, {"access_token": "TT2", "expires_in": 5184000}))
        self.assertEqual(PLATFORMS["threads"].access_token(self.ctx), "TT2")
        self.assertEqual(self.store.token("threads")["access_token"], "TT2")
        self.assertEqual(self.client.calls[0]["params"]["grant_type"], "th_refresh_token")

    def test_a_fresh_token_is_not_refreshed(self):
        self.assertEqual(PLATFORMS["threads"].access_token(self.ctx), "TT")
        self.assertEqual(self.client.calls, [])


class FakePlatform(Platform):
    media = "video"

    def __init__(self, name, outcomes):
        self.name, self.label, self.outcomes, self.calls = name, name.title(), list(outcomes), 0

    def configured(self, ctx):
        return True

    def publish(self, post, files, caption, ctx):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return Result(f"{self.name}-{self.calls}", f"https://{self.name}.example/{self.calls}")


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = make_cfg(self.tmp, platforms=("youtube", "tiktok", "threads"), retry_minutes=20, max_attempts=3)
        self.clock = [1_800_000_000.0]
        self.store = Store(self.cfg.db_path, clock=lambda: self.clock[0])
        self.local = [datetime(2026, 11, 3, 11, 0, tzinfo=ZoneInfo("Asia/Tashkent"))]
        self.fakes = {"youtube": FakePlatform("youtube", ["ok"]), "tiktok": FakePlatform("tiktok", ["ok"]), "threads": FakePlatform("threads", ["ok"])}
        self.runner = Runner(self.cfg, self.store, platforms=self.fakes, now=lambda: self.local[0], sleep=lambda s: None, clock=lambda: self.clock[0])
        patcher = mock.patch.object(Runner, "files_for", lambda s, day, post=None: {"card": "c", "video": "v"})
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("poster.media.cleanup")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.day = date(2026, 11, 3)

    def states(self, results):
        return {r["platform"]: r["state"] for r in results}

    def test_posts_to_every_connected_platform_once(self):
        first = self.runner.run_day(self.day)
        self.assertEqual(self.states(first), {"youtube": "posted", "tiktok": "posted", "threads": "posted"})
        second = self.runner.run_day(self.day)
        self.assertEqual(set(self.states(second).values()), {"already_posted"})
        self.assertEqual([f.calls for f in self.fakes.values()], [1, 1, 1])
        row = self.store.delivery("2026-11-03", "youtube")
        self.assertEqual((row["status"], row["url"]), ("posted", "https://youtube.example/1"))

    def test_one_platform_failing_does_not_stop_the_others_and_is_retried_later(self):
        self.fakes["tiktok"].outcomes = [PlatformError("down"), "ok"]
        results = self.runner.run_day(self.day)
        self.assertEqual(self.states(results), {"youtube": "posted", "tiktok": "failed", "threads": "posted"})
        self.assertEqual(self.states(self.runner.run_day(self.day))["tiktok"], "waiting")  # not again at once
        self.clock[0] += 21 * 60
        self.assertEqual(self.states(self.runner.run_day(self.day))["tiktok"], "posted")
        self.assertEqual(self.fakes["youtube"].calls, 1)

    def test_it_gives_up_after_the_attempts_are_used(self):
        self.fakes["tiktok"].outcomes = [PlatformError("down")]
        for _ in range(3):
            self.runner.run_day(self.day)
            self.clock[0] += 21 * 60
        self.assertEqual(self.states(self.runner.run_day(self.day))["tiktok"], "gave_up")
        self.assertEqual(self.fakes["tiktok"].calls, 3)
        manual = self.runner.run_day(self.day, only="tiktok", manual=True)  # the owner can still press the button
        self.assertEqual(self.states(manual)["tiktok"], "failed")
        self.assertEqual(self.fakes["tiktok"].calls, 4)

    def test_an_error_that_retrying_cannot_fix_is_not_retried(self):
        self.fakes["threads"].outcomes = [PlatformError("bad permissions", retryable=False)]
        self.runner.run_day(self.day)
        self.clock[0] += 3600
        self.assertEqual(self.states(self.runner.run_day(self.day))["threads"], "gave_up")
        self.assertEqual(self.fakes["threads"].calls, 1)

    def test_a_post_that_may_have_gone_out_is_never_retried_by_itself(self):
        self.fakes["youtube"].outcomes = [AmbiguousError("answer lost")]
        self.assertEqual(self.states(self.runner.run_day(self.day))["youtube"], "needs_review")
        self.clock[0] += 86400
        self.assertEqual(self.states(self.runner.run_day(self.day, manual=True))["youtube"], "needs_review")
        self.assertEqual(self.fakes["youtube"].calls, 1)
        self.store.reset("2026-11-03", "youtube")  # the owner has looked and cleared it
        self.fakes["youtube"].outcomes = ["ok"]
        self.assertEqual(self.states(self.runner.run_day(self.day))["youtube"], "posted")

    def test_a_crash_in_one_adapter_is_a_retryable_failure(self):
        self.fakes["threads"].outcomes = [KeyError("boom")]
        results = self.runner.run_day(self.day)
        self.assertEqual(self.states(results)["threads"], "failed")
        self.assertIn("KeyError", self.store.delivery("2026-11-03", "threads")["error"])

    def test_a_post_left_in_flight_by_a_stopped_service_needs_review(self):
        self.store.begin("2026-11-03", "youtube")
        self.assertEqual(self.states(self.runner.run_day(self.day))["youtube"], "in_progress")
        self.clock[0] += 3600
        self.assertEqual(self.states(self.runner.run_day(self.day))["youtube"], "needs_review")
        self.assertEqual(self.fakes["youtube"].calls, 0)

    def test_a_dry_run_posts_nothing_and_records_nothing(self):
        results = self.runner.run_day(self.day, dry_run=True)
        self.assertEqual(set(self.states(results).values()), {"dry_run"})
        self.assertEqual([f.calls for f in self.fakes.values()], [0, 0, 0])
        self.assertEqual(self.store.deliveries("2026-11-03"), [])
        self.assertIn("testday", results[0]["caption"].lower())

    def test_platforms_that_are_not_connected_are_skipped(self):
        self.fakes["tiktok"].configured = lambda ctx: False
        results = self.runner.run_day(self.day)
        self.assertEqual(self.states(results)["tiktok"], "not_connected")
        self.assertEqual(self.fakes["tiktok"].calls, 0)

    def test_the_schedule_waits_for_the_posting_time_and_the_switch(self):
        self.local[0] = datetime(2026, 11, 3, 9, 59, tzinfo=ZoneInfo("Asia/Tashkent"))
        self.assertIsNone(self.runner.tick())
        self.local[0] = datetime(2026, 11, 3, 10, 0, tzinfo=ZoneInfo("Asia/Tashkent"))
        self.assertEqual(set(self.states(self.runner.tick()).values()), {"posted"})
        self.assertIsNone(self.runner.tick())  # everything is posted: nothing more to do
        self.cfg.posting_enabled = False
        self.local[0] += timedelta(days=1)
        self.assertIsNone(self.runner.tick())
        self.assertEqual([f.calls for f in self.fakes.values()], [1, 1, 1])

    def test_a_service_that_wakes_late_catches_up_the_same_day(self):
        self.local[0] = datetime(2026, 11, 3, 18, 30, tzinfo=ZoneInfo("Asia/Tashkent"))
        self.assertEqual(set(self.states(self.runner.tick()).values()), {"posted"})

    def test_the_posting_time_is_in_the_configured_time_zone(self):
        self.assertEqual(self.runner.due_at(self.day).utcoffset(), timedelta(hours=5))

    def test_media_files_are_served_only_under_their_secret_key(self):
        key = self.store.media_key("2026-11-03")
        self.assertEqual(self.runner.media_path(key, "card.jpg"), f"{self.cfg.media_dir}/2026-11-03/card.jpg")
        self.assertIsNone(self.runner.media_path(key, "../../etc/passwd"))
        self.assertIsNone(self.runner.media_path("guess", "card.jpg"))


class OAuthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = make_cfg(self.tmp)
        self.store = Store(self.cfg.db_path)
        self.client = FakeClient()
        patcher = mock.patch.object(http, "client", self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_state_is_signed_and_expires(self):
        state = oauth.sign_state(self.cfg, "youtube", now=1000)
        self.assertEqual(oauth.check_state(self.cfg, state, now=1100), "youtube")
        self.assertIsNone(oauth.check_state(self.cfg, state, now=1000 + 901))
        self.assertIsNone(oauth.check_state(self.cfg, state[:-3] + "abc", now=1100))
        self.assertIsNone(oauth.check_state(self.cfg, "garbage", now=1100))
        other = make_cfg(self.tmp, secret_key="different")
        self.assertIsNone(oauth.check_state(other, state, now=1100))

    def test_authorize_urls_carry_the_redirect_and_the_scopes(self):
        for name, needle in (("youtube", "youtube.upload"), ("tiktok", "video.publish"), ("threads", "threads_content_publish"),
                             ("meta", "instagram_content_publish")):
            url = oauth.authorize_url(self.cfg, name, "STATE")
            self.assertIn("STATE", url)
            self.assertIn(needle, url)
            self.assertIn("social.example.com%2Foauth%2F" + name + "%2Fcallback", url)

    def test_youtube_keeps_the_refresh_token(self):
        self.client.add("POST", "oauth2.googleapis.com/token", FakeResponse(200, {"access_token": "A", "refresh_token": "R", "expires_in": 3600}))
        self.assertIn("connected", oauth.finish(self.cfg, self.store, "youtube", "CODE", now=100))
        self.assertEqual(self.store.token("youtube")["refresh_token"], "R")
        self.client.rules.clear()
        self.client.add("POST", "oauth2.googleapis.com/token", FakeResponse(200, {"access_token": "A"}))
        with self.assertRaises(PlatformError):
            oauth.finish(self.cfg, self.store, "youtube", "CODE")

    def test_threads_swaps_for_a_long_lived_token(self):
        self.client.add("POST", "/oauth/access_token", FakeResponse(200, {"access_token": "SHORT", "user_id": 42}))
        self.client.add("GET", "/access_token", FakeResponse(200, {"access_token": "LONG", "expires_in": 5184000}))
        self.client.add("GET", "/v1.0/me", FakeResponse(200, {"username": "testday"}))
        self.assertIn("@testday", oauth.finish(self.cfg, self.store, "threads", "CODE", now=100))
        saved = self.store.token("threads")
        self.assertEqual((saved["access_token"], saved["user_id"], saved["expires_at"]), ("LONG", "42", 100 + 5184000))
        self.assertEqual(self.client.calls[1]["params"]["grant_type"], "th_exchange_token")

    def test_meta_picks_the_page_with_an_instagram_account(self):
        self.client.add("GET", "/oauth/access_token", [FakeResponse(200, {"access_token": "SHORT"}), FakeResponse(200, {"access_token": "LONG"})])
        self.client.add("GET", "/me/accounts", FakeResponse(200, {"data": [
            {"id": "P1", "name": "Other", "access_token": "PT1"},
            {"id": "P2", "name": "TestDay", "access_token": "PT2", "instagram_business_account": {"id": "IG2", "username": "testday"}}]}))
        message = oauth.finish(self.cfg, self.store, "meta", "CODE")
        self.assertIn("TestDay", message)
        saved = self.store.token("meta")
        self.assertEqual((saved["page_id"], saved["page_token"], saved["ig_user_id"]), ("P2", "PT2", "IG2"))

    def test_tiktok_stores_both_tokens(self):
        self.client.add("POST", "oauth/token", FakeResponse(200, {"access_token": "A", "refresh_token": "R", "open_id": "o", "expires_in": 86400}))
        oauth.finish(self.cfg, self.store, "tiktok", "CODE", now=100)
        self.assertEqual(self.store.token("tiktok")["refresh_token"], "R")


class WebTests(AsyncHTTPTestCase):
    def get_app(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = make_cfg(self.tmp, posting_enabled=False)
        self.store = Store(self.cfg.db_path)
        self.fakes = {n: FakePlatform(n, ["ok"]) for n in ("youtube", "tiktok", "instagram", "threads", "facebook")}
        self.runner = Runner(self.cfg, self.store, platforms=self.fakes)
        self.ticks = []
        patcher = mock.patch.object(Runner, "files_for", lambda s, day, post=None: {"card": os.path.join(self.tmp, "card.jpg"), "video": os.path.join(self.tmp, "video.mp4")})
        patcher.start()
        self.addCleanup(patcher.stop)
        with open(os.path.join(self.tmp, "card.jpg"), "wb") as f:
            f.write(b"JPEGDATA")
        with open(os.path.join(self.tmp, "video.mp4"), "wb") as f:
            f.write(b"VIDEODATA")
        return make_app(self.cfg, self.store, self.runner, lambda: self.ticks.append(1))

    AUTH = {"Authorization": "Basic " + __import__("base64").b64encode(b"admin:pw").decode()}

    def test_the_health_check_is_open_and_the_admin_page_is_not(self):
        self.assertEqual(self.fetch("/healthz").code, 200)
        denied = self.fetch("/")
        self.assertEqual(denied.code, 401)
        self.assertIn("Basic", denied.headers.get("WWW-Authenticate", ""))  # so a browser asks for the password
        self.assertEqual(self.fetch("/api/status").code, 401)
        bad = {"Authorization": "Basic " + __import__("base64").b64encode(b"admin:wrong").decode()}
        self.assertEqual(self.fetch("/", headers=bad).code, 401)
        self.assertEqual(self.fetch("/api/status", headers=self.AUTH).code, 200)

    def test_without_a_password_set_nobody_gets_in(self):
        self.cfg.admin_password = ""
        self.assertEqual(self.fetch("/", headers=self.AUTH).code, 503)

    def test_the_dashboard_shows_today_and_every_platform(self):
        r = self.fetch("/", headers=self.AUTH)
        self.assertEqual(r.code, 200)
        page = r.body.decode()
        for label in ("Youtube", "Tiktok", "Instagram", "Threads", "Facebook"):
            self.assertIn(label, page)
        self.assertIn("Today", page)
        self.assertIn("Daily posting is off", page)
        self.assertIn("script-src 'nonce-", r.headers["Content-Security-Policy"])
        self.assertIn("noindex", page)

    def test_post_buttons_need_the_fetch_header(self):
        r = self.fetch("/api/run", method="POST", headers=self.AUTH, body="{}")
        self.assertEqual(r.code, 400)
        r = self.fetch("/api/run", method="POST", headers={**self.AUTH, "X-TestDay": "1"}, body=json.dumps({"platform": "youtube"}))
        self.assertEqual(r.code, 200)
        self.assertEqual(json.loads(r.body)["results"][0]["state"], "posted")
        self.assertEqual(self.fakes["youtube"].calls, 1)

    def test_dry_run_through_the_api(self):
        r = self.fetch("/api/run", method="POST", headers={**self.AUTH, "X-TestDay": "1"}, body=json.dumps({"dryRun": True}))
        results = json.loads(r.body)["results"]
        self.assertEqual({x["state"] for x in results}, {"dry_run"})
        self.assertEqual(sum(f.calls for f in self.fakes.values()), 0)

    def test_the_cron_address_needs_its_token_and_only_acts_when_posting_is_on(self):
        self.assertEqual(self.fetch("/api/run-daily").code, 403)
        self.assertEqual(self.fetch("/api/run-daily?token=nope").code, 403)
        r = self.fetch("/api/run-daily?token=cron")
        self.assertEqual((r.code, json.loads(r.body)["started"]), (200, False))
        self.cfg.posting_enabled = True
        r = self.fetch("/api/run-daily?token=cron", method="POST", body="")
        self.assertEqual((r.code, json.loads(r.body)["started"]), (202, True))

    def test_platforms_fetch_the_media_only_by_its_secret_address(self):
        key = self.store.media_key(self.runner.today().isoformat())
        day_dir = os.path.join(self.cfg.media_dir, self.runner.today().isoformat())
        os.makedirs(day_dir)
        for name, data in (("card.jpg", b"JPEGDATA"), ("video.mp4", b"VIDEODATA")):
            with open(os.path.join(day_dir, name), "wb") as f:
                f.write(data)
        r = self.fetch(f"/media/{key}/video.mp4")
        self.assertEqual((r.code, r.body, r.headers["Content-Type"]), (200, b"VIDEODATA", "video/mp4"))
        self.assertEqual(self.fetch(f"/media/{key}/card.jpg").headers["Content-Type"], "image/jpeg")
        ranged = self.fetch(f"/media/{key}/video.mp4", headers={"Range": "bytes=0-4"})
        self.assertEqual((ranged.code, ranged.body), (206, b"VIDEO"))
        self.assertEqual(self.fetch(f"/media/{key}/secret.txt").code, 404)
        self.assertEqual(self.fetch("/media/guess/video.mp4").code, 404)
        self.assertEqual(self.fetch(f"/media/{key}/..%2F..%2Fpasswd").code, 404)

    def test_the_connect_flow_redirects_to_the_platform_and_checks_the_state(self):
        r = self.fetch("/connect/youtube", headers=self.AUTH, follow_redirects=False)
        self.assertEqual(r.code, 302)
        self.assertTrue(r.headers["Location"].startswith("https://accounts.google.com/"))
        self.assertEqual(self.fetch("/connect/youtube", follow_redirects=False).code, 401)
        bad = self.fetch("/oauth/youtube/callback?code=C&state=forged")
        self.assertIn("expired or is not ours", bad.body.decode())
        state = oauth.sign_state(self.cfg, "youtube")
        client = FakeClient([("POST", "oauth2.googleapis.com/token", FakeResponse(200, {"access_token": "A", "refresh_token": "R", "expires_in": 3600}))])
        with mock.patch.object(http, "client", client):
            good = self.fetch(f"/oauth/youtube/callback?code=C&state={state}")
        self.assertIn("YouTube is connected", good.body.decode())
        self.assertEqual(self.store.token("youtube")["refresh_token"], "R")
        wrong_platform = self.fetch(f"/oauth/tiktok/callback?code=C&state={state}")
        self.assertIn("expired or is not ours", wrong_platform.body.decode())

    def test_clear_and_disconnect(self):
        self.store.begin("2026-11-03", "youtube")
        self.store.finish("2026-11-03", "youtube", "needs_review", error="x")
        h = {**self.AUTH, "X-TestDay": "1"}
        self.fetch("/api/retry", method="POST", headers=h, body=json.dumps({"day": "2026-11-03", "platform": "youtube"}))
        self.assertIsNone(self.store.delivery("2026-11-03", "youtube"))
        self.store.save_token("youtube", {"refresh_token": "R"})
        self.fetch("/api/disconnect", method="POST", headers=h, body=json.dumps({"name": "youtube"}))
        self.assertEqual(self.store.token("youtube"), {})


class ConfigTests(unittest.TestCase):
    def test_everything_has_a_safe_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config.from_env()
        self.assertFalse(cfg.posting_enabled)
        self.assertEqual(cfg.tiktok_privacy, "SELF_ONLY")
        self.assertEqual(cfg.timezone, "Asia/Tashkent")
        self.assertEqual(set(cfg.platforms), {"youtube", "tiktok", "instagram", "threads", "facebook"})
        self.assertEqual(cfg.admin_password, "")

    def test_settings_come_from_the_environment(self):
        env = {"POSTING_ENABLED": "1", "PLATFORMS": "threads, youtube, nonsense", "POST_TIME": "08:30", "PUBLIC_URL": "https://x.example/",
               "EXTRA_HASHTAGS": "#Uzbekistan, Tashkent"}
        with mock.patch.dict(os.environ, env, clear=True):
            cfg = Config.from_env()
        self.assertTrue(cfg.posting_enabled)
        self.assertEqual(cfg.platforms, ("threads", "youtube"))
        self.assertEqual(cfg.public_url, "https://x.example")
        self.assertEqual(cfg.extra_hashtags, ("Uzbekistan", "Tashkent"))
        self.assertEqual(cfg.redirect_uri("tiktok"), "https://x.example/oauth/tiktok/callback")


if __name__ == "__main__":
    unittest.main(verbosity=1)
