"""
Billing: prices, orders, fulfilment, and the Payme and Click merchant APIs.

What can be bought
  plan            – a pass for 1 or 3 months: "full" (every paper), "speaking", "writing" or "lr" (Listening and
                    Reading). A student's first full 1-month pass comes with an extra free month.
  writing_check   – an examiner marks one Writing submission.
  speaking_check  – an examiner marks one Speaking submission.

How money arrives
  Dodo   – foreign cards in US dollars, as a SUBSCRIPTION that renews every 1 or 3 months until the student cancels:
           the student pays on Dodo's page and Dodo calls POST /api/pay/dodo/webhook for every charge. Each charge is
           an order of its own (the later ones are made by the webhook) and adds one period to the pass.
  Payme  – Payme calls POST /api/pay/payme (JSON-RPC, Merchant API).
  Click  – Click calls POST /api/pay/click/prepare and /complete (SHOP API): Uzcard and Humo cards in so'm, one payment
           for the pass (it does not renew). Refunds go back through the Merchant API (click_merchant.py).

Fulfilment is idempotent: the plan period and the examiner check are keyed
by the order id, so a repeated callback never gives anything twice.
"""

import base64
import collections
import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
import urllib.parse

from . import accounts, analytics, checks, click_merchant, dodo, notify
from .db import iso, now, parse_time

log = logging.getLogger("mockexam.billing")


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


# The passes: {kind: {months: (price in so'm, price in US cents)}}. so'm for Payme and Click when they are connected; dollars for Dodo.
# The so'm price reads like the dollar one ($3.99 -> 39 000 so'm): at about 12 000 so'm to the dollar that is a discount of
# roughly a fifth for paying locally, where the fees are lower. docs/COSTS.md shows what each pass earns after fees,
# tax and the AI marking it includes.
# Passes are sold month by month only (3-month passes were retired in November 2026: a monthly price can follow the
# cost of AI marking; card subscriptions bought for 3 months before then keep renewing as they were).
PLAN_PRICES = {
    "full": {1: (79000, 799)},   # the prices live here, not in environment variables
    "speaking": {1: (59000, 599)},
    "writing": {1: (49000, 499)},
    "lr": {1: (39000, 399)},
}
PLAN_MONTHS = (1,)
PRICES = {
    "plan": PLAN_PRICES["full"][1][0],
    "writing_check": _int_env("WRITING_CHECK_PRICE", 10000),
    "speaking_check": _int_env("SPEAKING_CHECK_PRICE", 20000),
}
PLAN_DAYS = _int_env("PLAN_DAYS", 30)   # days in one month of a pass
PLAN_FIRST_BONUS_DAYS = _int_env("PLAN_FIRST_BONUS_DAYS", 30)
CURRENCY = "so'm"
PASS_TITLES = {"full": "All-in-one pass", "speaking": "Speaking pass", "writing": "Writing pass", "lr": "Listening and Reading pass"}

PAYME = {
    "merchant_id": os.environ.get("PAYME_MERCHANT_ID", "").strip(),
    "key": os.environ.get("PAYME_KEY", "").strip(),
    "test": os.environ.get("PAYME_TEST", "0") == "1",
    "account_field": os.environ.get("PAYME_ACCOUNT_FIELD", "order_id").strip() or "order_id",
    "ikpu": os.environ.get("PAYME_IKPU", "").strip(),
    "package_code": os.environ.get("PAYME_PACKAGE_CODE", "").strip(),
}
CLICK = {
    "service_id": os.environ.get("CLICK_SERVICE_ID", "").strip(),
    "merchant_id": os.environ.get("CLICK_MERCHANT_ID", "").strip(),
    "secret_key": os.environ.get("CLICK_SECRET_KEY", "").strip(),
    # The Merchant API user (to give money back from the admin page); without it refunds are done in Click's cabinet.
    "merchant_user_id": os.environ.get("CLICK_MERCHANT_USER_ID", "").strip(),
    # Only for display in Admin → Click: the address Click is given when it calls a relay in front of the site (for
    # example https://click.testday.uz) instead of the site itself. Empty: the site's own address.
    "callback_base": os.environ.get("CLICK_CALLBACK_BASE", "").strip().rstrip("/"),
}


def click_merchant_api():
    return click_merchant.MerchantApi(CLICK["service_id"], CLICK["merchant_user_id"], CLICK["secret_key"])


# What Click last sent and what we answered, newest first (memory only: it starts empty after every restart). Admin → Click
# shows it, so that a payment that fails on Click's side can be told from one that never reached the site.
CLICK_RECENT = collections.deque(maxlen=40)


def _safe(value, limit=40):
    """Text from the network, made harmless for the log and the admin page."""
    return re.sub(r"[^\w\-. :,/]", "?", str(value if value is not None else ""))[:limit]


def _click_seen(action, f, result, ip=None):
    entry = {"at": iso(now()), "action": action, "order": _safe(f.get("merchant_trans_id")),
             "clickTransId": _safe(f.get("click_trans_id"), 20), "amount": _safe(f.get("amount"), 20),
             "clickError": _safe(f.get("error"), 12) if action == "complete" else None,
             "error": result.get("error"), "note": result.get("error_note"), "ip": _safe(ip, 45) or None}
    CLICK_RECENT.appendleft(entry)
    log.info("Click %s: order=%s trans=%s amount=%s from=%s -> %s %s", action, entry["order"], entry["clickTransId"],
             entry["amount"], entry["ip"] or "?", entry["error"], entry["note"])


