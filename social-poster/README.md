# TestDay social poster

A small web service, **separate from the testday.uz website**, that posts one TestDay post a day to
**YouTube (Shorts), TikTok, Instagram (Reels), Threads and Facebook (Reels)**. It makes the post itself:
a picture and a short vertical video in TestDay's look, with a caption that ends with a link to testday.uz.

It lives in the `social-poster/` folder of this repository and deploys to Render as its own service.
Nothing in it is used by the website, and the website's deploy ignores it.

## What it posts

One post a day, always the same for a given date, so the admin page can show the next two weeks.

| Day | Post | Source |
|---|---|---|
| Monday, Friday | Word of the day: meaning, example, a phrase it goes with | 62 words in `scripts/build_bank.py` |
| Tuesday | Speaking Part 2 cue card, with the one-minute preparation | TestDay's own Speaking tests |
| Wednesday, Saturday | An IELTS tip for Listening, Reading, Writing or Speaking | 34 tips in `scripts/build_bank.py` |
| Thursday | A Writing Task 2 question | TestDay's own Writing tests |
| Sunday | About TestDay: five free full tests in every module | 6 notes in `scripts/build_bank.py` |

Nothing repeats until a pool is used up (about seven months for the words). To add your own words, tips or
notes, edit the lists in `scripts/build_bank.py`, run `python scripts/build_bank.py` in the repository and
commit the new `data/bank.json`.

## Put it on Render

1. In Render choose **New + → Blueprint**, pick this repository, and set the blueprint path to
   `social-poster/render.yaml`. This creates the service `testday-social` (Starter plan, with a 1 GB disk).
   Render asks for the settings marked `sync: false`; you can leave the platform keys empty for now.
2. When it has deployed, copy its address (for example `https://testday-social.onrender.com`) into the
   setting **PUBLIC_URL**. Instagram and Threads fetch the picture and video from this address, and the
   Connect buttons need it.
3. Open the address. The user name is anything; the password is the **ADMIN_PASSWORD** that Render generated
   (Environment tab).
4. Connect each platform (next section), try **Dry run** and then **Post now** on each, and when you are
   happy set **POSTING_ENABLED=1**. From then on the service posts every day at `POST_TIME` (10:00 Tashkent
   time) and, if it was asleep or a platform was down at that time, catches up later the same day.

Why Starter and a disk: the service has to be awake at posting time, and it must remember what it has
posted. Without a disk a redeploy forgets that, and the day could be posted twice. If you must use the
free plan, point a free timer (for example cron-job.org) at `https://…/api/run-daily?token=<CRON_TOKEN>`
every ten minutes to wake it, and accept that a redeploy can forget what was posted.

## Connect the platforms

Each platform needs an app that you register with it, once. On the admin page, **Connect** then signs in
and saves the tokens; they are renewed by the service. Register the **redirect addresses** shown at the
bottom of the admin page in each app. You can use only some platforms: one with no connection is skipped
(or list the ones you want in `PLATFORMS`).

| Platform | Register at | Settings to add | Good to know |
|---|---|---|---|
| YouTube | Google Cloud Console: a project, **YouTube Data API v3**, an OAuth client of type *Web application*; the scope is `youtube.upload` | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Set the consent screen to *In production*: in *Testing* Google ends the sign-in after 7 days. An upload costs 1,600 of the 10,000 daily quota units. If videos arrive as private, the project needs Google's API compliance audit. |
| TikTok | developers.tiktok.com: an app with **Login Kit** and **Content Posting API**, scopes `user.info.basic` and `video.publish` | `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` | Until TikTok audits the app, it can only post **private** videos. The service uses `SELF_ONLY`; after the audit set `TIKTOK_PRIVACY=PUBLIC_TO_EVERYONE`. |
| Threads | developers.facebook.com: an app with the **Threads** use case; add your Threads account as a tester; scopes `threads_basic`, `threads_content_publish` | `THREADS_APP_ID`, `THREADS_APP_SECRET` | The token lasts 60 days and the service renews it, so the service must run at least once every two months. |
| Facebook and Instagram | developers.facebook.com: a Business app with **Facebook Login**; scopes `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish` | `META_APP_ID`, `META_APP_SECRET` | The Instagram account must be a **professional** (Business or Creator) account linked to the Facebook Page. While the app is in development mode it works for the accounts that have a role in the app, which is all you need. One Connect covers both. |

