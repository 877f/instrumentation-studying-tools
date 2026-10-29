"""Geometry, Chapter 2: every kind of problem, as a generator plus a solver.

The textbook's exercises are the spec for these types and their test fixtures, but they are
not in this file: the site is public. Each generator makes fresh givens with the same structure
and difficulty, and each solver computes the answer, so the answer key is code.

Givens that are measurements are strings ("16.0", "9.200"): their trailing zeros decide how many
significant figures the textbook-style answer gets. Whole-degree angles are treated as exact.
Figures are drawn from each problem's own numbers (core/figures.py), never copied from the book.
"""
import math
from decimal import Decimal as D
from fractions import Fraction

from core.answers import PI, SHOW_UNIT, Ident, Num, Sym, dsqrt, fmt_mid as g, fmt_pi
from core.figures import (Fig, ang, circle_points, fan, height, lerp, meet, mid, parallels, pol,
                          quadrilateral, transversal, triangle)
from core.study import Solution, Type, approx, choice, given, keys, meas, pick_letters, sig, whole

RANGES = {"mm": (8, 900), "cm": (4, 600), "m": (0.3, 40), "in": (0.4, 60), "ft": (0.4, 250), "yd": (3, 900)}
UNITS = tuple(RANGES)
HALF = D("0.5")


def U(p):
    return SHOW_UNIT[p["unit"]]


def U2(p):
    return SHOW_UNIT[p["unit"]] + "²"


def gv(p, key):
    return f"{p[key]} {U(p)}"


def figs(rng):
    return rng.choice((2, 3, 3, 3, 3, 4))


def meas_u(rng, unit, n=None, lo=1.0, hi=1.0):
    a, b = RANGES[unit]
    return meas(rng, a * lo, b * hi, n or 3)


def near(rng, x, lo, hi, n=3):
    return meas(rng, float(x) * lo, float(x) * hi, n)


def letters_ok(p, key, n, forbid=""):
    s = p[key]
    if not (isinstance(s, str) and len(s) == n and s.isalpha() and s.isupper() and len(set(s)) == n):
        raise ValueError(key)
    if any(ch in forbid for ch in s):
        raise ValueError(key)
    return s


def dtan(deg):
    return D(repr(math.tan(math.radians(deg))))


def dcos(deg):
    return D(repr(math.cos(math.radians(deg))))


def deg(x):
    return f"{g(x)}°"


def angle_num(value, slips=()):
    return Num(value, "angle", slips=slips)


# ====================================================================== 2.1

# --- Fig. 2.10's layout: line L-V-R, V-P straight up, V-S between V-P and the near end -------------

FAN_ASKS = ("acute", "right", "straight", "obtuse", "sides", "adjacent")
FAN_ANGLE_ASKS = ("complement", "supplement", "other", "obtuse")


def fan_roles(p):
    left, v, right, slant, perp = p["letters"]
    near_, far = (right, left) if p["side"] == "right" else (left, right)
    return left, v, right, slant, perp, near_, far


def fan_valid(p, asks):
    keys(p, "letters", "side", "theta", "ask")
    letters_ok(p, "letters", 5)
    choice(p, "side", ("right", "left"))
    whole(p, "theta", 5, 85)
    choice(p, "ask", asks)
    return True


def fan_fig(p, mark=False):
    left, v, right, slant, perp, near_, far = fan_roles(p)
    th = p["theta"]
    f = Fig(f"Line {left}{v}{right} with {v} between {left} and {right}. Ray {v}{perp} points straight up, "
            f"at a right angle to the line. Ray {v}{slant} lies between {v}{perp} and {v}{near_}.")
    d = th if p["side"] == "right" else 180 - th
    O = (0, 0)
    fan(f, O, [(left, 180, True), (right, 0, True), (perp, 90, False), (slant, d, False)])
    f.label(O, v, 270, 14)
    f.right(O, 0 if p["side"] == "right" else 90, 11)
    if mark:
        f.arc(O, 0, th, f"{th}°", r=30) if p["side"] == "right" else f.arc(O, 180 - th, 180, f"{th}°", r=30)
    return f.out()


def fan_ident_view(p):
    left, v, right, slant, perp, near_, far = fan_roles(p)
    a = f"∠{slant}{v}{near_}"
    text = {"acute": "Name the two acute angles in the figure.",
            "right": "Name the two right angles in the figure.",
            "straight": "Name the straight angle in the figure.",
            "obtuse": "Name the obtuse angle in the figure.",
            "sides": f"Name the two sides of {a}.",
            "adjacent": f"Name the acute angle that is adjacent to {a}."}[p["ask"]]
    hint = {"acute": "Acute means less than 90°. The ray between the two arms of the right angle splits it into two.",
            "right": "A right angle is 90°, shown by the small square. The upright ray makes one on each side.",
            "straight": "A straight angle is 180°: its two sides point opposite ways along one line.",
            "obtuse": "Obtuse means more than 90° but less than 180°.",
            "sides": "The sides of an angle are the two rays that form it. Both start at the vertex, the middle letter.",
            "adjacent": "Adjacent angles share the vertex and one side, and don't overlap."}[p["ask"]]
    return {"text": text, "hint": hint, "figure": fan_fig(p)}


def fan_ident_solve(p):
    left, v, right, slant, perp, near_, far = fan_roles(p)
    th, L = p["theta"], p["letters"]
    s1, s2 = f"{slant}{v}{near_}", f"{perp}{v}{slant}"
    ask = p["ask"]
    if ask == "acute":
        return Solution(Ident([[s1], [s2]], 2, "angle", L, f"∠{s1} and ∠{s2}"),
                        [f"∠{s1} = {th}° and ∠{s2} = 90° − {th}° = {90 - th}°. Both are less than 90°.",
                         f"Every other angle at {v} is 90° or more, so these are the only acute ones."])
    if ask == "right":
        return Solution(Ident([[f"{left}{v}{perp}"], [f"{perp}{v}{right}"]], 2, "angle", L,
                              f"∠{left}{v}{perp} and ∠{perp}{v}{right}"),
                        [f"{v}{perp} is at 90° to line {left}{right} (the square mark).",
                         f"So the angles on both sides of it, ∠{left}{v}{perp} and ∠{perp}{v}{right}, are 90°."])
    if ask == "straight":
        return Solution(Ident([[f"{left}{v}{right}"]], 1, "angle", L, f"∠{left}{v}{right}"),
                        [f"{v}{left} and {v}{right} point opposite ways along one line: ∠{left}{v}{right} = 180°."])
    if ask == "obtuse":
        return Solution(Ident([[f"{far}{v}{slant}"]], 1, "angle", L, f"∠{far}{v}{slant}"),
                        [f"∠{far}{v}{slant} = 180° − {th}° = {180 - th}°, which is between 90° and 180°."])
    if ask == "sides":
        return Solution(Ident([[f"{v}{slant}"], [f"{v}{near_}"]], 2, "pair", L, f"{v}{slant} and {v}{near_}"),
                        [f"∠{s1} is formed by the rays {v}{slant} and {v}{near_}. Its vertex is {v}."])
    return Solution(Ident([[s2]], 1, "angle", L, f"∠{s2}"),
                    [f"∠{s2} shares the vertex {v} and the side {v}{slant} with ∠{s1}.",
                     f"It is acute: 90° − {th}° = {90 - th}°. (∠{far}{v}{slant} shares that side too, but it's obtuse.)"])


def fan_gen(asks, lo, hi):
    return lambda rng: {"letters": pick_letters(rng, 5), "side": rng.choice(("right", "left")),
                        "theta": rng.randint(lo, hi), "ask": rng.choice(asks)}


def fan_angle_view(p):
    left, v, right, slant, perp, near_, far = fan_roles(p)
    a, th = f"∠{slant}{v}{near_}", p["theta"]
    text = {"complement": f"{a} = {th}°. Find its complement.",
            "supplement": f"{a} = {th}°. Find its supplement.",
            "other": f"{a} = {th}°. Find ∠{perp}{v}{slant}.",
            "obtuse": f"{a} = {th}°. Find ∠{far}{v}{slant}."}[p["ask"]]
    hint = {"complement": "Two angles are complementary when they add up to 90°.",
            "supplement": "Two angles are supplementary when they add up to 180°.",
            "other": f"∠{perp}{v}{near_} is a right angle, and ray {v}{slant} splits it into two parts.",
            "obtuse": f"{far}, {v} and {near_} lie on one straight line, and the angles along a straight line add to 180°."
            }[p["ask"]]
    return {"text": text, "hint": hint, "figure": fan_fig(p, mark=True)}


def fan_angle_solve(p):
    left, v, right, slant, perp, near_, far = fan_roles(p)
    th = p["theta"]
    if p["ask"] in ("complement", "other"):
        first = ("The complement makes 90° with it." if p["ask"] == "complement" else
                 f"∠{perp}{v}{near_} = 90°, so ∠{perp}{v}{slant} + {th}° = 90°.")
        return Solution(angle_num(90 - th, [(180 - th, "That's the supplement (180°). The complement adds to 90°.")]),
                        [first, f"90° − {th}° = {90 - th}°"])
    first = ("The supplement makes 180° with it." if p["ask"] == "supplement" else
             f"∠{far}{v}{slant} and ∠{slant}{v}{near_} lie along the straight line {left}{right}, so they add to 180°.")
    return Solution(angle_num(180 - th, [(90 - th, "That's the complement (90°). The supplement adds to 180°.")]),
                    [first, f"180° − {th}° = {180 - th}°"])


# --- Fig. 2.11's layout: AD across, FE upright, CB slanted, all through O ----------------------------

THREE = {  # ask -> (answer from alpha, steps)
    "AOC": (lambda a: 90 - a, lambda a: ["AD and FE are perpendicular, so ∠AOF = 90°.",
                                        f"∠AOC = ∠AOF − ∠COF = 90° − {a}° = {90 - a}°"]),
    "AOB": (lambda a: 90 + a, lambda a: [f"∠AOC = 90° − {a}° = {90 - a}° (∠AOF is a right angle).",
                                        f"C, O and B lie on one line: ∠AOB = 180° − {90 - a}° = {90 + a}°"]),
    "BOD": (lambda a: 90 - a, lambda a: [f"∠AOC = 90° − {a}° = {90 - a}° (∠AOF is a right angle).",
                                        f"∠BOD and ∠AOC are vertical angles, so they are equal: {90 - a}°"]),
    "BOE": (lambda a: a, lambda a: [f"∠BOE and ∠COF are vertical angles (lines CB and FE cross at O).",
                                   f"So ∠BOE = ∠COF = {a}°"]),
    "COD": (lambda a: 90 + a, lambda a: [f"∠COD = ∠COF + ∠FOD = {a}° + 90° = {90 + a}°"]),
    "COE": (lambda a: 180 - a, lambda a: [f"F, O and E lie on one line, so ∠COE = 180° − ∠COF.",
                                         f"180° − {a}° = {180 - a}°"]),
    "BOF": (lambda a: 180 - a, lambda a: [f"C, O and B lie on one line, so ∠BOF = 180° − ∠COF.",
                                         f"180° − {a}° = {180 - a}°"]),
}


def three_fig(a):
    f = Fig(f"Lines AD (across), FE (upright) and CB (slanted, C upper left, B lower right) all cross at O. "
            f"∠FOD is a right angle and the angle between OC and OF is {a}°.")
    O = (0, 0)
    pts = {"A": pol(O, 1.0, 180), "D": pol(O, 1.0, 0), "F": pol(O, 0.95, 90), "E": pol(O, 0.95, 270),
           "C": pol(O, 1.0, 90 + a), "B": pol(O, 1.0, 270 + a)}
    for x, y in (("A", "D"), ("E", "F"), ("B", "C")):
        f.seg(pts[x], pts[y], arrow="ab")
    for name, d in (("A", 180), ("D", 0), ("F", 90), ("E", 270), ("C", 90 + a), ("B", 270 + a)):
        f.label(pts[name], name, d, 13)
    f.dot(O).label(O, "O", 235, 15)
    f.right(O, 0, 11)
    f.arc(O, 90, 90 + a, f"{a}°", r=24)
    return f.out()


