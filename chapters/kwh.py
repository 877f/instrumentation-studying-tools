"""Household kWh: the energy household appliances use, from a table like the textbook's.

Content only. The engine (sessions, grading) is core/problems.py. The appliance list is
kwh_appliances.csv in this folder: edit that file to change a rating or an hours range.

Terminology: energy = power × time, and kWh = (W × hours) ÷ 1000. A power rating is in
watts. Never "watts per hour".
"""
import csv
import math
import os

from core.fmt import fmt_answer, fmt_num
from core.problems import Answer, Level, Mode, ProblemModule, Setting, Solution

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kwh_appliances.csv")
DAYS_PER_MONTH = 30
RATE = Setting("rate", "Electricity rate", "¢ per kWh", default=12, lo=0.01, hi=1000)
SINGLES = 10               # questions per K1-K3 session in Variations mode
TABLES = 3                 # tables per K4/K5 session in Variations mode
TABLE_ROWS = (3, 6)        # appliances per table in Variations mode
WORKSHEET_ROWS = 6         # Worksheet mode splits the whole list into tables of at most this many
MAX_ROWS = 30              # longest table accepted back from the browser (and longest appliance list)


# ------------------------------------------------------------ appliance list

class Appliance:
    def __init__(self, name, watts, lo, hi, worksheet):
        self.name = name
        self.watts = watts
        self.lo, self.hi = lo, hi             # typical hours per day
        self.worksheet = worksheet            # the fixed hours used in Worksheet mode
        self.choices = hour_choices(lo, hi)   # clean hours for Variations mode


def hour_choices(lo, hi):
    """Clean hours in [lo, hi]: multiples of 0.5 h from 1 h up, multiples of 6 min (0.1 h) below 1 h."""
    if lo == hi:
        return [lo]
    tenths = range(math.ceil(lo * 10 - 1e-9), math.floor(hi * 10 + 1e-9) + 1)
    return [t / 10 for t in tenths if t > 0 and (t < 10 or t % 5 == 0)]


