# Going live: step-by-step

> **Current setup (already done):** Supabase project `MockExamination` has the schema (including the Listening and Speaking tables and the private `speaking` Storage bucket), the server secret hash and all tests. The Render service `ielts-mock-exam` has its environment variables set and deploys the `claude/loving-hamilton-ho09z6` branch automatically on every push. After merging that branch into `main`, switch the service back to `main` under **Render → ielts-mock-exam → Settings → Build & Deploy → Branch**.

The site runs with zero configuration, but for a public launch you want:

1. **Supabase**: stores content and every attempt permanently. Render's free disk is wiped on each deploy, so SQLite data would be lost.
2. **Anthropic API key** (optional but recommended): switches on the AI writing examiner.
3. **Render** (or any host that runs Python): serves the site.

Total time: about 30 minutes.

---

## 1. Supabase (database)

1. Create a free project at <https://supabase.com> (choose the region closest to your users).
2. In the dashboard open **SQL Editor → New query**, paste the whole of [`supabase/schema.sql`](supabase/schema.sql) and click **Run**.
   This creates the tables for tests, attempts, accounts, payments and examiner checks with Row Level Security **on**, plus the `app_*` database functions the server calls. The public key alone can read nothing; the server's requests carry the server secret, which the security policies check. Running the file again on an older database adds whatever is missing.
3. Create a server secret and store its hash:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"   # → SUPABASE_APP_SECRET
   ```

   Then in the SQL Editor (paste your secret in place of the placeholder):

   ```sql
   insert into private.app_secrets (name, secret_hash)
   values ('server', encode(sha256(convert_to('YOUR-SECRET', 'UTF8')), 'hex'))
   on conflict (name) do update set secret_hash = excluded.secret_hash;
   ```

4. Open **Project Settings → API** and copy the **Project URL** (`SUPABASE_URL`) and the **publishable** key (`SUPABASE_KEY`). The publishable key is safe to expose. On its own it can read nothing, because every function also requires the server secret. You never need the `service_role` key.
5. Upload the tests:

   ```bash
   SUPABASE_URL=https://xxxx.supabase.co \
   SUPABASE_KEY=sb_publishable_... \
   SUPABASE_APP_SECRET=your-secret \
   python scripts/seed_supabase.py
   ```

   The script validates every test first and refuses to upload broken content. Run it again whenever you add or edit a test, then call `POST /api/admin/refresh` (or wait 5 minutes) for the live site to pick up the change.

If Supabase is ever unreachable, the site keeps working using the bundled `content/` files.

## 2. AI writing examiner (Anthropic)

1. Create an API key at <https://console.anthropic.com> → **API Keys** and add billing credit.
2. Set `ANTHROPIC_API_KEY` on the server.
3. Optional tuning:
   - `ANTHROPIC_MODEL` defaults to `claude-opus-5` (most reliable marking). `claude-sonnet-5` is cheaper per script.
   - `AI_PER_IP_PER_HOUR` (default 6) and `AI_DAILY_LIMIT` (default 300) cap your spend. Each writing submission makes two model calls (Task 1 and Task 2).
   - Set a monthly spend limit in the Anthropic console as a hard safety net.

Without a key, writing submissions still get automatic checks, statistics and model answers. The site says clearly that AI marking is off.

## 3. Render (hosting)

1. Push this repository to GitHub.
2. In <https://dashboard.render.com> click **New + → Blueprint** and choose the repository. Render reads [`render.yaml`](render.yaml).
3. When prompted, fill in `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_APP_SECRET`, `ANTHROPIC_API_KEY` and `CONTACT_EMAIL`. `ADMIN_TOKEN` is generated for you; copy it from the Environment tab if you need the admin endpoints.
4. Click **Apply**. The health check is `/api/health`.
5. (Optional) **Settings → Custom Domains** to add your own domain. Render issues HTTPS automatically.

Free Render instances sleep after inactivity and take ~30 s to wake. Upgrade to a paid instance before promoting the site.

## 4. Accounts, the plan, payments and examiners

Test 1 of each module is free for everyone. Every other test (and its audio) needs the monthly plan, and students can pay per check for an examiner to mark their Writing. All of this is already built; these steps switch it on.

### 4.1 Sign-in (Supabase Auth)

In the Supabase dashboard:

1. **Authentication → URL Configuration**: set *Site URL* to `https://ielts-mock-exam.onrender.com` and add `https://ielts-mock-exam.onrender.com/auth-callback.html` under *Redirect URLs*.
2. **Authentication → Emails → Templates**: in both **Magic Link** and **Confirm signup**, add the code so students can type it:

   ```html
   <h2>Your sign-in code</h2>
   <p>Enter this code on the website: <strong>{{ .Token }}</strong></p>
   <p>Or <a href="{{ .ConfirmationURL }}">click here to sign in</a>.</p>
   ```
