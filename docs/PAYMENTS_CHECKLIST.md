# Payments checklist (production)

Run this once before taking real money, and again after any change to `mockexam/billing.py`,
the prices, or the Payme / Click cabinet settings. It takes about 30 minutes and costs one plan
payment, which you refund at the end.

What is sold: the monthly plan (39 000 so'm, first payment gives two months, no automatic
renewal), a Writing check (10 000 so'm) and a Speaking check (20 000 so'm). Prices come from
the env vars below, never from the browser.

## 1. Environment variables (Render → the testday service → Environment)

| Variable | Needed for | Notes |
|---|---|---|
| `SITE_URL` | all | `https://www.testday.uz` (the address the site ends up on; testday.uz redirects there). Return links after payment use it. |
| `SESSION_SECRET` | all | Long random string. Changing it signs everyone out. |
| `ADMIN_EMAILS` | refunds, card transfers | Your sign-in email. Admins see **Account → Admin → Orders**. |
| `CONTACT_EMAIL` | receipts, refund policy | Shown to students for refund requests. |
| `PLAN_PRICE`, `WRITING_CHECK_PRICE`, `SPEAKING_CHECK_PRICE` | prices | In so'm. Defaults 39000 / 10000 / 20000. |
| `PLAN_DAYS`, `PLAN_FIRST_BONUS_DAYS` | plan length | Defaults 30 and 30. |
| `PAYME_MERCHANT_ID`, `PAYME_KEY` | Payme | From the Payme business cabinet. `PAYME_KEY` is the **production** key. |
| `PAYME_TEST` | Payme | `1` only while testing in the Payme sandbox. Remove it (or set `0`) for real money. |
| `PAYME_ACCOUNT_FIELD` | Payme | Leave empty (`order_id`) unless the cabinet uses another account field name. |
| `PAYME_IKPU`, `PAYME_PACKAGE_CODE` | Payme fiscal receipts | Set both to send receipt details (ИКПУ / package code). |
| `CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`, `CLICK_SECRET_KEY` | Click | From the Click merchant cabinet. |
| `PAYMENT_CARD_NUMBER`, `PAYMENT_CARD_HOLDER` | card transfer | Optional. Without them the card option is hidden. |

A provider shows on the Prices page only when all of its variables are set.

## 2. Cabinet settings

- **Payme** business cabinet → the cash register (kassa) → endpoint URL:
  `https://www.testday.uz/api/pay/payme`. The login is `Paycom`; the password is `PAYME_KEY`.
- **Click** merchant cabinet → the service → URLs:
  - Prepare: `https://www.testday.uz/api/pay/click/prepare`
  - Complete: `https://www.testday.uz/api/pay/click/complete`
- Use the **www** address. `testday.uz` without www answers with a redirect, and payment
  servers do not follow redirects for their callbacks, so a payment would never be confirmed.
- Both must be HTTPS. No other URL is needed: the student is sent back to the site afterwards.

## 3. Sandbox first (no real money)

1. Set `PAYME_TEST=1` and the **test** key from the Payme sandbox, then redeploy.
2. In the Payme sandbox (test.paycom.uz), run the merchant API checks against
   `https://www.testday.uz/api/pay/payme`. Every check should pass: CheckPerformTransaction,
   CreateTransaction, PerformTransaction, CancelTransaction (before and after perform),
   CheckTransaction, GetStatement, wrong amount (-31001), unknown order (-31050) and wrong
   password (-32504).
3. Click has no public sandbox. Ask Click support to run their test payments against your
   service, or go straight to step 4 with a small real payment.
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
not started. It does **not** send money anywhere. The money goes back through the provider:

| Paid with | Send the money back | Then on the site |
|---|---|---|
| Payme | Payme cabinet → the transaction → Cancel (refund) | Nothing: Payme calls the site, and the order becomes Refunded automatically. |
| Click | Click cabinet or Click support | Admin → Orders → Refund. |
| Card transfer | Transfer the money back yourself | Admin → Orders → Refund. |

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
  it is refunded.
