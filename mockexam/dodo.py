"""
Dodo Payments (https://dodopayments.com): a merchant of record that takes foreign cards, Apple Pay and Google Pay
in US dollars and pays the seller out. No SDK: plain HTTPS with the standard library.

  DODO_PAYMENTS_API_KEY      the API key; "dodo_test_..." talks to the test servers, "dodo_live_..." to the live ones
  DODO_PAYMENTS_WEBHOOK_KEY  the webhook signing secret ("whsec_...")
  DODO_PRODUCTS              the product of each pass: "full-1=pdt_x, full-3=pdt_y, speaking-1=pdt_z, ..."
                             (kind of pass, a dash, the number of months). Each is a SUBSCRIPTION product in Dodo that
                             charges every 1 or 3 months until the student cancels.

Flow: the server makes a checkout session for an order (the order id travels in the metadata), the student pays on
Dodo's page, and Dodo calls POST /api/pay/dodo/webhook, for the first payment and again for every renewal. The webhook is verified (Standard Webhooks: HMAC-SHA256 over
"<id>.<timestamp>.<body>"), the payment is fetched from Dodo again, and only then is the order paid
(billing.handle_dodo_webhook).
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.error
import urllib.request

log = logging.getLogger("mockexam.dodo")

TEST_URL = "https://test.dodopayments.com"
LIVE_URL = "https://live.dodopayments.com"
TIMEOUT = 20
TOLERANCE_SECONDS = 300


class DodoError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _env(name):
    return os.environ.get(name, "").strip()


def api_key():
    return _env("DODO_PAYMENTS_API_KEY")


def webhook_key():
    return _env("DODO_PAYMENTS_WEBHOOK_KEY")


def products():
    """{(scope, months): product id} from DODO_PRODUCTS."""
    out = {}
    for item in _env("DODO_PRODUCTS").replace("\n", ",").replace(";", ",").split(","):
        name, _, pid = item.strip().partition("=")
        scope, _, months = name.strip().lower().rpartition("-")
        if scope and months.isdigit() and pid.strip():
            out[(scope, int(months))] = pid.strip()
    return out


def configured():
    return bool(api_key() and webhook_key() and products())


def product_id(scope, months):
    return products().get((scope, int(months)))


def base_url():
    return TEST_URL if api_key().startswith("dodo_test_") else LIVE_URL


def is_test_mode():
    return api_key().startswith("dodo_test_")


# --------------------------------------------------------------------------
# API calls
# --------------------------------------------------------------------------

def _request(method, path, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(base_url() + path, data=data, method=method, headers={
        "Authorization": f"Bearer {api_key()}", "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "TestDay/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read()[:300].decode("utf-8", "replace")
        log.warning("Dodo %s %s answered %s: %s", method, path, e.code, detail)
        raise DodoError("The card payment service did not accept this request. Please try again later.", 502) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log.warning("Dodo %s %s failed: %s", method, path, e)
        raise DodoError("The card payment service is not answering. Please try again in a minute.", 503) from e
    try:
        return json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError as e:
        raise DodoError("The card payment service sent an answer we could not read.", 502) from e


def create_checkout(order_id, scope, months, email, name, return_url):
    """A checkout session for one pass; returns the address of Dodo's payment page."""
    pid = product_id(scope, months)
    if not pid:
        raise DodoError("This pass cannot be paid by card yet.", 400)
    body = {
        "product_cart": [{"product_id": pid, "quantity": 1}],
        "customer": {"email": email, "name": name or email.split("@")[0]},
        "return_url": return_url,
        "metadata": {"order_id": str(order_id)},
        "allowed_payment_method_types": ["credit", "debit", "apple_pay", "google_pay"],
    }
    res = _request("POST", "/checkouts", body)
    if not res.get("checkout_url"):
        raise DodoError("The card payment service did not give a payment page.", 502)
    return res["checkout_url"]


def get_payment(payment_id):
    return _request("GET", f"/payments/{urllib.request.quote(str(payment_id), safe='')}")


def get_subscription(subscription_id):
    return _request("GET", f"/subscriptions/{urllib.request.quote(str(subscription_id), safe='')}")


def cancel_subscription(subscription_id):
    """Stop renewing at the end of the period already paid for (the student keeps the pass until then)."""
    return _request("PATCH", f"/subscriptions/{urllib.request.quote(str(subscription_id), safe='')}",
                    {"cancel_at_next_billing_date": True, "cancel_reason": "cancelled_by_customer"})


def refund(payment_id, reason="Refund requested on TestDay"):
    return _request("POST", "/refunds", {"payment_id": payment_id, "reason": reason[:300]})


# --------------------------------------------------------------------------
# Webhook signature (Standard Webhooks)
# --------------------------------------------------------------------------

def _secret_bytes(secret):
    if secret.startswith("whsec_"):
        try:
            return base64.b64decode(secret[len("whsec_"):])
        except ValueError:
            return b""
    return secret.encode("utf-8")


def sign(secret, msg_id, timestamp, body):
    """The v1 signature Dodo sends, for tests and for checking."""
    mac = hmac.new(_secret_bytes(secret), f"{msg_id}.{timestamp}.".encode("utf-8") + body, hashlib.sha256)
    return "v1," + base64.b64encode(mac.digest()).decode("ascii")


def verify_signature(headers, body, secret=None, at=None):
    """True if the webhook came from Dodo: right signature, and a timestamp within five minutes."""
    secret = secret if secret is not None else webhook_key()
    msg_id = headers.get("webhook-id", "")
    stamp = headers.get("webhook-timestamp", "")
    given = headers.get("webhook-signature", "")
    if not (secret and msg_id and stamp and given):
        return False
    try:
        if abs((at if at is not None else time.time()) - int(stamp)) > TOLERANCE_SECONDS:
            return False
    except ValueError:
        return False
    expected = sign(secret, msg_id, stamp, body)
    return any(hmac.compare_digest(expected, part) for part in given.split())