def three_view(p):
    return {"text": f"Lines AD and FE are perpendicular, and ∠COF = {p['alpha']}°. Find ∠{p['ask']}.",
            "hint": "Angles along a straight line add to 180°, and vertical angles (opposite each other) are equal.",
            "figure": three_fig(p["alpha"])}


def three_solve(p):
    fn, steps = THREE[p["ask"]]
    return Solution(angle_num(fn(p["alpha"])), steps(p["alpha"]))


def three_valid(p):
    keys(p, "alpha", "ask")
    whole(p, "alpha", 10, 80)
    choice(p, "ask", tuple(THREE))
    return True


# --- Fig. 2.12's layout: two lines across a horizontal one, meeting above it -----------------------

def transversals_fig(beta):
    a1 = 180 - beta
    f = Fig(f"A horizontal line is crossed by a shallow line (left) and a steeper line (right). They meet above it. "
            f"The marked angle at the left crossing is {beta}°. Angle 1 is between the shallow line and the "
            f"horizontal, to the right; angles 2 to 5 are where the two lines meet.")
    P, R = (0.0, 0.0), (1.0, 0.0)
    Q = meet(P, a1, R, 2 * a1)
    f.seg((-0.5, 0), (max(R[0], Q[0]) + 0.6, 0))
    f.seg(pol(P, -0.4, a1), pol(Q, 0.55, a1))
    f.seg(pol(R, -0.35, 2 * a1), pol(Q, 0.5, 2 * a1))
    f.arc(P, a1, 180, f"{beta}°", r=17, tr=34)
    f.label(P, "1", a1 / 2, 30, "num")
    for n, (lo, hi), d in (("2", (a1 + 180, 2 * a1 + 180), 17), ("3", (2 * a1, a1 + 180), 15),
                           ("4", (a1, 2 * a1), 21), ("5", (2 * a1 + 180, a1 + 360), 15)):
        f.label(Q, n, (lo + hi) / 2, d, "num")
    return f.out()


def transversals_view(p):
    return {"text": f"In the figure, ∠1 = ∠2 and the marked angle is {p['beta']}°. Find ∠{p['ask']}.",
            "hint": "Start at the marked angle: it and ∠1 lie along the horizontal line. "
                    "Then use ∠1 = ∠2, straight lines (180°) and vertical angles.",
            "figure": transversals_fig(p["beta"])}


def transversals_solve(p):
    b, n = p["beta"], p["ask"]
    a1 = 180 - b
    steps = [f"The marked angle and ∠1 lie along the horizontal line: ∠1 = 180° − {b}° = {a1}°"]
    if n == "1":
        return Solution(angle_num(a1), steps)
    steps.append(f"∠2 = ∠1 = {a1}° (given)")
    if n == "2":
        return Solution(angle_num(a1), steps)
    if n == "4":
        steps.append(f"∠4 and ∠2 are vertical angles: ∠4 = {a1}°")
        return Solution(angle_num(a1), steps)
    steps.append(f"∠3 and ∠2 lie along the steeper line: ∠3 = 180° − {a1}° = {b}°")
    if n == "5":
        steps.append(f"∠5 and ∠3 are vertical angles: ∠5 = {b}°")
    return Solution(angle_num(b), steps)


def transversals_valid(p):
    keys(p, "beta", "ask")
    whole(p, "beta", 120, 170)
    choice(p, "ask", ("1", "2", "3", "4", "5"))
    return True


# --- Fig. 2.13's layout: AB ∥ CD, a transversal through P, and a line at right angles to it at P -----

def parallels_fig(gm):
    f = Fig(f"Parallel lines AB (top) and CD (bottom). A transversal crosses AB at P going up to the right, "
            f"making {gm}° with AB on the upper right. From P a second line goes down to the right, at a right "
            f"angle to the transversal, to CD. Angles 1, 5 and 6 are at P; 2 is where the transversal meets CD; "
            f"3 and 4 are where the second line meets CD.")
    P = (0.0, 1.0)
    x2 = -1 / math.tan(math.radians(gm))
    dd = gm - 90
    X3 = meet(P, dd, (0, 0), 0)
    parallels(f, 1.0, 0.0, x2 - 0.7, X3[0] + 0.7, ("A", "B", "C", "D"))
    transversal(f, P, gm, -0.4, 1.45)
    f.seg(P, X3)
    f.text((X3[0] * 0.55 + 0.25, 1.32), "AB ∥ CD", "val")
    f.arc(P, 0, gm, f"{gm}°", r=18, tr=33)
    f.right(P, gm + 180, 10)
    f.label(P, "5", (gm + 180) / 2, 15, "num").label(P, "1", 180 + gm / 2, 19, "num")
    f.label(P, "6", (gm + 270 + 360) / 2, 30, "num")
    f.label((x2, 0), "2", (gm + 180) / 2, 15, "num")
    f.label(X3, "3", (gm + 90 + 180) / 2, 22, "num").label(X3, "4", (gm + 90) / 2, 15, "num")
    return f.out()


PARALLEL_STEPS = {
    "1": lambda g_: [f"∠1 and the {g_}° angle are vertical angles: ∠1 = {g_}°"],
    "5": lambda g_: [f"∠5 and the {g_}° angle lie along AB: ∠5 = 180° − {g_}° = {180 - g_}°"],
    "2": lambda g_: [f"∠5 = 180° − {g_}° = {180 - g_}° (along AB)",
                     f"∠2 and ∠5 are corresponding angles, and AB ∥ CD, so ∠2 = {180 - g_}°"],
    "6": lambda g_: [f"Below AB at P: ∠1 + 90° + ∠6 = 180°, and ∠1 = {g_}° (vertical to the {g_}° angle)",
                     f"∠6 = 180° − {g_}° − 90° = {90 - g_}°"],
    "3": lambda g_: [f"∠6 = 180° − {g_}° − 90° = {90 - g_}° (along AB at P)",
                     f"∠3 and ∠6 are alternate interior angles, and AB ∥ CD, so ∠3 = {90 - g_}°"],
    "4": lambda g_: [f"∠3 = ∠6 = 90° − {g_}° = {90 - g_}° (alternate interior angles)",
                     f"∠3 and ∠4 lie along CD: ∠4 = 180° − {90 - g_}° = {90 + g_}°"],
}
PARALLEL_VALUE = {"1": lambda g_: g_, "5": lambda g_: 180 - g_, "2": lambda g_: 180 - g_,
                  "6": lambda g_: 90 - g_, "3": lambda g_: 90 - g_, "4": lambda g_: 90 + g_}


def parallels_view(p):
    return {"text": f"AB ∥ CD, and the marked angle is {p['gamma']}°. Find ∠{p['ask']}.",
            "hint": "Vertical angles are equal. With parallel lines, corresponding angles and alternate interior "
                    "angles are equal. Angles along a straight line add to 180°.",
            "figure": parallels_fig(p["gamma"])}


def parallels_solve(p):
    return Solution(angle_num(PARALLEL_VALUE[p["ask"]](p["gamma"])), PARALLEL_STEPS[p["ask"]](p["gamma"]))


def parallels_valid(p):
    keys(p, "gamma", "ask")
    whole(p, "gamma", 45, 75)
    choice(p, "ask", tuple(PARALLEL_VALUE))
    return True


# --- Fig. 2.14's layout: the truss. AF ∥ BE, BDEC a rectangle --------------------------------------

TRUSS = {
    "ADB": (lambda a: 90 - a, lambda a: [f"ΔABD has a right angle at B: ∠ADB = 180° − 90° − {a}° = {90 - a}°"]),
    "BDF": (lambda a: 90 + a, lambda a: [f"ΔABD has a right angle at B: ∠ADB = 90° − {a}° = {90 - a}°",
                                        f"A, D and F lie on one line: ∠BDF = 180° − {90 - a}° = {90 + a}°"]),
    "EBC": (lambda a: a, lambda a: [f"AF ∥ BE, so ∠EBC and ∠A are corresponding angles: ∠EBC = {a}°"]),
    "ABE": (lambda a: 180 - a, lambda a: [f"AF ∥ BE, so ∠EBC = ∠A = {a}° (corresponding angles)",
                                         f"A, B and C lie on one line: ∠ABE = 180° − {a}° = {180 - a}°"]),
    "DBE": (lambda a: 90 - a, lambda a: [f"∠EBC = ∠A = {a}° (corresponding angles, AF ∥ BE)",
                                        f"∠DBC is a right angle: ∠DBE = 90° − {a}° = {90 - a}°"]),
    "DEB": (lambda a: a, lambda a: [f"∠EBC = ∠A = {a}° (corresponding angles, AF ∥ BE)",
                                   f"DE ∥ BC (BDEC is a rectangle), so ∠DEB = ∠EBC = {a}° (alternate interior angles)"]),
    "BEC": (lambda a: 90 - a, lambda a: [f"∠EBC = ∠A = {a}° (corresponding angles, AF ∥ BE)",
                                        f"ΔBEC has a right angle at C: ∠BEC = 90° − {a}° = {90 - a}°"]),
    "AFC": (lambda a: 90 - a, lambda a: [f"ΔAFC has a right angle at C: ∠AFC = 180° − 90° − {a}° = {90 - a}°"]),
    "FDE": (lambda a: a, lambda a: [f"DE ∥ AC, so ∠FDE and ∠A are corresponding angles: ∠FDE = {a}°"]),
    "BEF": (lambda a: 90 + a, lambda a: [f"∠BEC = 90° − ∠EBC = 90° − {a}° = {90 - a}°",
                                        f"F, E and C lie on one line: ∠BEF = 180° − {90 - a}° = {90 + a}°"]),
}


def truss_fig(a):
    t = math.tan(math.radians(a))
    A, B, C, D, E, F = (0, 0), (1, 0), (2, 0), (1, t), (2, t), (2, 2 * t)
    f = Fig(f"A truss: right triangle AFC with the right angle at C, ∠A = {a}°. B is on AC, D on AF above B, "
            f"E on FC beside D, so BDEC is a rectangle. Diagonal BE is parallel to AF.")
    f.poly([A, C, F]).seg(B, D).seg(D, E).seg(B, E)
    f.right(B, 90, 9).right(E, 90, 9).right(C, 90, 9)
    f.arc(A, 0, a, f"{a}°", r=26)
    for name, p, d in (("A", A, 200), ("B", B, 270), ("C", C, 320), ("D", D, 125), ("E", E, 0), ("F", F, 45)):
        f.label(p, name, d, 13)
    f.text((0.55, t * 1.45 + 0.12), "AF ∥ BE")
    return f.out()


def truss_view(p):
    return {"text": f"In the truss, AF ∥ BE and ∠A = {p['alpha']}°. Find ∠{p['ask']}.",
            "hint": "BDEC is a rectangle, so its corners are 90°. With the parallel lines, use corresponding or "
                    "alternate interior angles; in a right triangle the two acute angles add to 90°.",
            "figure": truss_fig(p["alpha"])}


def truss_solve(p):
    fn, steps = TRUSS[p["ask"]]
    return Solution(angle_num(fn(p["alpha"])), steps(p["alpha"]))


def truss_valid(p):
    keys(p, "alpha", "ask")
    whole(p, "alpha", 25, 65)
    choice(p, "ask", tuple(TRUSS))
    return True


# ====================================================================== 2.2

