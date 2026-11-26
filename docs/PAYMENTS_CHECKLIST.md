# Payments checklist (production)

Run this once before taking real money, and again after any change to `mockexam/billing.py`,
the prices, or the Payme / Click cabinet settings. It takes about 30 minutes and costs one plan
payment, which you refund at the end.

What is sold: passes for 1 or 3 months: Full (all four papers), Speaking, Writing, and Listening + Reading. A student pays by card in US dollars through Dodo (a subscription that renews every 1 or 3 months until the student cancels) or in so'm through Click (Uzcard and Humo: one payment that does not renew), and Payme works like Click. Examiner checks (Writing 10 000 so'm, Speaking 20 000 so'm) are sold only when `EXAMINER_CHECKS_ENABLED=1`. Prices are in `mockexam/billing.py` (`PLAN_PRICES`, so'm and US cents): Full 79 000 / 199 000 so'm ($7.99 / $19.99), Speaking 49 000 / 119 000 ($5.99 / $14.99), Writing 39 000 / 99 000 ($4.99 / $11.99), Listening + Reading 29 000 / 69 000 ($3.99 / $9.99). Prices come from the server, never from the browser.

## 1. Environment variables (Render → the testday service → Environment)

| Variable | Needed for | Notes |
|---|---|---|
| `SITE_URL` | all | `https://www.testday.uz` (the address the site ends up on; testday.uz redirects there). Return links after payment use it. |
| `SESSION_SECRET` | all | Long random string. Changing it signs everyone out. |
| `ADMIN_EMAILS` | refunds | Your sign-in email. Admins see **Account → Admin → Orders**. |
| `CONTACT_EMAIL` | receipts, refund policy | Shown to students for refund requests. |
| `EXAMINER_CHECKS_ENABLED` | examiner checks | Leave off (default) until you have examiners: nothing about examiners or checks shows or sells. `1` offers them (with `COMMERCE_ENABLED=1`). |
| `WRITING_CHECK_PRICE`, `SPEAKING_CHECK_PRICE` | prices | In so'm: the examiner checks (defaults 10000 / 20000). The passes are priced in `billing.PLAN_PRICES`; the old `PLAN_PRICE` variable is no longer read, so delete it on Render. |
| `DODO_PAYMENTS_API_KEY`, `DODO_PAYMENTS_WEBHOOK_KEY`, `DODO_PRODUCTS` | Dodo (card, US dollars) | The API key (`dodo_test_...` or `dodo_live_...`), the webhook signing secret (`whsec_...`) and the product of each pass: `full-1=pdt_x,full-3=pdt_y,speaking-1=...` (kind of pass, a dash, the months). See section 7. |
| `SPEAKING_AI_PER_MONTH`, `WRITING_AI_PER_MONTH` | AI caps | AI-rated Speaking tests and AI-marked Writing scripts in any 30 days (defaults 12 and 20): what the prices assume. |
| `PLAN_DAYS`, `PLAN_FIRST_BONUS_DAYS` | plan length | Defaults 30 and 30. |
| `PAYME_MERCHANT_ID`, `PAYME_KEY` | Payme | From the Payme business cabinet. `PAYME_KEY` is the **production** key. |
| `PAYME_TEST` | Payme | `1` only while testing in the Payme sandbox. Remove it (or set `0`) for real money. |
| `PAYME_ACCOUNT_FIELD` | Payme | Leave empty (`order_id`) unless the cabinet uses another account field name. |
| `PAYME_IKPU`, `PAYME_PACKAGE_CODE` | Payme fiscal receipts | Set both to send receipt details (ИКПУ / package code). |
| `CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`, `CLICK_SECRET_KEY` | Click | From Click (the message with your integration keys). Click shows on the Price page when all three are set. |
| `CLICK_MERCHANT_USER_ID` | Click refunds | Also from Click (`MERCHANT_USER_ID`). Optional: it lets **Admin → Orders → Refund** return the money through Click's Merchant API. Without it the admin page tells you to return the money in the Click cabinet. Not listed in `render.yaml` on purpose (a new secret there makes Render ask for it at the next sync): add it in the Render dashboard. |

A provider shows on the Prices page only when all of its variables are set (for Click: the first three).

## 2. Cabinet settings

- **Payme** business cabinet → the cash register (kassa) → endpoint URL:
  `https://www.testday.uz/api/pay/payme`. The login is `Paycom`; the password is `PAYME_KEY`.
- **Click** merchant cabinet (merchant.click.uz) → *Сервисы* → the pencil in the *Действие* column → URLs:
  - Prepare: `https://www.testday.uz/api/pay/click/prepare`
  - Complete: `https://www.testday.uz/api/pay/click/complete`
  - then ask Click to activate the service and to whitelist the server (section 8).
