"""
TestDay's two Telegram bots, run by the website itself (webhooks; no extra service). docs/TELEGRAM.md has the setup.

  @testdayuzbot (TELEGRAM_STUDENT_BOT_TOKEN)
    /start                the menu: band calculator, my results, connect my TestDay account, open the site
    /start <link code>    connects the Telegram account to a TestDay account (the code comes from the site's Account page)
    the band calculator   a widget that works entirely inside Telegram
    my results            a widget with the latest bands; it asks the bot for fresh numbers when it comes on screen
    messages it sends     a Speaking result ready, a pass ending soon, the exam in 7 days and tomorrow

  @testdaysupportbot (TELEGRAM_SUPPORT_BOT_TOKEN)
    a student writes      the message goes to the owner's chat (TELEGRAM_ADMIN_CHAT_ID), with a line naming the sender
    the owner replies     to that line (or to the copied message), and the reply goes back to the student

Telegram calls /api/telegram/hook/student and /api/telegram/hook/support with a secret header (TELEGRAM_WEBHOOK_SECRET,
or one derived from the server's own secret), so nobody else can feed the bots fake updates. Every update is answered
quickly; anything a user sends is treated as untrusted text.
"""

import base64
import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request

from . import guard, telegram_widgets
from .db import now

log = logging.getLogger("mockexam.telegram")

SITE = telegram_widgets.SITE
LINK_DAYS = 2   # a link code from the site works this long


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def token(bot):
    return _env("TELEGRAM_STUDENT_BOT_TOKEN" if bot == "student" else "TELEGRAM_SUPPORT_BOT_TOKEN")


def student_username():
    return _env("TELEGRAM_STUDENT_BOT_USERNAME", "testdayuzbot").lstrip("@")


def configured(bot="student"):
    return bool(token(bot))


def owner_chat():
    value = _env("TELEGRAM_ADMIN_CHAT_ID")
    return int(value) if re.fullmatch(r"-?\d+", value) else None


_secret = None


def set_server_secret(secret):
    """The server's own secret, from which the webhook secret and link codes are derived when not set separately."""
    global _secret
    _secret = secret


def webhook_secret():
    explicit = _env("TELEGRAM_WEBHOOK_SECRET")
    if explicit:
        return explicit
    base = _secret or _env("SESSION_SECRET") or "testday-dev"
    return hmac.new(base.encode(), b"telegram-webhook", hashlib.sha256).hexdigest()[:48]


def secret_ok(header):
    return bool(header) and hmac.compare_digest(str(header), webhook_secret())


# --------------------------------------------------------------------------
# The Bot API
# --------------------------------------------------------------------------

class TelegramError(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def call(bot, method, payload=None, timeout=10):
    """One Bot API call; returns its result or raises TelegramError. The token never appears in logs."""
    tok = token(bot)
    if not tok:
        raise TelegramError(f"the {bot} bot has no token")
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}", method="POST",
                                 data=json.dumps(payload or {}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read() or b"{}")
        except ValueError:
            data = {}
        raise TelegramError(f"{method}: {data.get('description') or e.code}", e.code) from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise TelegramError(f"{method}: {e}") from None
    if not data.get("ok"):
        raise TelegramError(f"{method}: {data.get('description')}", data.get("error_code"))
    return data.get("result")


def quietly(bot, method, payload):
    try:
        return call(bot, method, payload)
    except TelegramError as e:
        log.warning("Telegram %s bot: %s", bot, e)
        return None


# --------------------------------------------------------------------------
# Setting the bots up (at start and from Admin)
# --------------------------------------------------------------------------

COMMANDS = {
    "uz": [("start", "Menyu"), ("calc", "IELTS ball kalkulyatori"), ("results", "Natijalarim")],
    "ru": [("start", "Меню"), ("calc", "Калькулятор баллов IELTS"), ("results", "Мои результаты")],
    "en": [("start", "Menu"), ("calc", "IELTS band calculator"), ("results", "My results")],
}


