"""
HTTP API for accounts, plans and payments, examiners and checks, and admin.

  POST /api/auth/code                 email a 6-digit sign-in code
  POST /api/auth/verify               check the code, start a session
  POST /api/auth/token                start a session from a Google / email-link redirect
  POST /api/auth/google               sign in with the ID token from Google's button (GOOGLE_CLIENT_ID)
  GET  /api/auth/google               redirect to Google sign-in (via Supabase, when that is set up instead)
  POST /api/auth/logout
  GET  /api/me, POST /api/me          account, plan, examiner profile; change name
  GET  /api/progress                  band scores over time, for the progress chart

  GET  /api/billing                   prices and payment methods
  GET  /api/orders, POST /api/orders  your orders / create an order
  POST /api/orders/<id>/pay           start paying (redirect URL or card details)
  POST /api/subscriptions/cancel      stop the renewals of a pass
  POST /api/pay/dodo/webhook          Dodo Payments tells us a card payment or refund happened
  POST /api/pay/payme                 Payme Merchant API callback
  POST /api/pay/click/(prepare|complete)  Click SHOP API callbacks

  GET  /api/examiners[?kind=]         examiners students can choose
  GET  /api/examiners/<id>            one examiner with reviews
  GET  /api/checks                    your checks
  GET  /api/checks/<id>               one check (student, its examiner, or admin)
  POST /api/checks/<id>/rate          rate the examiner once
  GET  /api/examiner/me, POST         examiner dashboard data / edit profile
  POST /api/examiner/checks/<id>/start|result

  POST /api/speaking/<test>/start     start a Speaking test (signed in)
  POST /api/speaking/submissions/<id>/answers/<key>   upload one recorded answer (raw audio body)
  POST /api/speaking/submissions/<id>/plan            the questions so far; after an answer, one more if the AI examiner wants it
  POST /api/speaking/submissions/<id>/complete        finish the test (an AI-examiner test is then rated)
  POST /api/speaking/submissions/<id>/ai-review       rate an AI-examiner test again after a failure
  GET  /api/speaking/submissions/<id> the questions and recordings (owner, its examiner, admin)
  GET  /api/speaking/recordings/<id>  play one recording (same people)

  GET  /api/admin/orders, POST /api/admin/orders/<id>/(confirm|refund|cancel)
  GET  /api/admin/click, POST /api/admin/click/check   Click settings, recent callbacks, and a check of the keys
  GET  /api/admin/ai-usage                       what the AI examiner cost in the last 30 days, and who used it most
  GET  /api/admin/examiners, POST     list / add or update an examiner by email
  GET  /api/admin/users?q=, POST /api/admin/plan   find users / give plan days
"""

import asyncio
import json
import logging
import os
import re

import tornado.web

from . import accounts, ai_usage, analytics, auth, billing, checks, guard, notify, speaking, speaking_adaptive, speaking_ai, telegram_bot
from .dbcache import gather
from .web import BaseHandler, in_thread

log = logging.getLogger("mockexam.api")

DEV_CODES = os.environ.get("AUTH_DEV_CODES", "0") == "1"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

CODE_PER_IP = auth.AttemptLimiter(10, 3600)
CODE_PER_EMAIL = auth.AttemptLimiter(5, 3600)
VERIFY_PER_EMAIL = auth.AttemptLimiter(10, 900)
VERIFY_PER_IP = auth.AttemptLimiter(40, 3600)
# Only Google sign-ins that fail count: a student who signs in properly is never held up by a crowd behind the same address.
GOOGLE_BAD_PER_IP = auth.AttemptLimiter(30, 3600)


def _uuid(value):
    value = str(value or "").strip().lower()
    return value if UUID_RE.match(value) else None


def _public_user(profile):
    return {"id": profile["id"], "email": profile["email"], "name": profile.get("name") or "", "role": profile["role"],
            "goal": accounts.public_goal(profile),
            "telegram": {"available": telegram_bot.configured("student"), "connected": bool(profile.get("telegram_id")),
                         "ref": telegram_bot.chat_ref(profile.get("telegram_id")), "bot": telegram_bot.student_username()}}


def clean_name(value):
    name = re.sub(r"\s+", " ", str(value or "")).strip()
    return name[:80] or "Candidate"


def claim_attempts(db, client_id, user_id):
    """Attach the attempts this browser made before signing in to the account (the three tables at once)."""
    def claim(table):
        try:
            db.update(table, {"client_id": client_id, "user_id": None}, {"user_id": user_id})
        except Exception:
            log.exception("Could not claim %s", table)
    gather(*(lambda t=t: claim(t) for t in ("reading_attempts", "listening_attempts", "writing_submissions")))


def account_payload(db, profile):
    uid, role = profile["id"], profile["role"]
    staff = role in ("examiner", "admin")
    # Independent reads run side by side: the database may be far away.
    plan, examiner, open_checks, payments = gather(
        lambda: accounts.plan_status(db, uid),
        lambda: checks.get_examiner(db, uid) if staff else None,
        lambda: len(db.select("checks", {"examiner_id": uid, "status": ("in", ["waiting", "in_progress"])}, limit=100))
        if staff else 0,
        lambda: db.count("orders", {"status": "awaiting_confirmation"}) if role == "admin" else 0,
    )
    out = {"user": _public_user(profile), "plan": plan, "examiner": None, "todo": {}}
    if examiner:
        out["examiner"] = checks.public_examiner(examiner)
        out["todo"]["checks"] = open_checks
    if role == "admin":
        out["todo"]["payments"] = payments
    return out


# --------------------------------------------------------------------------
# Sign-in
# --------------------------------------------------------------------------

class ApiError(tornado.web.HTTPError):
    """An error whose message is shown to the user (and an optional machine-readable code and extra fields)."""

    public = True  # the message is safe to show, even with a 5xx status

    def __init__(self, status, message, code=None, extra=None):
        super().__init__(status, log_message=message.replace("%", "%%"))
        self.code = code
        self.extra = extra


