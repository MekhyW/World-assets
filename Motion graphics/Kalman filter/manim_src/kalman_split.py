"""Split screen: raw YOLO detections (left) vs Kalman-filtered track (right).

Render (from this folder):
    MG_LANG=en manim -qh --fps 60 kalman_split.py KalmanSplit   # English labels
    MG_LANG=pt manim -qh --fps 60 kalman_split.py KalmanSplit   # Portuguese labels

Optional Higgsfield art: drop drone.png / tree.png (subject on flat magenta)
into ../assets and they replace the vector stand-ins automatically; the
occlusion test then uses the tree image's alpha.
"""
import os

from common import *
import sim

LANG = os.environ.get("MG_LANG", "en")
STOP_AT = float(os.environ.get("MG_STOP_AT", "0"))   # >0: end early (still previews)

TXT = {
    "en": dict(raw="RAW DETECTIONS", kf="KALMAN FILTER", tracking="TRACKING", lost="TARGET LOST",
               acquiring="ACQUIRING", locked="LOCKED", predicting="PREDICTING"),
    "pt": dict(raw="DETECÇÃO BRUTA", kf="FILTRO DE KALMAN", tracking="RASTREANDO", lost="ALVO PERDIDO",
               acquiring="ADQUIRINDO", locked="TRAVADO", predicting="PREVENDO"),
}[LANG]

PW, PH, G = sim.PANEL_W, sim.PANEL_H, sim.GROUND_Y
CY = -0.35
LC = np.array([-2.225, CY, 0.0])
RC = np.array([2.225, CY, 0.0])
FPS = sim.FPS
T_OUT = sim.T_END - 0.55
T_LOCK = sim.T_FIRST_DET + 0.45

TREE_PNG = ASSET_DIR / "tree.png"
DRONE_PNG = ASSET_DIR / "drone.png"


def L(c, x, y):
    return c + np.array([x, y, 0.0])


def redraw(func, z):
    """Like always_redraw, but swaps the children each frame (no `become`
    alignment, so it stays fast and keeps its z-index)."""
    holder = Group()

    def upd(m, dt):     # dt arg -> counted as "moving" in every play/wait (never frozen)
        new = func()
        kids = new.submobjects if type(new) in (VGroup, Group) else [new]
        for k in kids:
            k.set_z_index(z)
        m.submobjects = list(kids)
    holder.add_updater(upd)
    holder.set_z_index(z)
    return holder


def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def envelope(t):
    return smooth01((t - 0.55) / 0.35) * (1 - smooth01((t - T_OUT) / 0.45))


def blink(t, hz=3.2):
    return 1.0 if (t * hz) % 1 < 0.62 else 0.25


# ======================================================================
#  static artwork
# ======================================================================
def make_panel(c, accent):
    bg = RoundedRectangle(width=PW, height=PH, corner_radius=0.16,
                          fill_color=PANEL_BG, fill_opacity=1, stroke_color=PANEL_EDGE, stroke_width=3).move_to(c)
    grid = VGroup()
    x0, x1 = -PW / 2 + 0.1, PW / 2 - 0.1
    y0, y1 = G, PH / 2 - 0.1
    for gx in np.arange(-1.8, 1.81, 0.6):
        grid.add(Line(L(c, gx, y0), L(c, gx, y1), stroke_color=GRID, stroke_width=2))
    for gy in np.arange(G + 0.6, y1, 0.6):
        grid.add(Line(L(c, x0, gy), L(c, x1, gy), stroke_color=GRID, stroke_width=2))
    ground = Line(L(c, x0, G), L(c, x1, G), stroke_color=SLATE, stroke_width=3)
    hatch = VGroup(*[Line(L(c, hx, G), L(c, hx - 0.14, G - 0.14), stroke_color="#222C3E", stroke_width=2)
                     for hx in np.arange(x0 + 0.16, x1, 0.2)])
    brackets = VGroup()
    k = 0.38
    for sx in (-1, 1):
        for sy in (-1, 1):
            corner = L(c, sx * (PW / 2 - 0.08), sy * (PH / 2 - 0.08))
            brackets.add(VMobject(stroke_color=accent, stroke_width=6).set_points_as_corners(
                [corner + np.array([-sx * k, 0, 0]), corner, corner + np.array([0, -sy * k, 0])]))
    return bg, VGroup(grid, hatch, ground), brackets