If you would rather not use the Connect buttons, a platform also accepts its keys as settings:
`YOUTUBE_REFRESH_TOKEN`, `TIKTOK_REFRESH_TOKEN`, `THREADS_ACCESS_TOKEN` with `THREADS_USER_ID`, and
`META_PAGE_TOKEN` with `FACEBOOK_PAGE_ID` and `INSTAGRAM_USER_ID`.

## How it stays safe

- **Each day is posted at most once per platform.** A post is marked *Posting…* before the request is sent.
  If a request may have gone through but its answer was lost (the connection dropped after the platform
  accepted it), it is marked **Check the platform** and is never retried by itself; look at the platform,
  then press *Clear, post again* if it did not go out.
- A failure that retrying could fix is tried again after `RETRY_MINUTES` (20), up to `MAX_ATTEMPTS` (3)
  times. A failure that cannot be fixed by trying again (a refused permission) is shown on the admin page.
- One platform failing never stops the others.
- The admin page needs the password. The pictures and videos are public only under a secret, unguessable
  address, which is what Instagram and Threads need in order to fetch them. Old files are deleted after
  `KEEP_MEDIA_DAYS` (7).
- Tokens are saved in the service's own database on the disk, not in the repository.
- Everything goes through the platforms' official APIs, using your own accounts.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `POSTING_ENABLED` | `0` | The daily schedule posts only when this is `1`. The buttons on the admin page always work. |
| `POST_TIME`, `TIMEZONE` | `10:00`, `Asia/Tashkent` | When the day's post goes out. |
| `PLATFORMS` | all five | Comma-separated list, for example `youtube,threads`. |
| `PUBLIC_URL` | (none) | This service's address. Needed for Instagram, Threads and Connect. |
| `SITE_URL` | `https://www.testday.uz` | The link in every caption (tagged with the platform, so the site's visits show where they came from). |
| `ADMIN_PASSWORD` | (none) | Without it nobody can open the admin page. |
| `CRON_TOKEN` | (none) | Lets an outside timer call `/api/run-daily?token=…`. |
| `SECRET_KEY` | random | Signs the Connect links; set it so a restart does not break a sign-in in progress. |
| `YOUTUBE_PRIVACY`, `TIKTOK_PRIVACY` | `public`, `SELF_ONLY` | How the video is posted. |
| `EXTRA_HASHTAGS` | `Uzbekistan` | Added to every post. |
| `DATA_DIR` | `runtime/` (`/var/data` on Render) | The database and the day's files. Put it on a disk. |

## Run it on your computer

```bash
cd social-poster
pip install -r requirements.txt
ADMIN_PASSWORD=pw python app.py        # http://localhost:10000, user name anything, password pw
python -m unittest discover -s tests -t .
```

No ffmpeg install is needed: the `imageio-ffmpeg` package carries one.

## What has and has not been tested

The tests (53, run in CI) check the weekly plan and every caption's length for two years ahead, the picture
and the video that are made (size, format, length), each platform's request sequence against a fake, token
refresh, the once-only and retry rules, the admin page, the sign-in links and the secret media address. A
run against local stand-ins for Threads, Instagram and Facebook also fetched the real picture and video over
HTTP, as the platforms do.

It has **not** been run against the real platforms, which needs your accounts. The requests follow each
platform's published API documentation, but expect that the first real post on a platform may show a
detail to adjust (a permission, an app setting). Do it one platform at a time with **Dry run** and
**Post now** before switching on `POSTING_ENABLED`. Platform rules also change, in particular TikTok's
audit for public posts, Instagram's and Facebook's app permissions, and Google's compliance audit.
