"""
What @testdayuzbot shows: the IELTS band calculator and the student's results card, each in two forms.

  Widgets (Telegram Bot API 10.4 HTML widgets, https://core.telegram.org/bots/widgets)
    calculator_html(lang)   steppers for Listening and Reading raw scores and Writing and Speaking bands, the overall
                            band; works entirely inside Telegram (a widget has no network)
    progress_html(lang)     the latest band per paper as bars, the overall estimate in a ring, the target, the days to
                            the exam; the numbers come from the bot as the chat state (progress_state), and the card
                            asks the bot for fresh numbers when it comes on screen
    Since 13 November 2026 Telegram refuses widgets from ordinary bots in production (INPUT_MEDIA_WIDGET_NOT_ALLOWED,
    confirmed by the Bot API team, no date given), so the bot tries them now and then and otherwise uses:

  Ordinary messages (work everywhere)
    calc_text / calc_keyboard     the same calculator as a message whose buttons change the numbers in place; the
                                  whole state travels in each button's callback data ("k30.30.12.12")
    progress_text                 the results card as formatted text, with bars

The two forms use the same tables and rounding as the site (scoring.py, public/js/seo-calc.js). Each widget must stay
under 4096 bytes after zlib compression (a test checks it).
"""

import html
import json
import re

from . import scoring

TEXT = {
    "uz": {
        "calc": "IELTS ball kalkulyatori", "l": "Listening", "r": "Reading", "w": "Writing", "s": "Speaking",
        "raw": "to'g'ri javob", "overall": "Umumiy ball", "hint": "Natija taxminiy, rasmiy IELTS natijasi emas.",
        "card": "Natijalaringiz", "none": "hali yo'q", "est": "Umumiy (taxminiy)", "goal": "Maqsad",
        "exam": "Imtihonga", "days": "kun", "today": "Imtihon bugun!", "tests": "Topshirilgan testlar",
        "refresh": "Yangilash", "open": "Saytda ochish", "link": "Hisob ulanmagan: saytda Telegramni ulang.",
        "tap": "Raqamlarni tugmalar bilan o'zgartiring.", "reset": "Boshidan", "gap": "maqsadgacha yana {n}",
        "reached": "maqsadga yetdingiz!", "first": "Hali test topshirmagansiz. Birinchi testni saytda boshlang!",
        "updated": "Yangilandi",
    },
    "ru": {
        "calc": "Калькулятор баллов IELTS", "l": "Listening", "r": "Reading", "w": "Writing", "s": "Speaking",
        "raw": "верных ответов", "overall": "Общий балл", "hint": "Оценка примерная, это не официальный результат IELTS.",
        "card": "Ваши результаты", "none": "пока нет", "est": "Общий (примерно)", "goal": "Цель",
        "exam": "До экзамена", "days": "дн.", "today": "Экзамен сегодня!", "tests": "Пройдено тестов",
        "refresh": "Обновить", "open": "Открыть на сайте", "link": "Аккаунт не подключён: подключите Telegram на сайте.",
        "tap": "Меняйте числа кнопками.", "reset": "Сначала", "gap": "до цели ещё {n}",
        "reached": "цель достигнута!", "first": "Вы ещё не прошли ни одного теста. Начните первый на сайте!",
        "updated": "Обновлено",
    },
    "en": {
        "calc": "IELTS band calculator", "l": "Listening", "r": "Reading", "w": "Writing", "s": "Speaking",
        "raw": "correct", "overall": "Overall band", "hint": "An estimate, not an official IELTS result.",
        "card": "Your results", "none": "none yet", "est": "Overall (estimate)", "goal": "Target",
        "exam": "Exam in", "days": "days", "today": "Your exam is today!", "tests": "Tests taken",
        "refresh": "Refresh", "open": "Open on the site", "link": "Not linked yet: connect Telegram on the site.",
        "tap": "Change the numbers with the buttons.", "reset": "Start again", "gap": "{n} to go",
        "reached": "target reached!", "first": "No tests yet. Start your first one on the site!",
        "updated": "Updated",
    },
}

ICON = {"l": "🎧", "r": "📖", "w": "✍️", "s": "🗣"}
SITE = "https://www.testday.uz"
CALC_PATH = {"uz": "/uz/ielts-band-score-hisoblash", "ru": "/ru/ielts-kalkulyator-ballov", "en": "/en/ielts-band-score-calculator"}
TABLES = {"l": scoring.LISTENING_BANDS, "r": scoring.ACADEMIC_READING_BANDS}


