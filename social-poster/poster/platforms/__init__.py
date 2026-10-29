"""The five platforms, in the order they are shown."""

from .meta import Facebook, Instagram
from .threads import Threads
from .tiktok import TikTok
from .youtube import YouTube

PLATFORMS = {p.name: p for p in (YouTube(), TikTok(), Instagram(), Threads(), Facebook())}
