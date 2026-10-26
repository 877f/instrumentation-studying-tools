"""Instrumentation Nation study tool: Flask server.

Local:   py app.py            (prints a LAN URL for your phone)
Hosted:  gunicorn app:app     (see gunicorn.conf.py)

The server is stateless. Each person's progress lives in their own browser,
and Weak spots mode sends those stats along when it asks for questions.
"""
import argparse
import logging
import math
import os
import random
import socket
import sys

from flask import Flask, jsonify, request, send_from_directory

from chapters import BY_ID as CHAPTERS_BY_ID, CHAPTERS
from core import grader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODES = ("worksheet", "variations", "weak")

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


def bad(msg, code=400):
    return jsonify({"error": msg}), code


def weak_weight(s):
    """Higher = more likely in Weak spots mode. Unseen or never-missed templates weigh 1."""
    a, c = s["attempts"], s["correct"]
    w = 1 + 10 * (a - c) / (a + 1)
    if s["last_correct"] is False:
        w *= 2
    return w


def clean_stats(raw):
    """Browser-sent stats -> {template_id: {"attempts", "correct", "last_correct"}}; junk is dropped."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for k, v in list(raw.items())[:500]:
        try:
            tid, a, c = int(k), int(v.get("attempts", 0)), int(v.get("correct", 0))
        except (TypeError, ValueError, AttributeError):
            continue
        last = v.get("last_correct")
        out[tid] = {"attempts": max(a, 0), "correct": min(max(c, 0), max(a, 0)),
                    "last_correct": last if isinstance(last, bool) else None}
    return out


def build_session(chapter, mode, parts, count, shuffle, template_ids, stats):
    if template_ids:
        pool = [chapter.by_id[i] for i in dict.fromkeys(template_ids) if i in chapter.by_id]
    else:
        pool = [t for t in chapter.templates if t.part in parts]
    if not pool:
        return []
    n = len(pool) if count == "all" else min(count, len(pool))
    rng = random.Random()
    if mode == "weak":
        unseen = {"attempts": 0, "correct": 0, "last_correct": None}
        keyed = [(rng.random() ** (1 / weak_weight(stats.get(t.id, unseen))), t) for t in pool]
        chosen = [t for _, t in sorted(keyed, key=lambda kt: kt[0], reverse=True)[:n]]
    else:
        chosen = rng.sample(pool, n) if n < len(pool) else list(pool)
        if shuffle:
            rng.shuffle(chosen)
        else:
            chosen.sort(key=lambda t: t.id)
    varied = mode != "worksheet"
    return [t.question(chapter, t.generate(rng) if varied else dict(t.worksheet), varied) for t in chosen]


def worksheet_chapter(cid):
    c = CHAPTERS_BY_ID.get(cid) if isinstance(cid, str) else None
    return c if getattr(c, "type", None) == "worksheet" else None


def formula_module(mid):
    m = CHAPTERS_BY_ID.get(mid) if isinstance(mid, str) else None
    return m if getattr(m, "type", None) == "formula" else None


def lookup():
    """Template + givens from a check/reveal request, or (None, None, body) if invalid."""
    body = request.get_json(silent=True) or {}
    chapter = worksheet_chapter(body.get("chapter"))
    t = chapter.by_id.get(body.get("template_id")) if chapter else None
    params = body.get("params")
    ok = (t is not None and isinstance(params, dict) and set(params) == set(t.kind.fields) and
          all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0
              for v in params.values()))
    return (t, params, body) if ok else (None, None, body)


# ------------------------------------------------------------------- routes

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/healthz")
def healthz():
    return "ok", 200, {"Content-Type": "text/plain", "Cache-Control": "no-store"}


@app.get("/api/chapters")
def api_chapters():
    return jsonify([c.summary() for c in CHAPTERS])


@app.get("/api/chapters/<cid>")
def api_chapter(cid):
    chapter = CHAPTERS_BY_ID.get(cid)
    return jsonify(chapter.detail()) if chapter else bad("No such chapter.", 404)


@app.post("/api/session")
def api_session():
    body = request.get_json(silent=True) or {}
    chapter = worksheet_chapter(body.get("chapter"))
    if chapter is None:
        return bad("No such chapter.")
    mode = body.get("mode", "worksheet")
    if mode not in MODES:
        return bad("Unknown mode.")
    parts = [p for p in body.get("parts") or [] if p in chapter.parts]
    ids = [i for i in body.get("template_ids") or [] if isinstance(i, int)]
    if not parts and not ids:
        return bad("Pick at least one part.")
    count = body.get("count", "all")
    if not (isinstance(count, int) and not isinstance(count, bool) and count > 0):
        count = "all"
    questions = build_session(chapter, mode, parts, count, bool(body.get("shuffle")), ids,
                              clean_stats(body.get("stats")))
    if not questions:
        return bad("No questions matched.")
    return jsonify({"chapter": chapter.id, "mode": mode, "questions": questions})


@app.post("/api/check")
def api_check():
    t, params, body = lookup()
    if t is None:
        return bad("Bad question data. Start a new session.")
    return jsonify(grader.check(t, params, str(body.get("answer", ""))[:200]))


@app.post("/api/reveal")
def api_reveal():
    t, params, _ = lookup()
    if t is None:
        return bad("Bad question data. Start a new session.")
    return jsonify(grader.reveal(t, params))


# ------------------------------------------------------- formula drills
# Stateless like the rest: the browser keeps the in-session stats and repeat queue.

def formula_lookup(body):
    """-> (module, level, formula) from a request body, or None if anything is invalid."""
    m = formula_module(body.get("module"))
    level = m.levels_by_id.get(body.get("level")) if m else None
    f = m.by_key.get(body.get("key")) if level else None
    return (m, level, f) if f is not None and f.key in level.keys else None


def numeric_params(f, params):
    ok = (isinstance(params, dict) and set(params) == set(f.knowns) and
          all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v > 0
              for v in params.values()))
    return params if ok else None


@app.post("/api/formula/session")
def api_formula_session():
    body = request.get_json(silent=True) or {}
    m = formula_module(body.get("module"))
    level = m.levels_by_id.get(body.get("level")) if m else None
    if level is None:
        return bad("No such level.")
    return jsonify({"module": m.id, "level": level.id, "questions": m.session(level, random.Random())})


@app.post("/api/formula/question")
def api_formula_question():
    found = formula_lookup(request.get_json(silent=True) or {})
    if found is None:
        return bad("Bad question data. Go back and start the level again.")
    m, level, f = found
    return jsonify({"question": m.question(level, f, random.Random())})


@app.post("/api/formula/check")
def api_formula_check():
    body = request.get_json(silent=True) or {}
    found = formula_lookup(body)
    if found is None:
        return bad("Bad question data. Go back and start the level again.")
    m, level, f = found
    answer = str(body.get("answer", ""))[:200]
    if level.numeric:
        params = numeric_params(f, body.get("params"))
        if params is None:
            return bad("Bad question data. Go back and start the level again.")
        return jsonify(m.check_numeric(f, params, answer))
    return jsonify(m.check_symbolic(f, answer))


@app.post("/api/formula/reveal")
def api_formula_reveal():
    body = request.get_json(silent=True) or {}
    found = formula_lookup(body)
    if found is None:
        return bad("Bad question data. Go back and start the level again.")
    m, level, f = found
    params = numeric_params(f, body.get("params")) if level.numeric else None
    if level.numeric and params is None:
        return bad("Bad question data. Go back and start the level again.")
    return jsonify(m.reveal(f, params, level.numeric))


@app.post("/api/formula/blank")
def api_formula_blank():
    body = request.get_json(silent=True) or {}
    m = formula_module(body.get("module"))
    if m is None:
        return bad("No such module.")
    answers = body.get("answers")
    return jsonify(m.grade_blank(answers if isinstance(answers, dict) else {}))


@app.get("/api/formula/<mid>/wheel")
def api_formula_wheel(mid):
    m = formula_module(mid)
    return jsonify(m.wheel()) if m else bad("No such module.", 404)


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
    ap = argparse.ArgumentParser(description="Instrumentation Nation study tool")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    args = ap.parse_args()

    if not port_free(args.port):
        print(f"Port {args.port} is already in use. Is the study tool already running in another window?\n"
              f"Close it, or run on another port:  py app.py --port 5050")
        sys.exit(1)

    ips = lan_ips()
    line = "=" * 64
    print(line)
    print(" Instrumentation Nation study tool is running")
    print(f"   This computer:          http://localhost:{args.port}")
    if ips:
        print(f"   Phone / other device:   http://{ips[0]}:{args.port}   (same Wi-Fi)")
        for ip in ips[1:]:
            print(f"   Other address:          http://{ip}:{args.port}   (often a virtual adapter)")
    else:
        print("   No LAN address found. Are you connected to Wi-Fi?")
    print(" Phone can't connect? See README.md -> 'Phone can't connect'.")
    print(" Press Ctrl+C to stop.")
    print(line, flush=True)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)   # keep the URL banner readable
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