def click_status():
    """The Click settings the admin page shows. The secret key is never shown, only whether it is there and how long it is."""
    return {
        "configured": "click" in providers(),
        "serviceId": CLICK["service_id"], "merchantId": CLICK["merchant_id"], "merchantUserId": CLICK["merchant_user_id"],
        "secretKey": {"set": bool(CLICK["secret_key"]), "length": len(CLICK["secret_key"])},
        "recent": list(CLICK_RECENT),
    }


def click_check():
    """
    Does Click accept our keys? Asks its Merchant API about an order that does not exist: Click either answers about the
    order (so it accepted the merchant user and the secret key) or refuses the keys (HTTP 401 or 403).
    Returns {"ok": True | False | None, "message": ...}; None means the answer proves nothing.
    """
    if not (CLICK["service_id"] and CLICK["merchant_id"] and CLICK["secret_key"]):
        return {"ok": False, "message": "CLICK_SERVICE_ID, CLICK_MERCHANT_ID and CLICK_SECRET_KEY are not all set on the server."}
    api = click_merchant_api()
    if not api.configured:
        return {"ok": False, "message": "CLICK_MERCHANT_USER_ID is not set, so the keys cannot be checked against Click "
                                        "(and refunds have to be done in the Click cabinet)."}
    try:
        api.payment_by_merchant_trans_id("connection-check", _click_days(now())[0])
        return {"ok": True, "message": "Click accepted the keys."}
    except click_merchant.ClickMerchantError as e:
        if e.http in (401, 403):
            return {"ok": False, "message": f"Click refused the keys (HTTP {e.http}): CLICK_MERCHANT_USER_ID or CLICK_SECRET_KEY is wrong."}
        if e.code is not None:    # Click answered about the order: it had accepted the keys
            return {"ok": True, "message": f"Click accepted the keys. It answered: {e}"}
        if e.http is not None:
            return {"ok": None, "message": f"Click answered HTTP {e.http}, which does not say whether the keys are right."}
        return {"ok": False, "message": str(e)}

KIND_TITLES = {
    "plan": "Pass",
    "writing_check": "Writing check by an examiner",
    "speaking_check": "Speaking check by an examiner",
}


class BillingError(Exception):
    def __init__(self, message, status=400, code=None):
        super().__init__(message)
        self.status = status
        self.code = code


def providers():
    """Payment methods that are switched on, in the order they are offered."""
    out = []
    if PAYME["merchant_id"] and PAYME["key"]:
        out.append("payme")
    if CLICK["service_id"] and CLICK["merchant_id"] and CLICK["secret_key"]:
        out.append("click")
    if dodo.configured():
        out.append("dodo")
    return out


def plan_table():
    """The passes and their prices for the Price page: {kind: {months: {"uzs": so'm, "usd": US cents}}}."""
    return {kind: {str(m): {"uzs": uzs, "usd": usd} for m, (uzs, usd) in months.items()} for kind, months in PLAN_PRICES.items()}


def public_config(enabled=True):
    """What the Price page needs. The passes and their prices are shown even before anything is for sale."""
    return {
        "enabled": bool(enabled),
        "currency": CURRENCY,
        "plans": plan_table(),
        "prices": {k: v for k, v in PRICES.items() if k != "plan"} if accounts.checks_enabled() and enabled else {},
        "planDays": PLAN_DAYS,
        "firstBonusDays": PLAN_FIRST_BONUS_DAYS,
        "aiCaps": ai_caps(),
        "providers": providers() if enabled else [],
        # The passes that can be paid by card, as "full-1", "speaking-3", ...
        "cardPasses": sorted(f"{scope}-{months}" for (scope, months) in dodo.products()) if enabled and dodo.configured() else [],
    }


def ai_caps():
    """What a pass includes of AI marking in any 30 days, and what a free account gets (ai_usage.py)."""
    from . import ai_usage
    caps = ai_usage.caps()
    return {**caps["pass"], "free": caps["free"]}


def plan_title(scope, months):
    return f"{PASS_TITLES.get(scope, 'Pass')}, {months} month{'s' if months != 1 else ''}"


# --------------------------------------------------------------------------
# Orders
# --------------------------------------------------------------------------

def get_order(db, order_id):
    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return None
    rows = db.select("orders", {"id": order_id}, limit=1)
    return rows[0] if rows else None


def order_scope(order):
    return order.get("scope") or "full"


def order_months(order):
    return int(order.get("months") or 1)


def order_currency(order):
    return order.get("currency") or "UZS"


def public_order(order):
    plan = order["kind"] == "plan"
    return {
        "id": order["id"],
        "kind": order["kind"],
        "title": plan_title(order_scope(order), order_months(order)) if plan else KIND_TITLES.get(order["kind"], order["kind"]),
        "scope": order_scope(order) if plan else None,
        "months": order_months(order) if plan else None,
        "amount": order["amount"],
        "currency": "USD" if order_currency(order) == "USD" else CURRENCY,
        "status": order["status"],
        "provider": order.get("provider"),
        "examinerId": order.get("examiner_id"),
        "submissionId": order.get("submission_id"),
        "createdAt": order.get("created_at"),
        "paidAt": order.get("paid_at"),
    }