def make_header(c, label, accent):
    sq = Square(0.2, fill_color=accent, fill_opacity=1, stroke_color=INK, stroke_width=4)
    txt = mono(label, 0.28, accent)
    g = VGroup(sq, txt).arrange(RIGHT, buff=0.14)
    outlined(txt, 9)
    return g.move_to([c[0], CY + PH / 2 + 0.42, 0])


def fit_headers(*heads):
    """Same scale for every header so both panels' titles match."""
    k = min(1.0, min((PW - 0.12) / h.width for h in heads))
    for h in heads:
        h.scale(k)


def make_vector_tree(c):
    circles = [Circle(radius=r).move_to(L(c, cx, cy)) for cx, cy, r in sim.CANOPY]
    canopy = Union(*circles, fill_color="#1B2333", fill_opacity=1, stroke_color="#3D4B6B", stroke_width=3)
    hl = VGroup()
    for cx, cy, r in sim.CANOPY[1:6]:
        blob = Circle(radius=r * 0.55).move_to(L(c, cx - 0.18 * r, cy + 0.25 * r))
        hl.add(Intersection(blob, canopy, fill_color="#27324B", fill_opacity=1, stroke_width=0))
    tr = sim.TRUNK
    trunk = Polygon(L(c, tr["x"] - tr["w_bot"] / 2, G), L(c, tr["x"] - tr["w_top"] / 2, tr["y_top"]),
                    L(c, tr["x"] + tr["w_top"] / 2, tr["y_top"]), L(c, tr["x"] + tr["w_bot"] / 2, G),
                    fill_color="#151B28", fill_opacity=1, stroke_color="#3D4B6B", stroke_width=3)
    return VGroup(trunk, canopy, hl)


class TreeImage:
    """Higgsfield tree, keyed. Provides the mobject factory and an alpha occluder."""

    def __init__(self, path):
        self.rgba = keyed_rgba(path)
        h_px, w_px = self.rgba.shape[:2]
        self.H = 4.35                       # ground -> canopy top
        self.W = self.H * w_px / h_px
        self.x0 = sim.TRUNK["x"] - self.W / 2
        self.ytop = G + self.H

    def mob(self, c):
        m = ImageMobject(self.rgba)
        m.height = self.H
        return m.move_to(L(c, sim.TRUNK["x"], G + self.H / 2))

    def occluder(self, x, y):
        h_px, w_px = self.rgba.shape[:2]
        u = int((x - self.x0) / self.W * w_px)
        v = int((self.ytop - y) / self.H * h_px)
        return 0 <= u < w_px and 0 <= v < h_px and self.rgba[v, u, 3] > 128


