"""
AI models through OpenRouter (https://openrouter.ai), one OpenAI-compatible API
in front of many model providers.

    OPENROUTER_API_KEY    turns AI marking on (Writing, and Speaking with the AI examiner)
    AI_MODEL              the model, default google/gemini-3.8-flash (must accept audio for Speaking)
    AI_REASONING          how hard the model thinks: low, medium (default) or high
    OPENROUTER_BASE_URL   default https://openrouter.ai/api/v1 (tests point it at a local fake)

complete_json() sends a system prompt and a user message (text and audio parts),
asks for JSON that follows a JSON Schema, and returns the parsed object. Every
call is logged with its token use and cost, never with the content.
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


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def configured():
    return bool(_env("OPENROUTER_API_KEY"))


def model_name():
    return _env("AI_MODEL") or DEFAULT_MODEL


def reasoning_level():
    level = _env("AI_REASONING", "medium").lower()
    return level if level in REASONING_LEVELS else "medium"


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
        if e.code in (401, 403):
            raise AiError("AI marking is not set up correctly on this site (the API key was refused).") from e
        if e.code == 402:
            raise AiError("AI marking is paused: the site's AI credit has run out.") from e
        if e.code == 413:
            raise AiError("The recording is too long to be assessed.") from e
        retry = e.code in (408, 500, 502, 503, 504)
        raise AiError(f"The AI examiner returned an error ({e.code}).", retryable=retry) from e
    except urllib.error.URLError as e:
        raise AiError("Could not reach the AI examiner.", retryable=True) from e
    except (TimeoutError, OSError) as e:
        raise AiError("The AI examiner took too long to answer.", retryable=True) from e
    except ValueError as e:
        raise AiError("The AI examiner sent an answer that could not be read.", retryable=True) from e


def complete_json(system, content, schema, name, max_tokens=8000, reasoning=None, timeout=180, attempts=3):
    """
    Ask the model for JSON that follows `schema`. `content` is a string or a list of
    parts (text_part, audio_part). Returns (data, meta) where meta has the model and usage.
    Retries busy, timed-out and unreadable answers with a short back-off.
    """
    if not configured():
        raise AiError("AI marking is not enabled on this site yet.")
    body = {
        "model": model_name(),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}],
        "response_format": {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}},
        "reasoning": {"effort": reasoning or reasoning_level(), "exclude": True},
        "max_tokens": max_tokens,
        "provider": {"require_parameters": True},
    }
    last = None
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            data = _post(body, timeout)
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
            usage = data.get("usage") or {}
            log.info("AI %s: model=%s %.1fs tokens in=%s out=%s cost=%s", name, data.get("model"),
                     time.monotonic() - started, usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("cost"))
            return result, {"model": data.get("model") or model_name(), "usage": usage}
        except AiError as e:
            last = e
            if not e.retryable or attempt == attempts:
                raise
            time.sleep(2 * attempt)
    raise last
