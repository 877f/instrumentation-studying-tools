"""Chapter 2 study tool: Flask server.

Run:  py app.py            (or: python app.py)
Then open the LAN URL it prints on your phone/laptop (same Wi-Fi).
"""
import argparse
import json
import logging
import math
import os
import random
import socket
import sys
import threading
import uuid
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory

import grader
from questions import BY_ID, PARTS, TEMPLATES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")
MAX_SESSIONS_KEPT = 100

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"), static_url_path="/static")
_lock = threading.Lock()
_recorded = set()   # question uids already counted, so a double-submit isn't counted twice


# ---------------------------------------------------------------- progress

def _empty_progress():
    return {"version": 1, "templates": {}, "sessions": []}


def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return _empty_progress()
    try:
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("templates", {})
        data.setdefault("sessions", [])
        return data
    except (OSError, ValueError):
        backup = PROGRESS_FILE + datetime.now().strftime(".broken-%Y%m%d-%H%M%S")
        try:
            os.replace(PROGRESS_FILE, backup)
            print(f"progress.json was unreadable; moved it to {backup} and started fresh.")
        except OSError:
            pass
        return _empty_progress()


def save_progress(data):
    tmp = PROGRESS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, PROGRESS_FILE)


def _now():
    return datetime.now().isoformat(timespec="seconds")


def record_attempt(template_id, correct, uid):
    with _lock:
        if uid and uid in _recorded:
            return
        if uid:
            _recorded.add(uid)
        data = load_progress()
        s = data["templates"].setdefault(str(template_id), {"attempts": 0, "correct": 0, "last_seen": None,
                                                            "last_correct": None})
        s["attempts"] += 1
        s["correct"] += int(correct)
        s["last_seen"] = _now()
        s["last_correct"] = bool(correct)
        save_progress(data)


def template_stats(data, tid):
    return data["templates"].get(str(tid), {"attempts": 0, "correct": 0, "last_seen": None, "last_correct": None})


def weak_weight(s):
    """Higher = more likely in Weak spots mode. Unseen or never-missed templates weigh 1."""
    a, c = s["attempts"], s["correct"]
    w = 1 + 10 * (a - c) / (a + 1)
    if s.get("last_correct") is False:
        w *= 2
    return w


# ------------------------------------------------------------------ helpers

def _params_ok(t, params):
    if not isinstance(params, dict) or set(params) != set(t.kind.fields):
        return False
    return all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0
               for v in params.values())


def _lookup():
    body = request.get_json(silent=True) or {}
    t = BY_ID.get(body.get("template_id"))
    if t is None or not _params_ok(t, body.get("params")):
        return None, None, body
    return t, body["params"], body


def build_session(mode, parts, count, shuffle, template_ids=None):
    pool = [BY_ID[i] for i in template_ids if i in BY_ID] if template_ids else \
        [t for t in TEMPLATES if t.part in parts]
    if not pool:
        return []
    n = len(pool) if count in (None, "all") else max(1, min(int(count), len(pool)))
    rng = random.Random()
    data = load_progress()
    if mode == "weak":
        keyed = [(rng.random() ** (1 / weak_weight(template_stats(data, t.id))), t) for t in pool]
        chosen = [t for _, t in sorted(keyed, key=lambda kt: kt[0], reverse=True)[:n]]
    else:
        chosen = rng.sample(pool, n) if n < len(pool) else list(pool)
        if shuffle:
            rng.shuffle(chosen)
        else:
            chosen.sort(key=lambda t: t.id)
    out = []
    for t in chosen:
        varied = mode != "worksheet"
        q = t.question(t.generate(rng) if varied else dict(t.worksheet), varied)
        q["uid"] = uuid.uuid4().hex
        s = template_stats(data, t.id)
        q["history"] = {"attempts": s["attempts"], "correct": s["correct"]}
        out.append(q)
    return out


