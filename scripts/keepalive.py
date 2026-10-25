"""Ping the hosted site so Render's free plan doesn't put it to sleep.

Render sleeps a free service after 15 minutes with no traffic. The default
interval is 14 minutes, because a ping exactly every 15 can land just after it
has gone to sleep.

    py scripts/keepalive.py                     ping every 14 min until Ctrl+C
    py scripts/keepalive.py --every 10          different interval, in minutes
    py scripts/keepalive.py --url https://your-app.onrender.com
    py scripts/keepalive.py --once              one ping; exit code 1 if it failed (used by GitHub Actions)

The URL can also come from the SITE_URL environment variable.
"""
import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

DEFAULT_URL = "https://instrumentationnation.com"


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ping(url, timeout=90):
    """GET <url>/healthz. A sleeping free service can take ~1 min to answer, hence the long timeout."""
    target = url.rstrip("/") + "/healthz"
    start = time.monotonic()
    try:
        req = urllib.request.Request(target, headers={"User-Agent": "instrumentation-nation-keepalive"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
    except (urllib.error.URLError, OSError) as e:
        print(f"{now()}  FAIL  {target}  ({getattr(e, 'reason', e)})", flush=True)
        return False
    secs = time.monotonic() - start
    ok = status == 200
    woke = "  (it was asleep)" if ok and secs > 10 else ""
    print(f"{now()}  {'ok  ' if ok else 'FAIL'}  HTTP {status}  {secs:.1f}s  {target}{woke}", flush=True)
    return ok


def main():
    ap = argparse.ArgumentParser(description="Keep the hosted study tool awake.")
    ap.add_argument("--url", default=os.environ.get("SITE_URL") or DEFAULT_URL)
    ap.add_argument("--every", type=float, default=14, help="minutes between pings (default 14)")
    ap.add_argument("--once", action="store_true", help="ping once and exit")
    args = ap.parse_args()

    if args.once:
        sys.exit(0 if ping(args.url) else 1)

    print(f"Pinging {args.url} every {args.every:g} min. Ctrl+C to stop.", flush=True)
    try:
        while True:
            ping(args.url)
            time.sleep(args.every * 60)
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
