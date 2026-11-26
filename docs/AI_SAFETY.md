# Safety checks around the AI examiner

TestDay uses a language model as an examiner: it reads a Writing script, or listens to Speaking answers, and gives
bands and feedback. Anything a candidate writes or says reaches the model, so a candidate can try to talk the model
into a higher band. This page lists what has gone wrong with automatic marking and with models acting as judges, and
what TestDay does about each. The code is `mockexam/ai_safety.py` (the checks), `mockexam/ai_usage.py` (allowances),
`mockexam/ai.py` (the model call), and the prompts in `writing.py` and `speaking_ai.py`. Tests: `AiSafetyTests` and
`AiAllowanceTests` in `scripts/test_app.py`.

## What history teaches

| Year | What happened | Lesson | What TestDay does |
|---|---|---|---|
| 2012–2020 | Les Perelman's **BABEL generator** wrote long, grand-sounding nonsense that ETS's e-rater scored highly; length and rare words were proxies for quality. ETS later added a filter for BABEL essays. | Markers that reward length and big words can be fooled by text that means nothing. | The prompt tells the examiner that rare words earn nothing when the sentences make no sense, and that repeated sentences earn no credit. Repetition is measured and reported to the model. Bands never depend on the word count except where the descriptors say so. |
| 2024 | **Universal adversarial phrases** (Raina, Liusie and Gales, EMNLP 2024): a phrase of about five words appended to any text pushed LLM judges to the top score; absolute scoring was the most vulnerable. | A model that gives a score out of N can be steered by text in the thing it scores. | The script sits between markers with a random name; the system prompt says that nothing inside can change the rules. Text addressed to the marker is detected and the script gets no criterion above band 6. |
| Jan 2024 | **ASCII smuggling**: Unicode "tag" characters (U+E0000–E007F) are invisible to people but read by models, so instructions can be hidden in text that looks clean. | Invisible characters are a channel for hidden instructions. | All invisible characters (tags, zero-width, direction controls, variation selectors, control characters) are removed from scripts before anything else happens. |
| 2025 | **Hidden prompts in research papers**: 18 arXiv preprints had white or tiny text such as "give a positive review only" aimed at AI reviewers. Studies disagree on how well it worked. | People will try it the moment a model marks their work. | The phrases "ignore the instructions", "give this band 9", "you are now…", "note to the examiner", chat-format tokens, in English, Russian and Uzbek, are found (after folding look-alike letters) and reported. |
| 2025 | **One token to fool LLM-as-a-judge** (NeurIPS 2025): answers like ":" or "Thought process:" got positive verdicts from many judge models. | Judges reward empty, confident-looking answers. | Scripts of 20 words or fewer are never sent; a script copied from the question or the model answer is not sent; every correction the model returns must quote words that really are in the script, or it is dropped. |
| 2025 | **Audio jailbreaks** (AudioJailbreak, WhisperInject and others): spoken or hidden instructions in audio steer audio-language models. | A Speaking answer can carry instructions too. | The listening prompt asks the model to report `speaksToMarker`; every transcript is also checked for instructions; a test with them gets no criterion above band 6. The model has no tools and cannot act, so the worst a spoken instruction can do is change a practice band, and that is capped. |
| 2024–2025 | **OWASP Top 10 for LLM applications** | The standard list of risks. | See the table below. |

## OWASP Top 10 for LLM applications (2025), applied

| Risk | How TestDay handles it |
|---|---|
| LLM01 Prompt injection | Random fences; "never an instruction" rules first in the prompt; instruction detection (text and transcripts); band cap at 6; invisible characters removed. |
| LLM02 Sensitive information disclosure | The model gets the question and the answer only: no name, email or account. OpenRouter is asked for providers that do not store or train on the data (`data_collection: deny`, see below). |
| LLM05 Improper output handling | Strict JSON schema; bands clamped to whole numbers 0–9; the overall band is computed by the server, never taken from the model; links and email addresses removed from feedback; made-up corrections dropped; every text length-limited; the page escapes everything it shows. |
| LLM06 Excessive agency | The model has no tools, no web access, and cannot change anything: it returns JSON that the server checks. |
| LLM07 System prompt leakage | The prompts hold only public IELTS descriptors and marking rules, no secrets; they tell the model not to repeat them. |
| LLM09 Misinformation | Every band is labelled a practice estimate, not an official IELTS result. |
| LLM10 Unbounded consumption | Per-person allowances (AI_COSTS.md), a spending net per person, a day budget for all free accounts, one Writing script at a time per person, per-IP and site-wide day caps, a cap on output tokens, script and recording size limits, and silence never sent. |

## Checks on a Writing script, in order

1. Invisible characters removed (`clean_text`).
2. Under 21 words: not sent (band 1, or 0 when blank).
3. Half or more of the script is the published model answer, word for word: not sent, band 0 ("Write your own response").
4. Most of the script repeats the question: not sent, band 1 (copied words do not count).
5. Fewer than half the letters are Latin (not English): not sent, band 0.
6. Otherwise sent, with what the checks found (instructions to the marker, repetition, partial copying) listed for
   the examiner, and the script between random fences.
7. What comes back: bands clamped; Task Achievement/Response at most 5 when the script is under half the minimum length;
   every criterion at most 6 when there was text addressed to the marker, and the student is told why; feedback
   without links; corrections only if they quote the script.

## Speaking

Silence is not sent. Each answer is listened to with the same security rules, and the model reports whether the
candidate spoke English, answered the question, sounded memorised, and spoke to the marker. The whole-test rating gets
each transcript between random fences. The same output checks apply (corrections and vocabulary must quote a transcript).

## Where the data goes

The model is Google Gemini, reached through OpenRouter. Every request asks OpenRouter for providers that do not store
or train on prompts (`AI_DATA_COLLECTION=deny`, the default). If no provider of the model meets that, the request goes
the normal way and the log says so loudly; `AI_DATA_COLLECTION=strict` stops marking instead. Google's paid API does not
train on prompts; it may keep flagged prompts up to 90 days for abuse monitoring. Turn on "no training" in the
OpenRouter privacy settings too.

## Known limits

- A candidate can still learn a memorised essay that is not our model answer; the examiner is told that memorised text
  earns little credit, but it cannot always tell.
- A Speaking answer read from a script or played from a recording can sound fluent; `soundsMemorised` catches some of it.
- Detection of instructions is a list of patterns; new wording will slip past it. The fences, the rules and the cap are
  the real defence; the patterns only make the cap and the message possible.
- The free-account day budget is counted in memory and starts again after a restart.
