"""
AI models through OpenRouter (https://openrouter.ai), one OpenAI-compatible API
in front of many model providers.

    OPENROUTER_API_KEY    turns AI marking on (Writing, and Speaking with the AI examiner)
    AI_MODEL              the model for anything that is not one of the steps below (each step has a tested
                          default in STEP_MODELS), default google/gemini-3.8-flash
    AI_MODEL_WRITING      marking a Writing task (text)
    AI_MODEL_LISTEN       listening to one Speaking answer (must accept audio)
    AI_MODEL_RATE         rating a whole Speaking test from its transcripts and notes (text)
    AI_MODEL_FALLBACK     tried once when the chosen model keeps failing (busy, down, or blocked by its own filter)
    AI_REASONING          how hard the model thinks: low, medium (default) or high
    AI_DATA_COLLECTION    deny (default): only model providers that do not store or train on what we send. If no
                          provider of the model qualifies, the request goes the normal way and the log says so loudly.
                          strict: the same, but never the normal way (AI marking stops instead). allow: any provider.
    OPENROUTER_BASE_URL   default https://openrouter.ai/api/v1 (tests point it at a local fake)

complete_json() sends a system prompt and a user message (text and audio parts),
asks for JSON that follows a JSON Schema, and returns the parsed object. Every
call is logged with its token use and cost, never with the content, and the cost of
every attempt (a retried answer costs too) is returned, so each job's cost can be kept.
"""

import base64
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request

from . import pool

log = logging.getLogger("mockexam.ai")

DEFAULT_MODEL = "google/gemini-3.8-flash"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
REASONING_LEVELS = ("low", "medium", "high")

# Formats OpenRouter accepts for audio input (the browser records the AI examiner's answers as WAV).
AUDIO_FORMATS = {"audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3", "audio/mp3": "mp3",
                 "audio/aac": "aac", "audio/mp4": "m4a", "audio/x-m4a": "m4a", "audio/ogg": "ogg",
                 "audio/flac": "flac", "audio/aiff": "aiff"}


class AiError(Exception):
    """The model could not give a usable answer. The message is safe to show to the user."""

    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable
        self.cost = 0.0   # US dollars the failed attempts still cost


class NoEndpoint(AiError):
    """No provider of the model meets the request's conditions (for example the data policy)."""


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def configured():
    return bool(_env("OPENROUTER_API_KEY"))


# What each step uses unless the environment says otherwise. Chosen on 26 November 2026 by testing the candidates on
# the same material (docs/COSTS.md): Gemini 3.1 Flash-Lite listens to each Speaking answer and marks Writing (about a
# quarter of the cost, the same Writing bands as 3.8 Flash on 17 of 20 criteria, no false safety blocks); Gemini 3.8
# Flash rates the whole Speaking test, one call per test, where it was the closest to official IELTS examiners.
STEP_MODELS = {"writing": "google/gemini-3.1-flash-lite", "listen": "google/gemini-3.1-flash-lite", "rate": DEFAULT_MODEL}
STEP_ENV = {"writing": "AI_MODEL_WRITING", "listen": "AI_MODEL_LISTEN", "rate": "AI_MODEL_RATE"}


def model_name(step=None):
    """The model for a step ("writing", "listen", "rate"): its own setting, else the tested default for that step.
    AI_MODEL is the model for anything else (and for every step when a step has no default)."""
    if step in STEP_ENV and _env(STEP_ENV[step]):
        return _env(STEP_ENV[step])
    if step in STEP_MODELS:
        return STEP_MODELS[step]
    return _env("AI_MODEL") or DEFAULT_MODEL


def fallback_model():
    return _env("AI_MODEL_FALLBACK") or DEFAULT_MODEL


def reasoning_level():
    level = _env("AI_REASONING", "medium").lower()
    return level if level in REASONING_LEVELS else "medium"


def data_policy():
    value = _env("AI_DATA_COLLECTION", "deny").lower()
    return value if value in ("deny", "strict", "allow") else "deny"


def text_part(text):
    return {"type": "text", "text": text}


def audio_part(data, mime):
    fmt = AUDIO_FORMATS.get(str(mime or "").split(";")[0].strip().lower())
    if not fmt:
        raise AiError("This recording's format cannot be sent to the AI examiner.")
    return {"type": "input_audio", "input_audio": {"data": base64.b64encode(data).decode("ascii"), "format": fmt}}


def _message_text(message):
    content = message.get("content")
    if isinstance(content, list):  # some providers return content parts
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content or ""


def parse_json(text):
    """The model's JSON answer; tolerates a ```json fence around it."""
    text = (text or "").strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fenced:
        text = fenced.group(1)
    try:
        value = json.loads(text)
    except ValueError as e:
        raise AiError("The AI examiner's answer could not be read. Please try again.", retryable=True) from e
    if not isinstance(value, dict):
        raise AiError("The AI examiner's answer could not be read. Please try again.", retryable=True)
    return value


