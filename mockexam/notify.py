"""
Notifications by email (Resend) and Telegram. Both are optional: without
configuration nothing is sent and the site works exactly the same.

  RESEND_API_KEY, EMAIL_FROM      emails to students, examiners and admins
                                  (EMAIL_FROM like "MockExam <noreply@your-domain>";
                                  the domain must be verified in Resend)
  TELEGRAM_BOT_TOKEN,             instant messages to the site owner
  TELEGRAM_ADMIN_CHAT_ID
  ADMIN_EMAILS                    admins who get the admin emails

Events
  payment_claimed   a student says they paid by card transfer   -> admins
  order_paid        payment received (Payme, Click or confirmed) -> the student; admins for Payme/Click
  check_assigned    a paid check is in an examiner's queue       -> the examiner; admins
  check_completed   the examiner sent the marks                  -> the student

Messages are sent from a small background pool, so no request waits for
them, and a failed send is only logged.
"""

import concurrent.futures
import html
import json
import logging
import os
import urllib.error
import urllib.request

log = logging.getLogger("mockexam.notify")

KIND_LABELS = {"plan": "Monthly plan", "writing_check": "Writing check", "speaking_check": "Speaking check"}

_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="notify")
SYNC = False  # tests send immediately


def _env(name):
    return os.environ.get(name, "").strip()


def site_url():
    return _env("SITE_URL").rstrip("/") or "http://localhost:8080"


def site_name():
    return _env("SITE_NAME") or "MockExam"


def admin_emails():
    return [e.strip().lower() for e in _env("ADMIN_EMAILS").split(",") if e.strip()]


def email_enabled():
    return bool(_env("RESEND_API_KEY") and _env("EMAIL_FROM"))


def telegram_enabled():
    return bool(_env("TELEGRAM_BOT_TOKEN") and _env("TELEGRAM_ADMIN_CHAT_ID"))


def money(amount):
    return f"{int(amount or 0):,}".replace(",", " ") + " so'm"


# --------------------------------------------------------------------------
# Transports (replaced in tests)
# --------------------------------------------------------------------------

def _post_json(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


def send_email(to, subject, text, button=None):
    """button = (label, url) adds a link button to the HTML version."""
    if not email_enabled() or not to:
        return False
    body = "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in text.split("\n\n"))
    if button:
        body += (f'<p><a href="{html.escape(button[1])}" style="display:inline-block;background:#1d5fb4;color:#fff;'
                 f'padding:10px 18px;border-radius:6px;text-decoration:none;font-weight:600">{html.escape(button[0])}</a></p>')
    page = (f'<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.5;color:#0f172a;max-width:560px">'
            f'{body}<p style="color:#5b6475;font-size:13px">{html.escape(site_name())}</p></div>')
    plain = text + (f"\n\n{button[0]}: {button[1]}" if button else "")
    _post_json("https://api.resend.com/emails",
               {"from": _env("EMAIL_FROM"), "to": [to] if isinstance(to, str) else to, "subject": subject,
                "text": plain, "html": page},
               {"Authorization": f"Bearer {_env('RESEND_API_KEY')}"})
    return True


def send_telegram(text):
    if not telegram_enabled():
        return False
    _post_json(f"https://api.telegram.org/bot{_env('TELEGRAM_BOT_TOKEN')}/sendMessage",
               {"chat_id": _env("TELEGRAM_ADMIN_CHAT_ID"), "text": text, "disable_web_page_preview": True})
    return True


def _run(job, *args):
    def safe():
        try:
            job(*args)
        except urllib.error.HTTPError as e:
            log.warning("Notification failed (%s): %s", e.code, e.read()[:300])
        except Exception:
            log.exception("Notification failed")
    if SYNC:
        safe()
    else:
        _POOL.submit(safe)


def _email_of(db, user_id):
    rows = db.select("profiles", {"id": user_id}, limit=1) if user_id else []
    return rows[0]["email"] if rows else None


def _to_admins(subject, text, button=None):
    send_telegram(f"{subject}\n{text}" + (f"\n{button[1]}" if button else ""))
    for email in admin_emails():
        send_email(email, subject, text, button)


# --------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------

def payment_claimed(db, order):
    def job():
        who = _email_of(db, order["user_id"]) or "a student"
        _to_admins(f"Card transfer to confirm: #MX{order['id']}",
                   f"{who} says they paid {money(order['amount'])} for: {KIND_LABELS.get(order['kind'], order['kind'])}.\n\n"
                   f"Check your bank for a transfer with MX{order['id']} in the comment, then confirm it.",
                   ("Open payments", f"{site_url()}/#/admin?tab=payments"))
    _run(job)


def order_paid(db, order, provider, plan_ends=None):
    def job():
        email = _email_of(db, order["user_id"])
        label = KIND_LABELS.get(order["kind"], order["kind"])
        if order["kind"] == "plan":
            detail = f"Your monthly plan is active{f' until {plan_ends}' if plan_ends else ''}. Every test is now open to you."
            button = ("Start practising", f"{site_url()}/#/")
        else:
            detail = "Your examiner has your test in their queue. Most checks are finished within 48 hours; we will email you when the marks are ready."
            button = ("My account", f"{site_url()}/#/account")
        send_email(email, f"Payment received: {label}",
                   f"Thank you! We received {money(order['amount'])} for order #MX{order['id']} ({label}).\n\n{detail}", button)
        if provider in ("payme", "click"):
            _to_admins(f"New payment: {money(order['amount'])} via {provider.title()}",
                       f"#MX{order['id']} · {label} · {email or order['user_id']}")
    _run(job)


def check_assigned(db, check):
    def job():
        skill = "Speaking" if check["kind"] == "speaking" else "Writing"
        link = f"{site_url()}/#/check/{check['id']}"
        send_email(_email_of(db, check["examiner_id"]), f"New {skill} check #{check['id']} for you",
                   f"A student has chosen you to mark their {skill} test. Please mark it within 48 hours.", ("Open the check", link))
        _to_admins(f"New {skill} check #{check['id']}", f"Assigned to {_email_of(db, check['examiner_id']) or check['examiner_id']}.")
    _run(job)


def check_completed(db, check):
    def job():
        skill = "Speaking" if check["kind"] == "speaking" else "Writing"
        band = check.get("overall_band")
        send_email(_email_of(db, check["student_id"]), f"Your {skill} check is ready",
                   f"Your examiner has marked your {skill} test"
                   + (f": band {float(band):.1f}" if band is not None else "") + ".\n\n"
                   "See the feedback on each criterion, and rate your examiner once you have read it.",
                   ("See your result", f"{site_url()}/#/check/{check['id']}"))
    _run(job)
