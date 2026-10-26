"""Ping the hosted site so Render's free plan doesn't put it to sleep.

Render sleeps a free service after 15 minutes with no traffic. Pinging every
10 minutes leaves a 5-minute margin for late or slow pings.

    py scripts/keepalive.py                     ping every 10 min until Ctrl+C
    py scripts/keepalive.py --every 5           different interval, in minutes
    py scripts/keepalive.py --url https://your-app.onrender.com
    py scripts/keepalive.py --once              one ping; exit code 1 if it failed (GitHub Actions / Task Scheduler)
    py scripts/keepalive.py --once --log scripts/keepalive.log    also append the result to a log file

The URL can also come from the SITE_URL environment variable.
"""
import argparse
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

DEFAULT_URL = "https://www.instrumentationnation.com"
LOG_KEEP_LINES = 1000


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def report(line, log_path):
    print(line, flush=True)
    if not log_path:
        return
    try:
        lines = []
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8") as f:
                lines = f.read().splitlines()[-(LOG_KEEP_LINES - 1):]
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines + [line]) + "\n")
    except OSError:
        pass


def ping(url, log_path=None, timeout=90):
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
        report(f"{now()}  FAIL  {target}  ({getattr(e, 'reason', e)})", log_path)
        return False
    secs = time.monotonic() - start
    ok = status == 200
    woke = "  (it was asleep)" if ok and secs > 10 else ""
    report(f"{now()}  {'ok  ' if ok else 'FAIL'}  HTTP {status}  {secs:.1f}s  {target}{woke}", log_path)
    return ok


def main():
    ap = argparse.ArgumentParser(description="Keep the hosted study tool awake.")
    ap.add_argument("--url", default=os.environ.get("SITE_URL") or DEFAULT_URL)
    ap.add_argument("--every", type=float, default=10, help="minutes between pings (default 10)")
    ap.add_argument("--once", action="store_true", help="ping once and exit")
    ap.add_argument("--log", help="also append results to this file (keeps the last 1000 lines)")
    args = ap.parse_args()

    if args.once:
        sys.exit(0 if ping(args.url, args.log) else 1)

    print(f"Pinging {args.url} every {args.every:g} min. Ctrl+C to stop.", flush=True)
    try:
        while True:
            ping(args.url, args.log)
            time.sleep(args.every * 60)
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