def tri_from_angles(a, b):
    """Triangle on base (0,0)-(1,0) with angle a at the left corner and b at the right one."""
    return [(0, 0), (1, 0), meet((0, 0), a, (1, 0), 180 - b)]


THIRD = ("scalene", "right", "iso_apex", "iso_base")


def third_fig(p):
    v = p["variant"]
    if v == "scalene":
        C, B = p["C"], p["B"]
        pts = tri_from_angles(180 - B - C, B)
        f = Fig(f"Triangle ABC: A on the left, B on the right, C at the top. ∠C = {C}°, ∠B = {B}°.")
        triangle(f, pts, ("A", "B", "C"), angles={1: f"{B}°", 2: f"{C}°"})
        f.angle_between(pts[0], pts[1], pts[2], "?", r=22, tc="q")
    elif v == "right":
        B = p["B"]
        h = math.tan(math.radians(90 - B))
        pts = [(0, 0), (1, 0), (0, h)]
        f = Fig(f"Right triangle ABC with the right angle at C (lower left), B at the top and A on the right. ∠B = {B}°.")
        triangle(f, pts, ("C", "A", "B"), angles={2: f"{B}°"}, right=0)
        f.angle_between(pts[1], pts[0], pts[2], "?", r=22, tc="q")
    elif v == "iso_apex":
        B = p["B"]
        pts = [(0, 0), (1, 0), (0.5, 0.5 * math.tan(math.radians(B)))]
        f = Fig(f"Isosceles triangle ABC with A at the top, AB = AC = {p['L']}. ∠B = {B}°.")
        triangle(f, pts, ("B", "C", "A"), sides={(0, 2): p["L"], (1, 2): p["L"]}, angles={0: f"{B}°"})
        f.angle_between(pts[2], pts[0], pts[1], "?", r=20, tc="q")
    else:
        C = p["C"]
        pts = [(0, 0), (1, 0), (0.5, 0.5 * math.tan(math.radians((180 - C) / 2)))]
        f = Fig(f"Isosceles triangle ABC with C at the top, CA = CB = {p['L']}. ∠C = {C}°.")
        triangle(f, pts, ("A", "B", "C"), sides={(0, 2): p["L"], (1, 2): p["L"]}, angles={2: f"{C}°"})
        f.angle_between(pts[0], pts[1], pts[2], "?", r=22, tc="q")
    return f.out()


def third_view(p):
    hint = {"scalene": "The three angles of a triangle add up to 180°.",
            "right": "The right angle is 90°, so the other two angles add up to 90°.",
            "iso_apex": "Two equal sides means the angles opposite them, the base angles, are equal too.",
            "iso_base": "Two equal sides means the two base angles are equal. Together they get what's left of 180°."
            }[p["variant"]]
    return {"text": "Find ∠A.", "hint": hint, "figure": third_fig(p)}


def third_solve(p):
    v = p["variant"]
    if v == "scalene":
        a = 180 - p["B"] - p["C"]
        return Solution(angle_num(a), [f"∠A + ∠B + ∠C = 180°", f"∠A = 180° − {p['B']}° − {p['C']}° = {a}°"])
    if v == "right":
        a = 90 - p["B"]
        return Solution(angle_num(a), [f"∠C = 90°, so ∠A + ∠B = 90°", f"∠A = 90° − {p['B']}° = {a}°"])
    if v == "iso_apex":
        a = 180 - 2 * p["B"]
        return Solution(angle_num(a), [f"AB = AC, so the base angles are equal: ∠C = ∠B = {p['B']}°",
                                       f"∠A = 180° − {p['B']}° − {p['B']}° = {a}°"])
    a = D(180 - p["C"]) / 2
    return Solution(angle_num(a, [(D(180 - p["C"]), "That's both base angles together. Each one is half of it.")]),
                    [f"CA = CB, so the base angles are equal: ∠A = ∠B", f"2∠A = 180° − {p['C']}° = {180 - p['C']}°",
                     f"∠A = {180 - p['C']}° ÷ 2 = {deg(a)}"])


def third_gen(rng):
    v = rng.choice(THIRD)
    if v == "scalene":
        while True:
            C, B = rng.randint(40, 110), rng.randint(25, 75)
            if 180 - B - C >= 20:
                return {"variant": v, "C": C, "B": B}
    if v == "right":
        return {"variant": v, "B": rng.randint(15, 75)}
    if v == "iso_apex":
        return {"variant": v, "B": rng.randint(35, 80), "L": str(rng.randint(2, 12))}
    return {"variant": v, "C": rng.randrange(30, 151, 2), "L": str(rng.randint(2, 12))}


def third_valid(p):
    v = choice(p, "variant", THIRD)
    if v == "scalene":
        keys(p, "variant", "C", "B")
        return whole(p, "C", 1, 178) + whole(p, "B", 1, 178) < 180
    if v == "right":
        keys(p, "variant", "B")
        return whole(p, "B", 1, 89)
    keys(p, "variant", "B" if v == "iso_apex" else "C", "L")
    given(p, "L", "0", "1000")
    return whole(p, "B", 1, 89) if v == "iso_apex" else whole(p, "C", 1, 179)


# --- triangle areas and perimeters ----------------------------------------------------------------

def sides_pts(base, left, right, up):
    b, l, r = float(base), float(left), float(right)
    x = (b * b + l * l - r * r) / (2 * b)
    y = math.sqrt(max(l * l - x * x, 1e-12))
    return [(0, 0), (b, 0), (x, y if up else -y)]


def triangle_ok(a, b, c):
    return a < b + c and b < a + c and c < a + b


def sides_gen(rng):
    unit = rng.choice(UNITS)
    while True:
        base = meas_u(rng, unit, 3)
        left = near(rng, base, 0.45, 0.95)
        lo = max(abs(float(base) - float(left)) * 1.3, float(base) * 0.3)
        hi = (float(base) + float(left)) * 0.8
        if lo >= hi:
            continue
        right = meas(rng, lo, hi, 3)
        s = [float(base), float(left), float(right)]
        if all(x < 0.97 * (sum(s) - x) for x in s):
            return {"base": base, "left": left, "right": right, "unit": unit, "up": rng.randint(0, 1)}


def sides_valid(p, extra=()):
    keys(p, "base", "left", "right", "unit", "up", *extra)
    choice(p, "unit", UNITS)
    whole(p, "up", 0, 1)
    return triangle_ok(given(p, "base"), given(p, "left"), given(p, "right"))


def sides_fig(p):
    pts = sides_pts(p["base"], p["left"], p["right"], p["up"])
    f = Fig(f"Triangle with sides {gv(p, 'base')}, {gv(p, 'left')} and {gv(p, 'right')}.")
    triangle(f, pts, sides={(0, 1): gv(p, "base"), (0, 2): gv(p, "left"), (1, 2): gv(p, "right")})
    return f.out()


def heron(a, b, c):
    s = (a + b + c) / 2
    return s, dsqrt(s * (s - a) * (s - b) * (s - c))


def heron_view(p):
    return {"text": "Find the area of the triangle. No height is given.",
            "hint": "With three sides and no height, use Heron's formula. Find the semi-perimeter s first and "
                    "keep all its digits.",
            "figure": sides_fig(p)}


def heron_solve(p):
    a, b, c = given(p, "base"), given(p, "left"), given(p, "right")
    s, area = heron(a, b, c)
    u = U(p)
    return Solution(Num(area, "area", p["unit"], sig(p["base"], p["left"], p["right"])),
                    [f"s = (a + b + c) / 2 = ({p['base']} + {p['left']} + {p['right']}) / 2 = {g(s)} {u}",
                     f"A = √(s(s − a)(s − b)(s − c))",
                     f"= √({g(s)} × {g(s - a)} × {g(s - b)} × {g(s - c)})",
                     f"= {g(area)} {U2(p)}"])


def bh_fig(p):
    b, h, k = float(p["b"]), float(p["h"]), p["apex"] / 100
    pts = [(0, 0), (b, 0), (k * b, h)]
    f = Fig(f"Triangle with base {gv(p, 'b')} and a dashed height of {gv(p, 'h')}"
            + (", which falls outside the triangle on the extended base." if not 0 <= k <= 1 else "."))
    triangle(f, pts, sides={(0, 1): gv(p, "b")})
    height(f, pts[2], pts[0], pts[1], gv(p, "h"))
    return f.out()


def bh_gen(rng):
    unit = rng.choice(UNITS)
    b = meas_u(rng, unit, figs(rng))
    apex = rng.choice((rng.randint(15, 85), rng.randint(15, 85), rng.randint(-35, -8), rng.randint(108, 135)))
    return {"b": b, "h": near(rng, b, 0.3, 1.1, figs(rng)), "unit": unit, "apex": apex}


def bh_valid(p):
    keys(p, "b", "h", "unit", "apex")
    choice(p, "unit", UNITS)
    given(p, "b"), given(p, "h")
    return whole(p, "apex", -200, 300) is not None


def bh_solve(p):
    b, h = given(p, "b"), given(p, "h")
    area = HALF * b * h
    return Solution(Num(area, "area", p["unit"], sig(p["b"], p["h"]),
                        slips=[(b * h, "That's base × height without the ½. A triangle is half of that rectangle.")]),
                    [f"A = ½bh", f"= ½ × {p['b']} × {p['h']}", f"= {g(area)} {U2(p)}"])


def right_legs_fig(p, a_key="a", b_key="b"):
    a, b = float(p[a_key]), float(p[b_key])
    f = Fig(f"Right triangle with legs {gv(p, a_key)} and {gv(p, b_key)}.")
    triangle(f, [(0, 0), (b, 0), (b, a)], sides={(0, 1): gv(p, b_key), (1, 2): gv(p, a_key)}, right=1)
    return f.out()


def legs_gen(rng):
    unit = rng.choice(UNITS)
    a = meas_u(rng, unit, figs(rng))
    return {"a": a, "b": near(rng, a, 0.5, 1.8, figs(rng)), "unit": unit}


def legs_valid(p):
    keys(p, "a", "b", "unit")
    choice(p, "unit", UNITS)
    return given(p, "a") and given(p, "b")


def legs_solve(p):
    a, b = given(p, "a"), given(p, "b")
    area = HALF * a * b
    return Solution(Num(area, "area", p["unit"], sig(p["a"], p["b"]),
                        slips=[(a * b, "You left out the ½. The legs are the base and height, so A = ½ab.")]),
                    ["The legs are perpendicular, so one is the base and the other the height.",
                     f"A = ½ × {p['a']} × {p['b']} = {g(area)} {U2(p)}"])


def iso_fig(p):
    leg, base = float(p["leg"]), float(p["base"])
    h = math.sqrt(leg * leg - base * base / 4)
    pts = [(0, 0), (base, 0), (base / 2, h)]
    f = Fig(f"Isosceles triangle with two equal sides of {gv(p, 'leg')} and a base of {gv(p, 'base')}.")
    triangle(f, pts, sides={(0, 1): gv(p, "base"), (0, 2): gv(p, "leg"), (1, 2): gv(p, "leg")},
             ticks=[(0, 2, 1), (1, 2, 1)])
    height(f, pts[2], pts[0], pts[1], "h")
    return f.out()


def iso_gen(rng):
    unit = rng.choice(UNITS)
    leg = meas_u(rng, unit, 3)
    return {"leg": leg, "base": near(rng, leg, 0.4, 1.6, 3), "unit": unit}


def iso_valid(p):
    keys(p, "leg", "base", "unit")
    choice(p, "unit", UNITS)
    return given(p, "base") < 2 * given(p, "leg")