- Use the **www** address. `testday.uz` without www answers with a redirect, and payment
  servers do not follow redirects for their callbacks, so a payment would never be confirmed.
- Use HTTPS. (Click's documentation allows plain HTTP too, which can be acceptable for a relay: the callbacks carry no secrets
  and the site checks every signature. Ask Click whether the cabinet accepts an `http://` address.) No other URL is needed: the
  student is sent back to the site afterwards.

## 3. Sandbox first (no real money)

1. Set `PAYME_TEST=1` and the **test** key from the Payme sandbox, then redeploy.
2. In the Payme sandbox (test.paycom.uz), run the merchant API checks against
   `https://www.testday.uz/api/pay/payme`. Every check should pass: CheckPerformTransaction,
   CreateTransaction, PerformTransaction, CancelTransaction (before and after perform),
   CheckTransaction, GetStatement, wrong amount (-31001), unknown order (-31050) and wrong
   password (-32504).
3. Click has no public sandbox that we found. After you give Click the two URLs they switch the service
   on; then go to step 4 with a small real payment and refund it (section 8).
4. Put the production key back and remove `PAYME_TEST`, then redeploy.

## 4. One real purchase

Use a separate student account (not an admin email), on a phone, with mobile data.

1. Sign in, then open **Prices → Get the pass**.
2. Pay with Payme. Expected:
   - you come back to the site;
   - **Account** says *Your pass is active until …*;
   - Reading Test 16 (the first paid one) opens at once, and Listening Test 2 plays its recording;
   - under Payments the order shows **Paid**, and **Receipt** shows the order number,
     amount, date, "Payme" and the pass dates;
   - the owner gets the Telegram message, if Telegram is set up.
3. In **Admin → Orders**, find the order (`#MX…`). It is Paid, with provider `payme`.
4. Repeat steps 1–3 with Click on a second account, if Click is live.
5. Optional: buy a Writing check on a free Writing result. The examiner receives it, and the
   receipt links to the check.

## 5. Refund

The **Refund** button in Admin → Orders takes back what the order bought: the pass days
(later months move up, so no paid day is lost), or the examiner check while the examiner has
not started. For Dodo and Click it also asks the provider to give the money back; for Payme it
does not, and says so. The money goes back through the provider:

| Paid with | Send the money back | Then on the site |
|---|---|---|
| Payme | Payme cabinet → the transaction → Cancel (refund) | Nothing: Payme calls the site, and the order becomes Refunded automatically. |
| Click | Nothing to do if `CLICK_MERCHANT_USER_ID` is set | Admin → Orders → Refund asks Click to reverse the payment (it looks the payment up by our order number, then reverses it), then takes the pass back. **Click returns a payment only in the month it was made** (one from last month only on the first day of this month), and Uzcard may refuse. If Click refuses, the admin page shows Click's reason and offers *Mark as refunded*, for when you returned the money by hand in the Click cabinet or with Click support. Without `CLICK_MERCHANT_USER_ID` the admin page tells you to return the money in the Click cabinet. |
| Dodo (card, USD) | Nothing to do in Dodo | Admin → Orders → Refund asks Dodo to refund the card, then takes the pass back. A refund made in the Dodo dashboard reaches the site through the webhook (`refund.succeeded`). |

Check after a refund:
- Reading Test 16 is locked again immediately, and so is Listening Test 2's audio;
- the order says **Refunded**, and the receipt button has gone;
- if the student had bought another month after this one, that month now starts today.

A check the examiner has already started cannot be refunded: Payme receives error -31007,
and the admin button says why. Policy: the plan is refundable within 3 days if no paid test
was started; an examiner check until the examiner starts it.

## 6. What protects the money (automated tests)

`python scripts/test_app.py` covers these on every push (CI):
- Payme and Click callbacks repeated or replayed change nothing twice: one plan period, one
  check;
- a wrong amount is refused before anything is stored (Payme -31001, Click -2);
- a refund removes exactly what was bought, moves queued plan time up, and refuses a check
  that is already being marked;
- paid tests and their audio open the moment an order is paid, and lock again the moment
  it is refunded;
- a pass that renews on its own (a card subscription) is not sold a second time, by card or by Click, and a Full pass that
  renews blocks every single-paper pass; a one-time pass (Click) can be added to, and the new one starts when the first ends;
