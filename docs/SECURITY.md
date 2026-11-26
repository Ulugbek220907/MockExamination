# Keeping TestDay up and its bills small

People who "take a startup down for fun" rarely break in. They do something cheaper: they repeat one request
thousands of times until a free allowance runs out (emails, database space, storage, bandwidth, AI credit) or the
server is too busy to answer. This page lists what was checked (26 November 2026), what the code does about it, and
the switches on Render and Cloudflare that only the owner can turn.

## What the code protects (mockexam/guard.py, ai_usage.py, ai_safety.py)

| Attack | What it would cost or break | Limit in the code (environment variable, default) |
|---|---|---|
| Ask for sign-in codes to random emails | The email service's day allowance (free plan: 100 a day), so real people cannot sign in; bounces hurt the domain | 10 codes an hour per address, 5 per email; `SIGNIN_EMAILS_PER_DAY` (90) for the whole site, after which people are asked to use Google; optional robot check (Cloudflare Turnstile) |
| Guess a sign-in code | An account | 6 digits, stored hashed, used once, 10 minutes, 5 tries per code, 10 checks per email in 15 minutes, 40 per address an hour |
| Send test answers in a loop (no account needed) | Database rows (the free database is 500 MB) | `SUBMITS_PER_USER_PER_HOUR` (30) signed in, `SUBMITS_PER_IP_PER_HOUR` (120: a school class shares one address) signed out; `ANON_SAVES_PER_DAY` (2000) signed-out results saved a day (results are always shown) |
| Upload recordings in a loop | Storage (free: 1 GB) and memory | 4 MB per answer, 8 tests and `SPEAKING_UPLOAD_MB_PER_DAY` (80) per person a day, `SPEAKING_UPLOAD_GB_PER_DAY` (3) for the site, `UPLOADS_AT_ONCE` (24) at the same moment |
| Play a recording again and again | Storage downloads (free: 5 GB a month; then the whole project is restricted) | the last 48 MB of recordings kept in memory; `RECORDING_FETCHES_PER_USER_PER_HOUR` (600) |
| Download Listening audio again and again | Bandwidth (Render free workspace: 5 GB a month, then $0.15 per GB) | `AUDIO_MB_PER_IP_PER_HOUR` (400); Cloudflare's cache (below) serves repeats at no cost |
| Use the AI examiner from many new accounts | AI credit | a free account gets one Writing and one Speaking marking, ever; `AI_FREE_WRITING_PER_DAY` / `AI_FREE_SPEAKING_PER_DAY` for all free accounts together; spending net per person (docs/COSTS.md) |
| Trick the AI examiner | Fake bands, bad feedback | docs/AI_SAFETY.md |
| Feedback form / analytics in a loop | Owner's inbox, database | 5 messages an hour per address and `FEEDBACK_PER_DAY` (100); 120 events per 10 minutes and `EVENTS_PER_DAY` (30000) |
| Start payments in a loop | Database rows | `ORDERS_PER_USER_PER_HOUR` (12) |
| Slow text | CPU: one request blocking everyone | every pattern used on scripts is bounded (a page of blank lines took 10 seconds before this check; now under 50 ms), with a test |
| IPv6 address hopping | Getting around per-address limits (a home has 18 quintillion addresses) | addresses are counted per /64 network |

Already in place before this check, and re-checked: sign-in cookies are signed, HttpOnly, Secure and SameSite;
requests from other sites are refused (Fetch Metadata, Origin, JSON only); a strict Content-Security-Policy and
the other security headers on every answer; payment webhooks are verified (Dodo signature with a 5-minute window,
Click signature, Payme login), all compared in constant time; prices come from the server only; recordings are
served only to their owner, the examiner marking them, or an admin; the admin pages need an admin account or the
admin token (compared in constant time); errors never show internals; no secrets are in the repository; the browser
never gets a database key.

## Second opinion (26 November 2026)