def user_orders(db, user_id, limit=50):
    """
    A user's orders, newest first, each with a receipt of what it unlocked: the plan period it
    added, or the examiner check it paid for. A refunded or unpaid order has no "unlocked".
    """
    rows = db.select("orders", {"user_id": user_id}, order=[("created_at", "desc")], limit=limit)
    periods = {p["order_id"]: p for p in db.select("subscription_periods", {"user_id": user_id}, limit=200)
               if p.get("order_id") is not None}
    paid_checks = {c["order_id"]: c for c in db.select("checks", {"student_id": user_id}, limit=200)}
    out = []
    for order in rows:
        item = public_order(order)
        if order["status"] == "paid":
            if order["kind"] == "plan" and order["id"] in periods:
                p = periods[order["id"]]
                item["unlocked"] = {"plan": {"startsAt": p["starts_at"], "endsAt": p["ends_at"], "scope": accounts.scope_of(p)}}
            elif order["id"] in paid_checks:
                c = paid_checks[order["id"]]
                item["unlocked"] = {"check": {"id": c["id"], "kind": c["kind"], "status": c["status"]}}
        out.append(item)
    return out


def create_order(db, user_id, kind, examiner_id=None, submission_id=None, scope="full", months=1, currency="UZS"):
    if kind not in PRICES:
        raise BillingError("Unknown product.")
    if kind != "plan" and not accounts.checks_enabled():
        raise BillingError("Examiner checks are not available yet.")
    pending = db.select("orders", {"user_id": user_id, "status": "pending"}, limit=15)
    if len(pending) >= 15:
        raise BillingError("You have too many unpaid orders. Please complete or wait for previous orders.")
    row = {"user_id": user_id, "kind": kind, "amount": PRICES[kind], "status": "pending"}
    if kind == "plan":
        try:
            months = int(months)
        except (TypeError, ValueError):
            raise BillingError("Unknown pass.")
        if scope not in PLAN_PRICES or months not in PLAN_PRICES[scope]:
            raise BillingError("Unknown pass.")
        # A pass that renews on its own (a card subscription) is not bought a second time: that would charge twice.
        for held in accounts.plan_status(db, user_id)["passes"]:
            if held["renews"] and held["scope"] in (scope, "full"):
                raise BillingError(
                    "Your All-in-one pass already opens every paper, and it renews on its own." if held["scope"] == "full" and scope != "full"
                    else "You already have this pass, and it renews on its own. Cancel the renewal in your account first if you want to change it.")
        uzs, usd = PLAN_PRICES[scope][months]
        if currency == "USD":
            if not dodo.product_id(scope, months) or not dodo.configured():
                raise BillingError("This pass cannot be paid by card yet.")
            row["amount"] = usd
        elif currency != "UZS":
            raise BillingError("Unknown currency.")
        else:
            row["amount"] = uzs
        # What is the usual (a full pass, 1 month, in so'm) needs no extra column, so an older database still works.
        for key, value, usual in (("scope", scope, "full"), ("months", months, 1), ("currency", currency, "UZS")):
            if value != usual:
                row[key] = value
    elif currency != "UZS":
        raise BillingError("Examiner checks are paid in so'm.")
    if kind in ("writing_check", "speaking_check"):
        check_kind = "writing" if kind == "writing_check" else "speaking"
        checks.validate_new_check(db, user_id, check_kind, examiner_id, submission_id)
        row.update({"examiner_id": examiner_id, "submission_id": int(submission_id)})
    return db.insert("orders", row)


def checkout(order, method, return_url, profile=None, cancel_url=None):
    """What the browser should do to pay: a redirect URL."""
    if order["status"] != "pending":
        raise BillingError("This order cannot be paid any more.")
    if method not in providers():
        raise BillingError("This payment method is not available.")
    if (method == "dodo") != (order_currency(order) == "USD"):
        raise BillingError("This payment method is not available for this order.")
    if method == "dodo":
        profile = profile or {}
        try:
            url = dodo.create_checkout(order["id"], order_scope(order), order_months(order), profile.get("email") or "",
                                       profile.get("name") or "", return_url, cancel_url)
        except dodo.DodoError as e:
            raise BillingError(str(e), e.status)
        return {"redirect": url}
    if method == "payme":
        params = [
            f"m={PAYME['merchant_id']}",
            f"ac.{PAYME['account_field']}={order['id']}",
            f"a={order['amount'] * 100}",
            f"c={return_url}",
            "l=uz",
        ]
        token = base64.b64encode(";".join(params).encode("utf-8")).decode("ascii")
        base = "https://checkout.test.paycom.uz/" if PAYME["test"] else "https://checkout.paycom.uz/"
        return {"redirect": base + token}
    if method == "click":
        # The payment page as Click documents it (docs.click.uz, "Платежная ссылка"): the amount as N.NN, and
        # transaction_param is the order number, which comes back as merchant_trans_id in Prepare and Complete.
        query = urllib.parse.urlencode({
            "service_id": CLICK["service_id"],
            "merchant_id": CLICK["merchant_id"],
            "amount": f"{float(order['amount']):.2f}",
            "transaction_param": order["id"],
            "return_url": return_url,
        })
        return {"redirect": f"https://my.click.uz/services/pay/?{query}"}
    raise BillingError("This payment method is not available.")


