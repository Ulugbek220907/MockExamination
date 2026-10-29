"""The web side: the admin page, a few JSON calls, the public address of the day's files, and the Connect buttons."""

import asyncio
import base64
import hmac
import html
import json
import logging
import os
import secrets
from datetime import date, timedelta

import tornado.web
from tornado.ioloop import IOLoop

from . import bank, oauth
from .http import PlatformError

log = logging.getLogger("poster.web")
KIND_LABELS = {"vocab": "Word of the day", "speaking": "Speaking Part 2", "tip": "Tip", "writing": "Writing Task 2", "promo": "TestDay"}
STATE_LABELS = {"posted": "Posted", "failed": "Failed", "posting": "Posting…", "needs_review": "Check the platform"}


def open_link(url):
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">open</a>' if url else ""


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


class Base(tornado.web.RequestHandler):
    @property
    def cfg(self):
        return self.application.settings["cfg"]

    @property
    def runner(self):
        return self.application.settings["runner"]

    @property
    def store(self):
        return self.application.settings["store"]

    def set_default_headers(self):
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("Referrer-Policy", "no-referrer")
        self.set_header("X-Frame-Options", "DENY")

    def require_admin(self):
        """HTTP Basic: any user name, the ADMIN_PASSWORD as the password. Without a password set, nobody gets in."""
        if not self.cfg.admin_password:
            raise tornado.web.HTTPError(503, "Set ADMIN_PASSWORD to use the admin page.")
        header = self.request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                _, _, password = base64.b64decode(header[6:]).decode("utf-8").partition(":")
            except (ValueError, UnicodeDecodeError):
                password = ""
            if hmac.compare_digest(password.encode(), self.cfg.admin_password.encode()):
                return
        raise tornado.web.HTTPError(401, "Sign in with the admin password.")

    def require_fetch(self):
        """POSTs come only from this page's own script: a form on another site cannot add this header."""
        if self.request.headers.get("X-TestDay") != "1":
            raise tornado.web.HTTPError(400, "Not allowed.")

    def write_error(self, status_code, **kwargs):
        if status_code == 401:  # error pages start from clean headers, so the browser's password prompt is asked for here
            self.set_header("WWW-Authenticate", 'Basic realm="TestDay Social", charset="UTF-8"')
        exc = kwargs.get("exc_info", (None, None, None))[1]
        message = getattr(exc, "log_message", None) or self._reason
        if self.request.path.startswith("/api/"):
            self.set_header("Content-Type", "application/json")
            self.finish(json.dumps({"error": message}))
        else:
            self.set_header("Content-Type", "text/plain; charset=utf-8")
            self.finish(message)

    def body_json(self):
        try:
            data = json.loads(self.request.body or b"{}")
        except ValueError:
            raise tornado.web.HTTPError(400, "Send JSON.")
        return data if isinstance(data, dict) else {}


class Health(Base):
    def get(self):
        self.write({"status": "ok"})


class Status(Base):
    def get(self):
        self.require_admin()
        self.write(self.snapshot())

    def snapshot(self):
        runner = self.runner
        today = runner.today()
        return {**runner.status(), "post": runner.post_for(today).to_dict(),
                "upcoming": [{"day": p.day, "kind": p.kind, "title": p.title} for p in runner.upcoming(14)],
                "history": self.store.deliveries(limit=60)}


class Run(Base):
    """Post (or rehearse) today's post now, to one platform or to all the connected ones."""

    async def post(self):
        self.require_admin()
        self.require_fetch()
        body = self.body_json()
        day = self.runner.today()
        only = body.get("platform") or None
        if only and only not in self.cfg.platforms:
            raise tornado.web.HTTPError(400, "Unknown platform.")
        results = await IOLoop.current().run_in_executor(
            None, lambda: self.runner.run_day(day, only=only, dry_run=bool(body.get("dryRun")), manual=True))
        self.write({"day": day.isoformat(), "results": results})


class Retry(Base):
    """Clear a delivery that needs review (after checking the platform), so it can be posted again."""

    def post(self):
        self.require_admin()
        self.require_fetch()
        body = self.body_json()
        self.store.reset(str(body.get("day", ""))[:10], str(body.get("platform", ""))[:20])
        self.write({"ok": True})