The security-relevant code (sign-in, sessions, every API handler, uploads, payments, file serving) was also given to
an uncensored model (Venice's Dolphin Mistral 24B, through OpenRouter) acting as an attacker. It listed 36 issues,
most of them "critical" or "high". Each was checked against the code; none is real:

- "Change the user id inside the session cookie": the cookie is signed, a changed one is not accepted.
- "Fake X-Forwarded-For to dodge the limits": only the last address, added by Render's own proxy, is used.
- "Read another student's Speaking test, recording or order by guessing its number" (about 20 variants): every one
  of these checks that the viewer owns it, marks it as its examiner, or is an admin; otherwise "not found".
- "Admin pages" (several variants): all need an admin account or the admin token.
- "Turn on AUTH_DEV_CODES": an environment setting only the owner can change, and the server refuses to start with it
  on the live site. "Path traversal in /audio/": Tornado's file handler keeps requests inside the site folder.
  "No HTTPS": Render forces HTTPS and the site sends HSTS.

Each claimed attack is now a test that tries it against the server (`AttackClaimsTests` in scripts/test_app.py).
A model saying "critical" is not evidence: check the code, then keep the check as a test.

## What only you can switch on (in this order)

1. **Two-factor sign-in everywhere.** Your Google account (it receives the admin sign-in codes: whoever reads that
   inbox is the admin), GitHub, Render, Supabase, Dodo, the Click cabinet, OpenRouter, Resend, Cloudflare and the
   domain registrar. Most "hacks" of small sites are a stolen password to one of these.
2. **A spending limit on the OpenRouter key** used by the site (OpenRouter → Keys → the key → credit limit, for
   example $30 a month). If everything else failed, this still caps the AI bill. Delete the key used for the model
   test once you have checked the results.
3. **Cloudflare in front of testday.uz** (free plan): it hides the server, absorbs floods, and caches the Listening
   audio so Render's bandwidth is not used for repeats.
   - Add the site to Cloudflare, move the nameservers, keep the DNS records, turn the orange cloud on for `testday.uz`
     and `www`. SSL/TLS mode: **Full (strict)**.
   - On Render, set `TRUST_CLOUDFLARE=1` (so limits count the visitor, not Cloudflare).
   - Security → WAF: turn on the free managed rules. Add one **rate-limiting rule**: path starts with `/api/`,
     more than 100 requests in 10 seconds from one address → block for 10 minutes.
   - Caching → Cache Rules: "Cache everything" for `/audio/examiners/*`, `/css/*`, `/js/*`, `/img/*` (respect the
     origin's cache headers).
   - Do **not** turn on "Bot Fight Mode" or "Under Attack" for the whole site: they would stop Click, Payme and Dodo
     from reaching `/api/pay/...`. If you ever need "Under Attack", add a Configuration Rule that sets the security
     level to "Essentially off" for paths starting with `/api/pay/` first.
   - Optional, strongest: Rules → Transform Rules → add a request header `X-Origin-Secret` with a long random value,
     and set the same value as `ORIGIN_SECRET` on Render. The server then refuses anyone who goes around Cloudflare
     to `testday.onrender.com`.
4. **A robot check on sign-in** (optional; free): Cloudflare → Turnstile → add a widget for `testday.uz` and
   `www.testday.uz`, mode "Managed". Put the site key in `TURNSTILE_SITE_KEY` and the secret in
   `TURNSTILE_SECRET_KEY` on Render. Most people never see it; scripts asking for codes are stopped.
5. **Backups.** The free database plan has no backups you can restore. Move to Supabase Pro when you have paying
   students (daily backups for 7 days), or export the database once a week.
6. **An uptime alert** (free, e.g. UptimeRobot) on `https://www.testday.uz/healthz`, so you hear about an outage
   before your students do.
7. **Suspend `testday-social`** on Render while you post the shorts by hand: it costs $7 a month and is one more
   public login page.

## When something happens

- Site slow or down, many requests in the Render log from a few addresses: turn on the Cloudflare rate-limiting rule
  (or "Under Attack" with the `/api/pay/` exception above).
- "Sign-in by email code is busy today": someone used up the day's emails; Google sign-in still works. Turn on
  Turnstile (step 4). Raise `SIGNIN_EMAILS_PER_DAY` only if your Resend plan allows more.
- AI bill growing: Admin → AI shows who used what; the OpenRouter key limit (step 2) is the last line.
- A secret leaked (a screenshot, a chat): create a new one at the service, put it on Render, delete the old one.
