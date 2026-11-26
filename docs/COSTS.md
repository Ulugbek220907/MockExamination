# What TestDay costs to run, and what each pass earns

The allowances in `mockexam/ai_usage.py`, the models in `mockexam/ai.py` (`STEP_MODELS`) and the prices in
`mockexam/billing.py` (`PLAN_PRICES`) are set from the numbers below (26 November 2026). **Admin → AI** shows what
marking really cost in the last 30 days, job by job, and how much recording storage is in use: replace these
estimates with real averages after a few weeks.

## 1. Fixed costs (every month, with or without students)

| Service | Now | When it must change | Then |
|---|---|---|---|
| Render, the website (`testday`, Starter) | $7 | more than ~150 students at once, or slow pages | $25 (1 CPU) |
| Render, the social poster (`testday-social`) | $7 + $0.25 disk | not needed while shorts are posted by hand: **suspend it** | $0 |
| Render bandwidth | 5 GB a month free (Hobby workspace) | Listening audio is ~7 MB per test; recordings played back | $0.15 per GB, or ~$0 behind Cloudflare's cache (docs/SECURITY.md) |
| Supabase (database, recordings) | Free: 500 MB database, **1 GB files**, 5 GB downloads | **an AI Speaking test stores ~19 MB of recordings for 30 days: the free plan holds about 50 tests**, and each AI review downloads them once | Pro $25: 8 GB database, 100 GB files, 250 GB downloads, daily backups |
| Resend (sign-in emails) | Free: 100 emails a day | more than ~90 sign-ins by email a day (Google sign-in sends none) | Pro $20: 50 000 a month |
| Domain | ~$1 a month | | |
| OpenRouter | pay as you go, +5.5% on each top-up | | |

So: **about $8–15 a month now**, and **about $55–60 a month** once Speaking sells (Supabase Pro and, with growth,
Resend Pro). Supabase Pro is the first one you will need: watch "Speaking recordings stored now" in Admin → AI.

## 2. The AI models (tested 26 November 2026)

Tested with the site's own prompts, on: 8 recordings of non-native English speakers with human pronunciation scores
(speechocean762, read speech, 30–70 seconds each), the 12 official IELTS Speaking samples on ielts.org with their
examiner bands (5.0 to 9.0; transcripts only), and 5 Task 2 essays (no examiner bands were available; compared with
the current model). Total cost of the test: $0.82.

**Listening to each Speaking answer** (audio; about 20 calls per test):

| Model | Words wrong | Pronunciation vs human (r) | Cost per answer | Time | Problems |
|---|---|---|---|---|---|
| Gemini 3.8 Flash (before) | 18.7% | 0.94 | $0.0043 | 6 s | its safety filter blocked a harmless clip (not every time) |
| **Gemini 3.1 Flash-Lite (now)** | 21.7% | 0.89 | **$0.0019** | **3 s** | none |
| Gemini 2.5 Flash-Lite | 33.9% | 0.76 | $0.0015 | 10 s | mishears accented speech |
| Qwen3.8 Omni Flash | 20.8% | 0.98 | $0.0010 | 26 s | ignored the answer format 2 times in 9; one provider (Alibaba) |
| MiMo v2.6 Flash | 22.9% | 0.88 | $0.0006 | 35–50 s | too slow |
| Muse Ember | 33.9% | 0.92 | $0.0009 | 5 s | mishears |
| Voxtral Small | — | — | $0.003–0.005 | 3 s | audio is priced high |
| DeepSeek V4.1 Flash | cannot hear audio | | | | |
| Gemini 2.5 Flash | retired on 1 December 2026 | | | | |

Round 2 (the same 8 recordings): Gemini 3.5 Flash-Lite 22.7% / 0.86 / $0.0021 (no better than 3.1, a little dearer);
Perceptron Mk1.5 34% and broken answers; GPT-Audio-Mini refused the structured answer with audio; Nemotron Nano Omni
(free) is not allowed by our data policy (free endpoints keep data); 3.1 Flash-Lite with shortened instructions saved
only 11% and lost some accuracy (r 0.84). Amazon Nova 2 Omni is not on OpenRouter.

Outside OpenRouter (prices from the providers, November 2026): Azure pronunciation assessment about $1–1.32 an hour
(~$0.20 a test); SpeechSuper about $0.006 an answer (~$0.12 a test); Groq Whisper speech-to-text $0.04 an hour, but it
cleans away fillers and pauses and does not judge pronunciation. Listening with Gemini 3.1 Flash-Lite (~$0.03 a test,
pronunciation included) is cheaper than all of them.