# ======================================================================
#  drone
# ======================================================================
def vector_drone(t, pos, tilt, opacity):
    g = VGroup()
    arm_c = "#5B6678"
    for s in (-1, 1):
        g.add(Line([s * 0.12, 0.0, 0], [s * 0.38, 0.05, 0], stroke_color=arm_c, stroke_width=7))
        g.add(Line([s * 0.12, -0.08, 0], [s * 0.2, -0.2, 0], stroke_color=arm_c, stroke_width=5))
        g.add(Rectangle(width=0.1, height=0.08, fill_color="#353D4C", fill_opacity=1,
                        stroke_color=INK, stroke_width=2).move_to([s * 0.38, 0.06, 0]))
        g.add(Ellipse(width=0.46, height=0.07, fill_color="#C9D1DC", fill_opacity=0.3,
                      stroke_color="#E6EBF2", stroke_width=1.5, stroke_opacity=0.55).move_to([s * 0.38, 0.12, 0]))
        ph = 47 * t + (0.0 if s < 0 else 1.3)
        half = 0.22 * abs(np.cos(ph)) + 0.02
        g.add(Line([s * 0.38 - half, 0.12, 0], [s * 0.38 + half, 0.12, 0], stroke_color=WHITE, stroke_width=3.5))
        led = "#FF7A1A" if (t * 2.5 + (0.5 if s > 0 else 0)) % 1 < 0.5 else "#7A3A10"
        g.add(Dot([s * 0.38, 0.0, 0], radius=0.026, color=led))
    g.add(RoundedRectangle(width=0.46, height=0.18, corner_radius=0.07, fill_color="#DCE2EA", fill_opacity=1,
                           stroke_color=INK, stroke_width=3))
    g.add(RoundedRectangle(width=0.26, height=0.06, corner_radius=0.03, fill_color="#9AA4B3", fill_opacity=1,
                           stroke_width=0).move_to([0, 0.05, 0]))
    g.add(Circle(radius=0.065, fill_color="#20252F", fill_opacity=1, stroke_color=INK, stroke_width=2).move_to([0, -0.12, 0]))
    g.add(Dot([0, -0.12, 0], radius=0.025, color="#4FA3FF"))
    g.rotate(tilt, about_point=ORIGIN).shift(pos)
    g.set_opacity(opacity) if opacity < 0.999 else None
    return g