# ------------------------------------------------------------------- routes

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/stats")
def api_stats():
    data = load_progress()
    templates = []
    for t in TEMPLATES:
        s = template_stats(data, t.id)
        templates.append({"id": t.id, "part": t.part, "text": t.render(t.worksheet), **s})
    return jsonify({
        "parts": {str(k): {"title": v, "count": sum(t.part == k for t in TEMPLATES)} for k, v in PARTS.items()},
        "templates": templates,
        "sessions": data["sessions"][-10:],
    })


@app.post("/api/session")
def api_session():
    body = request.get_json(silent=True) or {}
    mode = body.get("mode", "worksheet")
    if mode not in ("worksheet", "variations", "weak"):
        return jsonify({"error": "Unknown mode."}), 400
    parts = [p for p in body.get("parts", [1, 2, 3, 4, 5]) if p in PARTS]
    ids = body.get("template_ids")
    if not parts and not ids:
        return jsonify({"error": "Pick at least one part."}), 400
    count = body.get("count", "all")
    if count != "all" and not (isinstance(count, int) and count > 0):
        count = "all"
    questions = build_session(mode, parts, count, bool(body.get("shuffle")), ids)
    if not questions:
        return jsonify({"error": "No questions matched."}), 400
    return jsonify({"mode": mode, "questions": questions})


@app.post("/api/check")
def api_check():
    t, params, body = _lookup()
    if t is None:
        return jsonify({"error": "Bad question data. Start a new session."}), 400
    result = grader.check(t, params, str(body.get("answer", ""))[:200])
    if result["status"] != "unparsed":
        record_attempt(t.id, result["status"] == "correct", body.get("uid"))
    return jsonify(result)


@app.post("/api/reveal")
def api_reveal():
    t, params, body = _lookup()
    if t is None:
        return jsonify({"error": "Bad question data. Start a new session."}), 400
    record_attempt(t.id, False, body.get("uid"))
    return jsonify(grader.reveal(t, params))


@app.post("/api/session/complete")
def api_session_complete():
    body = request.get_json(silent=True) or {}
    entry = {
        "finished": _now(),
        "mode": body.get("mode"),
        "answered": int(body.get("answered", 0)),
        "correct": int(body.get("correct", 0)),
        "missed": [i for i in body.get("missed", []) if i in BY_ID],
    }
    with _lock:
        data = load_progress()
        data["sessions"] = (data["sessions"] + [entry])[-MAX_SESSIONS_KEPT:]
        save_progress(data)
    return jsonify({"ok": True})


@app.post("/api/progress/reset")
def api_reset():
    with _lock:
        save_progress(_empty_progress())
        _recorded.clear()
    return jsonify({"ok": True})


# ------------------------------------------------------------------ startup

def lan_ips():
    """Best guess at this machine's LAN address first, then any others."""
    ips = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))       # no packets are sent; this just picks the outgoing interface
        ips.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in ips and not ip.startswith(("127.", "169.254.")):   # skip loopback / link-local
                ips.append(ip)
    except OSError:
        pass
    return ips


def port_free(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser(description="Chapter 2 study tool")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    args = ap.parse_args()

    if not port_free(args.port):
        print(f"Port {args.port} is already in use. Is the study tool already running in another window?\n"
              f"Close it, or run on another port:  py app.py --port 5050")
        sys.exit(1)

    ips = lan_ips()
    line = "=" * 64
    print(line)
    print(" Chapter 2 Study Tool is running")
    print(f"   This computer:          http://localhost:{args.port}")
    if ips:
        print(f"   Phone / other device:   http://{ips[0]}:{args.port}   (same Wi-Fi)")
        for ip in ips[1:]:
            print(f"   Other address:          http://{ip}:{args.port}   (often a virtual adapter)")
    else:
        print("   No LAN address found. Are you connected to Wi-Fi?")
    print(f" Progress file: {PROGRESS_FILE}")
    print(" Windows may ask to allow Python through the firewall: click Allow.")
    print(" Phone can't connect? See README.md -> 'Phone can't connect'.")
    print(" Press Ctrl+C to stop.")
    print(line, flush=True)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)   # keep the URL banner readable
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