def words(lang):
    return TEXT.get(lang, TEXT["uz"])


def overall_band(bands):
    """The IELTS overall band: the mean of four bands, .25 up to the half band and .75 up to the whole band."""
    e = round(sum(bands) * 2)
    return e // 8 + (0 if e % 8 < 2 else 0.5 if e % 8 < 6 else 1)


def fmt(band):
    return f"{float(band):.1f}"


# --------------------------------------------------------------------------
# Widgets
# --------------------------------------------------------------------------

_STYLE = """<style>
body{margin:0;padding:12px 12px max(10px,env(safe-area-inset-bottom))}
.hd{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.tt{flex:1;min-width:0}.tt b{display:block;font-size:1.05em}
.hd small,.h,.n small{color:var(--tg-theme-hint-color);font-size:.8em}
.pill{flex:none;text-align:center;border-radius:14px;padding:5px 12px;background:var(--tg-theme-button-color);color:var(--tg-theme-button-text-color)}
.pill small{display:block;font-size:.65em;color:inherit}.pill b{font-size:1.7em;line-height:1.1}
.r{display:flex;align-items:center;gap:8px;padding:7px 0;border-top:1px solid var(--tg-theme-section-separator-color)}
.n{flex:1;min-width:0;font-weight:600;white-space:nowrap}.n small{display:block;font-weight:400}
.st{display:flex;align-items:center;border-radius:10px;background:var(--tg-theme-secondary-bg-color)}
.st button{background:none;border:0;padding:0;width:27px;height:30px;font:inherit;font-weight:700;color:var(--tg-theme-link-color)}
.st span{min-width:30px;text-align:center;font-weight:600;font-variant-numeric:tabular-nums}
.bd{min-width:38px;text-align:center;font-weight:700;color:var(--tg-theme-accent-text-color);font-variant-numeric:tabular-nums}
.h{margin:8px 0 0}
</style>"""


def calculator_html(lang="uz"):
    t = words(lang)
    tables = {k: [list(x) for x in v] for k, v in TABLES.items()}
    rows = "".join(
        f'<div class="r"><span class="n">{ICON[k]} {t[k]}<small>{"/40 " + t["raw"] if k in "lr" else "band"}</small></span>'
        f'<span class="st">{"<button data-k=" + k + " data-d=-5>«</button>" if k in "lr" else ""}'
        f'<button data-k={k} data-d=-1>−</button><span id="v{k}"></span><button data-k={k} data-d=1>+</button>'
        f'{"<button data-k=" + k + " data-d=5>»</button>" if k in "lr" else ""}</span>'
        f'<span class="bd" id="b{k}"></span></div>'
        for k in "lrws")
    return f"""{_STYLE}<div class="hd"><div class="tt"><b>📊 {t["calc"]}</b><small>{t["tap"]}</small></div>
<div class="pill"><small>{t["overall"]}</small><b id="o"></b></div></div>{rows}<p class="h">{t["hint"]}</p>
<script>
var T={json.dumps(tables, separators=(",", ":"))},S={{l:30,r:30,w:12,s:12}};
try{{var x=JSON.parse(localStorage.getItem("c"));if(x)S=x}}catch(e){{}}
function band(t,n){{for(var i=0;i<t.length;i++)if(n>=t[i][0])return t[i][1];return 2}}
function f(v){{return v.toFixed(1)}}
function $(i){{return document.getElementById(i)}}
function draw(){{var b={{}};for(var k in S){{var v=S[k];if(k=="l"||k=="r"){{b[k]=band(T[k],v);$("v"+k).textContent=v}}
else{{b[k]=v/2;$("v"+k).textContent=f(v/2)}}$("b"+k).textContent=f(b[k])}}
var e=Math.round((b.l+b.r+b.w+b.s)*2),w=Math.floor(e/8),q=e%8;$("o").textContent=f(w+(q<2?0:q<6?.5:1));
try{{localStorage.setItem("c",JSON.stringify(S))}}catch(e){{}}}}
document.querySelectorAll("button").forEach(function(btn){{btn.addEventListener("click",function(){{
var k=btn.dataset.k,max=k=="l"||k=="r"?40:18;S[k]=Math.max(0,Math.min(max,S[k]+Number(btn.dataset.d)));
draw();var W=window.TelegramWidget;if(W)W.HapticFeedback.selectionChanged()}})}});draw();
</script>"""