def iso_area_solve(p):
    leg, base = given(p, "leg"), given(p, "base")
    hb = base / 2
    h = dsqrt(leg * leg - hb * hb)
    area = HALF * base * h
    return Solution(Num(area, "area", p["unit"], sig(p["leg"], p["base"])),
                    ["The height from the top corner splits the base in half and makes two right triangles.",
                     f"h = √(leg² − (base/2)²) = √({p['leg']}² − {g(hb)}²) = {g(h)} {U(p)}",
                     f"A = ½ × base × h = ½ × {p['base']} × {g(h)} = {g(area)} {U2(p)}"])


def equi_fig(p):
    s = float(p["s"])
    pts = [(0, 0), (s, 0), (s / 2, s * math.sqrt(3) / 2)]
    f = Fig(f"Equilateral triangle with sides of {gv(p, 's')}.")
    triangle(f, pts, sides={(0, 1): gv(p, "s")}, ticks=[(0, 1, 1), (0, 2, 1), (1, 2, 1)])
    return f.out()


def equi_gen(rng):
    unit = rng.choice(UNITS)
    return {"s": meas_u(rng, unit, rng.choice((2, 3, 3, 4))), "unit": unit}


def equi_valid(p):
    keys(p, "s", "unit")
    choice(p, "unit", UNITS)
    return given(p, "s")


def equi_area_solve(p):
    s = given(p, "s")
    area = dsqrt(3) / 4 * s * s
    return Solution(Num(area, "area", p["unit"], sig(p["s"])),
                    [f"A = (√3 / 4) s²", f"= (√3 / 4) × {p['s']}²", f"= {g(area)} {U2(p)}"])


PERIM = ("sides", "equilateral", "isosceles")


def perim_gen(rng):
    v = rng.choice(PERIM)
    if v == "sides":
        return {"variant": v, **sides_gen(rng)}
    if v == "equilateral":
        return {"variant": v, **equi_gen(rng)}
    return {"variant": v, **iso_gen(rng)}


def perim_valid(p):
    v = choice(p, "variant", PERIM)
    q = {k: x for k, x in p.items() if k != "variant"}
    return {"sides": sides_valid, "equilateral": equi_valid, "isosceles": iso_valid}[v](q)


def perim_view(p):
    v = p["variant"]
    q = {k: x for k, x in p.items() if k != "variant"}
    if v == "sides":
        return {"text": "Find the perimeter of the triangle.", "hint": "The perimeter is the distance around: "
                "add the three sides.", "figure": sides_fig(q)}
    if v == "equilateral":
        return {"text": f"An equilateral triangle has sides of {gv(p, 's')}. Find its perimeter.",
                "hint": "All three sides of an equilateral triangle are equal.", "figure": equi_fig(q)}
    return {"text": f"An isosceles triangle has two equal sides of {gv(p, 'leg')} and a third side of "
                    f"{gv(p, 'base')}. Find its perimeter.",
            "hint": "Two sides are the same length. Add all three.", "figure": iso_fig(q)}


def perim_solve(p):
    v, u = p["variant"], U(p)
    if v == "sides":
        a, b, c = given(p, "base"), given(p, "left"), given(p, "right")
        total = a + b + c
        return Solution(Num(total, "length", p["unit"], sig(p["base"], p["left"], p["right"])),
                        [f"p = a + b + c = {p['base']} + {p['left']} + {p['right']} = {g(total)} {u}"])
    if v == "equilateral":
        s = given(p, "s")
        return Solution(Num(3 * s, "length", p["unit"], sig(p["s"]),
                            slips=[(s, "That's one side. The perimeter adds all three.")]),
                        [f"p = 3s = 3 × {p['s']} = {g(3 * s)} {u}"])
    leg, base = given(p, "leg"), given(p, "base")
    total = 2 * leg + base
    return Solution(Num(total, "length", p["unit"], sig(p["leg"], p["base"]),
                        slips=[(leg + base, "Two of the sides are equal: count the equal side twice.")]),
                    [f"p = 2 × {p['leg']} + {p['base']} = {g(total)} {u}"])


# --- Pythagorean theorem, Fig. 2.42's layout: a upright, b across, c the hypotenuse ---------------

TRIPLES = ((3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41), (12, 35, 37))
PAIRS = ("ab", "ac", "bc")


def pythag_values(p):
    vals = dict(zip(p["given"], (given(p, "v1"), given(p, "v2"))))
    if p["given"] == "ab":
        vals["c"] = dsqrt(vals["a"] ** 2 + vals["b"] ** 2)
    else:
        leg = "a" if p["given"] == "bc" else "b"
        other = "b" if leg == "a" else "a"
        vals[leg] = dsqrt(vals["c"] ** 2 - vals[other] ** 2)
    return vals


def pythag_gen(rng):
    unit, pair = rng.choice(UNITS), rng.choice(PAIRS)
    if rng.random() < 0.35:
        t, k = rng.choice(TRIPLES), rng.randint(1, 4)
        a, b = (t[0] * k, t[1] * k) if rng.random() < 0.5 else (t[1] * k, t[0] * k)
        vals = {"a": a, "b": b, "c": t[2] * k}
        return {"given": pair, "v1": str(vals[pair[0]]), "v2": str(vals[pair[1]]), "unit": unit, "exact": 1}
    while True:
        a = meas_u(rng, unit, 3)
        b = near(rng, a, 0.4, 2.5, 3)
        c = approx(math.hypot(float(a), float(b)), 3)
        vals = {"a": a, "b": b, "c": c}
        if c and float(c) > max(float(a), float(b)) * 1.03:
            return {"given": pair, "v1": vals[pair[0]], "v2": vals[pair[1]], "unit": unit, "exact": 0}


def pythag_valid(p):
    keys(p, "given", "v1", "v2", "unit", "exact")
    choice(p, "unit", UNITS)
    choice(p, "given", PAIRS)
    whole(p, "exact", 0, 1)
    v1, v2 = given(p, "v1"), given(p, "v2")
    return p["given"] == "ab" or v2 > v1 * D("1.01")


def pythag_fig(p, vals):
    a, b = float(vals["a"]), float(vals["b"])
    pts = [(0, 0), (b, 0), (b, a)]
    want = ({"a", "b", "c"} - set(p["given"])).pop()
    text = {k: (f"{k} = {p['v1' if k == p['given'][0] else 'v2']} {U(p)}" if k in p["given"] else f"{k} = ?")
            for k in "abc"}
    f = Fig(f"Right triangle with the right angle at the lower right: leg a upright, leg b across the bottom, "
            f"hypotenuse c. Given {text[p['given'][0]]} and {text[p['given'][1]]}.")
    key = {"a": (1, 2), "b": (0, 1), "c": (0, 2)}
    triangle(f, pts, sides={key[k]: text[k] for k in "abc"}, right=1, q=key[want])
    return f.out()


def pythag_view(p):
    want = ({"a", "b", "c"} - set(p["given"])).pop()
    x, y = p["given"]
    ex = " These values are exact." if p["exact"] else ""
    return {"text": f"For the right triangle, {x} = {gv(p, 'v1')} and {y} = {gv(p, 'v2')}.{ex} Find {want}.",
            "hint": "The Pythagorean theorem: c² = a² + b², where c is the hypotenuse, the side across from the "
                    "right angle." + ("" if want == "c" else " Solve it for the leg you need."),
            "figure": pythag_fig(p, pythag_values(p))}


def pythag_solve(p):
    vals = pythag_values(p)
    want = ({"a", "b", "c"} - set(p["given"])).pop()
    x, y = p["given"]
    s = None if p["exact"] else sig(p["v1"], p["v2"])
    v1, v2 = given(p, "v1"), given(p, "v2")
    u = U(p)
    if want == "c":
        slips = [(v1 + v2, "That adds the legs. Square them, add, then take the square root.")]
        steps = [f"c² = a² + b² = {p['v1']}² + {p['v2']}² = {g(v1 * v1 + v2 * v2)}",
                 f"c = √{g(v1 * v1 + v2 * v2)} = {g(vals['c'])} {u}"]
    else:
        slips = [(dsqrt(v1 * v1 + v2 * v2), f"That adds the squares, but {y} is the hypotenuse. Subtract: "
                                            f"{want}² = {y}² − {x}².")]
        steps = [f"{want}² = c² − {x}² = {p['v2']}² − {p['v1']}² = {g(v2 * v2 - v1 * v1)}",
                 f"{want} = √{g(v2 * v2 - v1 * v1)} = {g(vals[want])} {u}"]
    return Solution(Num(vals[want], "length", p["unit"], s, slips=slips), steps)


# --- Fig. 2.43's layout: angle θ at the left, b across, a upright, B at the top ------------------

RT_ASKS = ("B", "c", "a", "P", "A")


def rt_values(p):
    th, b = p["theta"], given(p, "b")
    if p["a"]:
        a = given(p, "a")
        c = dsqrt(a * a + b * b)
    else:
        a, c = b * dtan(th), b / dcos(th)
    return a, b, c


def rt_gen(rng):
    unit = rng.choice(UNITS)
    th = rng.randint(15, 70)
    while True:
        b = meas_u(rng, unit, 3)
        a = approx(float(b) * math.tan(math.radians(th)), 3)
        if a:
            break
    both = rng.random() < 0.5
    asks = ("B", "c", "P", "A") if both else RT_ASKS
    return {"theta": th, "b": b, "a": a if both else "", "unit": unit, "ask": rng.choice(asks)}


def rt_valid(p):
    keys(p, "theta", "b", "a", "unit", "ask")
    choice(p, "unit", UNITS)
    whole(p, "theta", 5, 85)
    given(p, "b")
    if p["a"] != "":
        given(p, "a")
    choice(p, "ask", RT_ASKS)
    return not (p["ask"] == "a" and p["a"])


def rt_fig(p):
    a, b, c = (float(x) for x in rt_values(p))
    pts = [(0, 0), (b, 0), (b, a)]
    ask = p["ask"]
    atext = gv(p, "a") if p["a"] else ("a = ?" if ask == "a" else "a")
    ctext = "c = ?" if ask == "c" else "c"
    f = Fig(f"Right triangle: angle {p['theta']}° at the left corner, leg {gv(p, 'b')} across the bottom, "
            + (f"leg {gv(p, 'a')} up the right side, " if p["a"] else "the upright leg a on the right, ")
            + "right angle at the lower right, B at the top, hypotenuse c.")
    triangle(f, pts, (None, None, "B"), sides={(0, 1): gv(p, "b"), (1, 2): atext, (0, 2): ctext},
             angles={0: f"{p['theta']}°"}, right=1, q={"a": (1, 2), "c": (0, 2)}.get(ask))
    if ask == "B":
        f.angle_between(pts[2], pts[0], pts[1], "?", r=18, tc="q")
    return f.out()


def rt_view(p):
    ask, th = p["ask"], p["theta"]
    legs = f"the legs are {gv(p, 'b')} and {gv(p, 'a')}" if p["a"] else f"the bottom leg is {gv(p, 'b')}"
    what = {"B": "∠B", "c": "the hypotenuse c", "a": "the upright leg a", "P": "the perimeter",
            "A": "the area"}[ask]
    hint = {"B": "The two acute angles of a right triangle add up to 90°.",
            "c": ("Use the Pythagorean theorem with the two legs." if p["a"] else
                  "The bottom leg is adjacent to the angle and c is the hypotenuse: use cos θ = adjacent / hypotenuse."),
            "a": "a is opposite the angle and b is adjacent to it: use tan θ = opposite / adjacent.",
            "P": "Add all three sides. " + ("Find c first with the Pythagorean theorem." if p["a"] else
                                            "Find a with tan θ and c with cos θ first."),
            "A": "The legs are perpendicular, so A = ½ × one leg × the other." + (
                "" if p["a"] else " Find the upright leg with tan θ first.")}[ask]
    return {"text": f"In the right triangle, the angle at the left is {th}° and {legs}. Find {what}.",
            "hint": hint, "figure": rt_fig(p)}