def fulfil_order(db, order_id, provider, external_id=None):
    """Give the customer what they paid for, then mark the order paid. Safe to repeat."""
    order = get_order(db, order_id)
    if not order:
        raise BillingError("Order not found.", 404)
    if order["status"] in ("cancelled", "refunded"):
        raise BillingError("This order was cancelled.")
    if order["kind"] == "plan":
        # The first full pass of one month comes with a free month; other passes are what they say.
        subscribed = (order.get("note") or "").startswith(accounts.SUBSCRIPTION_MARK)
        # The first full pass of one month comes with a free month; a subscription charges again each month, so no bonus.
        first = (not subscribed and order_scope(order) == "full" and order_months(order) == 1
                 and not accounts.plan_status(db, order["user_id"])["hadPaidPlan"])
        days = PLAN_DAYS * order_months(order) + (PLAN_FIRST_BONUS_DAYS if first else 0)
        accounts.grant_plan_period(db, order["user_id"], days, "payment", order_id=order["id"],
                                   note=order["note"] if subscribed else "first month + bonus" if first else None,
                                   scope=order_scope(order))
    else:
        check = checks.create_check(db, order)
    if order["status"] != "paid":
        fields = {"status": "paid", "paid_at": iso(now()), "provider": provider}
        if external_id:
            fields["external_id"] = str(external_id)
        updated = db.update("orders", {"id": order["id"], "status": ("in", ["pending", "awaiting_confirmation"])}, fields)
        order = updated[0] if updated else get_order(db, order["id"])
        if updated:  # tell people once, when the order changes to paid
            ends = None
            if order["kind"] == "plan":
                ends_at = parse_time(accounts.plan_status(db, order["user_id"])["endsAt"])
                ends = ends_at.strftime("%d %B %Y") if ends_at else None
            notify.order_paid(db, order, provider, ends)
            if order["kind"] != "plan":
                notify.check_assigned(db, check)
            analytics.record(db, "paid", user_id=order["user_id"], detail=order["kind"], order_id=order["id"])
    log.info("Order %s (%s, %s) paid via %s", order["id"], order["kind"], order["amount"], provider)
    return order


def can_refund(db, order):
    if order["kind"] == "plan":
        return True
    return checks.check_can_be_cancelled(db, order["id"])


def refund_order(db, order):
    """Undo a paid order (Payme/Click cancellation or an admin refund)."""
    if not can_refund(db, order):
        raise BillingError("The examiner has already started this check, so it cannot be refunded.")
    if order["kind"] == "plan":
        accounts.revoke_plan_period(db, order["id"])
    else:
        checks.cancel_check_for_order(db, order["id"])
    updated = db.update("orders", {"id": order["id"]}, {"status": "refunded", "cancelled_at": iso(now())})
    return updated[0] if updated else order


def refund_at_provider(order):
    """
    Ask the payment provider to give the money back: Dodo and Click are asked from here. Returns a note for the admin
    when the money has to be returned by hand (Payme, or Click without CLICK_MERCHANT_USER_ID), otherwise None.
    Raises BillingError (code "provider_refund_failed" for Click) when the provider refuses.
    """
    provider = order.get("provider")
    if provider == "dodo" and order.get("external_id"):
        try:
            dodo.refund(order["external_id"])
        except dodo.DodoError as e:
            raise BillingError(str(e), e.status)
        return None
    if provider == "click":
        return _refund_at_click(order)
    if provider == "payme":
        return "Return the money in the Payme Business cabinet: the pass has been taken back here, but Payme has not been asked."
    return None


def _click_days(paid_at):
    """The days Click may have dated a payment on: its own day (Uzbekistan, UTC+5, no daylight saving) and the UTC day."""
    paid = paid_at or now()
    local = paid.astimezone(datetime.timezone(datetime.timedelta(hours=5)))
    return list(dict.fromkeys([local.date(), paid.astimezone(datetime.timezone.utc).date()]))


def _click_payment_id(api, order):
    """Click's number for this order's payment: asked from Click by our order number, else the one saved at Complete."""
    last = None
    for day in _click_days(parse_time(order.get("paid_at"))):
        try:
            found = api.payment_by_merchant_trans_id(order["id"], day)
        except click_merchant.ClickMerchantError as e:
            last = e
            continue
        if found.get("payment_id"):
            return str(found["payment_id"])
    if order.get("external_id"):
        return str(order["external_id"])
    raise last or click_merchant.ClickMerchantError("Click has no record of this payment.", 404)


def _refund_at_click(order):
    api = click_merchant_api()
    if not api.configured:
        return ("Click was not asked to return the money, because CLICK_MERCHANT_USER_ID is not set on the server. "
                "Return it to the student in the Click cabinet (merchant.click.uz); the pass has been taken back here.")
    try:
        api.reverse(_click_payment_id(api, order))
    except click_merchant.ClickMerchantError as e:
        raise BillingError(
            f"{e} Click returns a payment only in the month it was made, and on the first day of the next month. If you "
            "have returned the money yourself in the Click cabinet, mark the order as refunded.",
            e.status, code="provider_refund_failed")
    return None


def cancel_unpaid_order(db, order):
    if order["status"] in ("pending", "awaiting_confirmation"):
        db.update("orders", {"id": order["id"], "status": ("in", ["pending", "awaiting_confirmation"])},
                  {"status": "cancelled", "cancelled_at": iso(now())})


# --------------------------------------------------------------------------
# Dodo webhook (see dodo.py)
# --------------------------------------------------------------------------

_subscription_lock = threading.Lock()


def _mark_cancelled(db, subscription_id):
    """The student stopped the renewals: the periods already paid for keep working, and are no longer 'renewing'."""
    mark = accounts.SUBSCRIPTION_MARK + subscription_id
    users = {p["user_id"] for p in db.select("subscription_periods", {"note": mark}, limit=200)}
    db.update("subscription_periods", {"note": mark}, {"note": mark + accounts.CANCELLED_SUFFIX})
    for user_id in users:
        accounts._plan_changed(user_id)   # the server forgets the plan it remembered


