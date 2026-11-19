# Facts on the guide pages, and when to check them again

Four pages state facts about the real exam (`mockexam/seo_guides.py`): how computer-delivered IELTS works
(`/en/computer-delivered-ielts-what-to-expect`, `/uz/ielts-kompyuterda-topshirish`, `/ru/ielts-na-kompyutere-format`), what it
costs in Uzbekistan (`/uz/ielts-imtihon-narxi-2026`, `/ru/ielts-stoimost-ekzamena-uzbekistan`), the state refund for IELTS 7.0+
(`/uz/ielts-kompensatsiya-7-ball`) and what band 7 means (`/en/how-to-get-band-7-in-ielts`). Each shows the date its facts were
checked and links to the official pages they came from. A page that shows an old date looks neglected and gets less trust, so
check the facts below on the schedule, then update the page.

## How to update after a check

1. Open `mockexam/seo_guides.py`. Change the prices (`BC_FEE`, `IDP_FEE`, `BC_UKVI_FEE`, ...) and `FACTS_CHECKED` at the top.
   The prices appear in the page text, titles and descriptions from those constants only.
2. Change any sentence whose rule changed. Run `python scripts/test_app.py`; open a pull request.
3. After it is deployed, in Google Search Console use "Request indexing" for the changed pages.

## Check again

| Fact | Where | How often | Official page |
|---|---|---|---|
| British Council fees (Academic and GT 2,798,000; UKVI 3,119,000; Life Skills 2,759,000; extra TRF 64,000) | fees pages | monthly (the fee rose in September 2026) | britishcouncil.uz/en/exam/ielts/book-test |
| IDP / Edu Action fee (2,800,000) and the cities it is confirmed for | fees pages | monthly | ielts.idp.com/uzbekistan/test-dates and /test-centre/edu-action |
| Cancellation and transfer rules (British Council 15 / 5-14 / under 5 days) | fees pages | quarterly | britishcouncil.uz/en/exam/ielts/cancellation-refund-and-transfer-policy |
| Payment methods (British Council: Payme, Xazna, Click, Uzum, bank transfer, KDB Bank branch, foreign cards) | fees pages | quarterly | britishcouncil.uz/en/exam/ielts/book-test |
| Paper IELTS and "Writing on Paper" in Uzbekistan | format pages | monthly through 2027 | the two booking pages above |
| One Skill Retake (available at both providers, 60 days) | format pages | quarterly | ielts.org/take-a-test/booking-your-test/one-skill-retake and both providers' pages |
| State refund: age, minimum band, steps, deadlines, Xazna payout | refund page | monthly, and on 2 January 2027 | my.gov.uz/uz/service/413, gov.uz/oz/yoshlar/sections/view/28105, lex.uz/docs/-5370812 |
| Results time (1-5 days, 1-2 typical at the British Council) | format pages | twice a year | ielts.org/take-a-test/your-results/fast-test-results-and-sharing |
| Band descriptors and the score tables (30 out of 40 for band 7) | band 7 page, calculator | yearly | ielts.org/take-a-test/your-results/ielts-scoring-in-detail |

## Where official pages disagree, and what the pages say

- **Age limit for the 7.0 refund.** britishcouncil.uz says "under 30". my.gov.uz and gov.uz say the person had not yet turned 31
  when taking the exam. The page follows the government pages and mentions the difference.
- **British Council fee.** Some module pages on britishcouncil.uz still show the old 2,664,000. The booking page (2,798,000) is
  used, and the old figure is named only as the price it rose from (Zamin.uz, 3 September 2026).
- **Listening transfer time.** Some britishcouncil.uz pages still carry the paper rule (10 minutes to copy answers). On computer
  there is none; the pages say so.
- **Payout of the refund.** Older pages mention a Xalq Bank branch; the Youth Affairs Agency (January 2026) says Xazna.

## Left out on purpose (could not be verified)

Do not add these until checked directly in the booking portals, on lex.uz or with the provider:

- Whether "Writing on Paper" is offered anywhere in Uzbekistan (the pages say it could not be confirmed).
- The price of One Skill Retake and of Enquiry on Results in so'm (not published).
- IDP Uzbekistan's cancellation deadline (its transfer page is dated 2021) and any IDP price before 2,800,000.
- PayPal or Klarna for the British Council in Uzbekistan (global template text), and local apps for IDP.
- The British Council claim that One Skill Retake is "offered exclusively" by it (IDP also offers it).
- Whether prep-course costs are refunded by the state programme (sources contradict each other), whether General Training, UKVI
  or One Skill Retake results qualify for the refund, and the 180-day application deadline (reported by one news site only).
- Life Skills result time (7 days at IDP, up to 9 at the British Council and ielts.org).