def setup(site_url):
    """Point both bots at this server and set the student bot's commands. Returns {bot: "ok" | an error}."""
    out = {}
    if not site_url.startswith("https://"):
        return {"student": "skipped: the site has no https address", "support": "skipped"}
    for bot in ("student", "support"):
        if not configured(bot):
            out[bot] = "no token"
            continue
        try:
            call(bot, "setWebhook", {"url": f"{site_url}/api/telegram/hook/{bot}", "secret_token": webhook_secret(),
                                     "allowed_updates": ["message", "callback_query", "widget_query"],
                                     "drop_pending_updates": False, "max_connections": 10})
            if bot == "student":
                for lang, cmds in COMMANDS.items():
                    payload = {"commands": [{"command": c, "description": d} for c, d in cmds]}
                    if lang != "uz":
                        payload["language_code"] = lang
                    call(bot, "setMyCommands", payload)
            else:
                call(bot, "setMyCommands", {"commands": [{"command": "start", "description": "Savol yozish / Написать / Ask"}]})
            out[bot] = "ok"
        except TelegramError as e:
            out[bot] = str(e)
    log.info("Telegram bots set up: %s", out)
    return out


# --------------------------------------------------------------------------
# Linking a Telegram account to a TestDay account
# --------------------------------------------------------------------------