def _subscription_payment(db, payment, payment_id, subscription_id):
    """A charge of a subscription: the first one pays the order made at checkout, each renewal makes an order of its own."""
    mark = accounts.SUBSCRIPTION_MARK + subscription_id
    total = int(payment.get("total_amount") or 0)
    with _subscription_lock:
        if db.select("orders", {"external_id": str(payment_id)}, limit=1):
            return f"payment {payment_id}: already applied"
        known = db.select("orders", {"note": mark}, order=[("id", "asc")], limit=1)
        base = known[0] if known else None
        if base is None:
            order_id = (payment.get("metadata") or {}).get("order_id")
            if not order_id:  # a payment may not carry what the checkout was given: the subscription does
                try:
                    order_id = (dodo.get_subscription(subscription_id).get("metadata") or {}).get("order_id")
                except dodo.DodoError as e:
                    raise BillingError(str(e), 503)
            base = get_order(db, order_id)
            if not base or order_currency(base) != "USD" or base["kind"] != "plan":
                return f"payment {payment_id}: no order"
            if total < int(base["amount"]):
                log.warning("Dodo payment %s is %s, less than order %s (%s)", payment_id, total, base["id"], base["amount"])
                return f"payment {payment_id}: amount too small"
            db.update("orders", {"id": base["id"]}, {"note": mark})
            order = get_order(db, base["id"])
        elif base["status"] == "pending":   # the first payment's webhook was missed: this one pays that order
            order = base
        else:   # a renewal
            order = db.insert("orders", {"user_id": base["user_id"], "kind": "plan", "amount": total or base["amount"],
                                         "status": "pending", "scope": order_scope(base), "months": order_months(base),
                                         "currency": "USD", "note": mark})
        try:
            fulfil_order(db, order["id"], "dodo", external_id=payment_id)
        except BillingError as e:
            log.warning("Dodo payment %s for order %s not applied: %s", payment_id, order["id"], e)
            return f"payment {payment_id}: {e}"
    return f"order {order['id']} paid"


def handle_dodo_webhook(db, headers, body):
    """
    Check a webhook from Dodo and act on it. Returns a short note for the log. Raises BillingError(401) when the
    signature is wrong, so that Dodo does not think the call was taken; anything we cannot use is answered with a note
    (not an error), because Dodo would only send it again.
    """
    if not dodo.verify_signature(headers, body):
        raise BillingError("Bad signature.", 401)
    try:
        event = json.loads(body.decode("utf-8"))
    except ValueError:
        raise BillingError("Unreadable webhook.", 400)
    kind = str(event.get("type") or "")
    data = event.get("data") or {}
    payment_id = data.get("payment_id")
    if kind in ("subscription.cancelled", "subscription.expired") and data.get("subscription_id"):
        _mark_cancelled(db, str(data["subscription_id"]))
        return f"{kind} {data['subscription_id']}"
    if kind not in ("payment.succeeded", "refund.succeeded") or not payment_id:
        return f"ignored {kind or 'event'}"
    if kind == "payment.succeeded":
        # Never trust the webhook alone: ask Dodo for the payment, and use what Dodo says.
        try:
            payment = dodo.get_payment(payment_id)
        except dodo.DodoError as e:
            raise BillingError(str(e), 503)  # Dodo will send the webhook again
        if payment.get("status") != "succeeded":
            return f"payment {payment_id}: not paid"
        if str(payment.get("currency") or "").upper() != "USD":
            return f"payment {payment_id}: wrong currency"
        if payment.get("subscription_id"):
            return _subscription_payment(db, payment, payment_id, str(payment["subscription_id"]))
        order = get_order(db, (payment.get("metadata") or {}).get("order_id"))
        if not order:
            return f"payment {payment_id}: no order"
        if order_currency(order) != "USD":
            return f"payment {payment_id}: wrong currency"
        if int(payment.get("total_amount") or 0) < int(order["amount"]):
            log.warning("Dodo payment %s is %s, less than order %s (%s)", payment_id, payment.get("total_amount"),
                        order["id"], order["amount"])
            return f"payment {payment_id}: amount too small"
        try:
            fulfil_order(db, order["id"], "dodo", external_id=payment_id)
        except BillingError as e:
            log.warning("Dodo payment %s for order %s not applied: %s", payment_id, order["id"], e)
            return f"payment {payment_id}: {e}"
        return f"order {order['id']} paid"
    rows = db.select("orders", {"external_id": str(payment_id)}, limit=1)
    order = rows[0] if rows else None
    if not order or order["status"] != "paid":
        return f"refund {payment_id}: no paid order"
    if not can_refund(db, order):
        log.warning("Dodo refunded order %s but its examiner check had started", order["id"])
        return f"refund {payment_id}: check already started"
    refund_order(db, order)
    return f"order {order['id']} refunded"


def cancel_subscriptions(db, user_id, scope=None):
    """Stop the renewals of a student's pass (of one kind, or all). The days already paid for stay. Returns how many."""
    marks = set()
    for o in db.select("orders", {"user_id": user_id, "provider": "dodo"}, limit=200):
        note = o.get("note") or ""
        if note.startswith(accounts.SUBSCRIPTION_MARK) and (scope is None or order_scope(o) == scope):
            marks.add(note)
    live = {p.get("note") for p in db.select("subscription_periods", {"user_id": user_id}, limit=200) if accounts.renews(p)}
    done = 0
    for mark in sorted(marks & live):
        sid = mark[len(accounts.SUBSCRIPTION_MARK):]
        try:
            dodo.cancel_subscription(sid)
        except dodo.DodoError as e:
            raise BillingError(str(e), e.status)
        _mark_cancelled(db, sid)
        done += 1
    return done