def rt_solve(p):
    a, b, c = rt_values(p)
    th, u, ask = p["theta"], U(p), p["ask"]
    s = sig(p["a"], p["b"]) if p["a"] else sig(p["b"])
    if ask == "B":
        return Solution(angle_num(90 - th), [f"∠B = 90° − {th}° = {90 - th}°"])
    if p["a"]:
        c_step = f"c = √(a² + b²) = √({p['a']}² + {p['b']}²) = {g(c)} {u}"
        a_step = None
    else:
        c_step = f"cos {th}° = b / c, so c = {p['b']} / cos {th}° = {g(c)} {u}"
        a_step = f"tan {th}° = a / b, so a = {p['b']} × tan {th}° = {g(a)} {u}"
    if ask == "a":
        return Solution(Num(a, "length", p["unit"], s), [a_step])
    if ask == "c":
        return Solution(Num(c, "length", p["unit"], s), [c_step])
    pre = [x for x in (a_step,) if x]
    if ask == "P":
        return Solution(Num(a + b + c, "length", p["unit"], s),
                        pre + [c_step, f"p = a + b + c = {g(a)} + {p['b']} + {g(c)} = {g(a + b + c)} {u}"])
    area = HALF * a * b
    return Solution(Num(area, "area", p["unit"], s, slips=[(a * b, "You left out the ½: A = ½ab.")]),
                    pre + [f"A = ½ab = ½ × {g(a)} × {p['b']} = {g(area)} {U2(p)}"])


# ====================================================================== 2.3

def square_fig(p, shape):
    s = 1.0
    if shape == "rhombus":
        pts = [(0, 0), (s, 0), (s + 0.55, 0.83), (0.55, 0.83)]
        f = Fig(f"Rhombus with sides of {gv(p, 's')}.")
        quadrilateral(f, pts, sides={0: gv(p, "s")})
        for i in range(4):
            f.ticks(pts[i], pts[(i + 1) % 4], 1)
    else:
        pts = [(0, 0), (s, 0), (s, s), (0, s)]
        f = Fig(f"Square with sides of {gv(p, 's')}.")
        quadrilateral(f, pts, sides={0: gv(p, "s")})
        f.right(pts[0], 0, 9)
    return f.out()


def rect_fig(p):
    l, w = float(p["l"]), float(p["w"])
    pts = [(0, 0), (l, 0), (l, w), (0, w)]
    f = Fig(f"Rectangle {gv(p, 'l')} long and {gv(p, 'w')} wide.")
    quadrilateral(f, pts, sides={0: f"l = {gv(p, 'l')}", 1: f"w = {gv(p, 'w')}"})
    f.right(pts[0], 0, 9)
    return f.out()


SHAPES = ("square", "rhombus", "rectangle")


def basic_gen(shapes):
    def gen(rng):
        shape, unit = rng.choice(shapes), rng.choice(UNITS)
        if shape == "rectangle":
            l = meas_u(rng, unit, figs(rng))
            return {"shape": shape, "l": l, "w": near(rng, l, 0.3, 0.95, figs(rng)), "unit": unit}
        return {"shape": shape, "s": meas_u(rng, unit, figs(rng)), "unit": unit}
    return gen


def basic_valid(shapes):
    def valid(p):
        shape = choice(p, "shape", shapes)
        choice(p, "unit", UNITS)
        if shape == "rectangle":
            keys(p, "shape", "l", "w", "unit")
            return given(p, "l") and given(p, "w")
        keys(p, "shape", "s", "unit")
        return given(p, "s")
    return valid


def basic_fig(p):
    return rect_fig(p) if p["shape"] == "rectangle" else square_fig(p, p["shape"])


def qp_view(p):
    shape = p["shape"]
    what = (f"a rectangle with l = {gv(p, 'l')} and w = {gv(p, 'w')}" if shape == "rectangle"
            else f"a {shape} with sides of {gv(p, 's')}")
    hint = {"square": "A square has four equal sides.",
            "rhombus": "A rhombus has four equal sides, like a square pushed over.",
            "rectangle": "A rectangle has two lengths and two widths."}[shape]
    return {"text": f"Find the perimeter of {what}.", "hint": hint, "figure": basic_fig(p)}


def qp_solve(p):
    u = U(p)
    if p["shape"] == "rectangle":
        l, w = given(p, "l"), given(p, "w")
        return Solution(Num(2 * (l + w), "length", p["unit"], sig(p["l"], p["w"]),
                            slips=[(l + w, "That's half the perimeter: there are two lengths and two widths."),
                                   (l * w, "That's the area. The perimeter is the distance around.")]),
                        [f"p = 2(l + w) = 2({p['l']} + {p['w']}) = {g(2 * (l + w))} {u}"])
    s = given(p, "s")
    return Solution(Num(4 * s, "length", p["unit"], sig(p["s"]),
                        slips=[(s * s, "That's the area (s²). The perimeter is 4s.")]),
                    [f"p = 4s = 4 × {p['s']} = {g(4 * s)} {u}"])


def qa_view(p):
    what = (f"a square with sides of {gv(p, 's')}" if p["shape"] == "square"
            else f"a rectangle with l = {gv(p, 'l')} and w = {gv(p, 'w')}")
    hint = "A square's area is s²." if p["shape"] == "square" else "A rectangle's area is length × width."
    return {"text": f"Find the area of {what}.", "hint": hint, "figure": basic_fig(p)}


def qa_solve(p):
    if p["shape"] == "rectangle":
        l, w = given(p, "l"), given(p, "w")
        return Solution(Num(l * w, "area", p["unit"], sig(p["l"], p["w"]),
                            slips=[(2 * (l + w), "That's the perimeter. The area is l × w.")]),
                        [f"A = lw = {p['l']} × {p['w']} = {g(l * w)} {U2(p)}"])
    s = given(p, "s")
    return Solution(Num(s * s, "area", p["unit"], sig(p["s"]),
                        slips=[(4 * s, "That's the perimeter. The area is s².")]),
                    [f"A = s² = {p['s']}² = {g(s * s)} {U2(p)}"])


# --- parallelograms (Figs. 2.61, 2.62): base, slanted side, dashed height ------------------------

def para_offset(p):
    side, h = float(p["side"]), float(p["h"])
    u = math.sqrt(max(side * side - h * h, 0))
    return u if p["lean"] == "right" else -u


def para_fig(p):
    b, h, u = float(p["base"]), float(p["h"]), para_offset(p)
    pts = [(0, 0), (b, 0), (b + u, h), (u, h)]
    f = Fig(f"Parallelogram with base {gv(p, 'base')}, slanted side {gv(p, 'side')} and a dashed height of "
            f"{gv(p, 'h')}. The height is not a side.")
    quadrilateral(f, pts, sides={2: gv(p, "base"), 1: gv(p, "side")})
    if u >= 0:
        height(f, pts[3], pts[0], pts[1], gv(p, "h"), side_away=pts[0])
    else:
        height(f, pts[0], pts[2], pts[3], gv(p, "h"), side_away=pts[3])
    return f.out()


def para_gen(rng):
    unit = rng.choice(UNITS)
    b = meas_u(rng, unit, rng.choice((2, 3, 3)))
    h = near(rng, b, 0.3, 0.75, rng.choice((2, 3, 3)))
    side = near(rng, h, 1.04, 1.45, rng.choice((2, 3, 3)))
    if float(side) <= float(h) * 1.01:
        return para_gen(rng)
    return {"base": b, "side": side, "h": h, "unit": unit, "lean": rng.choice(("left", "right"))}


def para_valid(p):
    keys(p, "base", "side", "h", "unit", "lean")
    choice(p, "unit", UNITS)
    choice(p, "lean", ("left", "right"))
    b, s, h = given(p, "base"), given(p, "side"), given(p, "h")
    return s > h and s * s - h * h < b * b * 4


def pp_view(p):
    return {"text": "Find the perimeter of the parallelogram.",
            "hint": "Opposite sides of a parallelogram are equal. The dashed height is not a side.",
            "figure": para_fig(p)}


def pp_solve(p):
    b, s, h = given(p, "base"), given(p, "side"), given(p, "h")
    return Solution(Num(2 * (b + s), "length", p["unit"], sig(p["base"], p["side"]),
                        slips=[(2 * (b + h), "You used the dashed height as a side. The height is never a side."),
                               (b + s, "That's half: a parallelogram has two of each side."),
                               (b * h, "That's the area. The perimeter is the distance around.")]),
                    [f"p = 2(base + side) = 2({p['base']} + {p['side']}) = {g(2 * (b + s))} {U(p)}",
                     f"The {gv(p, 'h')} height isn't used: it isn't a side."])


def pa_view(p):
    return {"text": "Find the area of the parallelogram.",
            "hint": "A parallelogram's area is base × height. The height is the dashed line, not the slanted side.",
            "figure": para_fig(p)}


def pa_solve(p):
    b, s, h = given(p, "base"), given(p, "side"), given(p, "h")
    return Solution(Num(b * h, "area", p["unit"], sig(p["base"], p["h"]),
                        slips=[(b * s, "You used the slanted side. The area uses the height: A = bh."),
                               (HALF * b * h, "That's a triangle's area. A parallelogram is the full bh, no ½.")]),
                    [f"A = bh = {p['base']} × {p['h']} = {g(b * h)} {U2(p)}",
                     f"The {gv(p, 'side')} slanted side isn't used."])


# --- trapezoids (Figs. 2.63, 2.64) ------------------------------------------------------------------

def trap_offset(p):
    """Horizontal offset of the top-left corner from the bottom-left one, chosen to fit the right side."""
    top, bot, lt, rt, h = (float(p[k]) for k in ("top", "bottom", "left", "right", "h"))
    m = math.sqrt(max(lt * lt - h * h, 0))
    return min((m, -m), key=lambda u: abs(math.hypot(bot - u - top, h) - rt))


def trap_fig(p):
    top, bot, h = float(p["top"]), float(p["bottom"]), float(p["h"])
    u = trap_offset(p)
    pts = [(0, 0), (bot, 0), (u + top, h), (u, h)]
    f = Fig(f"Trapezoid: top {gv(p, 'top')}, bottom {gv(p, 'bottom')}, left side {gv(p, 'left')}, right side "
            f"{gv(p, 'right')}, dashed height {gv(p, 'h')}. The height is not a side.")
    quadrilateral(f, pts, sides={0: gv(p, "bottom"), 1: gv(p, "right"), 2: gv(p, "top"), 3: gv(p, "left")})
    top_pt = pts[3] if 0 <= u <= bot else pts[2]
    height(f, top_pt, pts[0], pts[1], gv(p, "h"), side_away=pts[0] if top_pt is pts[3] else pts[1])
    return f.out()


def trap_gen(rng):
    unit = rng.choice(UNITS)
    while True:
        bot = meas_u(rng, unit, 3)
        b = float(bot)
        h = near(rng, b, 0.3, 0.6, 3)
        u = rng.uniform(0.1, 0.4) * b * rng.choice((1, 1, -0.5))
        top = approx(b * rng.uniform(0.45, 1.25), 3)
        if not top:
            continue
        hv = float(h)
        lt = approx(math.hypot(u, hv), 3)
        rt = approx(math.hypot(b - u - float(top), hv), 3)
        p = {"top": top, "bottom": bot, "left": lt, "right": rt, "h": h, "unit": unit}
        if lt and rt and float(lt) > hv * 1.03 and float(rt) > hv * 1.03 and trap_valid(p):
            return p


