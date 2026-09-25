# Going live: step-by-step

> **Current setup (already done):** Supabase project `MockExamination` has the schema, the server secret hash and all tests. The Render service `ielts-mock-exam` has its environment variables set and deploys the `claude/loving-hamilton-ho09z6` branch automatically on every push. After merging that branch into `main`, switch the service back to `main` under **Render → ielts-mock-exam → Settings → Build & Deploy → Branch**.

The site runs with zero configuration, but for a public launch you want:

1. **Supabase**: stores content and every attempt permanently. Render's free disk is wiped on each deploy, so SQLite data would be lost.
2. **Anthropic API key** (optional but recommended): switches on the AI writing examiner.
3. **Render** (or any host that runs Python): serves the site.

Total time: about 30 minutes.

---

## 1. Supabase (database)

1. Create a free project at <https://supabase.com> (choose the region closest to your users).
2. In the dashboard open **SQL Editor → New query**, paste the whole of [`supabase/schema.sql`](supabase/schema.sql) and click **Run**.
   This creates three tables (`tests`, `reading_attempts`, `writing_submissions`) with Row Level Security **on and no public policies**, plus six `app_*` database functions that the server calls.
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

## 4. Before you announce the site

- [ ] Delete the withdrawn Cambridge files: `git rm data/tests.json data/attempts.db scripts/build_tests_data.py`
- [ ] Pick your brand name (`SITE_NAME`). Avoid putting "IELTS" in the domain name or logo, because the IELTS partners protect the trademark. Descriptive use in text ("IELTS-style practice") with the disclaimer is what the site does now.
- [ ] Set `CONTACT_EMAIL` so users can ask for their data to be deleted (shown on the About & legal page).
- [ ] If you target users in the EU/UK, get a proper privacy policy and cookie review. The site uses no cookies and no trackers, only local storage for autosave and preferences.
- [ ] Run `python scripts/test_app.py` and take one reading and one writing test on the live URL.

## Admin endpoints

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://your-site/api/admin/stats
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" https://your-site/api/admin/refresh
```

Browse attempts and essays in Supabase under **Table Editor**.