# --------------------------------------------------------------------------
# Payme Merchant API (JSON-RPC). https://developer.help.paycom.uz
# --------------------------------------------------------------------------

PAYME_TIMEOUT_MS = 43_200_000  # an unperformed transaction expires after 12 hours

PAYME_ERRORS = {
    -32504: ("Insufficient privileges", "Недостаточно привилегий", "Imtiyozlar yetarli emas"),
    -32300: ("Only POST requests are accepted", "Метод запроса не POST", "So'rov usuli POST emas"),
    -32700: ("Could not parse the request", "Ошибка разбора JSON", "JSON so'rovini o'qib bo'lmadi"),
    -32600: ("Invalid JSON-RPC request", "Неверный запрос JSON-RPC", "JSON-RPC so'rovi noto'g'ri"),
    -32601: ("Method not found", "Метод не найден", "Usul topilmadi"),
    -31001: ("Incorrect amount", "Неверная сумма", "Noto'g'ri summa"),
    -31003: ("Transaction not found", "Транзакция не найдена", "Tranzaksiya topilmadi"),
    -31007: ("The order is completed and cannot be cancelled", "Заказ выполнен, отмена невозможна",
             "Buyurtma bajarilgan, bekor qilib bo'lmaydi"),
    -31008: ("This operation cannot be performed", "Невозможно выполнить операцию", "Amalni bajarib bo'lmaydi"),
    -31050: ("Order not found", "Заказ не найден", "Buyurtma topilmadi"),
    -31051: ("The order has already been paid or cancelled", "Заказ уже оплачен или отменён",
             "Buyurtma allaqachon to'langan yoki bekor qilingan"),
    -31052: ("Another payment for this order is in progress", "Заказ ожидает другой оплаты",
             "Bu buyurtma uchun boshqa to'lov kutilmoqda"),
}


class PaymeError(Exception):
    def __init__(self, code, data=None):
        super().__init__(code)
        self.code = code
        self.data = data


def _ms():
    return int(time.time() * 1000)