def _raise(e):
    raise ApiError(getattr(e, "status", 400), str(e), code=getattr(e, "code", None), extra=getattr(e, "extra", None))


class AuthCodeHandler(BaseHandler):
    async def post(self):
        body = self.body_json()
        try:
            email = auth.clean_email(body.get("email"))
        except auth.AuthError as e:
            _raise(e)
        if not CODE_PER_IP.allow(self.client_ip()) or not CODE_PER_EMAIL.allow(email):
            raise ApiError(429, "Too many codes requested. Please wait a few minutes.")
        # A robot check (Cloudflare Turnstile) when it is set up, and a cap on sign-in emails for the whole site a day:
        # a script asking for codes to random addresses would otherwise use up the email service and block everyone.
        if not await in_thread(guard.turnstile_ok, body.get("captcha"), self.client_ip()):
            raise ApiError(400, "Please confirm you are not a robot, then ask for the code again.", "captcha")
        if not guard.DAY.take("signin_email"):
            raise ApiError(503, "Sign-in by email code is busy today. Please sign in with Google, or try again tomorrow.",
                           "email_busy")
        try:
            code = await in_thread(self.auth.send_code, email, self.site_url() + "/auth-callback.html")
        except auth.AuthError as e:
            _raise(e)
        out = {"sent": True, "email": email}
        if code and DEV_CODES:
            out["devCode"] = code
        self.send_json(out)


class SessionMixin:
    async def finish_login(self, identity, client_id, existing=accounts._MISSING):
        profile = await in_thread(accounts.upsert_profile, self.db, identity, existing)
        if profile.pop("created_now", False):
            self.track("signup", client_id=client_id, user_id=profile["id"])
        # The database is far away: claiming this browser's attempts and reading the plan go side by side.
        claimed = in_thread(claim_attempts, self.db, client_id, profile["id"]) if client_id else asyncio.sleep(0)
        _, payload = await asyncio.gather(claimed, in_thread(account_payload, self.db, profile))
        self.start_session(profile["id"])
        self.send_json(payload)


class AuthVerifyHandler(SessionMixin, BaseHandler):
    async def post(self):
        body = self.body_json()
        try:
            email = auth.clean_email(body.get("email"))
            code = auth.clean_code(body.get("code"))
        except auth.AuthError as e:
            _raise(e)
        if not VERIFY_PER_EMAIL.allow(email) or not VERIFY_PER_IP.allow(self.client_ip()):
            raise ApiError(429, "Too many attempts. Please request a new code in a few minutes.")
        # Checking the code and finding the account are independent: one round trip instead of two.
        checked, existing = await asyncio.gather(
            in_thread(self._verify, email, code), in_thread(accounts.find_profile_by_email, self.db, email))
        if isinstance(checked, auth.AuthError):
            _raise(checked)
        await self.finish_login(checked, _uuid(body.get("clientId")), existing)

    def _verify(self, email, code):
        try:
            return self.auth.verify_code(email, code)
        except auth.AuthError as e:
            return e


class AuthTokenHandler(SessionMixin, BaseHandler):
    async def post(self):
        body = self.body_json()
        if not VERIFY_PER_IP.allow(self.client_ip()):
            raise ApiError(429, "Too many attempts. Please try again later.")
        try:
            identity = await in_thread(self.auth.user_from_token, str(body.get("accessToken") or ""))
        except auth.AuthError as e:
            _raise(e)
        await self.finish_login(identity, _uuid(body.get("clientId")))


class AuthGoogleHandler(SessionMixin, BaseHandler):
    @property
    def google(self):
        return self.application.settings["google"]

    async def get(self):
        """The older way: through Supabase's Google provider (used only when GOOGLE_CLIENT_ID is not set)."""
        url = self.auth.google_url(self.site_url() + "/auth-callback.html")
        if not url or not await in_thread(self.auth.google_enabled):
            raise ApiError(400, "Google sign-in is not available on this server.")
        self.redirect(url)

    async def post(self):
        """Sign in (or sign up: the account is made on the first time) with the ID token from Google's button."""
        if not self.google.enabled:
            raise ApiError(400, "Google sign-in is not available on this server.")
        body = self.body_json()
        ip = self.client_ip()
        if GOOGLE_BAD_PER_IP.blocked(ip):
            raise ApiError(429, "Too many attempts. Please try again later.")
        try:
            identity = await in_thread(self.google.verify, body.get("credential"))
        except auth.AuthError as e:
            if e.status < 500:
                GOOGLE_BAD_PER_IP.allow(ip)  # a refused token counts against the address; Google being down does not
            _raise(e)
        await self.finish_login(identity, _uuid(body.get("clientId")))


class LogoutHandler(BaseHandler):
    def post(self):
        self.end_session()
        self.send_json({"ok": True})


class MeHandler(BaseHandler):
    async def get(self):
        profile = await self.load_profile()
        if not profile:
            if self.current_user:
                self.end_session()  # the account no longer exists
            return self.send_json({"user": None})
        self.send_json(await in_thread(account_payload, self.db, profile))

    async def post(self):
        """Change the name and/or the study goal (only the fields sent)."""
        profile = await self.require_profile()
        body = self.body_json()
        try:
            values = accounts.clean_goal(body)
        except accounts.GoalError as e:
            _raise(e)
        if "name" in body:
            values["name"] = re.sub(r"\s+", " ", str(body.get("name") or "")).strip()[:80] or None
        if values:
            await in_thread(self.db.update, "profiles", {"id": profile["id"]}, values)
            profile.update(values)
        self.send_json(await in_thread(account_payload, self.db, profile))