("Words wrong" includes the speakers' own reading slips, so compare the models with each other.)

**Rating the whole Speaking test** (text: transcripts and listening notes; one call per test), against the official
examiner bands of the 12 IELTS samples:

| Model | Off by (average) | Bias | Within half a band | Ranking (r) | Cost per test | Time |
|---|---|---|---|---|---|---|
| Gemini 3.8 Flash, old prompt | 1.00 | −1.00 | 3 of 12 | 0.86 | $0.014 | 27 s |
| **Gemini 3.8 Flash, calibrated prompt (now)** | **0.68** | −0.68 | 5 of 11 | **0.93** | $0.013 | 23 s |
| DeepSeek V4.1 Flash | 0.80 | −0.80 | 5 of 10 | 0.85 | $0.004 | 44 s |
| Gemini 3.1 Flash-Lite, calibrated prompt | 1.21 | −1.21 | 4 of 12 | 0.87 | $0.003 | 5 s |
| Qwen3.8 Omni Flash | 0.93 | −0.93 | 2 of 7 | 0.76 | $0.003 | 63 s |
| Claude Haiku 5.5 | 1.50 | −1.42 | 2 of 12 | 0.62 | $0.003 | 19 s |
| GPT-5.6 Luna | 1.58 | −1.58 | 1 of 12 | 0.73 | $0.003 | 18 s |
| Muse Ember | 1.79 | −1.79 | 1 of 12 | 0.76 | $0.002 | 9 s |

Every model rated real candidates too low with the old prompt ("most candidates score 5 to 7", "fully fits"), so the
prompt was recalibrated. A small low bias remains, mostly for the strongest candidates (bands 8–9), partly because
the test had no audio. To calibrate further, have a teacher or examiner rate 20–30 real TestDay tests and compare.

**Marking Writing** (text; one call per task): Gemini 3.1 Flash-Lite gave the same band as Gemini 3.8 Flash on 17 of
20 criteria and was never more than one band apart (average difference −0.05), at $0.0027 a task instead of $0.0103
and in 5 s instead of 17 s. DeepSeek V4.1 Flash ($0.0023) and GPT-5.6 Luna ($0.0018) agreed on 15 of 20; Claude Haiku
5.5 marked about one band lower. **Now: Gemini 3.1 Flash-Lite**, with Gemini 3.8 Flash as the fallback.

Each step can be switched on Render without a code change: `AI_MODEL_LISTEN`, `AI_MODEL_RATE`, `AI_MODEL_WRITING`,
`AI_MODEL_FALLBACK` (the model tried once when the chosen one keeps failing).

## 3. One job

| Job | Before (all Gemini 3.8 Flash) | Now |
|---|---|---|
| Speaking test (~20 answers + the rating) | ~$0.11 | **~$0.05** (20 × $0.0016 + $0.02) |
| Writing script (Task 1 + Task 2) | ~$0.021 | **~$0.006** |

## 4. Allowances

| | Writing scripts | Speaking tests |
|---|---|---|
| A pass that covers the paper | 30 in any 30 days, 3 a day | **30 in any 30 days, 3 a day** (was 12) |
| A free account | **1, once** | **1, once** |
| Spending net per person per paper (30 days) | $2 | $3 |
| All free accounts together, a day | 40 | 15 |

Students practise Speaking more than Writing; with the cheaper listening model, 30 Speaking tests a month (one a day)
costs at most about $1.60 at full use.

## 5. What each pass earns (one month)

Net = price after the payment fee (Click assumed 2%; Dodo 4% + $0.40 + 1.5% foreign card + 0.5% subscription) and an
assumed 4% turnover tax. AI = the most a student can use in a month, with OpenRouter's 5.5% fee. At about 12 024 so'm
to the dollar.

| Pass | Price | Net (Click / Dodo) | AI at full use | Left at full use (Click / Dodo) |
|---|---|---|---|---|
| Listening + Reading | 39 000 so'm / $3.99 | $3.05 / $3.22 | $0 | $3.05 / $3.22 |
| Writing | 49 000 so'm / $4.99 | $3.83 / $4.12 | $0.19 | $3.64 / $3.93 |
| Speaking | 59 000 so'm / $5.99 | $4.61 / $5.02 | $1.59 | $3.02 / $3.43 |
| All-in-one | 79 000 so'm / $7.99 | $6.18 / $6.83 | $1.78 | $4.40 / $5.05 |

Most students use far less than the full allowance, so the real margin is higher.

**Break-even:** about 3–5 paying students cover today's fixed costs (~$8–15); about 15–20 cover the grown stack
(~$55–60, with Supabase Pro and Resend Pro).

## 6. When to change something

- Admin → AI shows an average above $0.08 per Speaking test or $0.01 per Writing script: check which model is in use
  (the Render log line at start-up names them) and whether the fallback is used often.
- "Speaking recordings stored now" near 800 MB: move Supabase to Pro, or lower `SPEAKING_KEEP_DAYS`.
- The dollar above 14 000 so'm: raise the so'm prices.
- Many "busy" refusals for free accounts: raise `AI_FREE_WRITING_PER_DAY` / `AI_FREE_SPEAKING_PER_DAY` if the budget allows.

Allowance settings: `WRITING_AI_PER_MONTH`, `WRITING_AI_PER_DAY`, `SPEAKING_AI_PER_MONTH`, `SPEAKING_AI_PER_DAY`,
`WRITING_AI_FREE_TOTAL`, `SPEAKING_AI_FREE_TOTAL`, `AI_FREE_WRITING_PER_DAY`, `AI_FREE_SPEAKING_PER_DAY`,
`AI_COST_CAP_WRITING_USD`, `AI_COST_CAP_SPEAKING_USD`.