class PaymeApi:
    def __init__(self, db, key=None, account_field=None):
        self.db = db
        self.key = key if key is not None else PAYME["key"]
        self.field = account_field or PAYME["account_field"]

    # -- entry point ---------------------------------------------------------
    def handle(self, body, authorization):
        request_id = None
        try:
            if not self._authorized(authorization):
                raise PaymeError(-32504)
            try:
                payload = json.loads(body or b"{}")
            except ValueError:
                raise PaymeError(-32700)
            if not isinstance(payload, dict) or not isinstance(payload.get("params", {}), dict):
                raise PaymeError(-32600)
            request_id = payload.get("id")
            method = payload.get("method")
            handler = {
                "CheckPerformTransaction": self.check_perform,
                "CreateTransaction": self.create,
                "PerformTransaction": self.perform,
                "CancelTransaction": self.cancel,
                "CheckTransaction": self.check,
                "GetStatement": self.statement,
                "SetFiscalData": lambda p: {"success": True},
            }.get(method)
            if not handler:
                raise PaymeError(-32601, method)
            return {"jsonrpc": "2.0", "id": request_id, "result": handler(payload.get("params") or {})}
        except PaymeError as e:
            en, ru, uz = PAYME_ERRORS.get(e.code, ("Error", "Ошибка", "Xatolik"))
            error = {"code": e.code, "message": {"en": en, "ru": ru, "uz": uz}}
            if e.data is not None:
                error["data"] = e.data
            return {"jsonrpc": "2.0", "id": request_id, "error": error}
        except Exception:
            log.exception("Payme request failed")
            return {"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": -31008, "message": {"en": "Internal error", "ru": "Внутренняя ошибка",
                                                          "uz": "Ichki xatolik"}}}

    def _authorized(self, header):
        if not self.key or not header or not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:].strip()).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return False
        login, _, password = decoded.partition(":")
        return login == "Paycom" and hmac.compare_digest(password, self.key)

    # -- helpers ---------------------------------------------------------------
    def _order_for(self, params):
        account = params.get("account") or {}
        order = get_order(self.db, account.get(self.field))
        if not order:
            raise PaymeError(-31050, self.field)
        return order

    def _check_order(self, order, amount):
        if order["status"] != "pending":
            raise PaymeError(-31051, self.field)
        if not isinstance(amount, int) or amount != order["amount"] * 100:
            raise PaymeError(-31001)

    def _txn(self, txn_id):
        rows = self.db.select("payme_transactions", {"id": str(txn_id)}, limit=1) if txn_id else []
        if not rows:
            raise PaymeError(-31003)
        return rows[0]

    def _expire_if_old(self, txn):
        if txn["state"] == 1 and _ms() - txn["create_time"] > PAYME_TIMEOUT_MS:
            self.db.update("payme_transactions", {"id": txn["id"], "state": 1},
                           {"state": -1, "cancel_time": _ms(), "reason": 4})
            order = get_order(self.db, txn["order_id"])
            if order:
                cancel_unpaid_order(self.db, order)
            raise PaymeError(-31008)

    @staticmethod
    def _txn_result(txn):
        return {"transaction": str(txn["id"]), "state": txn["state"], "create_time": txn["create_time"],
                "perform_time": txn["perform_time"], "cancel_time": txn["cancel_time"]}

    # -- methods ---------------------------------------------------------------
    def check_perform(self, params):
        order = self._order_for(params)
        self._check_order(order, params.get("amount"))
        active = self.db.select("payme_transactions", {"order_id": order["id"], "state": 1}, limit=1)
        if active:
            raise PaymeError(-31052, self.field)
        result = {"allow": True}
        if PAYME["ikpu"] and PAYME["package_code"]:
            result["detail"] = {"receipt_type": 0, "items": [{
                "title": KIND_TITLES.get(order["kind"], "Service"), "price": order["amount"] * 100, "count": 1,
                "code": PAYME["ikpu"], "package_code": PAYME["package_code"], "vat_percent": 0,
            }]}
        return result

    def create(self, params):
        txn_id = str(params.get("id") or "")
        if not txn_id:
            raise PaymeError(-32600)
        existing = self.db.select("payme_transactions", {"id": txn_id}, limit=1)
        if existing:
            txn = existing[0]
            if txn["state"] != 1:
                raise PaymeError(-31008)
            self._expire_if_old(txn)
            return {"create_time": txn["create_time"], "transaction": str(txn["id"]), "state": 1}
        order = self._order_for(params)
        self._check_order(order, params.get("amount"))
        others = self.db.select("payme_transactions", {"order_id": order["id"], "state": 1}, limit=1)
        if others:
            raise PaymeError(-31052, self.field)
        txn = self.db.insert("payme_transactions", {
            "id": txn_id, "order_id": order["id"], "amount": params["amount"], "state": 1,
            "payme_time": int(params.get("time") or _ms()), "create_time": _ms(),
        }, ignore_conflict=True) or self._txn(txn_id)
        return {"create_time": txn["create_time"], "transaction": str(txn["id"]), "state": txn["state"]}

    def perform(self, params):
        txn = self._txn(params.get("id"))
        if txn["state"] == 2:
            return {"transaction": str(txn["id"]), "perform_time": txn["perform_time"], "state": 2}
        if txn["state"] != 1:
            raise PaymeError(-31008)
        self._expire_if_old(txn)
        try:
            fulfil_order(self.db, txn["order_id"], "payme")
        except BillingError:
            raise PaymeError(-31008)
        updated = self.db.update("payme_transactions", {"id": txn["id"], "state": 1}, {"state": 2, "perform_time": _ms()})
        txn = updated[0] if updated else self._txn(txn["id"])
        return {"transaction": str(txn["id"]), "perform_time": txn["perform_time"], "state": txn["state"]}

    def cancel(self, params):
        txn = self._txn(params.get("id"))
        reason = params.get("reason")
        if txn["state"] in (-1, -2):
            return {"transaction": str(txn["id"]), "cancel_time": txn["cancel_time"], "state": txn["state"]}
        order = get_order(self.db, txn["order_id"])
        if txn["state"] == 1:
            updated = self.db.update("payme_transactions", {"id": txn["id"], "state": 1},
                                     {"state": -1, "cancel_time": _ms(), "reason": reason})
            if order:
                cancel_unpaid_order(self.db, order)
        else:  # performed: this is a refund
            if order and order["status"] == "paid":
                try:
                    refund_order(self.db, order)
                except BillingError:
                    raise PaymeError(-31007)
            updated = self.db.update("payme_transactions", {"id": txn["id"], "state": 2},
                                     {"state": -2, "cancel_time": _ms(), "reason": reason})
        txn = updated[0] if updated else self._txn(txn["id"])
        return {"transaction": str(txn["id"]), "cancel_time": txn["cancel_time"], "state": txn["state"]}

    def check(self, params):
        txn = self._txn(params.get("id"))
        result = self._txn_result(txn)
        result["reason"] = txn.get("reason")
        return result

    def statement(self, params):
        start, end = params.get("from"), params.get("to")
        if not isinstance(start, int) or not isinstance(end, int):
            raise PaymeError(-32600)
        rows = self.db.select("payme_transactions", {"payme_time": ("gte", start)}, order=[("payme_time", "asc")],
                              limit=1000)
        return {"transactions": [{
            "id": t["id"], "time": t["payme_time"], "amount": t["amount"],
            "account": {self.field: str(t["order_id"])},
            "create_time": t["create_time"], "perform_time": t["perform_time"], "cancel_time": t["cancel_time"],
            "transaction": str(t["id"]), "state": t["state"], "reason": t.get("reason"),
        } for t in rows if t["payme_time"] <= end]}


# --------------------------------------------------------------------------
# Click SHOP API (Prepare / Complete). https://docs.click.uz
# --------------------------------------------------------------------------

CLICK_NOTES = {
    0: "Success", -1: "SIGN CHECK FAILED!", -2: "Incorrect parameter amount", -3: "Action not found",
    -4: "Already paid", -5: "Order does not exist", -6: "Transaction does not exist",
    -7: "Failed to update order", -8: "Error in request from click", -9: "Transaction cancelled",
}


