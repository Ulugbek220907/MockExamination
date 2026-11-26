# What the AI examiner costs, and what each pass earns

The allowances in `mockexam/ai_usage.py` and the prices in `mockexam/billing.py` (`PLAN_PRICES`) are set from the sums
below. Re-check them when the model, its price, a fee or the exchange rate changes. **Admin → AI** shows what marking
really cost in the last 30 days (every job now saves the cost OpenRouter reported), so the estimates here can be
replaced with real averages after a few weeks.

## Inputs (26 November 2026)

| | |
|---|---|
| Model | `google/gemini-3.8-flash` through OpenRouter: $0.825 per million input tokens (text and audio), $4.125 per million output tokens (reasoning included) |
| OpenRouter fee | 5.5% on buying credits (card) |
| Exchange rate | about 12 024 so'm to the dollar (Central Bank, 17 November 2026) |
| Dodo (card, US dollars) | 4% + $0.40, +1.5% for a card from outside the US, +0.5% for a subscription |
| Click (so'm) | assumed 2% (check the contract) |
| Tax | assumed 4% of turnover (check with the accountant) |

## One job

| Job | What is sent | Typical | Heavy |
|---|---|---|---|
| Writing script (Task 1 + Task 2, marked separately) | ~3 300 input tokens per task (prompt, descriptors, question, script); ~3 800 output per task (feedback JSON + medium reasoning) | **$0.037** | $0.104 (both tasks hit the 12 000-token cap) |
| Speaking test (~20 answers, ~13 minutes recorded) | each answer: ~2 400 tokens of instructions + its audio (32 tokens a second) and ~750 out; then the whole-test rating: ~8 300 in, ~4 500 out | **$0.15** | $0.29 (26 answers, 18 minutes, twice the output) |

Silence is never sent, nor a script under 21 words, a copied model answer, a copied question or a response that is not
in English (see AI_SAFETY.md). Gemini caches repeated instructions, which can make Speaking about a third cheaper; the
sums above do not count on it.

## The allowances

| | Writing scripts | Speaking tests | Spending net (per paper, 30 days) |
|---|---|---|---|
| A pass that covers the paper | 30 in any 30 days, 3 a day | 12 in any 30 days, 3 a day | $2.00 Writing, $3.00 Speaking |
| A free account | 2 in any 30 days, 1 a day | 1 in any 30 days | $0.30 Writing, $0.50 Speaking |
| All free accounts together | 40 a day | 15 a day | about $3.90 a day at most |
| Admins and examiners | no personal limit | no personal limit | none |

A free account costs at most about $0.23 a month (typical) to $0.52 (heavy). The free day budget stops a flood of new
accounts from costing more than about $4 a day.

## What each pass earns (one month)

Net = price after the payment fee and the 4% tax. AI = the most a person can use in a month (with the 5.5% OpenRouter
fee), typical and heavy. The spending net caps the heavy case for Full at $5.28.

| Pass | so'm price (= $) | Net (Click) | Dollar price | Net (Dodo) | AI at full use: typical / heavy | Left: typical (Click / Dodo) |
|---|---|---|---|---|---|---|
| Listening + Reading | 39 000 ($3.24) | $3.05 | $3.99 | $3.22 | $0 / $0 | $3.05 / $3.22 |
| Writing | 49 000 ($4.08) | $3.83 | $4.99 | $4.12 | $1.16 / $2.11 (net) | $2.67 / $2.95 |
| Speaking | 59 000 ($4.91) | $4.61 | $5.99 | $5.02 | $1.87 / $3.17 (net) | $2.74 / $3.15 |
| Full | 79 000 ($6.57) | $6.18 | $7.99 | $6.83 | $3.04 / $5.28 (net) | $3.14 / $3.79 |

3 months: Listening + Reading 99 000 / $9.99, Writing 119 000 / $11.99, Speaking 149 000 / $14.99, Full 199 000 /
$19.99. With typical full use, Full for 3 months leaves about $6.40 (Click) and $8.50 (Dodo).

Most students use far less than the allowance, so the typical margin is higher than this table shows. The so'm prices
read like the dollar ones ($3.99 → 39 000 so'm), which is about a fifth less at today's rate: paying locally costs us
less in fees, and the dollar prices stay as they are, so no Dodo product needs changing.

## When to change something

- Real average cost per job (Admin → AI) above $0.06 for Writing or $0.22 for Speaking: lower the allowance or move
  Speaking's per-answer listening to a cheaper model.
- The dollar above 14 000 so'm: raise the so'm prices.
- Many "busy" refusals for free accounts: raise `AI_FREE_WRITING_PER_DAY` / `AI_FREE_SPEAKING_PER_DAY` if the budget allows.

Every number is an environment variable: `WRITING_AI_PER_MONTH`, `WRITING_AI_PER_DAY`, `WRITING_AI_FREE_PER_MONTH`,
`WRITING_AI_FREE_PER_DAY`, `SPEAKING_AI_PER_MONTH`, `SPEAKING_AI_PER_DAY`, `SPEAKING_AI_FREE_PER_MONTH`,
`SPEAKING_AI_FREE_PER_DAY`, `AI_FREE_WRITING_PER_DAY`, `AI_FREE_SPEAKING_PER_DAY`, `AI_COST_CAP_WRITING_USD`,
`AI_COST_CAP_SPEAKING_USD`, `AI_FREE_COST_CAP_WRITING_USD`, `AI_FREE_COST_CAP_SPEAKING_USD`.