_CARD_STYLE = """<style>
.ring{width:64px;height:64px;position:relative;flex:none}.ring svg{transform:rotate(-90deg)}
.ring b{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:1.25em}
.bar{flex:1.4;height:8px;border-radius:4px;background:var(--tg-theme-secondary-bg-color);position:relative}
.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:4px;background:var(--tg-theme-button-color);transition:width .4s}
.bar u{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--tg-theme-text-color);display:none}
.ch{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.ch span{border-radius:9px;padding:3px 8px;font-size:.85em;background:var(--tg-theme-secondary-bg-color)}
.bt{display:flex;gap:8px}.bt button{flex:1}
@media (prefers-reduced-motion:reduce){.bar i{transition:none}}
</style>"""


def progress_html(lang="uz"):
    t = words(lang)
    rows = "".join(f'<div class="r"><span class="n">{ICON[k]} {t[k]}</span><span class="bar"><i id="i{k}"></i>'
                   f'<u id="u{k}"></u></span><span class="bd" id="b{k}"></span></div>' for k in "lrws")
    keys = ("none", "goal", "exam", "days", "today", "tests", "link", "gap", "reached")
    return f"""{_STYLE}{_CARD_STYLE}<div class="hd"><div class="tt"><b id="h">📈 {t["card"]}</b><small>{t["est"]}</small></div>
<div class="ring"><svg width="64" height="64"><circle cx="32" cy="32" r="27" fill="none" stroke-width="7" stroke="var(--tg-theme-secondary-bg-color)"/>
<circle id="c" cx="32" cy="32" r="27" fill="none" stroke-width="7" stroke-linecap="round" stroke="var(--tg-theme-button-color)" stroke-dasharray="0 170"/></svg><b id="o">–</b></div></div>
{rows}<div class="ch" id="x"></div>
<div class="bt"><button id="u">🔄 {t["refresh"]}</button><button id="g">🌐 {t["open"]}</button></div>
<script>
var W=window.TelegramWidget,L={json.dumps({k: t[k] for k in keys}, ensure_ascii=False)};
function $(i){{return document.getElementById(i)}}
function f(v){{return v==null?"–":Number(v).toFixed(1)}}
function chip(s){{var e=document.createElement("span");e.textContent=s;$("x").appendChild(e)}}
function draw(s){{$("x").textContent="";if(!s){{chip(L.link);return}}
if(s.n)$("h").textContent="📈 "+s.n;
for(var k of["l","r","w","s"]){{var v=s.b&&s.b[k];$("b"+k).textContent=v==null?L.none:f(v);
$("i"+k).style.width=(v==null?0:v/9*100)+"%";var u=$("u"+k);if(s.t){{u.style.display="block";u.style.left=s.t/9*100+"%"}}}}
$("o").textContent=f(s.o);$("c").setAttribute("stroke-dasharray",(s.o==null?0:s.o/9*169.6)+" 170");
if(s.t)chip("🎯 "+L.goal+" "+f(s.t)+(s.o==null?"":s.o>=s.t?" · "+L.reached:" · "+L.gap.replace("{{n}}",f(s.t-s.o))));
if(s.d!=null)chip("📅 "+(s.d==0?L.today:L.exam+" "+s.d+" "+L.days));chip("📝 "+L.tests+": "+(s.c||0))}}
function load(){{var s=null;try{{s=JSON.parse(W.chatData)}}catch(e){{}}draw(s)}}
function ask(){{W.request("r").then(function(a){{try{{draw(JSON.parse(a.result))}}catch(e){{}}}},function(){{}})}}
if(W){{W.onEvent("chatDataChanged",load);load();ask();
$("u").addEventListener("click",ask);
$("g").addEventListener("click",function(){{W.openLink("{SITE}/#/account")}})}}
</script>"""


def progress_state(profile, points, today):
    """The card's chat state (at most 1024 bytes): the latest band per paper, the overall estimate, target and exam."""
    import datetime
    latest = {}
    for p in points:                       # oldest first, so the last one of each paper wins
        latest[p["module"][0]] = p["band"]
    bands = {k: latest.get(k) for k in "lrws"}
    overall = overall_band(bands.values()) if all(v is not None for v in bands.values()) else None
    days = None
    if profile.get("exam_date"):
        try:
            days = (datetime.date.fromisoformat(str(profile["exam_date"])[:10]) - today).days
            days = days if days >= 0 else None
        except ValueError:
            days = None
    name = (profile.get("name") or "").strip()[:40]
    state = {"b": bands, "o": overall, "t": profile.get("target_band"), "d": days, "c": len(points)}
    if name:
        state["n"] = name
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"))


