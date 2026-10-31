#!/usr/bin/env python3
"""
TestDay social poster: the web service. Run it with `python app.py`.

It serves the admin page, and once a minute checks whether it is time to post the day's post.
"""

import logging
import os
import sys

import tornado.ioloop
import tornado.httpserver

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poster.config import Config  # noqa: E402
from poster.runner import Runner  # noqa: E402
from poster.store import Store  # noqa: E402
from poster.web import make_app  # noqa: E402

log = logging.getLogger("poster")


def build(cfg=None):
    cfg = cfg or Config.from_env()
    store = Store(cfg.db_path)
    runner = Runner(cfg, store)
    return cfg, store, runner


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg, store, runner = build()
    busy = {"on": False}

    def tick():
        if busy["on"]:
            return
        busy["on"] = True
        try:
            results = runner.tick()
            if results:
                log.info("daily run: %s", [(r["platform"], r["state"]) for r in results])
        except Exception:  # noqa: BLE001
            log.exception("daily run failed")
        finally:
            busy["on"] = False

    app = make_app(cfg, store, runner, tick)
    server = tornado.httpserver.HTTPServer(app, xheaders=True)
    server.listen(cfg.port, address="0.0.0.0")
    loop = tornado.ioloop.IOLoop.current()
    # once a minute, and soon after start-up (a service that was asleep at posting time catches up when it wakes)
    tornado.ioloop.PeriodicCallback(lambda: loop.run_in_executor(None, tick), 60_000).start()
    loop.call_later(20, lambda: loop.run_in_executor(None, tick))
    log.info("TestDay social poster on port %s; posting %s at %s %s; platforms: %s", cfg.port,
             "ON" if cfg.posting_enabled else "OFF", cfg.post_time, cfg.timezone, ", ".join(cfg.platforms))
    loop.start()


if __name__ == "__main__":
    main()
