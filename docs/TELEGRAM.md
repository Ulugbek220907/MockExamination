# Telegram bots

Two bots, both run by the website itself (Telegram sends updates to the site; no extra service, no extra cost):

| Bot | What it does |
|---|---|
| **@testdayuzbot** (students) | `/start` menu; the **IELTS band calculator** (a Telegram widget that works inside the chat); **My results**, a widget with the latest band per paper, the overall estimate, the target and the days to the exam, refreshed whenever it comes on screen; messages when a **Speaking result is ready**, when a **pass ends within 3 days**, and **7 days and 1 day before the exam** (at 9:00 Tashkent time). Uzbek by default, Russian or English when the student's Telegram is in those languages. |
| **@testdaysupportbot** (support) | A student writes (text, photo, voice); the message reaches the owner's Telegram with a line `💬 #u<id> name @username · email`. The owner **replies to that line** (or to the copied message) and the reply goes back to the student. |

Widgets are Telegram's interactive messages (Bot API 10.4, November 2026). For now they work in private chats with
the bot only, and cannot be forwarded: exactly what these two need.

## Setting it up

1. **Supabase → SQL editor:** run the last block of `supabase/schema.sql` ("Telegram"). It adds `profiles.telegram_id`.
2. **Render → testday → Environment** (the tokens come from @BotFather → your bot → API Token; never paste them in a chat):
   - `TELEGRAM_STUDENT_BOT_TOKEN`: @testdayuzbot's token
   - `TELEGRAM_SUPPORT_BOT_TOKEN`: @testdaysupportbot's token
   - `TELEGRAM_ADMIN_CHAT_ID`: your own Telegram user id (already set if the site sends you alerts on Telegram).
     Open @testdaysupportbot once and press Start, so it may write to you.
   - optional `TELEGRAM_WEBHOOK_SECRET` (any long random text); without it one is derived from the server's secret.
3. Redeploy. About 20 seconds after start the site points both bots at itself; the Render log shows
   `Telegram bots set up: {'student': 'ok', 'support': 'ok'}`.
4. Test: open @testdayuzbot → Start → Band calculator. Then on the site → Account → **Connect Telegram** → Start in
   Telegram: "My results" now shows your bands. Write to @testdaysupportbot from another account and reply to the
   `#u…` line.

## BotFather (looks, not code)

- `/setdescription` and `/setabouttext` for both bots (what a student sees before pressing Start), and `/setuserpic`
  (the TestDay mark).
- `/setjoingroups` → Disable for both: they are for private chats.
- The commands of @testdayuzbot are set by the site (/start, /calc, /results, in Uzbek, Russian and English).

## Telegram names

Usernames allow only letters, digits and underscores (5–32), so `@testday.uz` cannot exist on Telegram.
Taken already (yours): `@testdayuz`, `@testdayofficial`, `@testdayuzbot`, `@testdaysupportbot`.
Looked free on 26 November 2026 and worth reserving with an empty channel or group: `@testday` (the strongest),
`@testday_uz`, `@testdaychat` (a students' group), `@testday_ielts`. Suggested use: `@testdayuz` the main channel
(matches Instagram @testdayuz), `@testdaychat` the community group, the bots as above.

## Safety

- Telegram's calls carry a secret header; anything else is refused (`TelegramTests`).
- A link code from the site is signed, works for 2 days and only for that account; one Telegram account links to one
  TestDay account. `/stop` in the bot, or Disconnect on the Account page, unlinks.
- A results card answers only for the Telegram account linked to it; anyone else gets nothing.
- Each Telegram user can send the student bot 20 messages a minute and the support bot 20 an hour.
- A student who blocks the bot is unlinked automatically.