# --------------------------------------------------------------------------
# Ordinary messages (HTML parse mode)
# --------------------------------------------------------------------------

CALC_START = (30, 30, 12, 12)          # Listening and Reading raw scores; Writing and Speaking as half bands (12 = 6.0)
_CALC_MAX = (40, 40, 18, 18)
_CALC_DATA = re.compile(r"^k(\d{1,2})\.(\d{1,2})\.(\d{1,2})\.(\d{1,2})$")


def calc_parse(data):
    """The calculator state in a button's callback data, kept inside the limits; None if it is not one."""
    m = _CALC_DATA.match(str(data or ""))
    if not m:
        return None
    return tuple(min(int(v), top) for v, top in zip(m.groups(), _CALC_MAX))


def _calc_data(state):
    return "k" + ".".join(str(v) for v in state)


def calc_bands(state):
    l, r, w, s = state
    return (scoring.band_for_raw_score(l, TABLES["l"]), scoring.band_for_raw_score(r, TABLES["r"]), w / 2, s / 2)


def calc_text(lang, state=CALC_START):
    t = words(lang)
    bands = calc_bands(state)
    lines = [f"<b>📊 {t['calc']}</b>", ""]
    for i, k in enumerate("lrws"):
        raw = f"{state[i]}/40 → " if k in "lr" else ""
        lines.append(f"{ICON[k]} {t[k]}:  {raw}<b>{fmt(bands[i])}</b>")
    lines += ["", f"⭐ {t['overall']}: <b>{fmt(overall_band(bands))}</b>", "", f"<i>{t['tap']} {t['hint']}</i>"]
    return "\n".join(lines)


def calc_keyboard(lang, state=CALC_START):
    """One row of steppers per paper; the middle button shows the value. Every button carries the state it leads to."""
    t = words(lang)
    rows = []
    for i, k in enumerate("lrws"):
        steps = (-5, -1, 1, 5) if k in "lr" else (-1, 1)
        row = []
        for d in steps:
            nxt = list(state)
            nxt[i] = max(0, min(_CALC_MAX[i], state[i] + d))
            label = {-5: "−5", -1: "−", 1: "+", 5: "+5"}[d] if k in "lr" else {-1: "− 0.5", 1: "+ 0.5"}[d]
            row.append({"text": label, "callback_data": _calc_data(nxt) if tuple(nxt) != state else "k_"})
        value = f"{ICON[k]} {state[i]}" if k in "lr" else f"{ICON[k]} {fmt(state[i] / 2)}"
        row.insert(len(row) // 2, {"text": value, "callback_data": "k_"})
        rows.append(row)
    rows.append([{"text": f"↺ {t['reset']}", "callback_data": _calc_data(CALC_START) if state != CALC_START else "k_"},
                 {"text": f"🌐 {t['open']}", "url": SITE + CALC_PATH.get(lang, CALC_PATH["uz"])}])
    return {"inline_keyboard": rows}


def _bar(band):
    full = int(float(band) + 0.5)
    return "▰" * full + "▱" * (9 - full)


def progress_text(lang, state_json):
    """The results card as a message, from progress_state's JSON. Names are escaped: they are the student's text."""
    t = words(lang)
    s = json.loads(state_json)
    title = f"📈 {t['card']}" + (f" · {html.escape(s['n'])}" if s.get("n") else "")
    lines = [f"<b>{title}</b>", ""]
    for k in "lrws":
        v = (s.get("b") or {}).get(k)
        lines.append(f"{ICON[k]} {t[k]}:  <b>{fmt(v)}</b>  {_bar(v)}" if v is not None else f"{ICON[k]} {t[k]}:  <i>{t['none']}</i>")
    lines.append("")
    if s.get("o") is not None:
        lines.append(f"⭐ {t['est']}: <b>{fmt(s['o'])}</b>")
    if s.get("t"):
        goal = f"🎯 {t['goal']}: <b>{fmt(s['t'])}</b>"
        if s.get("o") is not None:
            goal += f" · {t['reached']}" if s["o"] >= s["t"] else " · " + t["gap"].format(n=fmt(s["t"] - s["o"]))
        lines.append(goal)
    if s.get("d") is not None:
        lines.append("📅 " + (t["today"] if s["d"] == 0 else f"{t['exam']}: <b>{s['d']}</b> {t['days']}"))
    lines.append(f"📝 {t['tests']}: <b>{s.get('c') or 0}</b>")
    if not s.get("c"):
        lines += ["", t["first"]]
    return "\n".join(lines)
