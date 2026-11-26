"""
The two widgets @testdayuzbot sends (Telegram Bot API 10.4 HTML widgets, https://core.telegram.org/bots/widgets):

  calculator_html(lang)   the IELTS band calculator: Listening and Reading raw scores to bands, Writing and Speaking
                          bands, and the overall band. Works entirely inside Telegram (a widget has no network), with the
                          same tables and rounding as the site (scoring.py, public/js/seo-calc.js).
  progress_html(lang)     the student's progress card: latest band per paper, the overall estimate, the target and the
                          days to the exam. The numbers come from the bot as the widget's chat state (progress_state),
                          and the card asks the bot for fresh numbers whenever it comes on screen.

Widgets have no text boxes, so numbers are chosen with buttons. Each widget must stay under 4096 bytes after zlib
compression (a test checks it).
"""

import json

from . import scoring

TEXT = {
    "uz": {
        "calc": "IELTS ball kalkulyatori", "l": "Listening", "r": "Reading", "w": "Writing", "s": "Speaking",
        "raw": "to'g'ri javob", "overall": "Umumiy ball", "hint": "Natija taxminiy, rasmiy IELTS natijasi emas.",
        "card": "Natijalaringiz", "none": "hali yo'q", "est": "Umumiy (taxminiy)", "goal": "Maqsad",
        "exam": "Imtihonga", "days": "kun", "today": "Imtihon bugun!", "tests": "Topshirilgan testlar",
        "refresh": "Yangilash", "open": "Saytda ochish", "link": "Hisob ulanmagan: saytda Telegramni ulang.",
    },
    "ru": {
        "calc": "Калькулятор баллов IELTS", "l": "Listening", "r": "Reading", "w": "Writing", "s": "Speaking",
        "raw": "верных ответов", "overall": "Общий балл", "hint": "Оценка примерная, это не официальный результат IELTS.",
        "card": "Ваши результаты", "none": "пока нет", "est": "Общий (примерно)", "goal": "Цель",
        "exam": "До экзамена", "days": "дн.", "today": "Экзамен сегодня!", "tests": "Пройдено тестов",
        "refresh": "Обновить", "open": "Открыть на сайте", "link": "Аккаунт не подключён: подключите Telegram на сайте.",
    },
    "en": {
        "calc": "IELTS band calculator", "l": "Listening", "r": "Reading", "w": "Writing", "s": "Speaking",
        "raw": "correct", "overall": "Overall band", "hint": "An estimate, not an official IELTS result.",
        "card": "Your results", "none": "none yet", "est": "Overall (estimate)", "goal": "Target",
        "exam": "Exam in", "days": "days", "today": "Your exam is today!", "tests": "Tests taken",
        "refresh": "Refresh", "open": "Open on the site", "link": "Not linked yet: connect Telegram on the site.",
    },
}

SITE = "https://www.testday.uz"

_STYLE = """<style>
body{margin:0;padding:10px 12px;font:var(--tg-text-font-size,15px)/1.35 system-ui,sans-serif}
h3{margin:0 0 8px;font-size:1.05em}
.r{display:flex;align-items:center;gap:6px;padding:5px 0;border-top:1px solid var(--tg-theme-section-separator-color)}
.n{flex:1;font-weight:600}.n small{display:block;font-weight:400;color:var(--tg-theme-hint-color);font-size:.8em}
.v{min-width:46px;text-align:center;font-variant-numeric:tabular-nums}
.b{min-width:42px;text-align:right;font-weight:700;color:var(--tg-theme-accent-text-color);font-variant-numeric:tabular-nums}
button{min-width:34px;padding:4px 0}
.o{display:flex;justify-content:space-between;align-items:baseline;padding:8px 0 2px;border-top:2px solid var(--tg-theme-section-separator-color)}
.o b{font-size:1.9em;color:var(--tg-theme-accent-text-color)}
.h{color:var(--tg-theme-hint-color);font-size:.8em;margin:4px 0 0}
</style>"""