class ClickApi:
    def __init__(self, db, service_id=None, secret_key=None):
        self.db = db
        self.service_id = str(service_id if service_id is not None else CLICK["service_id"])
        self.secret = secret_key if secret_key is not None else CLICK["secret_key"]

    def _sign_ok(self, f, with_prepare_id):
        parts = [f.get("click_trans_id", ""), f.get("service_id", ""), self.secret, f.get("merchant_trans_id", "")]
        if with_prepare_id:
            parts.append(f.get("merchant_prepare_id", ""))
        parts += [f.get("amount", ""), f.get("action", ""), f.get("sign_time", "")]
        expected = hashlib.md5("".join(str(p) for p in parts).encode("utf-8")).hexdigest()
        return bool(self.secret) and hmac.compare_digest(expected, str(f.get("sign_string", "")).lower())

    @staticmethod
    def _reply(f, error, **extra):
        out = {"click_trans_id": _to_int(f.get("click_trans_id")), "merchant_trans_id": f.get("merchant_trans_id", ""),
               "error": error, "error_note": CLICK_NOTES.get(error, "Error")}
        out.update(extra)
        return out

    def _order_problem(self, f, order):
        if not order:
            return -5
        if order["status"] == "paid":
            return -4
        if order["status"] in ("cancelled", "refunded"):
            return -9
        try:
            if abs(float(f.get("amount", "0")) - order["amount"]) > 0.009:
                return -2
        except ValueError:
            return -2
        return 0

    def prepare(self, f, ip=None):
        result = self._prepare(f)
        _click_seen("prepare", f, result, ip)
        return result

    def complete(self, f, ip=None):
        result = self._complete(f)
        _click_seen("complete", f, result, ip)
        return result

    def _prepare(self, f):
        try:
            if str(f.get("action")) != "0":
                return self._reply(f, -3)
            if not self._sign_ok(f, False) or str(f.get("service_id")) != self.service_id:
                return self._reply(f, -1)
            order = get_order(self.db, f.get("merchant_trans_id"))
            problem = self._order_problem(f, order)
            if problem:
                return self._reply(f, problem)
            click_id = _to_int(f.get("click_trans_id"))
            if click_id is None:
                return self._reply(f, -8)
            txn = self.db.insert("click_transactions", {
                "click_trans_id": click_id, "order_id": order["id"], "amount": float(f["amount"]), "status": "prepared",
            }, ignore_conflict="click_trans_id") or self.db.select("click_transactions", {"click_trans_id": click_id})[0]
            if txn["order_id"] != order["id"]:   # a Click number is used once, for one order
                return self._reply(f, -8)
            return self._reply(f, 0, merchant_prepare_id=txn["id"])
        except Exception:
            log.exception("Click prepare failed")
            return self._reply(f, -7)

    def _complete(self, f):
        try:
            if str(f.get("action")) != "1":
                return self._reply(f, -3)
            if not self._sign_ok(f, True) or str(f.get("service_id")) != self.service_id:
                return self._reply(f, -1)
            rows = self.db.select("click_transactions", {"id": _to_int(f.get("merchant_prepare_id")) or 0}, limit=1)
            txn = rows[0] if rows else None
            if not txn or txn["click_trans_id"] != _to_int(f.get("click_trans_id")):
                return self._reply(f, -6)
            order = get_order(self.db, txn["order_id"])
            if txn["status"] == "completed":
                return self._reply(f, -4, merchant_confirm_id=txn["id"])
            if txn["status"] == "cancelled":
                return self._reply(f, -9)
            if _to_int(f.get("error")) not in (0, None):
                self.db.update("click_transactions", {"id": txn["id"]}, {"status": "cancelled"})
                if order:
                    cancel_unpaid_order(self.db, order)
                return self._reply(f, -9)
            problem = self._order_problem(f, order)
            if problem:
                # Click has taken the money, and we cannot give the pass: the owner is told (this is logged as an error,
                # which goes to Telegram) and the money is returned from the Click cabinet.
                log.error("Click payment %s for order %s was taken but cannot be applied (%s: %s); return the money",
                          f.get("click_trans_id"), order["id"] if order else f.get("merchant_trans_id"), problem,
                          CLICK_NOTES.get(problem))
                return self._reply(f, problem)
            # Click's own number of the payment is what its Merchant API needs to return the money later.
            fulfil_order(self.db, order["id"], "click", external_id=f.get("click_paydoc_id") or f.get("click_trans_id"))
            self.db.update("click_transactions", {"id": txn["id"]}, {"status": "completed", "completed_at": iso(now())})
            return self._reply(f, 0, merchant_confirm_id=txn["id"])
        except BillingError as e:
            log.error("Click payment %s was taken but order %s could not be paid: %s; return the money",
                      f.get("click_trans_id"), f.get("merchant_trans_id"), e)
            return self._reply(f, -9)
        except Exception:
            log.exception("Click complete failed")
            return self._reply(f, -7)


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _revenue_of(rows):
    usd = [r for r in rows if order_currency(r) == "USD"]
    rows = [r for r in rows if order_currency(r) != "USD"]   # the so'm figures are so'm only; card sales are counted apart
    plan = sum(int(r["amount"]) for r in rows if r["kind"] == "plan")
    total = sum(int(r["amount"]) for r in rows)
    return {"total": total, "plan": plan, "checks": total - plan, "orders": len(rows),
            "usdCents": sum(int(r["amount"]) for r in usd), "usdOrders": len(usd)}


def revenue(db, days, at=None):
    """Money from orders paid in the last `days` days (refunded orders no longer count), by kind."""
    return revenues(db, (days,), at)[days]


def revenues(db, windows=(7, 30), at=None):
    """{days: revenue} for several windows from ONE query: the longest window's orders, split by date."""
    at = at or now()
    rows = db.select("orders", {"status": "paid", "paid_at": ("gte", iso(at - datetime.timedelta(days=max(windows))))}, limit=10000)
    out = {}
    for days in windows:
        since = iso(at - datetime.timedelta(days=days))
        out[days] = _revenue_of([r for r in rows if iso(parse_time(r["paid_at"])) >= since])
    return out