class RunDaily(Base):
    """For an outside timer (a cron service that calls this address): do today's run if it is time. Answers at once."""

    def check(self):
        token = self.get_argument("token", "")
        if not self.cfg.cron_token or not hmac.compare_digest(token.encode(), self.cfg.cron_token.encode()):
            raise tornado.web.HTTPError(403, "Wrong token.")

    def run(self):
        if not self.cfg.posting_enabled:
            return self.write({"started": False, "reason": "POSTING_ENABLED is off"})
        IOLoop.current().run_in_executor(None, self.application.settings["tick"])
        self.set_status(202)
        self.write({"started": True})

    def get(self):
        self.check()
        self.run()

    def post(self):
        self.check()
        self.run()


class Disconnect(Base):
    def post(self):
        self.require_admin()
        self.require_fetch()
        name = str(self.body_json().get("name", ""))
        if name not in oauth.CONNECTIONS:
            raise tornado.web.HTTPError(400, "Unknown connection.")
        self.store.delete_token(name)
        self.write({"ok": True})


class Media(tornado.web.StaticFileHandler):
    """/media/<secret>/card.jpg and video.mp4: the files the platforms fetch. Not guessable, and nothing else is served."""

    def set_default_headers(self):
        self.set_header("X-Content-Type-Options", "nosniff")

    @classmethod
    def get_absolute_path(cls, root, path):
        return path  # resolved in validate_absolute_path, which has the runner

    def parse_url_path(self, url_path):
        return url_path

    def validate_absolute_path(self, root, absolute_path):
        key, _, filename = absolute_path.partition("/")
        found = self.application.settings["runner"].media_path(key, filename)
        if not found or not os.path.isfile(found):
            raise tornado.web.HTTPError(404)
        return found

    def get_content_type(self):
        return "video/mp4" if self.absolute_path.endswith(".mp4") else "image/jpeg"


class Preview(Base):
    """/preview/<day>/card.jpg or video.mp4, for the admin page (made on the spot if it does not exist yet)."""

    async def get(self, day, filename):
        self.require_admin()
        try:
            when = date.fromisoformat(day)
        except ValueError:
            raise tornado.web.HTTPError(404)
        today = self.runner.today()
        if filename not in ("card.jpg", "video.mp4") or not today - timedelta(days=5) <= when <= today + timedelta(days=14):
            raise tornado.web.HTTPError(404)
        files = await IOLoop.current().run_in_executor(None, self.runner.files_for, when)
        path = files["card" if filename == "card.jpg" else "video"]
        self.set_header("Content-Type", "image/jpeg" if filename == "card.jpg" else "video/mp4")
        self.set_header("Cache-Control", "private, max-age=300")
        with open(path, "rb") as f:
            self.write(f.read())


class Connect(Base):
    def get(self, name):
        self.require_admin()
        if name not in oauth.CONNECTIONS or not oauth.app_ready(self.cfg, name):
            raise tornado.web.HTTPError(400, "This connection needs its app settings and PUBLIC_URL first.")
        self.redirect(oauth.authorize_url(self.cfg, name, oauth.sign_state(self.cfg, name)))


class Callback(Base):
    async def get(self, name):
        message, ok = "", False
        if self.get_argument("error", ""):
            message = f"The sign-in was cancelled or refused: {self.get_argument('error_description', self.get_argument('error'))}"
        elif oauth.check_state(self.cfg, self.get_argument("state", "")) != name:
            message = "This sign-in link has expired or is not ours. Start again from the admin page."
        else:
            code = self.get_argument("code", "")
            try:
                message = await IOLoop.current().run_in_executor(None, oauth.finish, self.cfg, self.store, name, code)
                ok = True
            except PlatformError as e:
                message = str(e)
            except Exception as e:  # noqa: BLE001
                log.exception("connect %s failed", name)
                message = f"Something went wrong: {e.__class__.__name__}"
        self.set_header("Content-Type", "text/html; charset=utf-8")
        self.finish(page("Connect", f'<p class="{"ok" if ok else "bad"}">{esc(message)}</p><p><a href="/">Back to the admin page</a></p>'))