# ======================================================================
#  helpers for overlays
# ======================================================================
def dashed(points, dash=0.15, gap=0.1):
    """Split a polyline into dash sub-polylines by arc length."""
    if len(points) < 2:
        return []
    seg = np.linalg.norm(np.diff(points, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    out = []
    a = 0.0
    while a < s[-1]:
        b = min(a + dash, s[-1])
        idx = np.searchsorted(s, [a, b])
        pts = [np.array([np.interp(a, s, points[:, k]) for k in range(3)])]
        pts += list(points[idx[0]:idx[1]])
        pts.append(np.array([np.interp(b, s, points[:, k]) for k in range(3)]))
        out.append(np.array(pts))
        a = b + gap
    return out


def bracket_box(center, w, h, color, width=4, k=0.16):
    g = VGroup()
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = center + np.array([sx * w / 2, sy * h / 2, 0])
            g.add(VMobject(stroke_color=color, stroke_width=width).set_points_as_corners(
                [p + np.array([-sx * k, 0, 0]), p, p + np.array([0, -sy * k, 0])]))
    return g


class KalmanSplit(Scene):
    def get_moving_and_static_mobjects(self, animations):
        # Everything is driven by one clock and rebuilt every frame. Manim
        # normally snapshots the flattened family list when an animation
        # starts, which keeps drawing that frame's children ("ghost" drones).
        # Hand back the top-level mobjects so families are re-read each frame.
        return list(self.mobjects) + [m for m in self.foreground_mobjects if m not in self.mobjects], []

    def construct(self):
        # ---------------- assets / simulation ----------------
        tree_img = TreeImage(TREE_PNG) if TREE_PNG.exists() else None
        occ = tree_img.occluder if tree_img else sim.in_canopy
        drone_rgba = keyed_rgba(DRONE_PNG) if DRONE_PNG.exists() else None

        dets = sim.make_detections(occluder=occ)
        ts, est, cov, mode, accepted = sim.run_kf(dets)
        det_t = np.array([d[0] for d in dets])
        det_p = np.array([[d[1], d[2], 0.0] for d in dets])
        rng = np.random.default_rng(3)
        det_box = rng.normal(0, 0.12, (len(dets), 2))          # bbox size jitter
        det_conf = np.clip(rng.normal(0.66, 0.14, len(dets)), 0.31, 0.97)
        n_frames = len(ts)
        # display path: the filter output with a light 0.13 s gaussian ease so the
        # 30 Hz update steps don't show as kinks at 60 fps (no lag, no shape change)
        from scipy.ndimage import gaussian_filter1d
        i0 = int(np.argmax(~np.isnan(est[:, 0])))
        est = est.copy()
        est[i0:] = gaussian_filter1d(est[i0:], 8, axis=0, mode="nearest")
        i_lock = int(round(T_LOCK * FPS))

        clock = ValueTracker(0.0)
        clock.add_updater(lambda m, dt: m.increment_value(dt))
        self.add(clock)

        def T():
            return clock.get_value()

        def fidx(t):
            return int(np.clip(round(t * FPS), 0, n_frames - 1))

        # ---------------- static layers ----------------
        statics = []
        layers = {}
        for name, c, accent, label in (("L", LC, RAW, TXT["raw"]), ("R", RC, KF, TXT["kf"])):
            bg, deco, br = make_panel(c, accent)
            head = make_header(c, label, accent)
            tree = tree_img.mob(c) if tree_img else make_vector_tree(c)
            layers[name] = dict(bg=bg, deco=deco, br=br, head=head, tree=tree)
            statics += [bg, deco, br, head, tree]

        fit_headers(layers["L"]["head"], layers["R"]["head"])

        # ---------------- drones (behind the tree) ----------------
        def drone_state(t):
            p = sim.truth(t)
            v = sim.truth_vel(t)
            bob = 0.025 * np.sin(t * 5.1)
            tilt = float(np.clip(-0.16 * v[0], -0.32, 0.32))
            op = smooth01((t - 0.6) / 0.3) * (1 - smooth01((t - T_OUT) / 0.45))
            return np.array([p[0], p[1] + bob, 0.0]), tilt, op

        def make_drone_updater(c):
            if drone_rgba is None:
                def f():
                    t = T()
                    pos, tilt, op = drone_state(t)
                    return vector_drone(t, pos + c, tilt, op)
                return redraw(f, 3)
            base = ImageMobject(drone_rgba)
            base.width = sim.DRONE_W * 1.08

            def f():
                t = T()
                pos, tilt, op = drone_state(t)
                m = base.copy().rotate(tilt).move_to(pos + c)
                m.set_opacity(op)
                return m
            return redraw(f, 3)

        droneL, droneR = make_drone_updater(LC), make_drone_updater(RC)

        # ---------------- LEFT overlay: raw detections ----------------
        tag_cache = {}

        def det_tag(k):
            if k not in tag_cache:
                txt = mono(f"drone {det_conf[k]:.2f}", 0.13, INK)
                box = Rectangle(width=txt.width + 0.12, height=0.22, fill_color=RAW, fill_opacity=1, stroke_width=0)
                tag_cache[k] = VGroup(box, txt.move_to(box))
            return tag_cache[k]

        def left_overlay():
            t = T()
            e = envelope(t)
            g = VGroup()
            if e <= 0:
                return g
            fade = 0.9
            sel = np.where((det_t <= t) & (det_t > t - fade))[0]
            pts = [LC + det_p[k] for k in sel]
            for a, b, k in zip(pts, pts[1:], sel[1:]):
                age = (t - det_t[k]) / fade
                g.add(Line(a, b, stroke_color=RAW, stroke_width=3.5, stroke_opacity=0.7 * (1 - age) * e))
            for k, p in zip(sel, pts):
                age = (t - det_t[k]) / fade
                g.add(Dot(p, radius=0.055, fill_color=RAW, fill_opacity=(1 - age) * e,
                          stroke_color=INK, stroke_width=2, stroke_opacity=(1 - age) * e))
            if len(sel) and t - det_t[sel[-1]] < 0.075:
                k = sel[-1]
                p = LC + det_p[k]
                w = sim.DRONE_W * 1.15 * (1 + det_box[k, 0])
                h = 0.62 * (1 + det_box[k, 1])
                g.add(bracket_box(p, w, h, RAW, 5).set_stroke(opacity=e))
                tag = det_tag(k).copy()
                tag.next_to(p + np.array([-w / 2, h / 2, 0]), UP, buff=0.04, aligned_edge=LEFT)
                g.add(tag.set_opacity(e))
                g.add(Dot(p, radius=0.09, fill_color=WHITE, fill_opacity=e, stroke_color=RAW, stroke_width=4))
            return g

        # ---------------- RIGHT overlay: Kalman track ----------------
        def right_overlay():
            t = T()
            e = envelope(t)
            g = VGroup()
            if e <= 0:
                return g
            # filter input: the very same detections, faint
            sel = np.where((det_t <= t) & (det_t > t - 0.35))[0]
            for k in sel:
                age = (t - det_t[k]) / 0.35
                g.add(Dot(RC + det_p[k], radius=0.035, fill_color=WHITE, fill_opacity=0.35 * (1 - age) * e, stroke_width=0))
            i = fidx(t)
            if i < i_lock or np.isnan(est[i, 0]):
                return g
            P3 = np.c_[est[:, 0], est[:, 1], np.zeros(n_frames)] + RC
            # track history, split into runs of track / predict
            runs = []
            s0 = i_lock
            for j in range(i_lock + 1, i + 1):
                if mode[j] != mode[s0]:
                    runs.append((s0, j))
                    s0 = j
            runs.append((s0, i + 1))
            for a, b in runs:
                pts = P3[max(a - 1, i_lock):b]
                if len(pts) < 2:
                    continue
                if mode[a] == 2:
                    for d in dashed(pts):
                        g.add(VMobject(stroke_color=PRED, stroke_width=7, stroke_opacity=e).set_points_as_corners(d))
                else:
                    g.add(VMobject(stroke_color=KF, stroke_width=16, stroke_opacity=0.16 * e).set_points_as_corners(pts))
                    g.add(VMobject(stroke_color=KF, stroke_width=6.5, stroke_opacity=e).set_points_as_corners(pts))
            pred = mode[i] == 2
            col = PRED if pred else KF
            p = P3[i]
            # lead: where the filter thinks it is going (next 0.35 s)
            j0 = max(i - 6, i_lock)
            if i - j0 >= 3:
                v = (P3[i] - P3[j0]) / ((i - j0) / FPS)
                for f in np.linspace(0.08, 0.4, 5):
                    g.add(Dot(p + v * f, radius=0.032, fill_color=col, fill_opacity=0.75 * e * (1 - f), stroke_width=0))
            # uncertainty ellipse from the covariance
            w_, V = np.linalg.eigh(cov[i])
            radii = np.minimum(0.10 + 0.75 * np.sqrt(np.maximum(w_, 0)), 0.95)
            ell = Ellipse(width=2 * radii[1], height=2 * radii[0])
            ell.rotate(np.arctan2(V[1, 1], V[0, 1])).move_to(p)
            ell.set_fill(col, 0.12 * e).set_stroke(col, 3, opacity=0.85 * e)
            if pred:
                g.add(ell.copy().set_stroke(width=0))
                g.add(DashedVMobject(ell, num_dashes=24).set_fill(opacity=0))
            else:
                g.add(ell)
            # reticle
            rot = t * 1.1
            r = 0.42 + (0.05 * np.sin(t * 14) if pred else 0)
            ret = VGroup(Circle(radius=r, stroke_color=col, stroke_width=4.5, stroke_opacity=e))
            for a in range(4):
                ang = rot + a * PI / 2
                d = np.array([np.cos(ang), np.sin(ang), 0])
                ret.add(Line(d * (r - 0.12), d * (r + 0.14), stroke_color=col, stroke_width=4.5, stroke_opacity=e))
            ret.add(Dot(ORIGIN, radius=0.05, fill_color=col, fill_opacity=e))
            g.add(ret.shift(p))
            return g

        overL, overR = redraw(left_overlay, 6), redraw(right_overlay, 6)

        # ---------------- status strips ----------------
        def status_group(c, items):
            """items: list of (key, text, color). Returns dict key->mobject, all stacked at the same spot."""
            out = {}
            for key, s, col in items:
                dot = Dot(radius=0.065, color=col)
                txt = mono(s, 0.2, col)
                grp = VGroup(dot, txt).arrange(RIGHT, buff=0.12)
                grp.move_to(L(c, 0, G - 0.32)).align_to(L(c, -PW / 2 + 0.28, 0), LEFT)
                out[key] = grp
            return out

        stL = status_group(LC, [("trk", TXT["tracking"], RAW), ("lost", TXT["lost"], RAW)])
        stR = status_group(RC, [("acq", TXT["acquiring"], SLATE), ("lock", TXT["locked"], KF),
                                ("pred", TXT["predicting"], PRED)])

        def left_state(t):
            past = det_t[det_t <= t]
            if t < sim.T_FIRST_DET or len(past) == 0:
                return None
            return "lost" if t - past[-1] > 0.22 else "trk"

        def right_state(t):
            i = fidx(t)
            if t < sim.T_FIRST_DET:
                return None
            if t < T_LOCK:
                return "acq"
            return "pred" if mode[i] == 2 else "lock"

        def status_updater(states, fn, blinky):
            def upd(m, dt):
                t = T()
                s = fn(t)
                e = envelope(t)
                for key, mob in states.items():
                    o = e if key == s else 0.0
                    if key in blinky and key == s:
                        o *= blink(t)
                    mob.set_opacity(o)
            return upd

        statL = VGroup(*stL.values())
        statR = VGroup(*stR.values())
        statL.add_updater(status_updater(stL, left_state, {"lost"}))
        statR.add_updater(status_updater(stR, right_state, {"pred", "acq"}))

        # ---------------- coordinate readouts ----------------
        ro_cache = {}

        def readout(s, col):
            key = (s, col)
            if key not in ro_cache:
                ro_cache[key] = mono(s, 0.155, col, weight=MEDIUM)
            return ro_cache[key].copy()

        def fmt(x, y):
            return f"X{x:+.2f}  Y{y:+.2f}"

        def ro_left():
            t = T()
            e = envelope(t)
            past = np.where(det_t <= t)[0]
            if e <= 0 or t < sim.T_FIRST_DET or not len(past):
                return VGroup()
            k = past[-1]
            m = readout(fmt(det_p[k, 0], det_p[k, 1]), SLATE)
            return m.move_to(L(LC, 0, G - 0.64)).align_to(L(LC, -PW / 2 + 0.28, 0), LEFT).set_opacity(e)

        def ro_right():
            t = T()
            e = envelope(t)
            i = fidx(t)
            if e <= 0 or t < T_LOCK:
                return VGroup()
            i -= i % 3
            m = readout(fmt(est[i, 0], est[i, 1]), SLATE)
            return m.move_to(L(RC, 0, G - 0.64)).align_to(L(RC, -PW / 2 + 0.28, 0), LEFT).set_opacity(e)

        roL, roR = redraw(ro_left, 8), redraw(ro_right, 8)

        # ---------------- z order ----------------
        for nm in ("L", "R"):
            ly = layers[nm]
            ly["bg"].set_z_index(0)
            ly["deco"].set_z_index(1)
            ly["tree"].set_z_index(4)
            ly["br"].set_z_index(9)
            ly["head"].set_z_index(9)
        statL.set_z_index(8)
        statR.set_z_index(8)

        # ================= timeline =================
        bgs = [layers[n]["bg"] for n in "LR"]
        decos = [layers[n]["deco"] for n in "LR"]
        brs = [layers[n]["br"] for n in "LR"]
        heads = [layers[n]["head"] for n in "LR"]
        trees = [layers[n]["tree"] for n in "LR"]

        self.add(droneL, droneR, overL, overR, statL, statR, roL, roR)
        tree_in = [FadeIn(tr, shift=UP * 0.3) for tr in trees] if tree_img else \
            [GrowFromEdge(tr, DOWN) for tr in trees]
        self.play(
            LaggedStart(*[FadeIn(b, scale=0.94) for b in bgs], lag_ratio=0.15),
            LaggedStart(*[FadeIn(h, shift=DOWN * 0.25) for h in heads], lag_ratio=0.15),
            run_time=0.45,
        )
        self.play(
            *[Create(d, lag_ratio=0.02) for d in decos],
            *[Create(b) for b in brs],
            *tree_in,
            run_time=0.5,
        )
        end = STOP_AT if STOP_AT > 0 else T_OUT
        self.wait(max(end - T(), 0))
        if STOP_AT > 0:
            return
        self.play(*[FadeOut(m) for m in bgs + decos + brs + heads + trees], run_time=0.45)
        self.wait(max(sim.T_END - T(), 0.05))
