"""What every platform adapter shares: the context it works in, and the result it returns."""

import time
from dataclasses import dataclass

from ..http import PlatformError

POLL_SECONDS = 10     # between checks that a platform has finished processing an upload
POLL_TRIES = 36       # so at most about six minutes


@dataclass
class Result:
    external_id: str
    url: str = ""
    note: str = ""


class Context:
    """The service's settings, the token store and the public address of the day's files, for an adapter."""

    def __init__(self, cfg, store, media_key=None, sleep=time.sleep, now=time.time):
        self.cfg = cfg
        self.store = store
        self.media_key = media_key
        self.sleep = sleep
        self.now = now

    def token(self, name, env=None):
        """The saved token data for a platform, over any starting values from the environment."""
        data = dict(env or {})
        data.update({k: v for k, v in self.store.token(name).items() if v not in (None, "")})
        return data

    def save_token(self, name, data):
        merged = self.store.token(name)
        merged.update(data)
        self.store.save_token(name, merged)

    def media_url(self, filename):
        """Where the platforms fetch a file of the day from (Instagram and Threads read it over the internet)."""
        if not self.cfg.public_url:
            raise PlatformError("PUBLIC_URL is not set, so the platforms cannot fetch the day's picture or video.", retryable=False)
        if not self.media_key:
            raise PlatformError("The day's files are not ready.", retryable=False)
        return f"{self.cfg.public_url}/media/{self.media_key}/{filename}"

    def wait_until(self, check, what):
        """Call check() until it returns a value that is not None; PlatformError if it never does."""
        for _ in range(POLL_TRIES):
            value = check()
            if value is not None:
                return value
            self.sleep(POLL_SECONDS)
        raise PlatformError(f"{what} did not finish in time.")


class Platform:
    name = ""
    label = ""
    media = "video"          # which file it posts: "video" or "card"
    caption_limit = 2200

    def env_token(self, cfg):
        """Starting values from the environment, for a deploy that is given its keys rather than connected."""
        return {}

    def configured(self, ctx):
        raise NotImplementedError

    def publish(self, post, files, caption, ctx):
        """Post it. Returns a Result, or raises PlatformError (AmbiguousError once the post may exist)."""
        raise NotImplementedError

    def account(self, ctx):
        """A short description of the connected account, for the admin page ("" if not connected)."""
        return ""


def check_graph(response, what):
    """The JSON of a Graph API response, or a PlatformError built from its error object."""
    try:
        data = response.json()
    except ValueError:
        data = {}
    if 200 <= response.status_code < 300 and not (isinstance(data, dict) and data.get("error")):
        return data
    error = data.get("error") if isinstance(data, dict) else None
    message = (error or {}).get("message") if isinstance(error, dict) else str(error or response.text)[:200]
    code = (error or {}).get("code") if isinstance(error, dict) else None
    retryable = response.status_code >= 500 or response.status_code == 429 or code in (1, 2, 4, 17, 32, 613)
    raise PlatformError(f"{what}: {message or 'HTTP ' + str(response.status_code)}", retryable=retryable)