class Dashboard(Base):
    def get(self):
        self.require_admin()
        nonce = secrets.token_urlsafe(12)
        self.set_header("Content-Security-Policy", f"default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'; "
                        f"script-src 'nonce-{nonce}'; connect-src 'self'; form-action 'self'; base-uri 'none'")
        self.set_header("Content-Type", "text/html; charset=utf-8")
        self.set_header("Cache-Control", "no-store")
        self.finish(self.render_page(nonce))

    def render_page(self, nonce):
        runner, cfg = self.runner, self.cfg
        status = runner.status()
        post = runner.post_for(runner.today())
        deliveries = {d["platform"]: d for d in status["deliveries"]}
        notices = []
        if not cfg.admin_password:
            notices.append("ADMIN_PASSWORD is not set.")
        if not cfg.public_url:
            notices.append("PUBLIC_URL is not set: Instagram and Threads cannot fetch the picture and video, and Connect does not work.")
        if not status["postingEnabled"]:
            notices.append("Daily posting is off. Try “Dry run” on each platform, then set POSTING_ENABLED=1 to start the daily schedule.")
        rows = []
        for p in status["platforms"]:
            name = p["name"]
            d = deliveries.get(name)
            link = next((c for c, (_, group, _) in oauth.CONNECTIONS.items() if name in group), None)
            state = "Not connected" if not p["connected"] else (STATE_LABELS.get(d["status"], d["status"]) if d else "Ready")
            detail = ""
            if d and d.get("url"):
                detail = " " + open_link(d["url"])
            if d and d.get("error"):
                detail += f'<div class="err">{esc(d["error"])}</div>'
            buttons = []
            if p["connected"]:
                buttons.append(f'<button data-run="{name}" data-dry="1">Dry run</button>')
                buttons.append(f'<button class="primary" data-run="{name}">Post now</button>')
                if d and d["status"] in ("needs_review", "failed"):
                    buttons.append(f'<button data-retry="{name}" data-day="{esc(d["day"])}">Clear, post again</button>')
            if link:
                if oauth.app_ready(cfg, link):
                    buttons.append(f'<a class="btn" href="/connect/{link}">{"Reconnect" if p["connected"] else "Connect"}</a>')
                elif not p["connected"]:
                    buttons.append('<span class="muted">needs its app settings</span>')
                if self.store.token(link):  # only a connection made here can be undone here
                    buttons.append(f'<button data-disconnect="{link}">Disconnect</button>')
            rows.append(f'<tr><td><strong>{esc(p["label"])}</strong><div class="muted">{esc(p["account"])}</div></td>'
                        f'<td>{"video" if p["media"] == "video" else "picture"}</td><td>{esc(state)}{detail}</td><td class="act">{"".join(buttons)}</td></tr>')
        upcoming = "".join(f'<tr><td>{esc(u["day"])}</td><td>{esc(KIND_LABELS.get(u["kind"], u["kind"]))}</td><td>{esc(u["title"])}</td></tr>'
                           for u in [{"day": q.day, "kind": q.kind, "title": q.title} for q in runner.upcoming(14)])
        history = "".join(
            f'<tr><td>{esc(d["day"])}</td><td>{esc(d["platform"])}</td><td>{esc(STATE_LABELS.get(d["status"], d["status"]))}</td>'
            f'<td>{open_link(d.get("url"))} {esc(d.get("error") or "")}</td></tr>'
            for d in self.store.deliveries(limit=40))
        redirects = "".join(f'<li><strong>{esc(label)}:</strong> <code>{esc(cfg.redirect_uri(name))}</code></li>'
                            for name, (label, _, _) in oauth.CONNECTIONS.items()) if cfg.public_url else ""
        body = f"""
<header><h1>TestDay Social</h1>
<p class="muted">{esc(status["day"])} · posting time {esc(status["postTime"])} ({esc(status["timezone"])}) · daily posting <strong>{"ON" if status["postingEnabled"] else "OFF"}</strong></p></header>
{"".join(f'<p class="notice">{esc(n)}</p>' for n in notices)}
<section><h2>Today's post</h2>
<div class="today"><div><img src="/preview/{esc(status["day"])}/card.jpg" alt="Today's picture" width="270" height="338">
<video src="/preview/{esc(status["day"])}/video.mp4" controls preload="none" width="190" height="338" poster=""></video></div>
<div><p class="muted">{esc(KIND_LABELS.get(post.kind, post.kind))} · {esc(post.item_id)}</p><h3>{esc(post.title)}</h3>
<pre>{esc(bank.caption(post, "facebook", cfg.link("facebook")))}</pre></div></div></section>
<section><h2>Platforms</h2><table><thead><tr><th>Platform</th><th>Posts</th><th>Today</th><th></th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<pre id="out" class="out" hidden></pre></section>
<section><h2>Next 14 days</h2><table><tbody>{upcoming}</tbody></table></section>
<section><h2>History</h2><table><tbody>{history or '<tr><td class="muted">Nothing posted yet.</td></tr>'}</tbody></table></section>
{f'<section><h2>Redirect addresses</h2><p class="muted">Register these in each platform’s app settings.</p><ul>{redirects}</ul></section>' if redirects else ""}
<script nonce="{nonce}">
const post = (path, body) => fetch(path, {{method: "POST", headers: {{"Content-Type": "application/json", "X-TestDay": "1"}}, body: JSON.stringify(body)}}).then((r) => r.json());
const out = document.getElementById("out");
document.addEventListener("click", async (e) => {{
  const b = e.target.closest("button"); if (!b) return;
  if (b.dataset.run) {{
    const dry = b.dataset.dry === "1";
    if (!dry && !confirm("Post today's post to " + b.dataset.run + " now?")) return;
    b.disabled = true; out.hidden = false; out.textContent = "Working… (a video can take a minute)";
    const r = await post("/api/run", {{platform: b.dataset.run, dryRun: dry}}).catch((x) => ({{error: String(x)}}));
    out.textContent = JSON.stringify(r, null, 2); b.disabled = false;
    if (!dry) setTimeout(() => location.reload(), 1500);
  }} else if (b.dataset.retry) {{
    await post("/api/retry", {{day: b.dataset.day, platform: b.dataset.retry}}); location.reload();
  }} else if (b.dataset.disconnect) {{
    if (confirm("Disconnect " + b.dataset.disconnect + "?")) {{ await post("/api/disconnect", {{name: b.dataset.disconnect}}); location.reload(); }}
  }}
}});
</script>"""
        return page("TestDay Social", body, wide=True)