def progress_points(store, db, user_id):
    """
    One point per scored attempt, oldest first: timed Listening and Reading
    tests, Writing (the examiner's band if a check was marked, otherwise the AI
    estimate) and Speaking (the examiner's band, otherwise the AI examiner's).
    Also `activity`: every finished attempt (practice too), for the calendar.
    The three reads go to the database side by side.
    """
    scored, spoken, writing_checks = gather(
        lambda: store.list_history(None, 300, user_id=user_id),
        lambda: speaking.history_items(db, user_id, 300, counts=False),
        lambda: db.select("checks", {"student_id": user_id, "kind": "writing", "status": "completed"}, limit=500))
    marked = {c["submission_id"]: c for c in writing_checks}
    points, activity = [], []
    for i in scored + spoken:
        band, source = i.get("bandScore"), "auto"
        if i["module"] == "writing":
            if i["id"] in marked and marked[i["id"]].get("overall_band") is not None:
                try:
                    band, source = float(marked[i["id"]]["overall_band"]), "examiner"
                except (ValueError, TypeError):
                    band, source = None, "examiner"
            else:
                source = "ai"
        elif i["module"] == "speaking":
            source = "examiner"
            if band is None and i.get("aiBand") is not None:
                band, source = i["aiBand"], "ai"
        if not i.get("createdAt"):
            continue
        activity.append({"module": i["module"], "date": i["createdAt"], "mode": i.get("mode") or "exam",
                         "testId": i["testId"], "band": float(band) if band is not None else None})
        if i["module"] in ("reading", "listening") and i.get("mode") == "practice":
            continue  # untimed practice would inflate the trend
        if band is None:
            continue
        points.append({"module": i["module"], "date": i["createdAt"], "band": float(band), "testId": i["testId"],
                       "source": source})
    points.sort(key=lambda p: p["date"])
    activity.sort(key=lambda p: p["date"])
    return points, activity


class ProgressHandler(BaseHandler):
    async def get(self):
        profile = await self.require_profile()
        points, activity = await in_thread(progress_points, self.store, self.db, profile["id"])
        self.send_json({"points": points, "activity": activity})


# --------------------------------------------------------------------------
# Plans and payments
# --------------------------------------------------------------------------

class BillingConfigHandler(BaseHandler):
    def get(self):
        # The passes and their prices are public even before anything is for sale (payment services want to see them).
        self.send_json(billing.public_config(accounts.commerce_enabled()))


async def _own_order(handler, order_id):
    profile = await handler.require_profile()
    order = await in_thread(billing.get_order, handler.db, order_id)
    if not order or order["user_id"] != profile["id"]:
        raise ApiError(404, "Order not found.")
    return profile, order


class OrdersHandler(BaseHandler):
    async def get(self):
        profile = await self.require_profile()
        orders = await in_thread(billing.user_orders, self.db, profile["id"])
        self.send_json({"orders": orders})

    async def post(self):
        profile = await self.require_profile()
        body = self.body_json()
        if not guard.ORDERS.allow(profile["id"]):
            raise ApiError(429, "Too many orders started. Please wait a while, or write to us if a payment is stuck.")
        try:
            order = await in_thread(billing.create_order, self.db, profile["id"], str(body.get("kind") or ""),
                                    _uuid(body.get("examinerId")), body.get("submissionId"),
                                    str(body.get("scope") or "full"), body.get("months") or 1, str(body.get("currency") or "UZS"))
        except (billing.BillingError, checks.CheckError) as e:
            _raise(e)
        self.send_json({"order": billing.public_order(order)})


class OrderPayHandler(BaseHandler):
    async def post(self, order_id):
        profile, order = await _own_order(self, order_id)
        method = str(self.body_json().get("method") or "")
        try:
            result = await in_thread(billing.checkout, order, method, self.site_url() + "/#/account?paid=1", profile,
                                     self.site_url() + "/#/pricing")
        except billing.BillingError as e:
            _raise(e)
        self.send_json(result)


class SubscriptionCancelHandler(BaseHandler):
    """The student stops the renewals of a pass. The days already paid for stay."""

    async def post(self):
        profile = await self.require_profile()
        scope = str(self.body_json().get("scope") or "") or None
        try:
            done = await in_thread(billing.cancel_subscriptions, self.db, profile["id"], scope)
        except billing.BillingError as e:
            _raise(e)
        self.send_json({"cancelled": done, "plan": await in_thread(accounts.plan_status, self.db, profile["id"])})


class PaymeHandler(BaseHandler):
    async def post(self):
        api = billing.PaymeApi(self.db)
        result = await in_thread(api.handle, self.request.body, self.request.headers.get("Authorization", ""))
        self.send_json(result)


class DodoWebhookHandler(BaseHandler):
    """Dodo Payments calls this when a card payment or a refund happens (billing.handle_dodo_webhook checks it)."""

    async def post(self):
        try:
            note = await in_thread(billing.handle_dodo_webhook, self.db, self.request.headers, self.request.body)
        except billing.BillingError as e:
            _raise(e)
        self.send_json({"ok": True, "note": note})


class ClickHandler(BaseHandler):
    ACCEPTS_FORMS = True

    async def post(self, action):
        fields = {k: self.get_body_argument(k, "") for k in self.request.body_arguments}
        api = billing.ClickApi(self.db)
        result = await in_thread(api.prepare if action == "prepare" else api.complete, fields, self.client_ip())
        self.send_json(result)


# --------------------------------------------------------------------------
# Examiners and checks
# --------------------------------------------------------------------------

class ExaminersHandler(BaseHandler):
    async def get(self):
        kind = self.get_query_argument("kind", "")
        items = await in_thread(checks.list_examiners, self.db, kind if kind in ("writing", "speaking") else None)
        self.send_json({"examiners": items})


