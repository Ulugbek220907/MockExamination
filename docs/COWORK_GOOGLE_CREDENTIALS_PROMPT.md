# Prompt for Claude Cowork: get TestDay's Google credentials

**How to use it.** Open Claude Cowork on the computer where your browser is already signed in to Google (the account that
should own the project) and to Render. Let it use your browser, then paste everything below the line.

What you get: the **Client ID** for "Continue with Google" on the website (the website needs *only* the Client ID, no
secret), and, if you say yes to the optional job, a **Client ID and Client secret** for the social poster that uploads
YouTube Shorts. Cowork puts them into Render for you, or stops and lets you paste the secret yourself.

---

You are helping me set up Google sign-in credentials for my website **TestDay** (https://www.testday.uz, an IELTS practice
site hosted on Render). Work in my browser, in my own accounts, step by step. Be careful and slow rather than fast.

## What I need

| Job | What | Where the values go |
|---|---|---|
| **A** (needed) | A Google OAuth *Web application* client for **"Continue with Google" sign-in**. Only the **Client ID** is used. There is no secret to copy for this job. | Render, the **website** service (called `testday`), variable `GOOGLE_CLIENT_ID` |
| **B** (optional, only if I say yes) | A second OAuth *Web application* client for the **social poster** (uploads YouTube Shorts). It needs the **Client ID and the Client secret**. | Render, the **poster** service (called `testday-social`), variables `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` |

Use **two separate Google Cloud projects**: `TestDay` for Job A and `TestDay Social` for Job B. This keeps the YouTube
permission, which Google treats as sensitive, away from my students' sign-in.

## Rules you must follow

1. **Passwords and verification.** Never type or ask for my passwords. If Google or Render asks me to sign in, for a
   2-step code, a captcha, a phone or ID check, stop and tell me, and wait until I say it is done.
2. **Secrets.** The only secret in this task is the Job B **client secret** (also treat Render's values and the poster's
   admin password as secret). Never write a secret in your messages, in a file, in notes or in a summary. Do not repeat it
   even if you can see it on screen. Move it from Google to Render with copy and paste only. The **Client ID is not
   secret**; you may show it.
3. **Ask before the two production steps.** Stop and wait for my "go" before (a) pressing **Publish app** on the consent
   screen and (b) pressing **Save** on Render environment variables (that redeploys my live site). Before each, show me a
   short list of what you are about to do.
4. **No money, no extras.** Never enable billing, start a free trial, create a paid resource or accept an upsell. OAuth
   clients need none of that; if a page insists, stop and ask me.
5. **Stay in scope.** Do not change any other project, service, domain, email or setting. Do not upload a logo to the consent
   screen (that forces a review). If an optional field makes Google demand a review, leave it empty and tell me.
6. **If the screen does not match this prompt** (Google renames things often), find the equivalent. If you are not sure,
   stop and ask me instead of guessing.

## Step 0: ask me these questions in one message, then wait

1. Is Chrome signed in to the Google account that should own the project? (Tell me which email you see in the top-right
   corner so I can confirm it.)
2. Which addresses serve the site? Default: `https://www.testday.uz` and `https://testday.uz`. Also read the website
   service's own Render address (`https://<name>.onrender.com`) from the Render dashboard and tell me what you found.
3. Do I want **Job B** (the YouTube poster)? If yes, read the poster service's Render address
   (probably `https://testday-social.onrender.com`).
4. For the Job B secret: should you paste it into Render yourself, or will I do that step? (If I choose to do it myself,
   stop at that step and tell me exactly where to click.)

## Job A: Google sign-in client (Client ID only)

1. Open https://console.cloud.google.com/projectcreate . Create a project named **TestDay**. If I already have a project
   with that name, ask me whether to reuse it. Make sure it is selected in the project picker afterwards.