def trap_valid(p):
    keys(p, "top", "bottom", "left", "right", "h", "unit")
    choice(p, "unit", UNITS)
    top, bot, lt, rt, h = (given(p, k) for k in ("top", "bottom", "left", "right", "h"))
    if not (lt > h and rt > h):
        return False
    u = trap_offset(p)
    return abs(math.hypot(float(bot) - u - float(top), float(h)) - float(rt)) <= 0.05 * float(rt)


def tp_view(p):
    return {"text": "Find the perimeter of the trapezoid.",
            "hint": "Add all four sides. The dashed height is not a side.", "figure": trap_fig(p)}


def tp_solve(p):
    top, bot, lt, rt, h = (given(p, k) for k in ("top", "bottom", "left", "right", "h"))
    total = top + bot + lt + rt
    return Solution(Num(total, "length", p["unit"], sig(p["top"], p["bottom"], p["left"], p["right"]),
                        slips=[(total + h, "You added the dashed height too. It's inside the figure, not a side."),
                               (top + bot + 2 * h, "You used the height for the slanted sides. Use the sides "
                                                   "themselves; the height is never a side.")]),
                    [f"p = {p['top']} + {p['bottom']} + {p['left']} + {p['right']} = {g(total)} {U(p)}",
                     f"The {gv(p, 'h')} height isn't used: it isn't a side."])


def ta_view(p):
    return {"text": "Find the area of the trapezoid.",
            "hint": "A = ½(b₁ + b₂)h: the average of the two parallel sides, times the height.",
            "figure": trap_fig(p)}


def ta_solve(p):
    top, bot, h = given(p, "top"), given(p, "bottom"), given(p, "h")
    area = HALF * (top + bot) * h
    return Solution(Num(area, "area", p["unit"], sig(p["top"], p["bottom"], p["h"]),
                        slips=[((top + bot) * h, "You left out the ½: A = ½(b₁ + b₂)h.")]),
                    [f"A = ½(b₁ + b₂)h", f"= ½({p['top']} + {p['bottom']}) × {p['h']}",
                     f"= {g(area)} {U2(p)}"])


# --- composite figures (Figs. 2.65, 2.66): set up a formula -------------------------------------

COMPOSITES = {
    # shape: (letter roles, letter choices, {ask: (formula, slips)})
    "par_sq": (("side", "base", "height"), ("acs", "bw", "h"), {
        "P": ("4{side} + 2{base}", [("5{side} + 2{base}", "Leave out the dashed side: it's inside the figure."),
                                     ("6{side} + 2{base}", "That adds both perimeters, so the shared side counts "
                                                           "twice. Leave it out completely.")]),
        "A": ("{base}{height} + {side}^2", [("{base}{side} + {side}^2", "The parallelogram's area uses its height "
                                                                         "{height}, not the slanted side.")])}),
    "L": (("thick", "outer"), ("at", "bs"), {
        "P": ("4{outer}", [("4{outer} + 2{thick}", "Go around the outside once. The inner edges are each "
                                                   "{outer} − {thick}, not {outer}.")]),
        "A": ("{thick}(2{outer} - {thick})", [("{outer}^2", "That's the whole square. Take away the missing corner, "
                                                           "a square of side {outer} − {thick}.")])}),
    "rect_sq": (("len", "wid"), ("lb", "wh"), {
        "P": ("2{len} + 4{wid}", [("2{len} + 5{wid}", "Leave out the dashed side: it's inside the figure."),
                                  ("2{len} + 6{wid}", "That adds both perimeters, so the shared side counts twice.")]),
        "A": ("{len}{wid} + {wid}^2", [])}),
}
COMPOSITE_TEXT = {"par_sq": "a parallelogram with a square attached along its slanted side",
                  "L": "two trapezoids joined along the dashed line",
                  "rect_sq": "a rectangle with a square attached at one end"}


def comp_roles(p):
    roles, _, _ = COMPOSITES[p["shape"]]
    return dict(zip(roles, p["letters"]))


def comp_fig(p):
    r = comp_roles(p)
    shape = p["shape"]
    if shape == "par_sq":
        a, b, h = r["side"], r["base"], r["height"]
        H, B, u = 1.0, 2.1, 0.32
        P0, P1, P2, P3 = (0, 0), (B, 0), (B + u, H), (u, H)
        n = (H, -u)
        k = 1 / math.hypot(*n) * math.hypot(u, H)
        S1, S2 = (P2[0] + n[0] * k, P2[1] + n[1] * k), (P1[0] + n[0] * k, P1[1] + n[1] * k)
        f = Fig(f"A parallelogram with top and bottom {b}, slanted sides {a} and a dashed height {h}, with a square "
                f"of side {a} attached along its right side. The shared side is dashed.")
        f.seg(P1, P0).seg(P0, P3).seg(P3, P2).seg(P2, S1).seg(S1, S2).seg(S2, P1).seg(P1, P2, "dash")
        height(f, P3, P0, P1, h, side_away=P0)
        f.side(P3, P2, b, P0).side(S1, S2, a, P1)
    elif shape == "L":
        a, b = r["thick"], r["outer"]
        B, A = 1.0, 0.36
        pts = [(0, B), (B, B), (B, 0), (B - A, 0), (B - A, B - A), (0, B - A)]
        f = Fig(f"An L shape: an outer corner square {b} by {b} with the inner corner missing; both arms are {a} "
                f"thick. A dashed line from the inner corner to the outer corner splits it into two trapezoids.")
        f.poly(pts).seg(pts[4], pts[1], "dash")
        for v, d0 in ((pts[0], 270), (pts[5], 0), (pts[3], 0), (pts[2], 90)):
            f.right(v, d0, 8)
        f.side(pts[0], pts[1], b, pts[4]).side(pts[1], pts[2], b, pts[4])
        f.side(pts[2], pts[3], a, pts[1]).side(pts[5], pts[0], a, pts[1])
    else:
        l_, w = r["len"], r["wid"]
        L, W = 2.0, 0.8
        f = Fig(f"A rectangle {l_} long and {w} wide with a square of side {w} attached at its right end. "
                f"The shared side is dashed.")
        f.poly([(L, 0), (0, 0), (0, W), (L, W)], closed=False)
        f.poly([(L, W), (L + W, W), (L + W, 0), (L, 0)], closed=False).seg((L, 0), (L, W), "dash")
        f.right((0, 0), 0, 8).right((L + W, W), 180, 8)
        f.side((0, W), (L, W), l_, (0, 0)).side((0, 0), (0, W), w, (L, 0)).side((L + W, 0), (L + W, W), w, (L, 0))
    return f.out()


def comp_answer(p):
    r = comp_roles(p)
    formula, slips = COMPOSITES[p["shape"]][2][p["ask"]]
    target = "p" if p["ask"] == "P" else "A"
    word = "perimeter" if p["ask"] == "P" else "area"
    shown = formula.format(**r).replace("^2", "²").replace(" - ", " − ")
    return Sym(target, formula.format(**r), list(p["letters"]), word,
               slips=[(e.format(**r), m.format(**r)) for e, m in slips]), shown


def comp_view(p):
    word = "perimeter p" if p["ask"] == "P" else "area A"
    hint = ("Go around the outside and add each edge. Dashed lines are inside the figure, so they don't count."
            if p["ask"] == "P" else
            "Add the areas of the two pieces." + {"par_sq": " A parallelogram is base × height; a square is side².",
                                                  "L": " Each trapezoid is ½(b₁ + b₂)h, with parallel sides "
                                                       "outer and outer − thickness, and height the thickness.",
                                                  "rect_sq": " A rectangle is length × width; a square is side²."
                                                  }[p["shape"]])
    letters = ", ".join(p["letters"])
    return {"text": f"The figure is {COMPOSITE_TEXT[p['shape']]}. Set up a formula for its {word} in terms of "
                    f"{letters}. Don't include the dashed lines.",
            "hint": hint, "figure": comp_fig(p)}


def comp_solve(p):
    ans, shown = comp_answer(p)
    r = comp_roles(p)
    ans.expr_text = shown
    return Solution(ans, comp_steps(p["shape"], p["ask"], r))


def comp_steps(shape, ask, r):
    if shape == "par_sq":
        a, b, h = r["side"], r["base"], r["height"]
        if ask == "P":
            return [f"Outside edges: the parallelogram's two {b} sides and its left side {a}, plus the square's "
                    f"three outer sides, {a} each.", f"p = 2{b} + {a} + 3{a} = 4{a} + 2{b}"]
        return [f"Parallelogram: base × height = {b}{h}", f"Square: {a}²", f"A = {b}{h} + {a}²"]
    if shape == "L":
        a, b = r["thick"], r["outer"]
        if ask == "P":
            return [f"Outside edges: {b} and {b} along the outer corner, {a} and {a} across the two ends, and two "
                    f"inner edges of {b} − {a} each.", f"p = 2{b} + 2{a} + 2({b} − {a}) = 4{b}"]
        return [f"Each trapezoid: ½({b} + ({b} − {a})) × {a} = ½{a}(2{b} − {a})",
                f"Two of them: A = {a}(2{b} − {a}) = 2{a}{b} − {a}²",
                f"Check: the big square {b}² minus the missing corner ({b} − {a})² gives the same."]
    l_, w = r["len"], r["wid"]
    if ask == "P":
        return [f"Outside edges: two lengths {l_}, the rectangle's far end {w}, and the square's three outer sides, "
                f"{w} each.", f"p = 2{l_} + {w} + 3{w} = 2{l_} + 4{w}"]
    return [f"Rectangle: {l_}{w}. Square: {w}²", f"A = {l_}{w} + {w}²"]


def comp_gen(rng):
    shape = rng.choice(tuple(COMPOSITES))
    _, picks, _ = COMPOSITES[shape]
    return {"shape": shape, "ask": rng.choice(("P", "A")), "letters": "".join(rng.choice(c) for c in picks)}


def comp_valid(p):
    keys(p, "shape", "ask", "letters")
    shape = choice(p, "shape", tuple(COMPOSITES))
    choice(p, "ask", ("P", "A"))
    _, picks, _ = COMPOSITES[shape]
    s = p["letters"]
    return isinstance(s, str) and len(s) == len(picks) and all(ch in c for ch, c in zip(s, picks))


# ====================================================================== 2.4

# --- Fig. 2.85's layout: secant A-B-O-C-D, tangent A-E-F touching at E, chord EC, radius EO -------

CIRCLE_ASKS = ("secant", "tangent", "chords", "inscribed", "perp", "isosceles", "segment", "sector_acute",
               "radius", "diameter", "touch", "sector_obtuse")


def circle_roles(p):
    return dict(zip("ABCDEF", p["letters"]))


def circle_fig(p):
    L, phi = circle_roles(p), p["phi"]
    O = (0, 0)
    f = Fig(f"Circle with center O. Points {L['A']}, {L['B']}, O, {L['C']}, {L['D']} lie on one line across it: "
            f"{L['B']} and {L['C']} are on the circle, {L['A']} is far outside on the left and {L['D']} just outside "
            f"on the right. Line {L['A']}{L['E']}{L['F']} touches the circle only at {L['E']}, upper left. "
            f"Segments O{L['E']} and {L['E']}{L['C']} are drawn.")
    pts = circle_points(f, O, 1.0, {"B": (180, 1), "C": (0, 1), "E": (phi, 1)}, "O")
    A = (1 / math.cos(math.radians(phi)), 0)
    D = (1.22, 0)
    E = pts["E"]
    F = lerp(A, E, 1.32)
    f.seg(A, D).seg(A, F).seg(O, E).seg(E, pts["C"])
    f.dot(A).dot(D).dot(F)
    f.label(A, L["A"], 270, 13).label(pts["B"], L["B"], 235, 14).label(O, "O", 270, 13)
    f.label(pts["C"], L["C"], 222, 19).label(D, L["D"], 330, 13)
    f.label(E, L["E"], phi - 25, 15).label(F, L["F"], 75, 13)
    return f.out()