- Click: the payment link follows Click's documentation (amount as `N.NN`, order number as
  `transaction_param`); Prepare and Complete over HTTP with the MD5 signature (wrong signature
  -1, wrong amount -2, a Click number used for another order -8); Click's payment number is saved
  at Complete; a payment that cannot be applied is logged as an error (which reaches Telegram);
  the admin refund calls Click's Merchant API (`status_by_mti`, then `payment/reversal`) with the
  `Auth` header, falls back to the saved number, keeps the order paid when Click refuses, and
  never calls Click again for *Mark as refunded*.

## 7. Dodo Payments (card payments in US dollars)

Dodo is the merchant of record: it sells the pass to the student, handles taxes and pays you out in USD
(Payoneer or a bank). It takes foreign Visa and Mastercard, Apple Pay and Google Pay; it does not take
Uzcard or Humo and cannot charge in so'm.

1. **Supabase first.** Run the last block of `supabase/schema.sql` ("Passes for one paper or two ... Dodo") in the
   SQL editor, before the site with the new passes is live. It is safe to run again.
2. **Dodo dashboard (test mode).** Create the 8 products as **Subscription** products (USD, tax inclusive; repeat payment every 1 month or every 3 months; Subscription Period 20 years; no trial). The pricing model cannot be changed later, so a one-time product cannot be reused: Full, Speaking, Writing and
   Listening and Reading, each for 1 and 3 months. Create an API key (Developer → API Keys) and a webhook
   (Developer → Webhooks) at `https://www.testday.uz/api/pay/dodo/webhook` for `payment.succeeded`,
   `payment.failed`, `payment.cancelled`, `refund.succeeded`, `refund.failed`, `subscription.cancelled` and `subscription.expired`. In Settings → Subscriptions turn on the grace period, and in Settings → Recovery turn on Payment Retries, so a declined renewal is retried before access stops.
3. **Render.** Set the three `DODO_*` variables of section 1. The key's prefix decides test or live:
   `dodo_test_` talks to test.dodopayments.com, `dodo_live_` to live.dodopayments.com. The pass of a kind that
   has no product in `DODO_PRODUCTS` cannot be paid by card.
4. **Test.** With `COMMERCE_ENABLED=1`, buy a pass with Dodo's test card `4242 4242 4242 4242` (any future expiry,
   CVV 123). The order becomes Paid with provider `dodo`; **Account** shows the pass and its papers.
5. **Live.** Switch the Dodo dashboard to live mode, make the live products, key and webhook, and replace the three
   variables (a new product id for each pass). Repeat step 4 with a real card and refund it.

How it is protected: the webhook is verified (HMAC-SHA256, timestamp within 5 minutes), the payment is fetched
from Dodo again and must be `succeeded`, in USD, for at least the order's amount, and carry the order id in its
metadata; a repeated webhook changes nothing twice (see `DodoTests` in `scripts/test_app.py`).

How renewals work: every charge, the first and each renewal, calls the webhook. The first pays the order made at checkout; each renewal makes an order of its own and adds one period (30 or 90 days) to the pass, so a failed or cancelled renewal simply lets the pass run out. The student cancels in Account (the site asks Dodo to stop at the end of the period). A refund of one charge takes back that period only.

## 8. Click (Uzcard and Humo, in so'm)

A pass paid with Click is **one payment**: it opens the pass for the 1 or 3 months chosen and does not renew (a card
payment through Dodo does). The first Full pass of one month paid this way comes with the extra free month, as with
Payme. The site shows both ways of paying on the Price page and says which one renews.

**What Click gives you:** the login of the merchant cabinet (merchant.click.uz) and, for the service, `SERVICE_ID`,
`MERCHANT_ID`, `SECRET_KEY` and `MERCHANT_USER_ID`. Keep them out of chats and screenshots, and change the cabinet
password at the first sign-in.

1. **Render variables** (Environment tab of the `testday` service): `CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`,
   `CLICK_SECRET_KEY` and `CLICK_MERCHANT_USER_ID`. Save: Render redeploys, and Click appears on the Price page.
2. **Callback URLs** in the cabinet: Prepare `https://www.testday.uz/api/pay/click/prepare`, Complete
   `https://www.testday.uz/api/pay/click/complete`. Use **www**: the address without www redirects, and Click does
   not follow a redirect for a POST. Click calls them with `application/x-www-form-urlencoded`; the site answers JSON.