2. Open **Google Auth Platform** (https://console.cloud.google.com/auth/overview) and press **Get started**:
   - App name: **TestDay**. User support email: the Google account's own email (the one I confirmed).
   - Audience: **External**.
   - Contact email: the same email. Accept the user-data policy, then **Create**.
3. **Branding**: authorized domain `testday.uz`; home page `https://www.testday.uz`. If the site's privacy and terms pages
   are asked for, use `https://www.testday.uz/#/privacy` and `https://www.testday.uz/#/terms`. No logo.
4. **Data Access**: the scopes must be only `openid`, `.../auth/userinfo.email` and `.../auth/userinfo.profile`
   (the defaults). Add nothing else.
5. **Clients** -> **Create client**:
   - Application type: **Web application**. Name: `TestDay website`.
   - **Authorized JavaScript origins**: add each of these, exactly, with no path and no trailing slash:
     `https://www.testday.uz`, `https://testday.uz`, and the website service's Render address from Step 0.
   - **Authorized redirect URIs**: leave empty (sign-in does not use any).
   - **Create**. Copy the **Client ID** (it ends in `.apps.googleusercontent.com`). Ignore the client secret: it is not
     used and you must not copy it.
6. **Audience** -> press **Publish app** so the status is **In production**. (In *Testing* only people I list can sign in.)
   **Ask me for "go" first** (rule 3a).
7. In Render open the **website** service -> **Environment** -> add `GOOGLE_CLIENT_ID` = the Client ID (or edit it if it
   exists). **Ask me for "go"** (rule 3b), press **Save**, and wait for the deploy to finish (a few minutes).
8. Check: open `https://www.testday.uz/api/config` . The text must contain `"googleClientId": "<the Client ID>"`. Then open
   the site, press **Sign in**, and confirm that Google's own **Continue with Google** button appears and that there is no
   `origin_mismatch` error. Do **not** sign in to anything; you only check that the button is there.

## Job B (only if I said yes): YouTube poster client (Client ID and secret)

1. Create a second project named **TestDay Social** (same way as Job A, step 1).
2. **APIs & Services -> Library**: find **YouTube Data API v3** and press **Enable**.
3. **Google Auth Platform** -> Get started (App name `TestDay Social`, External, my email). In **Data Access** add the
   scope `https://www.googleapis.com/auth/youtube.upload` (Google calls it sensitive; that is expected).
4. **Audience**: ask me for "go", then **Publish app** (**In production**). Reason: in *Testing*, Google ends the connection
   after 7 days. Google will show an "unverified app" screen the first time I connect my channel; that is fine for my own
   account.
5. **Clients** -> **Create client**: Web application, name `TestDay social poster`.
   - Authorized redirect URI (exact): `<the poster's Render address>/oauth/youtube/callback`
     (for example `https://testday-social.onrender.com/oauth/youtube/callback`). No JavaScript origin is needed.
   - **Create**. A dialog shows the **Client ID** and the **Client secret**. **Copy the secret now, before you close the
     dialog**: Google may never show it again. (If it is lost, add a new secret on the client's page.)
6. Render, the **poster** service -> **Environment**: set `GOOGLE_CLIENT_ID` = the Client ID and `GOOGLE_CLIENT_SECRET` =
   the secret, by paste only, following my answer to question 4 of Step 0. Ask me for "go", press **Save**, wait for the deploy.
7. Check: open the poster's admin page (its Render address; it asks for the admin password, which I will type myself).
   The YouTube row must offer **Connect**, and the redirect address listed at the bottom must match what you registered.
   Do not press Connect unless I ask you to.

## When you finish, report like this (no secrets)

- Job A: project name, the **Client ID**, consent screen status (should be *In production*), the origins you added, and
  whether `/api/config` and the Sign in button passed.
- Job B (if done): project name, the **Client ID**, the redirect URI you registered, and the words "secret stored in
  Render, not displayed" (never the secret itself).
- Anything that looked odd, any warning Google showed, and anything you skipped.

## If something goes wrong

- `origin_mismatch` or "The given origin is not allowed": an origin in Job A step 5 is missing or has a typo. It must be
  exactly `https://` plus the host, nothing else. Fix it, wait a minute, retry.
- `redirect_uri_mismatch` (Job B): the registered URI must equal the poster's address plus `/oauth/youtube/callback`,
  character for character.
- "Access blocked: app has not completed verification" or "not authorized": the app is still in *Testing*; publish it
  (after my "go") or add my email as a test user.
- Google shows "The given client ID is not found" on the button: the Client ID in Render has a typo or an extra space.
- The website still shows no Google button after the deploy: confirm the variable is on the **website** service (not the
  poster), then wait for the deploy to finish and reload with the cache cleared.