class ExaminerDetailHandler(BaseHandler):
    async def get(self, examiner_id):
        row = await in_thread(checks.get_examiner, self.db, examiner_id)
        if not row or not row.get("approved"):
            raise ApiError(404, "Examiner not found.")
        examiner = next((e for e in await in_thread(checks.list_examiners, self.db, None, True) if e["id"] == examiner_id),
                        checks.public_examiner(row))
        reviews = await in_thread(checks.examiner_reviews, self.db, examiner_id)
        self.send_json({"examiner": examiner, "reviews": reviews})


def _submission_view(store, db, check):
    """What the student wrote or said, with the test questions, for the check page."""
    if check["kind"] == "writing":
        rows = db.select("writing_submissions", {"id": check["submission_id"]}, limit=1)
        if not rows:
            return None
        sub = rows[0]
        test = store.get_test(sub["test_id"]) or {}
        tasks = {t["taskNumber"]: t for t in test.get("tasks", [])}
        return {
            "testId": sub["test_id"], "title": test.get("title", sub["test_id"]),
            "candidateName": sub.get("candidate_name"), "createdAt": sub.get("created_at"),
            "tasks": [{
                "taskNumber": n, "title": (tasks.get(n) or {}).get("title", f"Task {n}"),
                "prompt": (tasks.get(n) or {}).get("prompt", ""), "visual": (tasks.get(n) or {}).get("visual"),
                "minWords": (tasks.get(n) or {}).get("minWords"), "response": sub.get(f"task{n}_text") or "",
                "words": sub.get(f"task{n}_words") or 0,
            } for n in (1, 2)],
        }
    sub = speaking.get_submission(db, check["submission_id"])
    return speaking.submission_view(db, store, sub) if sub else None


async def _visible_check(handler, check_id):
    profile = await handler.require_profile()
    check = await in_thread(checks.get_check, handler.db, check_id)
    if not check:
        raise ApiError(404, "Check not found.")
    role = "student" if check["student_id"] == profile["id"] else \
        "examiner" if check["examiner_id"] == profile["id"] else "admin" if profile["role"] == "admin" else None
    if not role:
        raise ApiError(404, "Check not found.")
    return profile, check, role


class MyChecksHandler(BaseHandler):
    async def get(self):
        profile = await self.require_profile()
        self.send_json({"checks": await in_thread(checks.checks_for_student, self.db, profile["id"])})


class CheckHandler(BaseHandler):
    async def get(self, check_id):
        _, check, role = await _visible_check(self, check_id)
        examiner = await in_thread(checks.get_examiner, self.db, check["examiner_id"])
        out = checks.public_check(check, examiner)
        out["viewerRole"] = role
        out["submission"] = await in_thread(_submission_view, self.store, self.db, check)
        self.send_json({"check": out})


class CheckRateHandler(BaseHandler):
    async def post(self, check_id):
        profile, check, _ = await _visible_check(self, check_id)
        body = self.body_json()
        try:
            check = await in_thread(checks.rate_check, self.db, check, profile["id"], body.get("rating"), body.get("review"))
        except checks.CheckError as e:
            _raise(e)
        self.send_json({"check": checks.public_check(check)})


class ExaminerMeHandler(BaseHandler):
    async def get(self):
        profile = await self.require_role("examiner")
        row = await in_thread(checks.get_examiner, self.db, profile["id"])
        queue = await in_thread(checks.checks_for_examiner, self.db, profile["id"])
        stats = next((e for e in await in_thread(checks.list_examiners, self.db, None, True) if e["id"] == profile["id"]), None)
        self.send_json({"examiner": stats or (checks.public_examiner(row) if row else None), "checks": queue})

    async def post(self):
        profile = await self.require_role("examiner")
        b = self.body_json()
        fields = {k: b[j] for j, k in (("displayName", "display_name"), ("headline", "headline"), ("bio", "bio"),
                                       ("doesWriting", "does_writing"), ("doesSpeaking", "does_speaking"),
                                       ("accepting", "accepting")) if j in b}
        try:
            row = await in_thread(checks.save_examiner, self.db, profile["id"], fields, False)
        except checks.CheckError as e:
            _raise(e)
        self.send_json({"examiner": checks.public_examiner(row)})


class ExaminerCheckActionHandler(BaseHandler):
    async def post(self, check_id, action):
        profile = await self.require_role("examiner")
        check = await in_thread(checks.get_check, self.db, check_id)
        if not check or check["examiner_id"] != profile["id"]:
            raise ApiError(404, "Check not found.")
        try:
            if action == "start":
                check = await in_thread(checks.start_check, self.db, check, profile["id"])
            else:
                check = await in_thread(checks.submit_result, self.db, check, profile["id"], self.body_json().get("result"))
                notify.check_completed(self.db, check)
        except checks.CheckError as e:
            _raise(e)
        self.send_json({"check": checks.public_check(check)})


# --------------------------------------------------------------------------
# Speaking tests
# --------------------------------------------------------------------------

class SpeakingStartHandler(BaseHandler):
    async def post(self, test_id):
        test = await in_thread(self.store.get_test, test_id)
        if not test or test.get("module") != "speaking":
            raise ApiError(404, "Speaking test not found.")
        profile = await self.load_profile()
        if not profile:
            raise ApiError(401, "Sign in to record your answers.", "login_required")
        plan = await in_thread(accounts.plan_status, self.db, profile["id"])
        if accounts.test_access(test) != "free":
            if not accounts.can_open_test(test, profile, plan):
                if accounts.test_access(test) == "soon":
                    raise ApiError(403, "This test is coming soon.", "coming_soon")
                raise ApiError(402, "This test is part of the monthly plan.", "plan_required")
        elif not accounts.retakes_allowed(profile, plan, test.get("module")) and await in_thread(accounts.already_taken, self.db, test, profile["id"]):
            raise ApiError(409, "You have already taken this test. Each free test can be taken once.", "already_taken")
        body = self.body_json()
        mode = body.get("mode")
        notice = None

        notice_code = None

        def start():
            nonlocal mode, notice, notice_code
            tier = None
            if mode == "ai":
                try:
                    tier = speaking_ai.check_can_start(self.db, profile, plan)
                except speaking_ai.ReviewError as e:
                    if not body.get("fallback"):
                        raise
                    # The test goes ahead without the AI's band (not configured, or the allowance is used).
                    mode, notice, notice_code = "exam", (str(e) if e.status == 429 else None), getattr(e, "code", None)
            try:
                return speaking.start_submission(self.db, profile["id"], test, clean_name(body.get("candidateName")), mode,
                                                 usage={"tier": tier} if tier else None)
            except Exception:
                ai_usage.release("speaking", tier)
                raise
        try:
            sub = await in_thread(start)
        except (speaking.SpeakingError, speaking_ai.ReviewError) as e:
            _raise(e)
        state = speaking_adaptive.state_of(sub)
        self.send_json({"submissionId": sub["id"], "mode": sub.get("mode"), "notice": notice, "noticeCode": notice_code,
                        "plan": speaking_adaptive.public_plan(test, state) if state else None})