def pairs(names):
    return [a + b for i, a in enumerate(names) for b in names[i + 1:]]


def circle_ident_solve(p):
    L = circle_roles(p)
    A, B, C, Dd, E, F = (L[k] for k in "ABCDEF")
    letters = p["letters"] + "O"
    secant, tangent = pairs([A, B, "O", C, Dd]), pairs([A, E, F])
    spec = {
        "secant": ([secant], 1, "pair", f"{A}{Dd} (any two of {A}, {B}, O, {C}, {Dd} name it)",
                   f"Line {A}{Dd} cuts the circle at two points, {B} and {C}, so it's a secant."),
        "tangent": ([tangent], 1, "pair", f"{A}{F} (or {A}{E}, {E}{F})",
                    f"Line {A}{F} touches the circle only at {E}, so it's a tangent."),
        "chords": ([[B + C], [E + C]], 2, "pair", f"{B}{C} and {E}{C}",
                   f"{B}{C} and {E}{C} both have their ends on the circle. {B}{C} is also a diameter, which is a chord "
                   f"through the center."),
        "inscribed": ([[E + C + B, E + C + "O", E + C + A]], 1, "angle", f"∠{E}{C}{B}",
                      f"∠{E}{C}{B} has its vertex {C} on the circle, and its sides {C}{E} and {C}{B} are chords. "
                      f"(∠{E}{C}O names the same angle.)"),
        "perp": ([["O" + E], tangent], 2, "pair", f"O{E} and {A}{F}",
                 f"O{E} is a radius to the point where the tangent {A}{F} touches, and a tangent is perpendicular "
                 f"to that radius."),
        "isosceles": ([["O" + E + C]], 1, "set3", f"ΔO{E}{C}",
                      f"O{E} and O{C} are both radii, so they're equal and ΔO{E}{C} is isosceles."),
        "segment": ([[E + C]], 1, "pair", f"the segment cut off by chord {E}{C} (between chord {E}{C} and arc {E}{C})",
                    f"A segment is the region between a chord and its arc: chord {E}{C} and arc {E}{C}."),
        "sector_acute": ([["O" + E + B]], 1, "set3", f"sector O{E}{B}",
                         f"Sector O{E}{B} lies between radii O{E} and O{B}. Its central angle ∠{E}O{B} is less than "
                         f"90°. (∠{E}O{C}, the other one, is obtuse.)"),
        "sector_obtuse": ([["O" + E + C]], 1, "set3", f"sector O{E}{C}",
                          f"Sector O{E}{C} lies between radii O{E} and O{C}. Its central angle ∠{E}O{C} is more than "
                          f"90°."),
        "radius": ([["O" + E], ["O" + B], ["O" + C]], 1, "pair", f"O{E} (or O{B}, O{C})",
                   f"O{E}, O{B} and O{C} each join the center to a point on the circle."),
        "diameter": ([[B + C]], 1, "pair", f"{B}{C}", f"{B}{C} is a chord through the center O."),
        "touch": ([[E]], 1, "point", f"{E}", f"The tangent {A}{F} meets the circle only at {E}."),
    }[p["ask"]]
    items, pick, kind, shown, step = spec
    prefix = {"isosceles": "Δ", "sector_acute": "sector ", "sector_obtuse": "sector "}.get(p["ask"], "")
    return Solution(Ident(items, pick, kind, letters, shown, prefix), [step])


def circle_ident_view(p):
    text = {"secant": "Name a secant line.", "tangent": "Name the tangent line.",
            "chords": "Name the two chords drawn in the figure.", "inscribed": "Name the inscribed angle.",
            "perp": "Name two lines that are perpendicular.", "isosceles": "Name an isosceles triangle.",
            "segment": "Name a segment of the circle by the chord that cuts it off.",
            "sector_acute": "Name a sector whose central angle is acute.",
            "sector_obtuse": "Name a sector whose central angle is obtuse.",
            "radius": "Name a radius.", "diameter": "Name the diameter.",
            "touch": "Name the point of tangency."}[p["ask"]]
    hint = {"secant": "A secant line crosses the circle at two points.",
            "tangent": "A tangent line touches the circle at exactly one point.",
            "chords": "A chord is a segment with both ends on the circle. A diameter counts.",
            "inscribed": "An inscribed angle has its vertex on the circle, and its sides are chords.",
            "perp": "A tangent is perpendicular to the radius drawn to the point where it touches.",
            "isosceles": "Two radii of the same circle are equal.",
            "segment": "A segment is the region between a chord and the arc it cuts off.",
            "sector_acute": "A sector is the region between two radii and their arc. Its central angle is at O.",
            "sector_obtuse": "A sector is the region between two radii and their arc. Its central angle is at O.",
            "radius": "A radius joins the center to a point on the circle.",
            "diameter": "A diameter is a chord through the center.",
            "touch": "It's where the tangent line meets the circle."}[p["ask"]]
    return {"text": "The circle has center O. " + text, "hint": hint, "figure": circle_fig(p)}


def circle_ident_gen(rng):
    return {"letters": pick_letters(rng, 6, "ABCDEFGHJKLMNPRSTUVWXYZ"), "phi": rng.randint(100, 118),
            "ask": rng.choice(CIRCLE_ASKS)}


def circle_ident_valid(p):
    keys(p, "letters", "phi", "ask")
    letters_ok(p, "letters", 6, forbid="O")
    whole(p, "phi", 95, 125)
    choice(p, "ask", CIRCLE_ASKS)
    return True


# --- circumference and area ------------------------------------------------------------------------

def rd_fig(p, label=None):
    f = Fig(f"Circle with {label or ('radius r = ' if p['given'] == 'r' else 'diameter d = ') + gv(p, 'value')}.")
    O = (0, 0)
    f.circle(O, 1.0).dot(O)
    if label:
        f.label((0, 1), label, 90, 12, "val")
    elif p["given"] == "r":
        f.seg(O, pol(O, 1, 30), "thin").side(O, pol(O, 1, 30), f"r = {gv(p, 'value')}", (0.5, -0.5))
    else:
        f.seg((-1, 0), (1, 0), "thin").side((-1, 0), (1, 0), f"d = {gv(p, 'value')}", (0, -1))
    return f.out()


def rd_gen(rng):
    unit = rng.choice(UNITS)
    return {"given": rng.choice(("r", "d")), "value": meas_u(rng, unit, figs(rng)), "unit": unit}


def rd_valid(p):
    keys(p, "given", "value", "unit")
    choice(p, "given", ("r", "d"))
    choice(p, "unit", UNITS)
    return given(p, "value")


def circ_view(p):
    what = "radius r" if p["given"] == "r" else "diameter d"
    return {"text": f"Find the circumference of a circle with {what} = {gv(p, 'value')}.",
            "hint": "C = 2πr, or C = πd with the diameter.", "figure": rd_fig(p)}


def circ_solve(p):
    v = given(p, "value")
    u = U(p)
    if p["given"] == "r":
        c = 2 * PI * v
        return Solution(Num(c, "length", p["unit"], sig(p["value"]),
                            slips=[(PI * v, "That's πr. The circumference is 2πr."),
                                   (PI * v * v, "That's the area (πr²). The circumference is 2πr.")]),
                        [f"C = 2πr = 2π × {p['value']} = {g(c)} {u}"])
    c = PI * v
    return Solution(Num(c, "length", p["unit"], sig(p["value"]),
                        slips=[(2 * PI * v, "With the diameter it's πd, not 2πd."),
                               (PI * v * v / 4, "That's the area. The circumference is πd.")]),
                    [f"C = πd = π × {p['value']} = {g(c)} {u}"])


def area_view(p):
    what = "radius r" if p["given"] == "r" else "diameter d"
    return {"text": f"Find the area of a circle with {what} = {gv(p, 'value')}.",
            "hint": "A = πr²." + (" The radius is half the diameter." if p["given"] == "d" else ""),
            "figure": rd_fig(p)}


def area_solve(p):
    v = given(p, "value")
    if p["given"] == "r":
        a = PI * v * v
        return Solution(Num(a, "area", p["unit"], sig(p["value"]),
                            slips=[(2 * PI * v, "That's the circumference. The area is πr².")]),
                        [f"A = πr² = π × {p['value']}² = {g(a)} {U2(p)}"])
    r = v / 2
    a = PI * r * r
    return Solution(Num(a, "area", p["unit"], sig(p["value"]),
                        slips=[(PI * v * v, "That used the diameter as the radius. r = d / 2 first."),
                               (PI * v, "That's the circumference. The area is πr².")]),
                    [f"r = d / 2 = {p['value']} / 2 = {g(r)} {U(p)}", f"A = πr² = π × {g(r)}² = {g(a)} {U2(p)}"])


def fromc_gen(rng):
    unit = rng.choice(UNITS)
    return {"c": meas_u(rng, unit, figs(rng)), "unit": unit}


def fromc_valid(p):
    keys(p, "c", "unit")
    choice(p, "unit", UNITS)
    return given(p, "c")


def fromc_view(p):
    return {"text": f"Find the area of a circle with circumference C = {gv(p, 'c')}.",
            "hint": "Get the radius from the circumference first: C = 2πr, so r = C / (2π). Then A = πr².",
            "figure": rd_fig(p, f"C = {gv(p, 'c')}")}


def fromc_solve(p):
    c = given(p, "c")
    r = c / (2 * PI)
    a = c * c / (4 * PI)
    return Solution(Num(a, "area", p["unit"], sig(p["c"]),
                        slips=[(PI * c * c, "That treats the circumference as the radius. Find r = C / (2π) first.")]),
                    [f"r = C / (2π) = {p['c']} / (2π) = {g(r)} {U(p)}",
                     f"A = πr² = π × {g(r)}² = {g(a)} {U2(p)}",
                     f"(In one step: A = C² / (4π).)"])


# --- Fig. 2.86's layout: diameter AB, tangent TB at B, A-C-T in a line -----------------------------

TANGENT = {
    "CBT": (lambda b: 90 - b, lambda b: ["TB is tangent at B and AB is a diameter, so ∠ABT = 90° "
                                         "(a tangent is perpendicular to the radius where it touches).",
                                         f"∠CBT = ∠ABT − ∠ABC = 90° − {b}° = {90 - b}°"]),
    "BCT": (lambda b: 90, lambda b: ["∠ACB = 90°: it's inscribed in a semicircle, since AB is a diameter.",
                                     "A, C and T lie on one line: ∠BCT = 180° − 90° = 90°"]),
    "ACB": (lambda b: 90, lambda b: ["AB is a diameter, so ∠ACB is inscribed in a semicircle: ∠ACB = 90°"]),
    "CAB": (lambda b: 90 - b, lambda b: ["∠ACB = 90° (inscribed in a semicircle).",
                                         f"In ΔABC: ∠CAB = 180° − 90° − {b}° = {90 - b}°"]),
    "BTC": (lambda b: b, lambda b: [f"∠ABT = 90° (tangent ⟂ radius), so ∠CBT = 90° − {b}° = {90 - b}°",
                                    "∠BCT = 90° (∠ACB is inscribed in a semicircle, and A, C, T are in line).",
                                    f"In ΔBCT: ∠BTC = 180° − 90° − {90 - b}° = {b}°"]),
}