3. **Ask Click to activate the service** (it is off by default) and to **whitelist the server** before the first real
   payment: domain `www.testday.uz`, port 443 and its IP addresses (today 216.24.57.16 and 216.24.57.18; Render's are
   shared and can change, so ask whether the domain is enough).
   **Render has no fixed inbound IP** (its static addresses are for outbound traffic only; `216.24.57.1` is the documented
   address for a root domain's A record, and the CNAME address of `www` is a pool that can change). If Click wants a static
   IP, or will not whitelist a domain, put a small **relay** in front of the site, on a server in Uzbekistan (inside TAS-IX, so
   Click needs no whitelist, or at least with an IP that never changes): `click.testday.uz` (A record to the relay's IP)
   forwards only the two callback paths to `https://www.testday.uz`. With Caddy on the relay:

   ```
   click.testday.uz {
       handle /api/pay/click/prepare {
           reverse_proxy https://www.testday.uz { header_up Host {upstream_hostport} }
       }
       handle /api/pay/click/complete {
           reverse_proxy https://www.testday.uz { header_up Host {upstream_hostport} }
       }
       handle { respond "Not found" 404 }
   }
   ```

   The relay holds no secrets (every callback is signed and checked by the site). Give Click the relay's addresses instead
   (`https://click.testday.uz/api/pay/click/prepare` and `/complete`), and set `CLICK_CALLBACK_BASE=https://click.testday.uz`
   in Render so that Admin → Click shows them.
4. **Fiscal receipts.** Click says fiscalization (the OFD API) is required only for a service that sells more than one
   IKPU code. TestDay sells one kind of thing (access to an online practice platform), so one IKPU on the service is
   enough and the site does not call the OFD API. Ask Click (or your accountant) which IKPU code applies and that it
   is set on the service.
5. **First payment.** From a second account, on a phone, buy the cheapest pass (Listening + Reading, 1 month, 29 000
   so'm) with your own Uzcard or Humo card. Expected: you come back to the site, **Account** says the pass is active,
   Admin → Orders shows the order **Paid** with provider `click`, and the Render log has no line starting
   "Click payment ... cannot be applied".
6. **Refund it** from Admin → Orders → Refund on the same day. Expected: the order says Refunded, the pass is gone, and
   Click returns the money to the card (it can take a few banking days).

**Admin → Click** shows what the site has (service id, merchant id, merchant user id, how long the secret key is, never the key
itself), the two addresses to give Click, and the last 40 requests Click has made to the site with our answer to each (kept
in memory: the list is empty after a restart). **Check that Click accepts the keys** asks Click's Merchant API about an order that
does not exist: "Click accepted the keys" means `CLICK_MERCHANT_USER_ID` and `CLICK_SECRET_KEY` are right (the secret key is also
what signs Prepare and Complete). Every request is also logged: `Click prepare: order=22 trans=... amount=... from=<ip> -> 0 Success`.

**If the first payment fails on Click's page** (for example *Оплата временно невозможна. Недостаточно информации от поставщика*):
open Admin → Click (or the Render log, search `click`).
- **Nothing listed / no `Click prepare` line**: Click never reached the site. The cause is on Click's side or in the cabinet: the
  service is not activated yet, the server is not whitelisted (Click asks for the domain, port and IP of any server outside TAS-IX
  before the first payment), or the cabinet addresses are not saved exactly as above (with **www**; a redirect from the bare domain
  is not followed). Send Click the time, the order number and this finding.
- **A line with `-1 SIGN CHECK FAILED!`**: Click reached the site but `CLICK_SECRET_KEY` or `CLICK_SERVICE_ID` in Render is not the one
  Click uses (a typo, a space). Use the keys check, and compare the service id on the page with the one Click gave you.
- **A line with `-5` or `-2`**: the order or the amount does not match: send me the line.
- **`0 Success` for prepare but no complete**: the payment was not finished by the student.

What the site does for Click (`mockexam/billing.py`, `ClickApi`):
- **Prepare** checks the signature (`md5(click_trans_id + service_id + SECRET_KEY + merchant_trans_id + amount + action +
  sign_time)`), the service id, that the order exists and is unpaid, and that the amount is exactly the price; it stores
  the Click transaction and answers its id. A repeated Prepare answers the same id.
- **Complete** checks the signature (with `merchant_prepare_id`), then gives the pass and marks the order paid, once. A
  repeat answers -4 (already paid). A Complete that carries an error from Click cancels the order (-9).
- If Click has taken the money but the pass cannot be given (the order was cancelled in between, or the same order was
  paid twice), the site answers Click with an error, **logs an error** (which also goes to the owner on Telegram) and the
  money is returned from the Click cabinet or with Admin → Orders → Refund.

Not built: paying by saved card (Click's `card_token`, for automatic renewals) and the OFD fiscal API. A local student
who wants more time buys another pass when the first ends; the site emails a reminder 3 days before.
