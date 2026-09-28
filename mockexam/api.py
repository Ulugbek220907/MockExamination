"""
HTTP API for accounts, plans and payments, examiners and checks, and admin.

  POST /api/auth/code                 email a 6-digit sign-in code
  POST /api/auth/verify               check the code, start a session
  POST /api/auth/token                start a session from a Google / email-link redirect
  GET  /api/auth/google               redirect to Google sign-in (via Supabase)
  POST /api/auth/logout
  GET  /api/me, POST /api/me          account, plan, examiner profile; change name

  GET  /api/billing                   prices and payment methods
  GET  /api/orders, POST /api/orders  your orders / create an order
  POST /api/orders/<id>/pay           start paying (redirect URL or card details)
  POST /api/orders/<id>/manual-paid   "I have transferred the money"
  POST /api/pay/payme                 Payme Merchant API callback
  POST /api/pay/click/(prepare|complete)  Click SHOP API callbacks

  GET  /api/examiners[?kind=]         examiners students can choose
  GET  /api/examiners/<id>            one examiner with reviews
  GET  /api/checks                    your checks
  GET  /api/checks/<id>               one check (student, its examiner, or admin)
  POST /api/checks/<id>/rate          rate the examiner once
  GET  /api/examiner/me, POST         examiner dashboard data / edit profile
  POST /api/examiner/checks/<id>/start|result

  GET  /api/admin/orders, POST /api/admin/orders/<id>/(confirm|refund|cancel)
  GET  /api/admin/examiners, POST     list / add or update an examiner by email
  GET  /api/admin/users?q=, POST /api/admin/plan   find users / give plan days
"""

import logging
import os
import re

import tornado.web

from . import accounts, auth, billing, checks
from .web import BaseHandler, in_thread

log = logging.getLogger("mockexam.api")

DEV_CODES = os.environ.get("AUTH_DEV_CODES", "0") == "1"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

CODE_PER_IP = auth.AttemptLimiter(10, 3600)
CODE_PER_EMAIL = auth.AttemptLimiter(5, 3600)
VERIFY_PER_EMAIL = auth.AttemptLimiter(10, 900)
VERIFY_PER_IP = auth.AttemptLimiter(40, 3600)


def _uuid(value):
    value = str(value or "").strip().lower()
    return value if UUID_RE.match(value) else None


def _public_user(profile):
    return {"id": profile["id"], "email": profile["email"], "name": profile.get("name") or "", "role": profile["role"]}


def claim_attempts(db, client_id, user_id):
    """Attach the attempts this browser made before signing in to the account."""
    for table in ("reading_attempts", "listening_attempts", "writing_submissions"):
        try:
            db.update(table, {"client_id": client_id, "user_id": None}, {"user_id": user_id})
        except Exception:
            log.exception("Could not claim %s", table)


def account_payload(db, profile):
    out = {"user": _public_user(profile), "plan": accounts.plan_status(db, profile["id"]), "examiner": None}
    if profile["role"] in ("examiner", "admin"):
        row = checks.get_examiner(db, profile["id"])
        if row:
            out["examiner"] = checks.public_examiner(row)
    return out


# --------------------------------------------------------------------------
# Sign-in
# --------------------------------------------------------------------------

class ApiError(tornado.web.HTTPError):
    """An error whose message is shown to the user (and an optional machine-readable code)."""

    def __init__(self, status, message, code=None):
        super().__init__(status, log_message=message.replace("%", "%%"))
        self.code = code


def _raise(e):
    raise ApiError(getattr(e, "status", 400), str(e))


class AuthCodeHandler(BaseHandler):
    async def post(self):
        body = self.body_json()
        try:
            email = auth.clean_email(body.get("email"))
        except auth.AuthError as e:
            _raise(e)
        if not CODE_PER_IP.allow(self.client_ip()) or not CODE_PER_EMAIL.allow(email):
            raise ApiError(429, "Too many codes requested. Please wait a few minutes.")
        try:
            code = await in_thread(self.auth.send_code, email, self.site_url() + "/auth-callback.html")
        except auth.AuthError as e:
            _raise(e)
        out = {"sent": True, "email": email}
        if code and DEV_CODES:
            out["devCode"] = code
        self.send_json(out)


class SessionMixin:
    async def finish_login(self, identity, client_id):
        profile = await in_thread(accounts.upsert_profile, self.db, identity)
        if client_id:
            await in_thread(claim_attempts, self.db, client_id, profile["id"])
        self.start_session(profile["id"])
        self.send_json(await in_thread(account_payload, self.db, profile))


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
        try:
            identity = await in_thread(self.auth.verify_code, email, code)
        except auth.AuthError as e:
            _raise(e)
        await self.finish_login(identity, _uuid(body.get("clientId")))


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


class AuthGoogleHandler(BaseHandler):
    async def get(self):
        url = self.auth.google_url(self.site_url() + "/auth-callback.html")
        if not url or not await in_thread(self.auth.google_enabled):
            raise ApiError(400, "Google sign-in is not available on this server.")
        self.redirect(url)


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
        profile = await self.require_profile()
        name = re.sub(r"\s+", " ", str(self.body_json().get("name") or "")).strip()[:80]
        await in_thread(self.db.update, "profiles", {"id": profile["id"]}, {"name": name or None})
        profile["name"] = name
        self.send_json(await in_thread(account_payload, self.db, profile))


# --------------------------------------------------------------------------
# Plans and payments
# --------------------------------------------------------------------------