def _post(body, timeout):
    url = (_env("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/") + "/chat/completions"
    site = _env("SITE_URL") or "https://www.testday.uz"
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "Authorization": f"Bearer {_env('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
        "HTTP-Referer": site,
        "X-Title": "TestDay",
    })
    try:
        with pool.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        log.warning("OpenRouter HTTP %s: %s", e.code, detail)
        if e.code == 429:
            raise AiError("The AI examiner is busy right now. Please try again in a minute.", retryable=True) from e
        if e.code == 403 and ("SAFETY" in detail or "blocked" in detail.lower()):
            # The model's own safety filter stopped an ordinary answer (it happens with harmless speech, and not every
            # time): not a problem with the key, and worth one more try.
            err = AiError("The AI examiner could not assess this answer. Please try again.", retryable=True)
            err.blocked = True
            raise err from e
        if e.code in (401, 403):
            raise AiError("AI marking is not set up correctly on this site (the API key was refused).") from e
        if e.code == 402:
            raise AiError("AI marking is paused: the site's AI credit has run out.") from e
        if e.code == 413:
            raise AiError("The recording is too long to be assessed.") from e
        if e.code == 404 and (body.get("provider") or {}).get("data_collection") == "deny":
            raise NoEndpoint("AI marking is not available right now.") from e
        retry = e.code in (408, 500, 502, 503, 504)
        raise AiError(f"The AI examiner returned an error ({e.code}).", retryable=retry) from e
    except urllib.error.URLError as e:
        raise AiError("Could not reach the AI examiner.", retryable=True) from e
    except (TimeoutError, OSError) as e:
        raise AiError("The AI examiner took too long to answer.", retryable=True) from e
    except ValueError as e:
        raise AiError("The AI examiner sent an answer that could not be read.", retryable=True) from e


def _cost(usage):
    try:
        return max(0.0, float((usage or {}).get("cost") or 0))
    except (TypeError, ValueError):
        return 0.0


_fallback_logged = False


def complete_json(system, content, schema, name, max_tokens=8000, reasoning=None, timeout=180, attempts=3, step=None):
    """
    complete_json_with() with the step's model; if that model keeps failing for a reason another model may not have
    (busy, unavailable, its own safety filter), the fallback model is tried once. The cost of both is returned.
    """
    model = model_name(step)
    try:
        return complete_json_with(model, system, content, schema, name, max_tokens, reasoning, timeout, attempts)
    except AiError as e:
        fallback = fallback_model()
        if fallback == model or not getattr(e, "retryable", False) and not isinstance(e, NoEndpoint) and not getattr(e, "blocked", False):
            raise
        log.warning("AI %s: %s failed (%s); trying %s", name, model, e, fallback)
        try:
            data, meta = complete_json_with(fallback, system, content, schema, name, max_tokens, reasoning, timeout, 1)
        except AiError as e2:
            e2.cost = round(getattr(e2, "cost", 0.0) + getattr(e, "cost", 0.0), 6)
            raise
        meta["cost"] = round(meta.get("cost", 0.0) + getattr(e, "cost", 0.0), 6)
        meta["fallback"] = True
        return data, meta


def complete_json_with(model, system, content, schema, name, max_tokens=8000, reasoning=None, timeout=180, attempts=3):
    """
    Ask the model for JSON that follows `schema`. `content` is a string or a list of
    parts (text_part, audio_part). Returns (data, meta): meta has the model, the last
    answer's usage, and "cost" (US dollars for every attempt, retries included).
    Retries busy, timed-out and unreadable answers with a short back-off.
    """
    global _fallback_logged
    if not configured():
        raise AiError("AI marking is not enabled on this site yet.")
    policy = data_policy()
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
        "reasoning": {"effort": reasoning or reasoning_level(), "exclude": True},
        "max_tokens": max_tokens,
        "provider": {"require_parameters": True, **({} if policy == "allow" else {"data_collection": "deny"})},
    }
    last, spent, tokens_in, tokens_out = None, 0.0, 0, 0
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            try:
                data = _post(body, timeout)
            except NoEndpoint:
                if policy == "strict":
                    raise
                # No provider of this model promises not to keep the data: say so where the owner will see it, and
                # carry on the normal way rather than stop marking (AI_DATA_COLLECTION=strict stops instead).
                if not _fallback_logged:
                    log.error("No provider of %s meets data_collection=deny; using the default routing. Set "
                              "AI_DATA_COLLECTION=strict to stop instead, or choose another AI_MODEL.", body["model"])
                    _fallback_logged = True
                body["provider"].pop("data_collection", None)
                data = _post(body, timeout)
            usage = data.get("usage") or {}
            spent += _cost(usage)
            tokens_in += int(usage.get("prompt_tokens") or 0)
            tokens_out += int(usage.get("completion_tokens") or 0)
            if data.get("error"):
                err = data["error"]
                code = err.get("code") if isinstance(err, dict) else None
                log.warning("OpenRouter error in response: %s", str(err)[:400])
                raise AiError("The AI examiner returned an error.", retryable=code in (429, 500, 502, 503, 504, None))
            choices = data.get("choices") or []
            if not choices:
                raise AiError("The AI examiner returned an empty answer.", retryable=True)
            choice = choices[0]
            finish = str(choice.get("finish_reason") or choice.get("native_finish_reason") or "").lower()
            if finish in ("length", "max_tokens"):
                raise AiError("The AI examiner's answer was cut off. Please try again.", retryable=True)
            if finish in ("content_filter", "safety", "refusal"):
                raise AiError("The AI examiner declined to assess this response.")
            result = parse_json(_message_text(choice.get("message") or {}))
            log.info("AI %s: model=%s %.1fs tokens in=%s out=%s cost=%s", name, data.get("model"),
                     time.monotonic() - started, usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("cost"))
            return result, {"model": data.get("model") or model, "usage": usage, "cost": round(spent, 6),
                            "tokensIn": tokens_in, "tokensOut": tokens_out, "attempts": attempt}
        except AiError as e:
            last = e
            e.cost = round(spent, 6)
            if not e.retryable or attempt == attempts:
                raise
            time.sleep(2 * attempt)
    raise last