STYLE = """
:root{--ground:#e9e8e2;--ink:#0f1a30;--muted:#5d677c;--rule:#c9c8c0;--card:#f4f3ee}
*{box-sizing:border-box}body{margin:0;background:var(--ground);color:var(--ink);font:16px/1.5 "Schibsted Grotesk",system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:980px;margin:0 auto;padding:32px 16px 64px}h1{font-size:2rem;margin:0}h2{font-size:1.15rem;margin:36px 0 10px}h3{margin:.2rem 0 .6rem}
.muted{color:var(--muted);font-size:.9rem}.notice{background:#f6e7b6;border:1px solid #d9c37a;padding:10px 14px;border-radius:10px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--rule);border-radius:10px;overflow:hidden}
td,th{padding:10px 12px;border-bottom:1px solid var(--rule);text-align:left;vertical-align:top;font-size:.95rem}th{color:var(--muted);font-weight:600}
.act{display:flex;gap:8px;flex-wrap:wrap}button,.btn{font:inherit;font-size:.9rem;padding:6px 14px;border:1px solid var(--ink);background:transparent;color:var(--ink);border-radius:999px;cursor:pointer;text-decoration:none}
button.primary{background:var(--ink);color:var(--ground)}button:disabled{opacity:.5}.err{color:#a02c1c;font-size:.85rem;margin-top:4px}
.today{display:flex;gap:20px;flex-wrap:wrap}.today>div:first-child{display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap}.today>div:last-child{min-width:0;flex:1 1 300px}
img,video{border-radius:8px;border:1px solid var(--rule);background:#fff;max-width:100%;height:auto}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--rule);padding:12px;border-radius:10px;font:inherit;font-size:.9rem;max-width:100%}.out{font:12px/1.4 ui-monospace,monospace}
@media (max-width:640px){td,th{padding:8px}table{display:block;overflow-x:auto}}
code{background:var(--card);padding:2px 6px;border-radius:6px}.ok{color:#1d6b3a}.bad{color:#a02c1c}a{color:var(--ink)}
"""


def page(title, body, wide=False):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="robots" content="noindex"><title>{esc(title)}</title><style>{STYLE}</style></head><body><main>{body}</main></body></html>')


def make_app(cfg, store, runner, tick):
    return tornado.web.Application([
        (r"/healthz", Health),
        (r"/", Dashboard),
        (r"/api/status", Status),
        (r"/api/run", Run),
        (r"/api/retry", Retry),
        (r"/api/disconnect", Disconnect),
        (r"/api/run-daily", RunDaily),
        (r"/media/(.*)", Media, {"path": "/"}),
        (r"/preview/(\d{4}-\d{2}-\d{2})/(card\.jpg|video\.mp4)", Preview),
        (r"/connect/([a-z]+)", Connect),
        (r"/oauth/([a-z]+)/callback", Callback),
    ], cfg=cfg, store=store, runner=runner, tick=tick)