class BillingConfigHandler(BaseHandler):
    def get(self):
        self.send_json(billing.public_config())


async def _own_order(handler, order_id):
    profile = await handler.require_profile()
    order = await in_thread(billing.get_order, handler.db, order_id)
    if not order or order["user_id"] != profile["id"]:
        raise ApiError(404, "Order not found.")
    return profile, order


class OrdersHandler(BaseHandler):
    async def get(self):
        profile = await self.require_profile()
        rows = await in_thread(lambda: self.db.select("orders", {"user_id": profile["id"]},
                                                      order=[("created_at", "desc")], limit=50))
        self.send_json({"orders": [billing.public_order(o) for o in rows]})

    async def post(self):
        profile = await self.require_profile()
        body = self.body_json()
        try:
            order = await in_thread(billing.create_order, self.db, profile["id"], str(body.get("kind") or ""),
                                    _uuid(body.get("examinerId")), body.get("submissionId"))
        except (billing.BillingError, checks.CheckError) as e:
            _raise(e)
        self.send_json({"order": billing.public_order(order)})


class OrderPayHandler(BaseHandler):
    async def post(self, order_id):
        _, order = await _own_order(self, order_id)
        method = str(self.body_json().get("method") or "")
        try:
            result = billing.checkout(order, method, self.site_url() + "/#/account")
        except billing.BillingError as e:
            _raise(e)
        self.send_json(result)


class OrderManualPaidHandler(BaseHandler):
    async def post(self, order_id):
        profile, order = await _own_order(self, order_id)
        try:
            order = await in_thread(billing.mark_manual_paid, self.db, order, profile["id"])
        except billing.BillingError as e:
            _raise(e)
        self.send_json({"order": billing.public_order(order)})


class PaymeHandler(BaseHandler):
    async def post(self):
        api = billing.PaymeApi(self.db)
        result = await in_thread(api.handle, self.request.body, self.request.headers.get("Authorization", ""))
        self.send_json(result)


class ClickHandler(BaseHandler):
    ACCEPTS_FORMS = True

    async def post(self, action):
        fields = {k: self.get_body_argument(k, "") for k in self.request.body_arguments}
        api = billing.ClickApi(self.db)
        result = await in_thread(api.prepare if action == "prepare" else api.complete, fields)
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
    rows = db.select("speaking_submissions", {"id": check["submission_id"]}, limit=1)
    if not rows:
        return None
    sub = rows[0]
    test = store.get_test(sub["test_id"]) or {}
    return {"testId": sub["test_id"], "title": test.get("title", sub["test_id"]), "candidateName": sub.get("candidate_name"),
            "createdAt": sub.get("created_at"), "answers": sub.get("answers") or []}


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
        except checks.CheckError as e:
            _raise(e)
        self.send_json({"check": checks.public_check(check)})


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------

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


class AdminOrderActionHandler(AdminHandler):
    async def post(self, order_id, action):
        await self.require_admin()
        order = await in_thread(billing.get_order, self.db, order_id)
        if not order:
            raise ApiError(404, "Order not found.")
        try:
            if action == "confirm":
                order = await in_thread(billing.fulfil_order, self.db, order["id"], order.get("provider") or "manual")
            elif action == "refund":
                if order["status"] != "paid":
                    raise billing.BillingError("Only paid orders can be refunded.")
                order = await in_thread(billing.refund_order, self.db, order)
            else:
                await in_thread(billing.cancel_unpaid_order, self.db, order)
                order = await in_thread(billing.get_order, self.db, order["id"])
        except (billing.BillingError, checks.CheckError) as e:
            _raise(e)
        self.send_json({"order": billing.public_order(order)})


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
            return [dict(_public_user(dict(r, role=accounts.profile_role(r))), createdAt=r.get("created_at"),
                         plan=accounts.plan_status(self.db, r["id"])) for r in rows]
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


def routes():
    return [
        (r"/api/auth/code", AuthCodeHandler),
        (r"/api/auth/verify", AuthVerifyHandler),
        (r"/api/auth/token", AuthTokenHandler),
        (r"/api/auth/google", AuthGoogleHandler),
        (r"/api/auth/logout", LogoutHandler),
        (r"/api/me", MeHandler),
        (r"/api/billing", BillingConfigHandler),
        (r"/api/orders", OrdersHandler),
        (r"/api/orders/(\d+)/pay", OrderPayHandler),
        (r"/api/orders/(\d+)/manual-paid", OrderManualPaidHandler),
        (r"/api/pay/payme", PaymeHandler),
        (r"/api/pay/click/(prepare|complete)", ClickHandler),
        (r"/api/examiners", ExaminersHandler),
        (r"/api/examiners/([0-9a-f\-]{36})", ExaminerDetailHandler),
        (r"/api/checks", MyChecksHandler),
        (r"/api/checks/(\d+)", CheckHandler),
        (r"/api/checks/(\d+)/rate", CheckRateHandler),
        (r"/api/examiner/me", ExaminerMeHandler),
        (r"/api/examiner/checks/(\d+)/(start|result)", ExaminerCheckActionHandler),
        (r"/api/admin/orders", AdminOrdersHandler),
        (r"/api/admin/orders/(\d+)/(confirm|refund|cancel)", AdminOrderActionHandler),
        (r"/api/admin/examiners", AdminExaminersHandler),
        (r"/api/admin/users", AdminUsersHandler),
        (r"/api/admin/plan", AdminPlanHandler),
    ]
