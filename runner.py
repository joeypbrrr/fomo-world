#!/usr/bin/env python3
"""Scan public sources and write data/ideas.json.

The owner's box should run this every 30 minutes. Git pushes that often are
fine for one JSON file; the static site re-reads it and shows the countdown.

    python3 runner.py --once
    python3 runner.py --once --publish
    python3 runner.py --loop --publish
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from research.config import SCAN_INTERVAL_SECONDS
from research.pipeline import run


def scan_once(publish: bool) -> dict:
    document = run()
    stamp = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S ET")
    print(
        f"scan {stamp} ideas={len(document['ideas'])} tokens={document.get('token_count', 0)}",
        flush=True,
    )
    if publish:
        from publish_data import publish as publish_site
        result = publish_site()
        print("publish", result.get("published") or result.get("detail"), flush=True)
    return document


def loop(interval: int, publish: bool) -> None:
    while True:
        started = time.monotonic()
        try:
            scan_once(publish)
        except Exception as exc:  # noqa: BLE001 - keep the loop alive and visible
            print("scan failed:", exc, flush=True)
        remaining = interval - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="FOMO World 30-minute research runner")
    parser.add_argument("--once", action="store_true", help="Scan a single time and exit")
    parser.add_argument("--loop", action="store_true", help="Scan, sleep, repeat")
    parser.add_argument("--publish", action="store_true", help="Push data JSON and the site to gh-pages")
    parser.add_argument("--interval", type=int, default=SCAN_INTERVAL_SECONDS, help="Seconds between scans in --loop")
    args = parser.parse_args(argv)
    if args.loop and args.once:
        parser.error("pick one of --once or --loop")
    if args.loop:
        loop(args.interval, args.publish)
        return 0
    scan_once(args.publish)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