def _b64(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def link_code(user_id, at=None):
    """A code for t.me/<bot>?start=<code> (at most 64 characters of A-Z a-z 0-9 _ -), valid LINK_DAYS days."""
    raw_id = bytes.fromhex(str(user_id).replace("-", ""))
    expires = int((at or time.time()) + LINK_DAYS * 86400).to_bytes(5, "big")
    body = raw_id + expires
    sig = hmac.new(webhook_secret().encode(), b"link:" + body, hashlib.sha256).digest()[:12]
    return _b64(body + sig)


def user_from_code(code, at=None):
    """The TestDay user id in a valid, unexpired link code, else None."""
    try:
        raw = _unb64(code)
    except (ValueError, TypeError):
        return None
    if len(raw) != 16 + 5 + 12:
        return None
    body, sig = raw[:21], raw[21:]
    if not hmac.compare_digest(sig, hmac.new(webhook_secret().encode(), b"link:" + body, hashlib.sha256).digest()[:12]):
        return None
    if int.from_bytes(body[16:], "big") < (at or time.time()):
        return None
    h = body[:16].hex()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def link_url(user_id):
    return f"https://t.me/{student_username()}?start={link_code(user_id)}"


def profile_for_chat(db, chat_id):
    rows = db.select("profiles", {"telegram_id": int(chat_id)}, limit=1)
    return rows[0] if rows else None


def connect(db, user_id, chat_id):
    """Link the Telegram user to the TestDay account (one Telegram account to one TestDay account)."""
    for other in db.select("profiles", {"telegram_id": int(chat_id)}, limit=5):
        if other["id"] != user_id:
            db.update("profiles", {"id": other["id"]}, {"telegram_id": None})
    rows = db.update("profiles", {"id": user_id}, {"telegram_id": int(chat_id)})
    return rows[0] if rows else None


def disconnect(db, user_id):
    db.update("profiles", {"id": user_id}, {"telegram_id": None})


# --------------------------------------------------------------------------
# Words
# --------------------------------------------------------------------------

WORDS = {
    "uz": {
        "hello": "Assalomu alaykum! Bu TestDay boti: IELTS Listening, Reading, Writing va Speaking mashqlari.\n\n"
                 "Bu yerda ball kalkulyatori va natijalaringiz bor. Natija tayyor bo'lganda va imtihon yaqinlashganda xabar beraman.",
        "linked": "Telegram TestDay hisobingizga ulandi ✅ Endi natijalaringiz shu yerda.",
        "bad_link": "Bu havola eskirgan yoki noto'g'ri. Saytdagi Hisob sahifasida \"Telegramni ulash\"ni qayta bosing.",
        "not_linked": "Natijalarni ko'rish uchun TestDay hisobingizni ulang: saytdagi Hisob sahifasida \"Telegramni ulash\" tugmasini bosing.",
        "calc": "📊 Ball kalkulyatori", "results": "📈 Natijalarim", "connect": "🔗 Hisobni ulash", "site": "🌐 Saytni ochish",
        "unlinked": "Telegram hisobingizdan uzildi. Qayta ulash uchun saytdagi Hisob sahifasidan foydalaning.",
        "speaking_ready": "🎙 Speaking natijangiz tayyor: taxminiy ball {band}.", "open_result": "Natijani ochish",
        "pass_ending": "⏳ Passingiz {date} kuni tugaydi. Mashqni to'xtatmaslik uchun uzaytiring.", "renew": "Uzaytirish",
        "exam_7": "📅 IELTS imtihoningizga 7 kun qoldi. Bugun bitta to'liq test ishlab ko'ring!",
        "exam_1": "📅 Imtihon ertaga! Yaxshi dam oling. Omad! 🍀", "practice": "Mashq qilish",
        "slow": "Biroz sekinroq, iltimos 🙂",
    },
    "ru": {
        "hello": "Здравствуйте! Это бот TestDay: тренировка IELTS Listening, Reading, Writing и Speaking.\n\n"
                 "Здесь калькулятор баллов и ваши результаты. Я напишу, когда будет готов результат и когда приблизится экзамен.",
        "linked": "Telegram подключён к вашему аккаунту TestDay ✅ Теперь результаты здесь.",
        "bad_link": "Ссылка устарела или неверна. Нажмите «Подключить Telegram» на странице аккаунта на сайте ещё раз.",
        "not_linked": "Чтобы видеть результаты, подключите аккаунт TestDay: на сайте, на странице аккаунта, нажмите «Подключить Telegram».",
        "calc": "📊 Калькулятор баллов", "results": "📈 Мои результаты", "connect": "🔗 Подключить аккаунт", "site": "🌐 Открыть сайт",
        "unlinked": "Telegram отключён от аккаунта. Подключить снова можно на странице аккаунта на сайте.",
        "speaking_ready": "🎙 Результат Speaking готов: примерно {band}.", "open_result": "Открыть результат",
        "pass_ending": "⏳ Ваш пропуск заканчивается {date}. Продлите, чтобы не прерывать занятия.", "renew": "Продлить",
        "exam_7": "📅 До экзамена IELTS 7 дней. Пройдите сегодня один полный тест!",
        "exam_1": "📅 Экзамен завтра! Хорошо отдохните. Удачи! 🍀", "practice": "Тренироваться",
        "slow": "Чуть помедленнее, пожалуйста 🙂",
    },
    "en": {
        "hello": "Hello! This is the TestDay bot: IELTS Listening, Reading, Writing and Speaking practice.\n\n"
                 "Here you have the band calculator and your results. I will message you when a result is ready and when your exam is near.",
        "linked": "Telegram is now connected to your TestDay account ✅ Your results are here.",
        "bad_link": "This link has expired or is not right. Press \"Connect Telegram\" on the site's Account page again.",
        "not_linked": "To see your results, connect your TestDay account: on the site's Account page, press \"Connect Telegram\".",
        "calc": "📊 Band calculator", "results": "📈 My results", "connect": "🔗 Connect my account", "site": "🌐 Open the site",
        "unlinked": "Telegram is disconnected from your account. You can connect it again on the site's Account page.",
        "speaking_ready": "🎙 Your Speaking result is ready: about band {band}.", "open_result": "Open the result",
        "pass_ending": "⏳ Your pass ends on {date}. Renew it to keep practising.", "renew": "Renew",
        "exam_7": "📅 Your IELTS exam is in 7 days. Take one full test today!",
        "exam_1": "📅 Your exam is tomorrow! Rest well. Good luck! 🍀", "practice": "Practise",
        "slow": "A little slower, please 🙂",
    },
}

SUPPORT_WORDS = {
    "uz": {"hello": "Assalomu alaykum! TestDay yordam xizmati. Savolingizni yozing (matn, rasm yoki ovozli xabar), tez orada javob beramiz.",
           "got": "Rahmat, xabaringiz yuborildi. Tez orada javob beramiz.", "slow": "Juda ko'p xabar. Birozdan keyin yozing, iltimos.",
           "off": "Yordam xizmati hozir ishlamayapti. Iltimos, saytdagi Feedback tugmasidan foydalaning."},
    "ru": {"hello": "Здравствуйте! Поддержка TestDay. Напишите вопрос (текст, фото или голосовое), мы скоро ответим.",
           "got": "Спасибо, сообщение отправлено. Скоро ответим.", "slow": "Слишком много сообщений. Напишите чуть позже, пожалуйста.",
           "off": "Поддержка сейчас не работает. Пожалуйста, воспользуйтесь кнопкой Feedback на сайте."},
    "en": {"hello": "Hello! This is TestDay support. Write your question (text, photo or voice message) and we will answer soon.",
           "got": "Thank you, your message has been sent. We will answer soon.", "slow": "Too many messages. Please write again a little later.",
           "off": "Support is not available right now. Please use the Feedback button on the site."},
}


def lang_of(user):
    code = str((user or {}).get("language_code") or "").lower()
    return "ru" if code.startswith(("ru", "be", "kk", "uk")) else "en" if code.startswith("en") else "uz"


def menu(lang, linked):
    w = WORDS[lang]
    rows = [[{"text": w["calc"], "callback_data": "calc"}, {"text": w["results"], "callback_data": "results"}]]
    if not linked:
        rows.append([{"text": w["connect"], "url": f"{SITE}/#/account"}])
    rows.append([{"text": w["site"], "url": f"{SITE}/"}])
    return {"inline_keyboard": rows}


# --------------------------------------------------------------------------
# The student bot
# --------------------------------------------------------------------------

STUDENT_MESSAGES = guard.Window("TELEGRAM_MESSAGES_PER_USER_PER_MINUTE", 20, 60)


def send_calculator(chat_id, lang):
    return call("student", "sendWidget", {"chat_id": chat_id, "html": telegram_widgets.calculator_html(lang)})


def send_results(db, progress, chat_id, lang):
    profile = profile_for_chat(db, chat_id)
    if not profile:
        return call("student", "sendMessage", {"chat_id": chat_id, "text": WORDS[lang]["not_linked"],
                                               "reply_markup": menu(lang, False)})
    state = results_state(db, progress, profile)
    return call("student", "sendWidget", {"chat_id": chat_id, "html": telegram_widgets.progress_html(lang),
                                          "chat_data": state, "allow_queries": True})


def results_state(db, progress, profile):
    points, _ = progress(profile["id"])
    return telegram_widgets.progress_state(profile, points, now().date())


def handle_student(db, progress, update):
    """One update for @testdayuzbot. `progress(user_id)` gives (points, activity) as on the Account page."""
    if "widget_query" in update:
        q = update["widget_query"]
        chat_id = (q.get("chat") or {}).get("id")
        profile = profile_for_chat(db, chat_id) if chat_id else None
        data = results_state(db, progress, profile) if profile and q.get("data") == "r" else ""
        quietly("student", "answerWidgetQuery", {"widget_query_id": q["id"], **({"data": data} if data else {})})
        if data and q.get("message_id"):
            try:
                call("student", "editMessageWidgetData", {"chat_id": chat_id, "message_id": q["message_id"], "chat_data": data})
            except TelegramError as e:
                if "not modified" not in str(e):
                    log.warning("Telegram: could not refresh a results card: %s", e)
        return
    if "callback_query" in update:
        cb = update["callback_query"]
        lang = lang_of(cb.get("from"))
        chat_id = ((cb.get("message") or {}).get("chat") or {}).get("id") or (cb.get("from") or {}).get("id")
        quietly("student", "answerCallbackQuery", {"callback_query_id": cb["id"]})
        if not STUDENT_MESSAGES.allow(chat_id):
            return
        if cb.get("data") == "calc":
            send_calculator(chat_id, lang)
        elif cb.get("data") == "results":
            send_results(db, progress, chat_id, lang)
        return
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    if chat.get("type") != "private":
        return
    chat_id, lang = chat["id"], lang_of(msg.get("from"))
    if not STUDENT_MESSAGES.allow(chat_id):
        return
    text = str(msg.get("text") or "").strip()
    command, _, arg = text.partition(" ")
    command = command.split("@")[0].lower()
    if command == "/start" and arg:
        user_id = user_from_code(arg.strip())
        if not user_id or not db.select("profiles", {"id": user_id}, limit=1):
            call("student", "sendMessage", {"chat_id": chat_id, "text": WORDS[lang]["bad_link"], "reply_markup": menu(lang, False)})
            return
        connect(db, user_id, chat_id)
        call("student", "sendMessage", {"chat_id": chat_id, "text": WORDS[lang]["linked"], "reply_markup": menu(lang, True)})
        send_results(db, progress, chat_id, lang)
        return
    if command in ("/calc", "/calculator"):
        send_calculator(chat_id, lang)
    elif command in ("/results", "/progress"):
        send_results(db, progress, chat_id, lang)
    elif command in ("/stop", "/unlink"):
        profile = profile_for_chat(db, chat_id)
        if profile:
            disconnect(db, profile["id"])
        call("student", "sendMessage", {"chat_id": chat_id, "text": WORDS[lang]["unlinked"]})
    else:
        linked = profile_for_chat(db, chat_id) is not None
        call("student", "sendMessage", {"chat_id": chat_id, "text": WORDS[lang]["hello"], "reply_markup": menu(lang, linked)})


# --------------------------------------------------------------------------
# Messages to a student (results, reminders)
# --------------------------------------------------------------------------

def notify(db, user_id, key, button=None, **values):
    """Send one of WORDS[...][key] to the student's Telegram if it is connected. True if sent."""
    if not configured("student"):
        return False
    rows = db.select("profiles", {"id": user_id}, limit=1)
    profile = rows[0] if rows else None
    chat_id = profile.get("telegram_id") if profile else None
    if not chat_id:
        return False
    lang = "uz"
    text = WORDS[lang][key].format(**values)
    payload = {"chat_id": chat_id, "text": text}
    if button:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": WORDS[lang][button[0]], "url": button[1]}]]}
    try:
        call("student", "sendMessage", payload)
        return True
    except TelegramError as e:
        if e.code == 403:   # the student blocked the bot: stop writing to them
            disconnect(db, user_id)
        log.warning("Telegram: could not message a student: %s", e)
        return False


def speaking_result_ready(db, sub, result):
    band = result.get("overallBand")
    if band is None:
        return
    notify(db, sub["user_id"], "speaking_ready", ("open_result", f"{SITE}/#/speaking/{sub['id']}"), band=f"{float(band):.1f}")


def pass_ending(db, user_id, ends_at):
    date = str(ends_at)[:10]
    notify(db, user_id, "pass_ending", ("renew", f"{SITE}/#/pricing"), date=date)


_reminded = set()


def exam_reminders(db, at=None):
    """At about 9:00 in Tashkent, remind students whose exam is in 7 days or tomorrow. Returns how many were sent."""
    at = at or now()
    local = at + datetime.timedelta(hours=5)
    if local.hour != 9:
        return 0
    sent = 0
    for days, key in ((7, "exam_7"), (1, "exam_1")):
        day = (local.date() + datetime.timedelta(days=days)).isoformat()
        for p in db.select("profiles", {"exam_date": day}, limit=2000):
            mark = (p["id"], day, key)
            if not p.get("telegram_id") or mark in _reminded:
                continue
            _reminded.add(mark)
            if notify(db, p["id"], key, ("practice", f"{SITE}/")):
                sent += 1
    return sent


# --------------------------------------------------------------------------
# The support bot: students write, the owner answers
# --------------------------------------------------------------------------

SUPPORT_MESSAGES = guard.Window("TELEGRAM_SUPPORT_PER_USER_PER_HOUR", 20, 3600)
_thanked = {}
_threads = {}            # message id in the owner's chat -> the student's chat id (the header line carries it too)
_threads_lock = threading.Lock()
MARK = re.compile(r"#u(\d{3,15})\b")


def _remember(owner_message_id, student_id):
    with _threads_lock:
        _threads[owner_message_id] = student_id
        if len(_threads) > 5000:
            for k in list(_threads)[:2500]:
                del _threads[k]


def handle_support(db, update):
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    if chat.get("type") != "private":
        return
    sender = msg.get("from") or {}
    owner = owner_chat()
    lang = lang_of(sender)
    words = SUPPORT_WORDS[lang]
    text = str(msg.get("text") or "")
    if owner is not None and chat["id"] == owner:
        reply = msg.get("reply_to_message") or {}
        target = None
        with _threads_lock:
            target = _threads.get(reply.get("message_id"))
        if target is None:
            found = MARK.search(str(reply.get("text") or reply.get("caption") or ""))
            target = int(found.group(1)) if found else None
        if target is None:
            if not text.startswith("/"):
                call("support", "sendMessage", {"chat_id": owner, "text": "Reply to a student's message (the line with #u…) to answer them."})
            return
        try:
            call("support", "copyMessage", {"chat_id": target, "from_chat_id": owner, "message_id": msg["message_id"]})
            call("support", "sendMessage", {"chat_id": owner, "text": "✓ Sent", "reply_to_message_id": msg["message_id"]})
        except TelegramError as e:
            call("support", "sendMessage", {"chat_id": owner, "text": f"Could not send: {e}"})
        return
    if text.split(" ")[0].split("@")[0].lower() == "/start":
        call("support", "sendMessage", {"chat_id": chat["id"], "text": words["hello"]})
        return
    if owner is None:
        call("support", "sendMessage", {"chat_id": chat["id"], "text": words["off"]})
        return
    if not SUPPORT_MESSAGES.allow(chat["id"]):
        if _thanked.get(("slow", chat["id"]), 0) < time.time() - 600:
            _thanked[("slow", chat["id"])] = time.time()
            call("support", "sendMessage", {"chat_id": chat["id"], "text": words["slow"]})
        return
    name = " ".join(x for x in (sender.get("first_name"), sender.get("last_name")) if x)[:60]
    who = f"@{sender['username']}" if sender.get("username") else ""
    profile = profile_for_chat(db, chat["id"]) if "telegram_id" in _profile_columns(db) else None
    account = f" · {profile['email']}" if profile else ""
    header = call("support", "sendMessage", {"chat_id": owner, "text": f"💬 #u{chat['id']} {name} {who}{account}".strip()})
    copied = call("support", "copyMessage", {"chat_id": owner, "from_chat_id": chat["id"], "message_id": msg["message_id"]})
    if header:
        _remember(header["message_id"], chat["id"])
    if copied:
        _remember(copied["message_id"], chat["id"])
    if _thanked.get(chat["id"], 0) < time.time() - 1800:   # one thank-you per half hour, not one per message
        _thanked[chat["id"]] = time.time()
        call("support", "sendMessage", {"chat_id": chat["id"], "text": words["got"]})


_columns_cache = {}


def _profile_columns(db):
    """Whether the profiles table has telegram_id yet (the Supabase SQL block may not have been run)."""
    if "profiles" not in _columns_cache:
        try:
            db.select("profiles", {"telegram_id": 0}, limit=1)
            _columns_cache["profiles"] = {"telegram_id"}
        except Exception:  # noqa: BLE001
            _columns_cache["profiles"] = set()
    return _columns_cache["profiles"]


def handle_update(bot, db, progress, update):
    """Never raises: Telegram would only send the update again."""
    try:
        if bot == "student":
            handle_student(db, progress, update)
        elif bot == "support":
            handle_support(db, update)
    except TelegramError as e:
        log.warning("Telegram %s bot: %s", bot, e)
    except Exception:  # noqa: BLE001
        log.exception("Telegram %s bot: the update could not be handled", bot)