def tangent_fig(b):
    O, A, B = (0, 0), (0, 1), (0, -1)
    k = 2 * math.cos(math.radians(b))
    C = (k * math.sin(math.radians(b)), -1 + k * math.cos(math.radians(b)))
    t = -2 / (C[1] - 1)
    T = (A[0] + (C[0] - A[0]) * t, -1)
    f = Fig(f"Circle with center O. AB is a vertical diameter, A at the top. Line TB touches the circle at B, with "
            f"T to the right. C is on the circle at the lower right, on line AT. Chord BC is drawn; ∠ABC = {b}°.")
    f.circle(O, 1).dot(O).dot(A).dot(B).dot(C).dot(T)
    f.seg(A, B).seg((-0.7, -1), (T[0] + 0.35, -1)).seg(A, T).seg(B, C)
    f.arc(B, 90 - b, 90, f"{b}°", r=26, tr=40)
    f.label(A, "A", 90, 12).label(B, "B", 270, 13).label(O, "O", 180, 11).label(C, "C", 15, 12).label(T, "T", 270, 13)
    return f.out()


def tangent_view(p):
    return {"text": f"AB is a diameter, TB is tangent to the circle at B, and ∠ABC = {p['beta']}°. Find ∠{p['ask']}.",
            "hint": "A tangent is perpendicular to the radius where it touches, and an angle inscribed in a "
                    "semicircle is 90°. Then use the triangle angle sum.",
            "figure": tangent_fig(p["beta"])}


def tangent_solve(p):
    fn, steps = TANGENT[p["ask"]]
    return Solution(angle_num(fn(p["beta"])), steps(p["beta"]))


def tangent_valid(p):
    keys(p, "beta", "ask")
    whole(p, "beta", 30, 80)
    choice(p, "ask", tuple(TANGENT))
    return True


# --- Fig. 2.87's layout: triangle ABC inscribed, arc AC and ∠CAB given -----------------------------

INSCRIBED = ("arc_bc", "arc_ab", "ABC", "ACB")


def inscribed_fig(x, y):
    bc = 2 * y
    tc = 90 + (bc - x) / 2
    ta, tb = tc + x, tc - bc
    O = (0, 0)
    f = Fig(f"Triangle ABC inscribed in a circle: A on the left, B on the right, C at the top. Arc AC is {x}° and "
            f"the inscribed angle at A, ∠CAB, is {y}°.")
    pts = circle_points(f, O, 1.0, {"A": (ta, 1), "B": (tb, 1), "C": (tc, 1)}, None)
    f.poly([pts["A"], pts["B"], pts["C"]])
    for n in "ABC":
        f.label(pts[n], n, {"A": ta, "B": tb, "C": tc}[n], 13)
    m = (ta + tc) / 2
    f.label(pol(O, 1, m), f"{x}°", m, 16, "val")
    f.angle_between(pts["A"], pts["B"], pts["C"], f"{y}°", r=22)
    return f.out()


def inscribed_view(p):
    x, y = p["arc_ac"], p["a"]
    what = {"arc_bc": "arc BC", "arc_ab": "arc AB (the one not containing C)", "ABC": "∠ABC", "ACB": "∠ACB"}[p["ask"]]
    return {"text": f"Triangle ABC is inscribed in the circle. Arc AC = {x}° and ∠CAB = {y}°. Find {what}.",
            "hint": "An inscribed angle is half the arc it cuts off. The three arcs add up to 360°.",
            "figure": inscribed_fig(x, y)}


def inscribed_solve(p):
    x, y, ask = p["arc_ac"], p["a"], p["ask"]
    ab = 360 - x - 2 * y
    if ask == "arc_bc":
        return Solution(angle_num(2 * y, [(D(y) / 2, "Other way round: the arc is twice the inscribed angle.")]),
                        [f"∠CAB is inscribed and cuts off arc BC, so it's half of it.", f"arc BC = 2 × {y}° = {2 * y}°"])
    if ask == "arc_ab":
        return Solution(angle_num(ab), [f"arc BC = 2 × ∠CAB = 2 × {y}° = {2 * y}°",
                                        f"The three arcs make the full circle: arc AB = 360° − {x}° − {2 * y}° = {ab}°"])
    if ask == "ABC":
        v = D(x) / 2
        return Solution(angle_num(v, [(D(x) * 2, "Other way round: the inscribed angle is half the arc.")]),
                        [f"∠ABC is inscribed and cuts off arc AC: ∠ABC = ½ × {x}° = {deg(v)}"])
    v = D(ab) / 2
    return Solution(angle_num(v), [f"arc AB = 360° − {x}° − 2 × {y}° = {ab}°",
                                   f"∠ACB cuts off arc AB: ∠ACB = ½ × {ab}° = {deg(v)}",
                                   f"Check: {y}° + {deg(D(x) / 2)} + {deg(v)} = 180°"])


def inscribed_gen(rng):
    while True:
        x, y = rng.randrange(40, 141, 2), rng.randint(20, 80)
        if 50 <= 360 - x - 2 * y <= 250:
            return {"arc_ac": x, "a": y, "ask": rng.choice(INSCRIBED)}


def inscribed_valid(p):
    keys(p, "arc_ac", "a", "ask")
    x, y = whole(p, "arc_ac", 10, 300), whole(p, "a", 5, 170)
    choice(p, "ask", INSCRIBED)
    return 10 <= 360 - x - 2 * y <= 340


# --- degrees to radians ----------------------------------------------------------------------------

COMMON = ("15", "22.5", "30", "36", "45", "60", "72", "90", "120", "135", "150", "210", "225", "240", "270",
          "300", "315", "330")


def rad_gen(rng):
    if rng.random() < 0.45:
        return {"deg": rng.choice(COMMON)}
    return {"deg": f"{rng.randint(50, 3590) / 10:.1f}"}


def rad_valid(p):
    keys(p, "deg")
    return given(p, "deg", "0", "720")


def rad_view(p):
    return {"text": f"Change {p['deg']}° to radians.",
            "hint": "π rad = 180°, so multiply the degrees by π/180.", "figure": None}


def rad_solve(p):
    d = given(p, "deg")
    frac = Fraction(p["deg"]) / 180
    v = d * PI / 180
    s = sig(p["deg"]) if "." in p["deg"] else None
    return Solution(Num(v, "radian", sig=s, pi=frac,
                        slips=[(d, "That's still in degrees. Multiply by π/180."),
                               (d * 180 / PI, "That multiplies by 180/π. Going to radians, multiply by π/180.")]),
                    [f"radians = degrees × π/180", f"= {p['deg']} × π/180 = {fmt_pi(frac)}",
                     f"= {g(v)} rad"])


# ==================================================================== types

TYPES = [
    Type("fan_ident", "2.1", "Name angles and sides in a fan of rays",
         fan_gen(FAN_ASKS, 20, 70), lambda p: fan_valid(p, FAN_ASKS), fan_ident_view, fan_ident_solve),
    Type("fan_angle", "2.1", "Complements and supplements",
         fan_gen(FAN_ANGLE_ASKS, 15, 75), lambda p: fan_valid(p, FAN_ANGLE_ASKS), fan_angle_view, fan_angle_solve),
    Type("three_lines", "2.1", "Angles where three lines cross",
         lambda rng: {"alpha": rng.randint(20, 70), "ask": rng.choice(tuple(THREE))},
         three_valid, three_view, three_solve),
    Type("transversals", "2.1", "Two lines crossing a third",
         lambda rng: {"beta": rng.randint(135, 160), "ask": rng.choice(("1", "2", "3", "4", "5"))},
         transversals_valid, transversals_view, transversals_solve),
    Type("parallels", "2.1", "Parallel lines and a transversal",
         lambda rng: {"gamma": rng.randint(50, 70), "ask": rng.choice(tuple(PARALLEL_VALUE))},
         parallels_valid, parallels_view, parallels_solve),
    Type("truss", "2.1", "Angle-chasing in a truss",
         lambda rng: {"alpha": rng.randint(32, 58), "ask": rng.choice(tuple(TRUSS))},
         truss_valid, truss_view, truss_solve),

    Type("third_angle", "2.2", "The third angle of a triangle", third_gen, third_valid, third_view, third_solve),
    Type("area_bh", "2.2", "Area from base and height", bh_gen, bh_valid,
         lambda p: {"text": "Find the area of the triangle.", "hint": "A = ½ × base × height. The height is the "
                    "dashed line, at right angles to the base.", "figure": bh_fig(p)}, bh_solve),
    Type("area_heron", "2.2", "Area from three sides (Heron's formula)", sides_gen, sides_valid, heron_view,
         heron_solve),
    Type("area_legs", "2.2", "Area of a right triangle from its legs", legs_gen, legs_valid,
         lambda p: {"text": f"A right triangle has legs of {gv(p, 'a')} and {gv(p, 'b')}. Find its area.",
                    "hint": "The two legs are at right angles, so one is the base and the other the height.",
                    "figure": right_legs_fig(p)}, legs_solve),
    Type("area_isosceles", "2.2", "Area of an isosceles triangle", iso_gen, iso_valid,
         lambda p: {"text": f"An isosceles triangle has two equal sides of {gv(p, 'leg')} and a third side of "
                            f"{gv(p, 'base')}. Find its area.",
                    "hint": "Drop the height to the third side: it cuts that side in half and makes two right "
                            "triangles. Find the height with the Pythagorean theorem.",
                    "figure": iso_fig(p)}, iso_area_solve),
    Type("area_equilateral", "2.2", "Area of an equilateral triangle", equi_gen, equi_valid,
         lambda p: {"text": f"An equilateral triangle has sides of {gv(p, 's')}. Find its area.",
                    "hint": "Use A = (√3 / 4)s², or find the height with the Pythagorean theorem.",
                    "figure": equi_fig(p)}, equi_area_solve),
    Type("perimeter", "2.2", "Perimeter of a triangle", perim_gen, perim_valid, perim_view, perim_solve),
    Type("pythag", "2.2", "Missing side of a right triangle", pythag_gen, pythag_valid, pythag_view, pythag_solve),
    Type("right_angle_leg", "2.2", "Right triangle from an angle and a leg", rt_gen, rt_valid, rt_view, rt_solve),

    Type("quad_perimeter", "2.3", "Perimeter: square, rhombus, rectangle", basic_gen(SHAPES), basic_valid(SHAPES),
         qp_view, qp_solve),
    Type("para_perimeter", "2.3", "Perimeter of a parallelogram", para_gen, para_valid, pp_view, pp_solve),
    Type("trap_perimeter", "2.3", "Perimeter of a trapezoid", trap_gen, trap_valid, tp_view, tp_solve),
    Type("quad_area", "2.3", "Area: square, rectangle", basic_gen(("square", "rectangle")),
         basic_valid(("square", "rectangle")), qa_view, qa_solve),
    Type("para_area", "2.3", "Area of a parallelogram", para_gen, para_valid, pa_view, pa_solve),
    Type("trap_area", "2.3", "Area of a trapezoid", trap_gen, trap_valid, ta_view, ta_solve),
    Type("composite", "2.3", "Formula for a composite figure", comp_gen, comp_valid, comp_view, comp_solve),

    Type("circle_parts", "2.4", "Name the parts of a circle", circle_ident_gen, circle_ident_valid,
         circle_ident_view, circle_ident_solve),
    Type("circumference", "2.4", "Circumference from r or d", rd_gen, rd_valid, circ_view, circ_solve),
    Type("circle_area", "2.4", "Area from r or d", rd_gen, rd_valid, area_view, area_solve),
    Type("area_from_c", "2.4", "Area from the circumference", fromc_gen, fromc_valid, fromc_view, fromc_solve),
    Type("tangent", "2.4", "Tangent and diameter angles",
         lambda rng: {"beta": rng.randint(40, 75), "ask": rng.choice(tuple(TANGENT))},
         tangent_valid, tangent_view, tangent_solve),
    Type("inscribed", "2.4", "Inscribed angles and arcs", inscribed_gen, inscribed_valid, inscribed_view,
         inscribed_solve),
    Type("radians", "2.4", "Degrees to radians", rad_gen, rad_valid, rad_view, rad_solve),
]