3. **Authentication → Emails → SMTP Settings**: connect an email service. Supabase's built-in email only reaches your own team's addresses.
   [Resend](https://resend.com) (3,000 emails a month free) and [Brevo](https://www.brevo.com) (300 a day free) both work: create an account, verify your domain, copy the SMTP host, port, user and password into Supabase, and set the sender to something like `no-reply@your-domain`.
   Then raise **Rate Limits → emails per hour** to fit your traffic.
4. **Google sign-in (optional)**:
   - In [Google Cloud Console](https://console.cloud.google.com/apis/credentials), create an *OAuth client ID* of type *Web application*.
   - Add `https://xlsdbilvhxmhmmolooac.supabase.co/auth/v1/callback` as an *Authorized redirect URI*.
   - Paste the client ID and secret into **Supabase → Authentication → Sign In / Providers → Google** and enable it.
   - The "Continue with Google" button appears automatically.

On Render, set `ADMIN_EMAILS` to your own email address. After you sign in with it you get the **Admin** page (`#/admin`).

### 4.2 Prices

Change prices with environment variables (in so'm): `PLAN_PRICE` (default 39000 a month), `WRITING_CHECK_PRICE` (10000), `SPEAKING_CHECK_PRICE` (20000). `PLAN_FIRST_BONUS_DAYS` (30) is the free extra month on a student's first payment.

### 4.3 Payments

The site offers every payment method that is configured:

- **Card transfer (works today)**:
  - Set `PAYMENT_CARD_NUMBER` and `PAYMENT_CARD_HOLDER`.
  - Students transfer the amount with the order number (for example `MX12`) in the comment, then press *I have paid*.
  - When the money arrives, you press **Confirm payment** under Admin → Payments to confirm.
- **Payme**:
  - Sign a merchant agreement at <https://business.payme.uz> and create a cash desk (*kassa*).
  - In the cash desk settings, set the endpoint to `https://ielts-mock-exam.onrender.com/api/pay/payme` and the account field to `order_id`.
  - Put the cash desk ID in `PAYME_MERCHANT_ID` and the key in `PAYME_KEY`. For testing, use the test key with `PAYME_TEST=1`, and run Payme's sandbox tests before going live.
  - If Payme asks for fiscal receipt details, add your MXIK code in `PAYME_IKPU` and the package code in `PAYME_PACKAGE_CODE`.
- **Click**:
  - Register a service at <https://merchant.click.uz>.
  - Set the *Prepare URL* to `https://ielts-mock-exam.onrender.com/api/pay/click/prepare` and the *Complete URL* to `…/api/pay/click/complete`.
  - Put the service ID, merchant ID and secret key in `CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID` and `CLICK_SECRET_KEY`.

Payments are idempotent: a repeated callback never grants the plan or a check twice. A Payme or Click cancellation of a paid order refunds it automatically (it removes the plan time or cancels a check that has not started). Admins can also refund from the Admin page.

### 4.4 Examiners

1. The examiner signs in to the site once (so their account exists).
2. You open **Admin → Examiners**, enter their email, name and headline, and tick *Approve now*.
3. The examiner opens **Examiner** in the menu, completes their profile, and marks checks from their queue.

Students choose an examiner on the results page of any Writing or Speaking test. Examiners choose what they mark (*I mark Writing* / *I mark Speaking*) on their profile. For a Speaking check the examiner plays the candidate's recordings next to the marking form. After a check is marked the student can rate the examiner once, and ratings are shown to other students. Pay your examiners outside the site; Admin → All orders lists every paid check and who marked it.

### 4.5 Speaking recordings

- Answers are recorded in the browser (Opus, about 32 kbit/s) and uploaded one by one while the test goes on. A full test is about 2 MB.
- They are stored in the private Supabase Storage bucket `speaking` (created by `supabase/schema.sql`). Like the tables, only requests with the server secret can read or write it. The free Supabase plan includes 1 GB of file storage, which holds roughly 400 full tests at a time.
- Recordings are deleted automatically after `SPEAKING_KEEP_DAYS` (default 60) days, but never while an examiner is still marking them. Unfinished tests are removed after 48 hours.
- Limits against abuse: `SPEAKING_TESTS_PER_DAY` (default 8) tests per student per day, and `SPEAKING_UPLOAD_MB_PER_DAY` (default 80) MB of audio per student per day. Each answer is at most 4 MB.
- Browsers only allow the microphone on `https://` sites (and `localhost`). Render provides HTTPS automatically.

### 4.6 Notifications (recommended)

Without these the site works, but you only see new payments and checks when you open the site. The menu shows a red counter
on **Admin** (payments to confirm) and **Examiner** (checks to mark) either way.

- **Emails** (students, examiners, and the addresses in `ADMIN_EMAILS`):
  - Create a free account at <https://resend.com>, add and verify your domain, and create an API key.
  - Set `RESEND_API_KEY` and `EMAIL_FROM` (for example `MockExam <noreply@your-domain.uz>`).
  - You can use the same Resend account as the SMTP sender for the sign-in codes (section 4.1).
  - Students get "payment received" and "your check is ready". Examiners get "new check for you". Admins get "card transfer to confirm".
- **Telegram** (instant messages to you):
  1. Talk to **@BotFather** in Telegram, send `/newbot`, and copy the token into `TELEGRAM_BOT_TOKEN`.
  2. Send any message to your new bot.
  3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy the `chat` → `id` number into `TELEGRAM_ADMIN_CHAT_ID`.
  4. You get a message for every card transfer to confirm, every Payme/Click payment and every new check.

## 5. Before you announce the site

- [ ] Delete the withdrawn Cambridge files: `git rm data/tests.json data/attempts.db scripts/build_tests_data.py`
- [ ] Pick your brand name (`SITE_NAME`). Avoid putting "IELTS" in the domain name or logo, because the IELTS partners protect the trademark. Descriptive use in text ("IELTS-style practice") with the disclaimer is what the site does now.
- [ ] Set `CONTACT_EMAIL` so users can ask for their data to be deleted (shown on the About & legal page).
- [ ] If you target users in the EU/UK, get a proper privacy policy and cookie review. The site uses one sign-in cookie and no trackers, plus local storage for autosave and preferences. Speaking recordings are personal data (a voice): the About page explains who can hear them and when they are deleted.
- [ ] Run `python scripts/test_app.py` and take one test of each module on the live URL (Speaking on a phone too).
- [ ] Sign in with your admin email, buy the plan once by card transfer and confirm it in Admin, then order and mark a Writing check and a Speaking check with a test examiner account.

## Admin endpoints

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://your-site/api/admin/stats
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" https://your-site/api/admin/refresh
```

Browse attempts and essays in Supabase under **Table Editor**.
