"""Figures for study-guide problems: original SVG, drawn from each problem's own geometry.

Builders work in plain math coordinates (y up, any scale). Fig.out() scales the drawing to fit,
flips y for SVG and returns primitives that static/study.js draws without knowing any geometry:
  {"t": "path", "d": ..., "c": class}           lines, arcs, right-angle marks, ticks, arrowheads
  {"t": "circle", "x", "y", "r", "c": class}
  {"t": "text", "x", "y", "s": text, "c": class, "a": anchor}
Text, angle arcs and right-angle marks are sized in output units, so they stay readable at any scale.
Classes: ln (main lines), thin, dash (heights and other construction lines), mark (angle arcs),
fill (arrowheads, dots), pt (point labels), val (measurements), q (the unknown, in the pointer color).

The reusable helpers at the bottom are the ones the geometry chapters need: a fan of rays,
parallel lines with a transversal, a triangle with marked angles, a quadrilateral with a dashed
height, and a circle with labeled points.
"""
import math

W_MAX, H_MAX = 300, 220
FONT = {"pt": 17, "val": 15, "q": 15.5, "num": 15}
PAD = 6


def pol(p, r, deg):
    a = math.radians(deg)
    return (p[0] + r * math.cos(a), p[1] + r * math.sin(a))


def ang(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def mid(a, b):
    return lerp(a, b, 0.5)


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def meet(p, d1, q, d2):
    """Where the line through p (direction d1 degrees) meets the line through q (direction d2)."""
    u = (math.cos(math.radians(d1)), math.sin(math.radians(d1)))
    v = (math.cos(math.radians(d2)), math.sin(math.radians(d2)))
    den = u[0] * v[1] - u[1] * v[0]
    t = ((q[0] - p[0]) * v[1] - (q[1] - p[1]) * v[0]) / den
    return (p[0] + u[0] * t, p[1] + u[1] * t)


def centroid(pts):
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def _span(a0, a1):
    return (a1 - a0) % 360


class Fig:
    def __init__(self, alt):
        self.alt = alt                # text alternative for screen readers
        self.geo = []                 # world-space geometry
        self.marks = []               # anchored at a world point, sized in output units

    # -- geometry ---------------------------------------------------------

    def seg(self, a, b, c="ln", arrow=""):
        """arrow: "" none, "b" at b, "ab" at both ends."""
        self.geo.append(("seg", a, b, c, arrow))
        return self

    def ray(self, a, deg, length, c="ln", arrow=True, name=None, dist_=14):
        b = pol(a, length, deg)
        self.seg(a, b, c, "b" if arrow else "")
        if name:
            self.label(b, name, deg, dist_)
        return b

    def poly(self, pts, c="ln", closed=True):
        self.geo.append(("poly", list(pts), c, closed))
        return self

    def circle(self, c0, r, c="ln"):
        self.geo.append(("circle", c0, r, c))
        return self

    def dot(self, p):
        self.marks.append(("dot", p))
        return self

    # -- marks (output-unit sizes) ----------------------------------------

    def arc(self, v, a0, a1, text=None, r=20, c="mark", tc="val", tr=None):
        """Angle mark at v from direction a0 counter-clockwise to a1, with optional text on the bisector."""
        self.marks.append(("arc", v, a0, a1, r, c))
        if text:
            b = a0 + _span(a0, a1) / 2
            self.label(v, text, b, tr or r + 12, tc)
        return self

    def angle_between(self, v, p, q, text=None, r=20, tc="val", tr=None):
        """Mark the smaller angle at v between rays v->p and v->q."""
        a0, a1 = ang(v, p), ang(v, q)
        if _span(a0, a1) > 180:
            a0, a1 = a1, a0
        return self.arc(v, a0, a1, text, r, tc=tc, tr=tr)

    def right(self, v, a0, size=10):
        """Right-angle square at v between direction a0 and a0 + 90."""
        self.marks.append(("right", v, a0, size))
        return self

    def right_between(self, v, p, q, size=10):
        a0, a1 = ang(v, p), ang(v, q)
        return self.right(v, a0 if _span(a0, a1) < 180 else a1, size)

    def ticks(self, a, b, n=1):
        self.marks.append(("ticks", a, b, n))
        return self

    def label(self, p, s, deg=90, d=13, c="pt"):
        """Text `d` output units from p, in direction deg."""
        self.marks.append(("text", p, s, deg, d, c))
        return self

    def side(self, a, b, s, away=None, d=13, c="val"):
        """Text beside segment ab, on the side away from point `away` (default: left of a->b)."""
        m = mid(a, b)
        n = ang(a, b) + 90
        if away is not None and math.cos(math.radians(n - ang(m, away))) > 0:
            n += 180
        return self.label(m, s, n, d, c)

    def text(self, p, s, c="val"):
        return self.label(p, s, 0, 0, c)

    # -- output -----------------------------------------------------------

    def out(self):
        pts = []
        for g in self.geo:
            if g[0] == "seg":
                pts += [g[1], g[2]]
            elif g[0] == "poly":
                pts += g[1]
            elif g[0] == "circle":
                (x, y), r = g[1], g[2]
                pts += [(x - r, y - r), (x + r, y + r)]
        for m in self.marks:
            pts.append(m[1])
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        s = min(W_MAX / max(x1 - x0, 1e-9), H_MAX / max(y1 - y0, 1e-9))

        def T(p):
            return ((p[0] - x0) * s, (y1 - p[1]) * s)

        items, box = [], []

        def path(d, c):
            items.append({"t": "path", "d": d, "c": c})

        def P(p):
            return f"{p[0]:.1f} {p[1]:.1f}"

        def head(tip, frm):
            a = math.atan2(tip[1] - frm[1], tip[0] - frm[0])
            l, w = 10, 4.2
            b1 = (tip[0] - l * math.cos(a) + w * math.sin(a), tip[1] - l * math.sin(a) - w * math.cos(a))
            b2 = (tip[0] - l * math.cos(a) - w * math.sin(a), tip[1] - l * math.sin(a) + w * math.cos(a))
            path(f"M{P(tip)}L{P(b1)}L{P(b2)}Z", "fill")

        for g in self.geo:
            if g[0] == "seg":
                a, b = T(g[1]), T(g[2])
                path(f"M{P(a)}L{P(b)}", g[3])
                if "b" in g[4]:
                    head(b, a)
                if "a" in g[4]:
                    head(a, b)
                box += [a, b]
            elif g[0] == "poly":
                q = [T(p) for p in g[1]]
                path("M" + "L".join(P(p) for p in q) + ("Z" if g[3] else ""), g[2])
                box += q
            elif g[0] == "circle":
                (cx, cy), r = T(g[1]), g[2] * s
                items.append({"t": "circle", "x": round(cx, 1), "y": round(cy, 1), "r": round(r, 1), "c": g[3]})
                box += [(cx - r, cy - r), (cx + r, cy + r)]

        def scr(p, r, deg):                       # output point r units from p in math direction deg
            a = math.radians(deg)
            return (p[0] + r * math.cos(a), p[1] - r * math.sin(a))

        for m in self.marks:
            v = T(m[1])
            if m[0] == "dot":
                items.append({"t": "circle", "x": round(v[0], 1), "y": round(v[1], 1), "r": 3.2, "c": "fill"})
            elif m[0] == "arc":
                _, _, a0, a1, r, c = m
                p0, p1 = scr(v, r, a0), scr(v, r, a1)
                large = 1 if _span(a0, a1) > 180 else 0
                path(f"M{P(p0)}A{r} {r} 0 {large} 0 {P(p1)}", c)
            elif m[0] == "right":
                _, _, a0, size = m
                p1, p3 = scr(v, size, a0), scr(v, size, a0 + 90)
                p2 = (p1[0] + p3[0] - v[0], p1[1] + p3[1] - v[1])
                path(f"M{P(p1)}L{P(p2)}L{P(p3)}", "mark")
            elif m[0] == "ticks":
                a, b, n = T(m[1]), T(m[2]), m[3]
                c0 = mid(a, b)
                d = math.atan2(b[1] - a[1], b[0] - a[0])
                for i in range(n):
                    off = (i - (n - 1) / 2) * 4.5
                    cx, cy = c0[0] + off * math.cos(d), c0[1] + off * math.sin(d)
                    nx, ny = -math.sin(d) * 6, math.cos(d) * 6
                    path(f"M{cx - nx:.1f} {cy - ny:.1f}L{cx + nx:.1f} {cy + ny:.1f}", "mark")
            elif m[0] == "text":
                _, _, txt, deg, d, c = m
                x, y = scr(v, d, deg)
                fs = FONT.get(c, 15)
                w = 0.6 * fs * len(txt) if c != "pt" else 0.62 * fs * len(txt)
                cos = math.cos(math.radians(deg))
                anchor = "middle"
                if d and cos > 0.45:
                    anchor, x = "start", x - fs * 0.15
                elif d and cos < -0.45:
                    anchor, x = "end", x + fs * 0.15
                items.append({"t": "text", "x": round(x, 1), "y": round(y, 1), "s": txt, "c": c, "a": anchor})
                left = x - (w / 2 if anchor == "middle" else w if anchor == "end" else 0)
                box += [(left, y - fs * 0.6), (left + w, y + fs * 0.6)]

        bx0, by0 = min(p[0] for p in box) - PAD, min(p[1] for p in box) - PAD
        bx1, by1 = max(p[0] for p in box) + PAD, max(p[1] for p in box) + PAD
        return {"vb": [round(bx0, 1), round(by0, 1), round(bx1 - bx0, 1), round(by1 - by0, 1)],
                "items": items, "alt": self.alt}


# ------------------------------------------------------------- the helpers

def fan(fig, v, rays, length=1.0):
    """A fan of rays from vertex v: [(name, direction in degrees, arrow?)]. Returns name -> far point."""
    fig.dot(v)
    return {name: fig.ray(v, deg, length, arrow=arrow, name=name) for name, deg, arrow in rays}


def parallels(fig, y_top, y_bottom, x0, x1, names=None):
    """Two horizontal parallel lines with arrowheads at both ends. names: ("A", "B", "C", "D")."""
    fig.seg((x0, y_top), (x1, y_top), arrow="ab").seg((x0, y_bottom), (x1, y_bottom), arrow="ab")
    if names:
        a, b, c, d = names
        fig.label((x0, y_top), a, 180, 14).label((x1, y_top), b, 0, 14)
        fig.label((x0, y_bottom), c, 180, 14).label((x1, y_bottom), d, 0, 14)


def transversal(fig, through, deg, y_lo, y_hi):
    """A line through `through` at angle deg, drawn between heights y_lo and y_hi, arrowheads at both ends."""
    t = math.tan(math.radians(deg))
    pa = (through[0] + (y_lo - through[1]) / t, y_lo)
    pb = (through[0] + (y_hi - through[1]) / t, y_hi)
    fig.seg(pa, pb, arrow="ab")
    return pa, pb


def triangle(fig, pts, names=None, sides=None, angles=None, right=None, ticks=None, q=None):
    """pts: three corners. names: corner labels. sides: {(i, j): text}. angles: {i: text} (an arc at corner i).
    right: corner index with a right-angle mark. ticks: [(i, j, n)] equal-side marks. q: side key drawn as unknown."""
    fig.poly(pts)
    c = centroid(pts)
    for i, p in enumerate(pts):
        if names and names[i]:
            fig.label(p, names[i], ang(c, p), 14)
    for (i, j), s in (sides or {}).items():
        fig.side(pts[i], pts[j], s, c, 13, "q" if (i, j) == q else "val")
    for i, s in (angles or {}).items():
        o = [pts[k] for k in range(3) if k != i]
        fig.angle_between(pts[i], o[0], o[1], s, r=22)
    if right is not None:
        o = [pts[k] for k in range(3) if k != right]
        fig.right_between(pts[right], o[0], o[1])
    for i, j, n in ticks or ():
        fig.ticks(pts[i], pts[j], n)


def height(fig, apex, a, b, text, side_away=None):
    """Dashed height from apex to line ab, with its right-angle mark. If the foot falls outside ab,
    the base is extended with a dashed line. Returns the foot."""
    d = ang(a, b)
    foot = meet(a, d, apex, d + 90)
    fig.seg(apex, foot, "dash")
    near = a if dist(foot, a) <= dist(foot, b) else b
    far = b if near is a else a
    t = ((foot[0] - a[0]) * (b[0] - a[0]) + (foot[1] - a[1]) * (b[1] - a[1])) / dist(a, b) ** 2
    if t < 0 or t > 1:
        fig.seg(foot, near, "dash")
    up, toward = ang(foot, apex), ang(foot, far)
    fig.right(foot, up if _span(up, toward) < 180 else toward, 9)
    if text:
        fig.side(apex, foot, text, side_away if side_away is not None else near, 12)
    return foot


def quadrilateral(fig, pts, names=None, sides=None, h=None):
    """pts: four corners, counter-clockwise. sides: {i: text} for side pts[i] -> pts[i+1].
    h: (top point, bottom line index, text) draws a dashed height from top point to that side."""
    fig.poly(pts)
    c = centroid(pts)
    for i, p in enumerate(pts):
        if names and names[i]:
            fig.label(p, names[i], ang(c, p), 14)
    for i, s in (sides or {}).items():
        fig.side(pts[i], pts[(i + 1) % 4], s, c)
    if h:
        top, k, s = h
        height(fig, top, pts[k], pts[(k + 1) % 4], s)


def circle_points(fig, c, r, points, center="O", dots=True):
    """A circle with named points on (or off) it: points = {name: (direction deg, distance as a multiple of r)}.
    Returns name -> point, with the center included."""
    fig.circle(c, r)
    out = {center: c} if center else {}
    if center:
        fig.dot(c)
    for name, (deg, k) in points.items():
        p = pol(c, r * k, deg)
        out[name] = p
        if dots:
            fig.dot(p)
    return out
