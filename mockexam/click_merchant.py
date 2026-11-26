"""
CLICK Merchant API (https://docs.click.uz/merchant-api): what the SITE asks of Click, as opposed to the Shop API
callbacks Click makes to the site (billing.ClickApi). It is used to give a student's money back (a payment reversal)
and to look a payment up. No SDK: plain HTTPS with the standard library.

  CLICK_SERVICE_ID, CLICK_SECRET_KEY   the same as for the Shop API
  CLICK_MERCHANT_USER_ID               the "merchant_user_id" Click gives with the keys

Every request carries   Auth: merchant_user_id:digest:timestamp   where timestamp is the current Unix time in seconds
and digest = sha1(timestamp + secret_key). Click answers HTTP 200 with {"error_code": 0, "error_note": "Success", ...};
a request that cannot be done (payment not found, reversal not allowed) comes back with another error_code.

Click's rules for a reversal: the payment must be completed and made by online card; it can be reversed only in the
reporting month it was made in (a payment of last month only on the first day of this month); UZCARD may refuse.
"""

import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("mockexam.click")

BASE_URL = "https://api.click.uz/v2/merchant"
TIMEOUT = 20


class ClickMerchantError(Exception):
    def __init__(self, message, status=502, code=None, http=None):
        super().__init__(message)
        self.status = status
        self.code = code        # Click's own error_code, when it sent one
        self.http = http        # the HTTP status Click answered with, when it answered at all


class MerchantApi:
    def __init__(self, service_id, merchant_user_id, secret_key, base_url=BASE_URL):
        self.service_id = str(service_id or "").strip()
        self.merchant_user_id = str(merchant_user_id or "").strip()
        self.secret = str(secret_key or "").strip()
        self.base_url = base_url.rstrip("/")

    @property
    def configured(self):
        return bool(self.service_id and self.merchant_user_id and self.secret)

    def auth_header(self, at=None):
        stamp = str(int(at if at is not None else time.time()))
        digest = hashlib.sha1((stamp + self.secret).encode("utf-8")).hexdigest()
        return f"{self.merchant_user_id}:{digest}:{stamp}"

    def _request(self, method, path):
        if not self.configured:
            raise ClickMerchantError("Click is not set up for refunds (CLICK_MERCHANT_USER_ID is missing).", 400)
        req = urllib.request.Request(self.base_url + path, method=method, headers={
            "Accept": "application/json", "Content-Type": "application/json", "Auth": self.auth_header(),
            "User-Agent": "TestDay/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            detail = e.read()[:300].decode("utf-8", "replace")
            log.warning("Click %s %s answered %s: %s", method, path, e.code, detail)
            raise ClickMerchantError(f"Click did not accept the request (HTTP {e.code}).", 502, http=e.code) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            log.warning("Click %s failed: %s", method, e)
            raise ClickMerchantError("Click is not answering. Please try again in a minute.", 503) from e
        try:
            data = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError as e:
            raise ClickMerchantError("Click sent an answer we could not read.", 502) from e
        if not isinstance(data, dict):
            raise ClickMerchantError("Click sent an answer we could not read.", 502)
        code = data.get("error_code")
        if code not in (0, None):
            note = str(data.get("error_note") or "").strip() or "no reason given"
            raise ClickMerchantError(f"Click said: {note} (code {code}).", 502, code)
        return data

    @staticmethod
    def _part(value):
        return urllib.parse.quote(str(value), safe="")

    def payment_by_merchant_trans_id(self, merchant_trans_id, day):
        """Click's record of the payment made for our order number on `day` (a date): {"payment_id": ..., ...}."""
        return self._request("GET", f"/payment/status_by_mti/{self._part(self.service_id)}/"
                                    f"{self._part(merchant_trans_id)}/{day.isoformat()}")

    def payment_status(self, payment_id):
        return self._request("GET", f"/payment/status/{self._part(self.service_id)}/{self._part(payment_id)}")

    def reverse(self, payment_id):
        """Give the whole payment back to the student's card."""
        return self._request("DELETE", f"/payment/reversal/{self._part(self.service_id)}/{self._part(payment_id)}")