def calculator_html(lang="uz"):
    t = TEXT.get(lang, TEXT["uz"])
    tables = {"l": [list(x) for x in scoring.LISTENING_BANDS], "r": [list(x) for x in scoring.ACADEMIC_READING_BANDS]}
    rows = "".join(
        f'<div class="r"><span class="n">{t[k]}<small>{"/40 " + t["raw"] if k in "lr" else "band"}</small></span>'
        f'{"<button data-k=" + k + " data-d=-5>−5</button>" if k in "lr" else ""}'
        f'<button data-k={k} data-d=-1>−</button><span class="v" id="v{k}"></span><button data-k={k} data-d=1>+</button>'
        f'{"<button data-k=" + k + " data-d=5>+5</button>" if k in "lr" else ""}'
        f'<span class="b" id="b{k}"></span></div>'
        for k in "lrws")
    return f"""{_STYLE}<h3>{t["calc"]}</h3>{rows}
<div class="o"><span>{t["overall"]}</span><b id="o"></b></div><p class="h">{t["hint"]}</p>
<script>
var T={json.dumps(tables, separators=(",", ":"))},S={{l:30,r:30,w:12,s:12}};
try{{var x=JSON.parse(localStorage.getItem("c"));if(x)S=x}}catch(e){{}}
function band(t,n){{for(var i=0;i<t.length;i++)if(n>=t[i][0])return t[i][1];return 2}}
function f(v){{return v.toFixed(1)}}
function draw(){{var b={{}};for(var k in S){{var v=S[k];if(k=="l"||k=="r"){{b[k]=band(T[k],v);document.getElementById("v"+k).textContent=v}}
else{{b[k]=v/2;document.getElementById("v"+k).textContent=f(v/2)}}document.getElementById("b"+k).textContent=f(b[k])}}
var e=Math.round((b.l+b.r+b.w+b.s)*2),w=Math.floor(e/8),q=e%8;document.getElementById("o").textContent=f(w+(q<2?0:q<6?.5:1));
try{{localStorage.setItem("c",JSON.stringify(S))}}catch(e){{}}}}
document.querySelectorAll("button").forEach(function(btn){{btn.addEventListener("click",function(){{
var k=btn.dataset.k,max=k=="l"||k=="r"?40:18;S[k]=Math.max(0,Math.min(max,S[k]+Number(btn.dataset.d)));
draw();var W=window.TelegramWidget;if(W)W.HapticFeedback.selectionChanged()}})}});draw();
</script>"""


def progress_html(lang="uz"):
    t = TEXT.get(lang, TEXT["uz"])
    rows = "".join(f'<div class="r"><span class="n">{t[k]}</span><span class="b" id="b{k}"></span></div>' for k in "lrws")
    return f"""{_STYLE}<h3 id="h">{t["card"]}</h3>{rows}
<div class="o"><span>{t["est"]}</span><b id="o">–</b></div><p class="h" id="x"></p>
<p><button id="u">{t["refresh"]}</button> <button id="g">{t["open"]}</button></p>
<script>
var W=window.TelegramWidget,L={json.dumps({k: t[k] for k in ("none", "goal", "exam", "days", "today", "tests", "link")}, ensure_ascii=False)};
function f(v){{return v==null?L.none:Number(v).toFixed(1)}}
function draw(s){{if(!s){{document.getElementById("x").textContent=L.link;return}}
if(s.n)document.getElementById("h").textContent=s.n;
for(var k of["l","r","w","s"])document.getElementById("b"+k).textContent=f(s.b&&s.b[k]);
document.getElementById("o").textContent=s.o==null?"–":f(s.o);var p=[];
if(s.t)p.push(L.goal+": "+f(s.t));if(s.d!=null)p.push(s.d==0?L.today:L.exam+": "+s.d+" "+L.days);
p.push(L.tests+": "+(s.c||0));document.getElementById("x").textContent=p.join(" · ")}}
function load(){{var s=null;try{{s=JSON.parse(W.chatData)}}catch(e){{}}draw(s)}}
function ask(){{W.request("r").then(function(a){{try{{draw(JSON.parse(a.result))}}catch(e){{}}}},function(){{}})}}
if(W){{W.onEvent("chatDataChanged",load);load();ask();
document.getElementById("u").addEventListener("click",ask);
document.getElementById("g").addEventListener("click",function(){{W.openLink("{SITE}/#/account")}})}}
</script>"""


def progress_state(profile, points, today):
    """The card's chat state (at most 1024 bytes): the latest band per paper, the overall estimate, target and exam."""
    import datetime
    latest = {}
    for p in points:                       # oldest first, so the last one of each paper wins
        latest[p["module"][0]] = p["band"]
    bands = {k: latest.get(k) for k in "lrws"}
    overall = None
    if all(v is not None for v in bands.values()):
        e = round(sum(bands.values()) * 2)
        overall = e // 8 + (0 if e % 8 < 2 else 0.5 if e % 8 < 6 else 1)
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
