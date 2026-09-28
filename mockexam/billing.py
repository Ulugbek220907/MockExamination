"""
Billing: prices, orders, fulfilment, and the Payme and Click merchant APIs.

What can be bought
  plan            – the monthly plan (all tests). The first paid month comes
                    with an extra free month.
  writing_check   – an examiner marks one Writing submission.
  speaking_check  – an examiner marks one Speaking submission.

How money arrives
  Payme  – Payme calls POST /api/pay/payme (JSON-RPC, Merchant API).
  Click  – Click calls POST /api/pay/click/prepare and /complete (SHOP API).
  Manual – the student transfers to a card and presses "I have paid";
           an admin confirms the payment in the admin panel.

Fulfilment is idempotent: the plan period and the examiner check are keyed
by the order id, so a repeated callback never gives anything twice.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse

from . import accounts, checks
from .db import iso, now

log = logging.getLogger("mockexam.billing")


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


PRICES = {
    "plan": _int_env("PLAN_PRICE", 39000),
    "writing_check": _int_env("WRITING_CHECK_PRICE", 10000),
    "speaking_check": _int_env("SPEAKING_CHECK_PRICE", 20000),
}
PLAN_DAYS = _int_env("PLAN_DAYS", 30)
PLAN_FIRST_BONUS_DAYS = _int_env("PLAN_FIRST_BONUS_DAYS", 30)
CURRENCY = "so'm"

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
}
MANUAL = {
    "card_number": os.environ.get("PAYMENT_CARD_NUMBER", "").strip(),
    "card_holder": os.environ.get("PAYMENT_CARD_HOLDER", "").strip(),
}

KIND_TITLES = {
    "plan": "Monthly plan",
    "writing_check": "Writing check by an examiner",
    "speaking_check": "Speaking check by an examiner",
}


class BillingError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def providers():
    """Payment methods that are switched on, in the order they are offered."""
    out = []
    if PAYME["merchant_id"] and PAYME["key"]:
        out.append("payme")
    if CLICK["service_id"] and CLICK["merchant_id"] and CLICK["secret_key"]:
        out.append("click")
    if MANUAL["card_number"]:
        out.append("manual")
    return out


def public_config():
    return {
        "currency": CURRENCY,
        "prices": PRICES,
        "planDays": PLAN_DAYS,
        "firstBonusDays": PLAN_FIRST_BONUS_DAYS,
        "providers": providers(),
        "manual": {"cardNumber": MANUAL["card_number"], "cardHolder": MANUAL["card_holder"]} if MANUAL["card_number"] else None,
    }


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


def public_order(order):
    return {
        "id": order["id"],
        "kind": order["kind"],
        "title": KIND_TITLES.get(order["kind"], order["kind"]),
        "amount": order["amount"],
        "currency": CURRENCY,
        "status": order["status"],
        "provider": order.get("provider"),
        "examinerId": order.get("examiner_id"),
        "submissionId": order.get("submission_id"),
        "createdAt": order.get("created_at"),
        "paidAt": order.get("paid_at"),
    }


def create_order(db, user_id, kind, examiner_id=None, submission_id=None):
    if kind not in PRICES:
        raise BillingError("Unknown product.")
    row = {"user_id": user_id, "kind": kind, "amount": PRICES[kind], "status": "pending"}
    if kind in ("writing_check", "speaking_check"):
        check_kind = "writing" if kind == "writing_check" else "speaking"
        checks.validate_new_check(db, user_id, check_kind, examiner_id, submission_id)
        row.update({"examiner_id": examiner_id, "submission_id": int(submission_id)})
    return db.insert("orders", row)


def checkout(order, method, return_url):
    """What the browser should do to pay: a redirect URL, or manual transfer details."""
    if order["status"] != "pending":
        raise BillingError("This order cannot be paid any more.")
    if method not in providers():
        raise BillingError("This payment method is not available.")
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
        query = urllib.parse.urlencode({
            "service_id": CLICK["service_id"],
            "merchant_id": CLICK["merchant_id"],
            "amount": order["amount"],
            "transaction_param": order["id"],
            "return_url": return_url,
        })
        return {"redirect": f"https://my.click.uz/services/pay?{query}"}
    return {"manual": {
        "cardNumber": MANUAL["card_number"],
        "cardHolder": MANUAL["card_holder"],
        "amount": order["amount"],
        "reference": f"MX{order['id']}",
    }}


def mark_manual_paid(db, order, user_id):
    """The student says they transferred the money; an admin must confirm it."""
    if order["user_id"] != user_id:
        raise BillingError("Order not found.", 404)
    if order["status"] == "awaiting_confirmation":
        return order
    updated = db.update("orders", {"id": order["id"], "status": "pending"},
                        {"status": "awaiting_confirmation", "provider": "manual"})
    if not updated:
        raise BillingError("This order cannot be paid any more.")
    return updated[0]


def fulfil_order(db, order_id, provider):
    """Give the customer what they paid for, then mark the order paid. Safe to repeat."""
    order = get_order(db, order_id)
    if not order:
        raise BillingError("Order not found.", 404)
    if order["status"] in ("cancelled", "refunded"):
        raise BillingError("This order was cancelled.")
    if order["kind"] == "plan":
        first = not accounts.plan_status(db, order["user_id"])["hadPaidPlan"]
        days = PLAN_DAYS + (PLAN_FIRST_BONUS_DAYS if first else 0)
        accounts.grant_plan_period(db, order["user_id"], days, "payment", order_id=order["id"],
                                   note="first month + bonus" if first else None)
    else:
        checks.create_check(db, order)
    if order["status"] != "paid":
        updated = db.update("orders", {"id": order["id"], "status": ("in", ["pending", "awaiting_confirmation"])},
                            {"status": "paid", "paid_at": iso(now()), "provider": provider})
        order = updated[0] if updated else get_order(db, order["id"])
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


def cancel_unpaid_order(db, order):
    if order["status"] in ("pending", "awaiting_confirmation"):
        db.update("orders", {"id": order["id"], "status": ("in", ["pending", "awaiting_confirmation"])},
                  {"status": "cancelled", "cancelled_at": iso(now())})


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

    def prepare(self, f):
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
            return self._reply(f, 0, merchant_prepare_id=txn["id"])
        except Exception:
            log.exception("Click prepare failed")
            return self._reply(f, -7)

    def complete(self, f):
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
                return self._reply(f, problem)
            fulfil_order(self.db, order["id"], "click")
            self.db.update("click_transactions", {"id": txn["id"]}, {"status": "completed", "completed_at": iso(now())})
            return self._reply(f, 0, merchant_confirm_id=txn["id"])
        except BillingError:
            return self._reply(f, -9)
        except Exception:
            log.exception("Click complete failed")
            return self._reply(f, -7)


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