@tornado.web.stream_request_body
class SpeakingAnswerHandler(BaseHandler):
    """Receives one recorded answer as the raw request body (audio/webm, audio/mp4, ...)."""

    async def prepare(self):
        # Only recorded audio is accepted. Browsers cannot send these types to another
        # site without a CORS preflight, which this server never allows, so no CSRF.
        self.chunks, self.size = [], 0
        if not guard.origin_allowed(self.request.headers, self.request.path):   # (BaseHandler.prepare is not used here)
            raise tornado.web.HTTPError(403, "Please use the site's address")
        if self.request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise tornado.web.HTTPError(403, "Cross-site request blocked")
        origin = self.request.headers.get("Origin")
        if origin and not self._is_same_origin(origin):
            raise tornado.web.HTTPError(403, "Cross-origin state change blocked")
        if self.request.method != "POST":
            return
        if speaking.base_mime(self.request.headers.get("Content-Type")) not in speaking.AUDIO_TYPES:
            raise ApiError(415, "This audio format is not supported.")
        self.profile = await self.require_profile()
        # Each recording waits in memory until it is complete: only so many at the same moment (the page retries).
        if not guard.UPLOADS.enter():
            raise ApiError(503, "Many answers are being saved right now. Retrying…", "busy")
        self.gated = True

    def _leave(self):
        if getattr(self, "gated", False):
            self.gated = False
            guard.UPLOADS.leave()

    def on_finish(self):
        self._leave()

    def on_connection_close(self):
        self._leave()
        super().on_connection_close()

    def data_received(self, chunk):
        self.size += len(chunk)
        if self.size <= speaking.MAX_RECORDING_BYTES:
            self.chunks.append(chunk)

    async def post(self, submission_id, key):
        if self.size > speaking.MAX_RECORDING_BYTES:
            raise ApiError(413, "The recording is too long.")
        data = b"".join(self.chunks)
        mime = self.request.headers.get("Content-Type")
        duration = self.request.headers.get("X-Duration")
        if not guard.DAY.take("upload_mb", max(1, -(-len(data) // (1024 * 1024)))):
            raise ApiError(503, "Recording is paused on the site for today. Please try again tomorrow.", "uploads_full")

        def save():
            sub = speaking.own_submission(self.db, submission_id, self.profile["id"])
            test = self.store.get_test(sub["test_id"])
            if not test:
                raise speaking.SpeakingError("Speaking test not found.", 404)
            rec = speaking.save_recording(self.db, self.store.files, sub, test, key, data, mime, duration)
            try:  # a test that adapts to the candidate listens to each answer as it arrives
                speaking_adaptive.queue_analysis(self.db, self.store.files, self.store, sub, key, rec["id"])
            except Exception:
                log.exception("Could not start the analysis of an answer")
            return rec
        try:
            rec = await in_thread(save)
        except speaking.SpeakingError as e:
            _raise(e)
        self.send_json({"recording": rec})


class SpeakingPlanHandler(BaseHandler):
    """
    The questions an AI-examiner test has so far. Sent after the candidate answers the last question planned in Part 1
    or Part 3 ({"after": key}), it adds one more question when the AI examiner wants it (speaking_adaptive.py).
    """

    async def post(self, submission_id):
        profile = await self.require_profile()
        after = self.body_json().get("after")
        after = after if isinstance(after, str) and re.match(r"^[a-z0-9][a-z0-9\-]{0,30}$", after) else None

        def plan():
            sub = speaking.own_submission(self.db, submission_id, profile["id"])
            test = self.store.get_test(sub["test_id"])
            if not test:
                raise speaking.SpeakingError("Speaking test not found.", 404)
            return speaking_adaptive.next_plan(self.db, self.store.files, self.store, sub, test, after)
        try:
            result = await in_thread(plan)
        except (speaking.SpeakingError, speaking_adaptive.AdaptiveError) as e:
            _raise(e)
        self.send_json({"plan": result})


class SpeakingCompleteHandler(BaseHandler):
    async def post(self, submission_id):
        profile = await self.require_profile()
        body = self.body_json()
        try:
            seconds = max(0, min(int(body.get("timeSpentSeconds") or 0), 4 * 3600))
        except (TypeError, ValueError):
            seconds = 0

        def complete():
            sub = speaking.own_submission(self.db, submission_id, profile["id"])
            sub = speaking.complete_submission(self.db, sub, body.get("notes"), seconds)
            if sub.get("mode") == "ai":
                sub["ai_review"] = speaking_ai.start_review(self.db, self.store.files, self.store, sub)
            view = speaking.submission_view(self.db, self.store, sub)
            view["aiReview"] = speaking_ai.public_review(sub)
            return view
        try:
            view = await in_thread(complete)
        except speaking.SpeakingError as e:
            _raise(e)
        self.send_json({"submission": view})
        self.track("test_finished", user_id=profile["id"], module="speaking", test_id=view.get("testId"))


class SpeakingSubmissionHandler(BaseHandler):
    async def get(self, submission_id):
        profile = await self.require_profile()

        def load():
            sub = speaking.get_submission(self.db, submission_id)
            role = speaking.viewer_role(self.db, profile, sub) if sub else None
            if not role:
                raise speaking.SpeakingError("Speaking test not found.", 404)
            view = speaking.submission_view(self.db, self.store, sub)
            view["viewerRole"] = role
            # The examiner marking a check does not see the AI's band, so it cannot sway theirs.
            view["aiReview"] = speaking_ai.public_review(sub) if role in ("owner", "admin") else None
            if role == "owner":
                check = speaking.checks_by_submission(self.db, profile["id"]).get(sub["id"])
                view["check"] = checks.public_check(check, include_result=False) if check else None
            return view
        try:
            view = await in_thread(load)
        except speaking.SpeakingError as e:
            _raise(e)
        self.send_json({"submission": view})


class SpeakingAiReviewHandler(BaseHandler):
    """Rate an AI-examiner test again after the first review failed."""

    async def post(self, submission_id):
        profile = await self.require_profile()

        def retry():
            sub = speaking.own_submission(self.db, submission_id, profile["id"])
            if sub["status"] != "completed":
                raise speaking.SpeakingError("Finish the test first.", 409)
            speaking_ai.retry_review(self.db, self.store.files, self.store, sub)
            return speaking_ai.public_review(speaking.get_submission(self.db, sub["id"]))
        try:
            review = await in_thread(retry)
        except (speaking.SpeakingError, speaking_ai.ReviewError) as e:
            _raise(e)
        self.send_json({"aiReview": review})


class RecordingHandler(BaseHandler):
    """Streams one recording to its owner, the examiner marking it, or an admin. Supports Range requests."""

    async def get(self, recording_id):
        profile = await self.require_profile()
        if not guard.RECORDING_FETCHES.allow(profile["id"]):
            raise ApiError(429, "Too many requests for recordings. Please wait a few minutes.")
        rid = _uuid(recording_id)
        row = await in_thread(speaking.recording_for, self.db, profile, rid) if rid else None
        data = guard.RECORDINGS.get(row["path"]) if row else None
        if row and data is None:
            data = await in_thread(self.store.files.get, row["path"])
            guard.RECORDINGS.put(row["path"], data)
        if data is None:
            raise ApiError(404, "Recording not found.")
        self.set_header("Content-Type", row["mime"])
        self.set_header("Accept-Ranges", "bytes")
        self.set_header("Cache-Control", "private, max-age=3600")
        size = len(data)
        m = re.match(r"^bytes=(\d*)-(\d*)$", self.request.headers.get("Range", "").strip())
        if m and (m.group(1) or m.group(2)):
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
            else:
                start, end = max(0, size - int(m.group(2))), size - 1
            if start >= size or start > end:
                self.set_status(416)
                self.set_header("Content-Range", f"bytes */{size}")
                return self.finish()
            self.set_status(206)
            self.set_header("Content-Range", f"bytes {start}-{end}/{size}")
            data = data[start:end + 1]
        self.finish(data)


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Funnel events and feedback (see mockexam/analytics.py)
# --------------------------------------------------------------------------

EVENTS_PER_IP = auth.AttemptLimiter(120, 600)
FEEDBACK_PER_IP = auth.AttemptLimiter(5, 3600)
MAX_EVENT_BYTES = 1024
MAX_FEEDBACK_BYTES = 6 * 1024


class EventsHandler(BaseHandler):
    """POST /api/events: a browser reports visit, free_test_started or cta_click. Answers 204 at once."""

    async def post(self):
        if len(self.request.body or b"") > MAX_EVENT_BYTES:
            raise ApiError(413, "Event too large.")
        try:
            event = analytics.client_event(self.body_json())
        except analytics.AnalyticsError as e:
            raise ApiError(e.status, str(e))
        if not EVENTS_PER_IP.allow(self.client_ip()):
            raise ApiError(429, "Too many events.")
        body = self.body_json()
        if guard.DAY.take("event"):   # over the day's budget, events are dropped quietly
            self.track(event.pop("name"), client_id=_uuid(body.get("clientId")), user_id=self.current_user, **event)
        self.set_status(204)
        self.finish()


class FeedbackHandler(BaseHandler):
    """POST /api/feedback: a message from the Feedback button (rating and email optional)."""

    async def post(self):
        if len(self.request.body or b"") > MAX_FEEDBACK_BYTES:
            raise ApiError(413, "Please keep the message shorter.")
        body = self.body_json()
        try:
            fields = analytics.clean_feedback(body)
        except analytics.AnalyticsError as e:
            raise ApiError(e.status, str(e))
        if not FEEDBACK_PER_IP.allow(self.client_ip()):
            raise ApiError(429, "Thank you! You have sent several messages already; please try again later.")
        if not guard.DAY.take("feedback"):
            raise ApiError(429, "Thank you! We have received many messages today; please try again tomorrow.")
        row = dict(fields, client_id=_uuid(body.get("clientId")), user_id=self.current_user)
        try:
            saved = await in_thread(self.db.insert, "feedback", row)
        except Exception:  # noqa: BLE001 – e.g. the feedback table is not created yet (run supabase/schema.sql)
            log.exception("Could not save feedback")
            raise ApiError(503, "Sorry, we could not save your message. Please try again later.")
        try:
            await in_thread(notify.feedback_received, saved)
        except Exception:  # noqa: BLE001 – the message is saved; the owner sees it in Admin
            log.warning("Could not notify about feedback", exc_info=True)
        self.send_json({"ok": True})


class AdminHandler(BaseHandler):
    async def require_admin(self):
        if self.require_admin_token():
            return None
        return await self.require_role("admin")


def _emails_for(db, user_ids):
    ids = list({u for u in user_ids if u})
    if not ids:
        return {}
    return {p["id"]: p["email"] for p in db.select("profiles", {"id": ("in", ids)}, limit=len(ids))}


class AdminClickHandler(AdminHandler):
    """Admin → Click: the settings (never the secret key), the two addresses Click must call, and what Click has sent."""

    async def get(self):
        await self.require_admin()
        info = billing.click_status()
        base = billing.CLICK["callback_base"] or self.site_url()
        info["urls"] = {"prepare": f"{base}/api/pay/click/prepare", "complete": f"{base}/api/pay/click/complete"}
        self.send_json(info)


class AdminClickCheckHandler(AdminHandler):
    async def post(self):
        await self.require_admin()
        self.send_json(await in_thread(billing.click_check))


class TelegramLinkHandler(BaseHandler):
    """POST: a link that opens @testdayuzbot and connects this account. DELETE: disconnect Telegram."""

    async def post(self):
        profile = await self.require_profile()
        if not telegram_bot.configured("student"):
            raise ApiError(503, "Telegram is not set up on this site yet.")
        self.send_json({"url": telegram_bot.link_url(profile["id"])})

    async def delete(self):
        profile = await self.require_profile()
        await in_thread(telegram_bot.disconnect, self.db, profile["id"])
        self.send_json({"connected": False})


class TelegramHookHandler(BaseHandler):
    """Updates from Telegram for one of the bots. Only Telegram knows the secret header."""

    async def post(self, bot):
        if not telegram_bot.secret_ok(self.request.headers.get("X-Telegram-Bot-Api-Secret-Token")):
            raise ApiError(403, "Not allowed.")
        try:
            update = json.loads(self.request.body or b"{}")
        except ValueError:
            raise ApiError(400, "Not JSON.")
        if isinstance(update, dict):
            store, db = self.store, self.db
            await in_thread(telegram_bot.handle_update, bot, db, lambda uid: progress_points(store, db, uid), update)
        self.send_json({"ok": True})


class AdminAiUsageHandler(AdminHandler):
    """Admin → AI: jobs and their cost per paper in the last 30 days, and the people who used the AI examiner most."""

    async def get(self):
        await self.require_admin()
        data = await in_thread(ai_usage.summary, self.db)
        ids = [p["userId"] for p in data["top"]]
        if ids:
            profiles = await in_thread(lambda: self.db.select("profiles", {"id": ("in", ids)}, limit=len(ids)))
            plans = await in_thread(accounts.plan_statuses, self.db, ids)
            emails = {p["id"]: p.get("email") for p in profiles}
            for p in data["top"]:
                p["email"] = emails.get(p["userId"])
                p["modules"] = (plans.get(p["userId"]) or {}).get("modules") or []
        self.send_json(data)


class AdminOrdersHandler(AdminHandler):
    async def get(self):
        await self.require_admin()
        status = self.get_query_argument("status", "")
        where = {"status": status} if status in ("pending", "awaiting_confirmation", "paid", "cancelled", "refunded") else {}

        def load():
            rows = self.db.select("orders", where, order=[("created_at", "desc")], limit=200)
            emails = _emails_for(self.db, [r["user_id"] for r in rows] + [r.get("examiner_id") for r in rows])
            return [dict(billing.public_order(r), userEmail=emails.get(r["user_id"]),
                         examinerEmail=emails.get(r.get("examiner_id"))) for r in rows]
        self.send_json({"orders": await in_thread(load)})


class AdminFeedbackHandler(AdminHandler):
    async def get(self):
        await self.require_admin()
        rows = await in_thread(lambda: self.db.select("feedback", order=[("created_at", "desc")], limit=100))
        self.send_json({"feedback": [analytics.public_feedback(r) for r in rows]})


class AdminOrderActionHandler(AdminHandler):
    async def post(self, order_id, action):
        await self.require_admin()
        order = await in_thread(billing.get_order, self.db, order_id)
        if not order:
            raise ApiError(404, "Order not found.")
        note = None
        try:
            if action == "confirm":
                order = await in_thread(billing.fulfil_order, self.db, order["id"], order.get("provider") or "manual")
            elif action == "refund":
                if order["status"] != "paid":
                    raise billing.BillingError("Only paid orders can be refunded.")
                if not billing.can_refund(self.db, order):
                    raise billing.BillingError("The examiner has already started this check, so it cannot be refunded.")
                # Dodo and Click are asked to give the money back; {"manual": true} says the admin has returned it already.
                if not self.body_json().get("manual"):
                    note = await in_thread(billing.refund_at_provider, order)
                order = await in_thread(billing.refund_order, self.db, order)
            else:
                await in_thread(billing.cancel_unpaid_order, self.db, order)
                order = await in_thread(billing.get_order, self.db, order["id"])
        except (billing.BillingError, checks.CheckError) as e:
            _raise(e)
        self.send_json({"order": billing.public_order(order), "note": note})


class AdminExaminersHandler(AdminHandler):
    async def get(self):
        await self.require_admin()

        def load():
            items = checks.list_examiners(self.db, None, include_hidden=True)
            emails = _emails_for(self.db, [e["id"] for e in items])
            return [dict(e, email=emails.get(e["id"])) for e in items]
        self.send_json({"examiners": await in_thread(load)})

    async def post(self):
        await self.require_admin()
        b = self.body_json()
        email = str(b.get("email") or "").strip().lower()

        def save():
            profile = accounts.find_profile_by_email(self.db, email)
            if not profile:
                raise checks.CheckError("No account with this email. Ask the examiner to sign in once first.", 404)
            if accounts.profile_role(profile) != "admin" and profile["role"] != "examiner":
                self.db.update("profiles", {"id": profile["id"]}, {"role": "examiner"})
            fields = {k: b[j] for j, k in (("displayName", "display_name"), ("headline", "headline"), ("bio", "bio"),
                                           ("doesWriting", "does_writing"), ("doesSpeaking", "does_speaking"),
                                           ("accepting", "accepting"), ("approved", "approved")) if j in b}
            if not checks.get_examiner(self.db, profile["id"]) and "display_name" not in fields:
                fields["display_name"] = profile.get("name") or email.split("@")[0]
            return checks.save_examiner(self.db, profile["id"], fields, admin=True)
        try:
            row = await in_thread(save)
        except checks.CheckError as e:
            _raise(e)
        self.send_json({"examiner": checks.public_examiner(row)})


class AdminUsersHandler(AdminHandler):
    async def get(self):
        await self.require_admin()
        q = self.get_query_argument("q", "").strip().lower()[:80]

        def load():
            rows = self.db.select("profiles", {"email": ("ilike", q)} if q else {}, order=[("created_at", "desc")], limit=50)
            plans = accounts.plan_statuses(self.db, [r["id"] for r in rows])  # one query for all of them
            return [dict(_public_user(dict(r, role=accounts.profile_role(r))), createdAt=r.get("created_at"),
                         plan=plans[r["id"]]) for r in rows]
        self.send_json({"users": await in_thread(load)})


class AdminPlanHandler(AdminHandler):
    async def post(self):
        await self.require_admin()
        b = self.body_json()
        try:
            days = int(b.get("days"))
        except (TypeError, ValueError):
            raise ApiError(400, "Enter the number of days.")
        if not 1 <= days <= 400:
            raise ApiError(400, "Days must be between 1 and 400.")
        profile = await in_thread(accounts.find_profile_by_email, self.db, str(b.get("email") or ""))
        if not profile:
            raise ApiError(404, "No account with this email.")
        await in_thread(accounts.grant_plan_period, self.db, profile["id"], days, "admin", None,
                        str(b.get("note") or "")[:200] or None)
        self.send_json({"plan": await in_thread(accounts.plan_status, self.db, profile["id"])})


def commerce_only(handler_class):
    """The same handler, but answering 404 while the site sells nothing (COMMERCE_ENABLED is off)."""
    class Gated(handler_class):
        async def prepare(self):
            if not accounts.commerce_enabled():
                raise ApiError(404, "Not available.")
            result = super().prepare()
            if result is not None:
                await result

    Gated.__name__ = handler_class.__name__
    return Gated


def checks_only(handler_class):
    """The same handler, but answering 404 while examiner checks are not offered (EXAMINER_CHECKS_ENABLED is off)."""
    class Gated(handler_class):
        async def prepare(self):
            if not accounts.checks_enabled():
                raise ApiError(404, "Not available.")
            result = super().prepare()
            if result is not None:
                await result

    Gated.__name__ = handler_class.__name__
    return Gated


def routes():
    return [
        (r"/api/auth/code", AuthCodeHandler),
        (r"/api/auth/verify", AuthVerifyHandler),
        (r"/api/auth/token", AuthTokenHandler),
        (r"/api/auth/google", AuthGoogleHandler),
        (r"/api/auth/logout", LogoutHandler),
        (r"/api/me", MeHandler),
        (r"/api/progress", ProgressHandler),
        (r"/api/billing", BillingConfigHandler),
        (r"/api/orders", commerce_only(OrdersHandler)),
        (r"/api/orders/(\d+)/pay", commerce_only(OrderPayHandler)),
        (r"/api/subscriptions/cancel", commerce_only(SubscriptionCancelHandler)),
        (r"/api/pay/payme", commerce_only(PaymeHandler)),
        (r"/api/pay/click/(prepare|complete)", commerce_only(ClickHandler)),
        (r"/api/pay/dodo/webhook", DodoWebhookHandler),
        (r"/api/examiners", checks_only(ExaminersHandler)),
        (r"/api/examiners/([0-9a-f\-]{36})", checks_only(ExaminerDetailHandler)),
        (r"/api/checks", checks_only(MyChecksHandler)),
        (r"/api/checks/(\d+)", checks_only(CheckHandler)),
        (r"/api/checks/(\d+)/rate", checks_only(CheckRateHandler)),
        (r"/api/examiner/me", checks_only(ExaminerMeHandler)),
        (r"/api/examiner/checks/(\d+)/(start|result)", checks_only(ExaminerCheckActionHandler)),
        (r"/api/speaking/([a-z0-9][a-z0-9\-]{0,80})/start", SpeakingStartHandler),
        (r"/api/speaking/submissions/(\d+)/answers/([a-z0-9][a-z0-9\-]{0,30})", SpeakingAnswerHandler),
        (r"/api/speaking/submissions/(\d+)/plan", SpeakingPlanHandler),
        (r"/api/speaking/submissions/(\d+)/complete", SpeakingCompleteHandler),
        (r"/api/speaking/submissions/(\d+)/ai-review", SpeakingAiReviewHandler),
        (r"/api/speaking/submissions/(\d+)", SpeakingSubmissionHandler),
        (r"/api/speaking/recordings/([0-9a-f\-]{36})", RecordingHandler),
        (r"/api/admin/click", AdminClickHandler),
        (r"/api/admin/click/check", AdminClickCheckHandler),
        (r"/api/admin/ai-usage", AdminAiUsageHandler),
        (r"/api/telegram/link", TelegramLinkHandler),
        (r"/api/telegram/hook/(student|support)", TelegramHookHandler),
        (r"/api/admin/orders", AdminOrdersHandler),
        (r"/api/admin/orders/(\d+)/(confirm|refund|cancel)", AdminOrderActionHandler),
        (r"/api/admin/feedback", AdminFeedbackHandler),
        (r"/api/events", EventsHandler),
        (r"/api/feedback", FeedbackHandler),
        (r"/api/admin/examiners", AdminExaminersHandler),
        (r"/api/admin/users", AdminUsersHandler),
        (r"/api/admin/plan", AdminPlanHandler),
    ]