def load(path=DATA_FILE):
    """Read kwh_appliances.csv. Any problem stops the app with the line number, like a formula typo does."""
    name_ = os.path.basename(path)

    def number(text, what, line):
        try:
            v = float(str(text).replace(",", "").strip())
        except ValueError:
            raise ValueError(f"{name_} line {line}: {what} \"{text}\" isn't a number") from None
        if not (math.isfinite(v) and v > 0):
            raise ValueError(f"{name_} line {line}: {what} must be more than 0")
        return v

    out = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = {"appliance", "watts", "hours_min", "hours_max", "worksheet_hours"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{name_}: missing column(s) {', '.join(sorted(missing))}")
        for line, row in enumerate(reader, start=2):
            name = (row["appliance"] or "").strip()
            if not name:
                continue
            watts = number(row["watts"], "watts", line)
            lo = number(row["hours_min"], "hours_min", line)
            hi = number(row["hours_max"], "hours_max", line)
            ws = number(row["worksheet_hours"], "worksheet_hours", line)
            if len(name) > 30:
                raise ValueError(f"{name_} line {line}: keep the appliance name to 30 characters")
            if not lo <= hi <= 24 or ws > 24:
                raise ValueError(f"{name_} line {line}: hours must run from hours_min up to hours_max, at most 24")
            a = Appliance(name, watts, lo, hi, ws)
            if not a.choices:
                raise ValueError(f"{name_} line {line}: no clean hours (0.1 h steps below 1 h, 0.5 h steps above) "
                                 f"between {lo:g} and {hi:g}")
            out.append(a)
    names = [a.name for a in out]
    if not out or len(out) > MAX_ROWS or len(set(names)) != len(names):
        raise ValueError(f"{name_}: needs 1 to {MAX_ROWS} appliances, each with a different name")
    return out


APPLIANCES = load()


# ---------------------------------------------------------------- formatting

def num(x):
    """12200 -> "12,200", 0.30000000000000004 -> "0.3": commas, at most 6 significant figures."""
    return fmt_num(x, 6) if abs(x) < 1e-3 else f"{x:,.6g}"


def cents_text(x):
    return f"{x:,.2f}".rstrip("0").rstrip(".")


def money(x):
    return f"${x:,.2f}"


def kwh(watts, hours):
    return float(f"{watts * hours / 1000:.10g}")


def hours_shown(h):
    return f"{fmt_num(h)} h" + (f" (= {num(h * 60)} min)" if h < 1 else "")


# ---------------------------------------------------------------- questions

LEVELS = [
    Level("K1", "One appliance", "Given the power rating and the hours used, find the kWh."),
    Level("K2", "Unit twists", "The time is in minutes, or the power is in kW."),
    Level("K3", "Rearrange", "Given the kWh, find the watts or the hours."),
    Level("K4", "Appliance table", "3 to 6 appliances: each row's kWh, then the TOTAL."),
    Level("K5", "Monthly cost", f"The daily TOTAL, then the kWh and cost for a {DAYS_PER_MONTH}-day month."),
]
MODES = [
    Mode("worksheet", "Worksheet", "Fixed hours from the sheet."),
    Mode("variations", "Variations", "Random hours from each appliance's typical range."),
    Mode("custom", "Custom", "Type your own hours and wattages, then solve."),
]
LEVEL_TYPES = {"K1": ("kwh",), "K2": ("kwh-min", "kwh-kw"), "K3": ("find-w", "find-h"),
               "K4": ("table",), "K5": ("monthly",)}
ROW_FIELDS = {"find-w": ("kwh", "hours"), "find-h": ("kwh", "watts")}    # every other type: watts and hours
LIMITS = {"watts": 1e6, "hours": 24, "kwh": 1e5}
TYPE_LABELS = {"kwh": "One appliance", "kwh-min": "Time in minutes", "kwh-kw": "Power in kW",
               "find-w": "Find the watts", "find-h": "Find the hours", "table": "Appliance table",
               "monthly": "Table and monthly cost"}
MISS = {"kwh": "Find kWh from watts and hours", "kwh-min": "Find kWh with the time in minutes",
        "kwh-kw": "Find kWh with the power in kW", "find-w": "Find watts from kWh and hours",
        "find-h": "Find hours from kWh and watts"}
# Hints never show a formula: the quiz this practices for allows no notes.
HINTS = {
    "kwh": "Multiply to get watt-hours first, then change watt-hours into kilowatt-hours.",
    "kwh-min": "Change the minutes into hours before anything else.",
    "kwh-kw": "The rating is already in kilowatts.",
    "find-w": "Work backwards: change the kWh into watt-hours, then share them out over the hours.",
    "find-h": "Work backwards: change the kWh into watt-hours, then see how long this rating takes to use them.",
    "table": "Do each row on its own, the same way as Level K1. The TOTAL is all the rows together.",
    "monthly": f"Start from the daily TOTAL. A month here is {DAYS_PER_MONTH} days, and the rate is in cents, "
               "so change cents into dollars at the end.",
}
WH = "That's the energy in watt-hours (Wh). Divide by 1000 to get kWh."
CARRY_TOTAL = ("Your TOTAL matches the sum of your own rows, so the adding is right. "
               "Fix the rows marked wrong and the TOTAL follows.")
CARRY_MONTH = f"Your monthly kWh matches your own TOTAL × {DAYS_PER_MONTH} days, so that step is right. Fix the TOTAL first."
CARRY_COST = "Your cost matches your own monthly kWh × the rate, so that step is right. Fix the monthly kWh first."


def row(a, h):
    return {"name": a.name, "watts": a.watts, "hours": h}


def twists(a, h):
    """K2 twists that make sense here: power in kW from 250 W up, time in minutes up to 3 h."""
    return (["kwh-kw"] if a.watts >= 250 else []) + (["kwh-min"] if h <= 3 else [])


def generate(level, mode, rng, settings):
    fixed = mode == "worksheet"

    def hours(a):
        return a.worksheet if fixed else rng.choice(a.choices)

    if level.id in ("K1", "K2", "K3"):
        pool = list(APPLIANCES) if fixed else rng.sample(APPLIANCES, len(APPLIANCES))
        out, want = [], "kwh-min"
        for i, a in enumerate(pool):
            h = hours(a)
            if level.id == "K1":
                out.append({"type": "kwh", "rows": [row(a, h)]})
            elif level.id == "K2":
                opts = twists(a, h)
                if not opts:
                    continue
                if fixed:                       # alternate the twists down the sheet
                    t = want if want in opts else opts[0]
                    want = {"kwh-min": "kwh-kw", "kwh-kw": "kwh-min"}[want] if t == want else want
                else:
                    t = rng.choice(opts)
                out.append({"type": t, "rows": [row(a, h)]})
            else:
                t = ("find-w", "find-h")[i % 2] if fixed else rng.choice(("find-w", "find-h"))
                other = {"hours": h} if t == "find-w" else {"watts": a.watts}
                out.append({"type": t, "rows": [{"name": a.name, "kwh": kwh(a.watts, h), **other}]})
        return out if fixed else out[:SINGLES]

    t = "table" if level.id == "K4" else "monthly"
    n = len(APPLIANCES)
    if fixed:
        k = -(-n // WORKSHEET_ROWS)
        groups = [APPLIANCES[i * n // k:(i + 1) * n // k] for i in range(k)]
    else:
        lo, hi = min(TABLE_ROWS[0], n), min(TABLE_ROWS[1], n)
        groups = [[APPLIANCES[i] for i in sorted(rng.sample(range(n), rng.randint(lo, hi)))] for _ in range(TABLES)]
    out = []
    for g in groups:
        p = {"type": t, "rows": [row(a, hours(a)) for a in g]}
        if t == "monthly":
            p["rate"] = settings["rate"]
        out.append(p)
    return out


def custom(level, body, settings):
    """A table typed in by the student: Level K4, or K5 when it includes the monthly cost."""
    if level.id not in ("K4", "K5"):
        raise ValueError("A custom problem is a table: Level K4, or K5 for the monthly cost.")
    raw = body.get("rows")
    if not isinstance(raw, list) or not raw:
        raise ValueError("Type the hours for at least one appliance.")
    if len(raw) > MAX_ROWS:
        raise ValueError(f"Use at most {MAX_ROWS} appliances.")
    rows = []
    for r in raw:
        r = r if isinstance(r, dict) else {}
        name, w, h = r.get("name"), r.get("watts"), r.get("hours")
        if not (isinstance(name, str) and 0 < len(name.strip()) <= 30):
            raise ValueError("Every row needs an appliance name.")
        if not _ok(w, LIMITS["watts"]):
            raise ValueError(f"{name}: the power rating must be a number of watts above 0.")
        if not _ok(h, LIMITS["hours"]):
            raise ValueError(f"{name}: the hours must be above 0 and at most 24.")
        rows.append({"name": name.strip(), "watts": w, "hours": h})
    p = {"type": "table" if level.id == "K4" else "monthly", "rows": rows, "custom": True}
    if level.id == "K5":
        p["rate"] = settings["rate"]
    return p


def _ok(v, hi):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 < v <= hi


def valid(level, p):
    if not isinstance(p, dict) or p.get("type") not in LEVEL_TYPES.get(level.id, ()):
        return False
    t = p["type"]
    table = t in ("table", "monthly")
    allowed = {"type", "rows"} | ({"custom"} if table else set()) | ({"rate"} if t == "monthly" else set())
    if not (set(p) <= allowed and "rows" in p and p.get("custom", True) is True):
        return False
    if t == "monthly" and not _ok(p.get("rate"), RATE.hi):
        return False
    rows = p["rows"]
    if not (isinstance(rows, list) and 1 <= len(rows) <= (MAX_ROWS if table else 1)):
        return False
    fields = ROW_FIELDS.get(t, ("watts", "hours"))
    return all(isinstance(r, dict) and set(r) == {"name", *fields} and isinstance(r["name"], str)
               and 0 < len(r["name"]) <= 30 and all(_ok(r[k], LIMITS[k]) for k in fields) for r in rows)


def view(level, p):
    t, rows = p["type"], p["rows"]
    shown = []
    for i, r in enumerate(rows):
        if t == "find-w":
            cells = {"watts": {"input": "w0"}, "hours": {"text": num(r["hours"])}, "kwh": {"text": num(r["kwh"])}}
        elif t == "find-h":
            cells = {"watts": {"text": num(r["watts"])}, "hours": {"input": "h0"}, "kwh": {"text": num(r["kwh"])}}
        else:
            w = f"{num(r['watts'] / 1000)} kW" if t == "kwh-kw" else num(r["watts"])
            h = f"{num(r['hours'] * 60)} min" if t == "kwh-min" else num(r["hours"])
            cells = {"watts": {"text": w}, "hours": {"text": h}, "kwh": {"input": f"r{i}"}}
        shown.append({"name": r["name"], **cells})
    table = t in ("table", "monthly")
    r0 = rows[0]
    prompt = {
        "kwh": "How much energy does it use? Find the kWh.",
        "kwh-min": "How much energy does it use? Find the kWh.",
        "kwh-kw": "How much energy does it use? Find the kWh.",
        "find-w": "It used the energy shown. What is its power rating in watts?",
        "find-h": "It used the energy shown. How many hours was it on?",
        "table": "Find each appliance's kWh, then the TOTAL kWh.",
        "monthly": f"Find each row's kWh and the daily TOTAL. Then find the kWh for a {DAYS_PER_MONTH}-day month "
                   f"and what it costs at {num(p.get('rate', 0))}¢ per kWh.",
    }[t]
    if table:
        desc = f"{'Custom table' if p.get('custom') else 'Table'}: {', '.join(r['name'] for r in rows)}"
        if t == "monthly":
            desc += f" at {num(p['rate'])}¢ per kWh"
    elif t == "find-w":
        desc = f"{r0['name']}: {num(r0['kwh'])} kWh in {num(r0['hours'])} h, find W"
    elif t == "find-h":
        desc = f"{r0['name']}: {num(r0['kwh'])} kWh at {num(r0['watts'])} W, find hours"
    else:
        w = shown[0]["watts"]["text"] + ("" if t == "kwh-kw" else " W")
        h = shown[0]["hours"]["text"] + ("" if t == "kwh-min" else " h")
        desc = f"{r0['name']}: {w} for {h}"
    return {"type": t, "type_label": TYPE_LABELS[t], "prompt": prompt, "hint": HINTS[t], "desc": desc,
            "layout": {"kind": "table", "rows": shown, "total": "total" if table else None,
                       "below": ["month", "cost"] if t == "monthly" else []}}


def row_step(r):
    wh = r["watts"] * r["hours"]
    return (f"{r['name']}: {num(r['watts'])} W × {num(r['hours'])} h = {num(wh)} Wh, "
            f"then {num(wh)} Wh ÷ 1000 = {num(wh / 1000)} kWh")


def solve(level, p):
    t, rows = p["type"], p["rows"]
    r = rows[0]

    if t in ("kwh", "kwh-min", "kwh-kw"):
        e = kwh(r["watts"], r["hours"])
        steps, notes, slips = [], [], [(1000, WH)]
        if t == "kwh-min":
            steps.append(f"Change minutes to hours: {num(r['hours'] * 60)} min ÷ 60 = {num(r['hours'])} h")
            slips.append((60, "Looks like the minutes were used as hours. Change minutes to hours first (÷ 60)."))
        if t == "kwh-kw":
            steps.append(f"Change kW to watts: {num(r['watts'] / 1000)} kW × 1000 = {num(r['watts'])} W")
            notes.append("Shortcut: kW × hours gives kWh straight away.")
            slips.append((0.001, "1000 times too small: the rating was already in kW, so don't divide by 1000 again."))
        steps.append(row_step(r))
        return Solution([Answer("r0", r["name"], "kwh", e, MISS[t], slips)], steps, fmt_answer(e, "kwh"), notes)

    if t in ("find-w", "find-h"):
        wh = r["kwh"] * 1000
        if t == "find-w":
            w, h = float(f"{wh / r['hours']:.10g}"), r["hours"]
            last = f"Divide by the hours: {num(wh)} Wh ÷ {num(h)} h = {num(w)} W"
            ans = Answer("w0", r["name"], "power", w, MISS[t])
        else:
            w, h = r["watts"], float(f"{wh / r['watts']:.10g}")
            last = f"Divide by the watts: {num(wh)} Wh ÷ {num(w)} W = {num(h)} h"
            ans = Answer("h0", r["name"], "hours", h, MISS[t], shown=hours_shown, slips=[
                (0.001, "1000 times too small: change kWh into watt-hours (× 1000) before dividing by the watts."),
                (60, "That's minutes. The box is in hours: divide by 60, or type min after the number.")])
        steps = [f"Change kWh to watt-hours: {num(r['kwh'])} kWh × 1000 = {num(wh)} Wh", last,
                 f"Check: {num(w)} W × {num(h)} h = {num(w * h)} Wh, then ÷ 1000 = {num(w * h / 1000)} kWh"]
        return Solution([ans], steps, ProblemModule._shown(ans, ans.value))

    # tables: K4, and K5 with the monthly cost
    es = [kwh(x["watts"], x["hours"]) for x in rows]
    total = float(f"{sum(es):.10g}")
    keys = [f"r{i}" for i in range(len(rows))]
    month_t = t == "monthly"
    answers = [Answer(k, x["name"], "kwh", e, "A row's kWh", [(1000, WH)]) for k, x, e in zip(keys, rows, es)]
    answers.append(Answer("total", "TOTAL kWh", "kwh", total, "The daily TOTAL" if month_t else "The TOTAL kWh",
                          [(1000, WH)], carry=(lambda v: sum(v[k] for k in keys), keys, CARRY_TOTAL)))
    steps = [row_step(x) for x in rows]
    steps.append(f"TOTAL = {' + '.join(num(e) for e in es)} = {num(total)} kWh")
    big = max(es)
    names = " and ".join(x["name"] for x, e in zip(rows, es) if e == big)
    notes = [f"Biggest energy user: {names}, {num(big)} kWh ({round(100 * big / total)}% of the TOTAL)."]
    headline = f"TOTAL {fmt_answer(total, 'kwh')}"
    if month_t:
        rate = p["rate"]
        month = float(f"{total * DAYS_PER_MONTH:.10g}")
        cents = month * rate
        cost = cents / 100
        steps += [f"Month: {num(total)} kWh per day × {DAYS_PER_MONTH} days = {num(month)} kWh",
                  f"Cost: {num(month)} kWh × {num(rate)}¢ per kWh = {cents_text(cents)}¢ = {money(cost)}"]
        answers += [
            Answer("month", "Monthly kWh", "kwh", month, "kWh for the month",
                   [(1 / DAYS_PER_MONTH, f"That's one day. Multiply by {DAYS_PER_MONTH} days for the month."),
                    (1000, WH)],
                   carry=(lambda v: v["total"] * DAYS_PER_MONTH, ["total"], CARRY_MONTH)),
            Answer("cost", "Monthly cost ($)", "cost", cost, "The monthly cost",
                   [(100, "That's the cost in cents. Divide by 100 for dollars, or type ¢ after the number."),
                    (1 / DAYS_PER_MONTH, f"That's one day's cost. A month here is {DAYS_PER_MONTH} days.")],
                   shown=money, short=money, carry=(lambda v: v["month"] * rate / 100, ["month"], CARRY_COST)),
        ]
        headline = f"{fmt_answer(month, 'kwh')} a month · {money(cost)}"
    return Solution(answers, steps, headline, notes)


# Review screens only (results and session summary), never during questions.
FORMULAS = [
    {"title": "Energy", "items": [
        {"name": "Energy", "formula": "energy = power × time",
         "note": "A power rating is in watts (W). Energy is in kilowatt-hours (kWh)."},
        {"name": "Kilowatt-hours", "formula": "kWh = (W × hours) ÷ 1000",
         "note": "W × hours gives watt-hours (Wh). Divide by 1000 for kWh."},
        {"name": "Unit changes", "formula": "hours = minutes ÷ 60 · W = kW × 1000", "note": None},
        {"name": "Find the watts", "formula": "W = (kWh × 1000) ÷ hours", "note": None},
        {"name": "Find the hours", "formula": "hours = (kWh × 1000) ÷ W", "note": None},
    ]},
    {"title": "A month's bill", "items": [
        {"name": "Daily TOTAL", "formula": "TOTAL kWh = the rows added up", "note": None},
        {"name": "Month", "formula": f"monthly kWh = daily TOTAL × {DAYS_PER_MONTH}", "note": None},
        {"name": "Cost", "formula": "cost ($) = monthly kWh × rate (¢ per kWh) ÷ 100", "note": None},
    ]},
]

MODULE = ProblemModule(
    id="kwh",
    title="Household kWh",
    badge="kWh",
    intro="Find the energy household appliances use, from a table like the textbook's. "
          "Nothing is saved: your stats reset when you close the page.",
    reminder="Energy = power × time, so kWh = (W × hours) ÷ 1000.",
    levels=LEVELS,
    modes=MODES,
    settings=[RATE],
    generate=generate,
    valid=valid,
    view=view,
    solve=solve,
    custom=custom,
    formulas=FORMULAS,
    extra={"appliances": [{"name": a.name, "watts": a.watts} for a in APPLIANCES]},
)
