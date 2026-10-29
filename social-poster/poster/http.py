"""
All calls to the platforms go through `client`, so tests can replace it with a fake and nothing real is
ever called in a test.
"""

import requests


class PlatformError(Exception):
    """A platform refused or failed a request. `retryable` says whether trying again later could help."""

    def __init__(self, message, retryable=True):
        super().__init__(message)
        self.retryable = retryable


class AmbiguousError(PlatformError):
    """The request that publishes the post was sent but its answer was lost. The post may exist, so never retry."""

    def __init__(self, message):
        super().__init__(message, retryable=False)


class Client:
    TIMEOUT = (10, 180)

    def __init__(self):
        self.session = requests.Session()

    def send(self, method, url, **kwargs):
        kwargs.setdefault("timeout", self.TIMEOUT)
        return self.session.request(method, url, **kwargs)


client = Client()


def call(method, url, **kwargs):
    """Send a request through the current client; a dropped connection becomes a PlatformError."""
    try:
        return client.send(method, url, **kwargs)
    except requests.RequestException as e:
        raise PlatformError(f"{method} {url.split('?')[0]} failed: {e.__class__.__name__}") from e


def json_of(response, what):
    """The JSON body of a successful response, or a PlatformError that says what the platform answered."""
    try:
        data = response.json()
    except ValueError:
        data = None
    if not 200 <= response.status_code < 300:
        raise PlatformError(f"{what}: HTTP {response.status_code} {_short(data if data is not None else response.text)}",
                            retryable=response.status_code >= 500 or response.status_code == 429)
    return data if data is not None else {}


def _short(value, limit=300):
    text = value if isinstance(value, str) else str(value)
    return text[:limit]
