from common import *

rng = np.random.default_rng(7)

# ---------------- timeline (seconds) ----------------
T_HEAT0 = 0.8     # chip starts warming
T_HEAT1 = 3.9     # fully red-hot
T_EX = 4.1        # boom
T_END = 8.2

BB_CENTER = DOWN * 3.2   # breadboard sits low, smoke has room to rise
CHIP_OFF = RIGHT * 0.75  # shield centre relative to ESP centre


def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def heat(t):
    return smooth01((t - T_HEAT0) / (T_HEAT1 - T_HEAT0)) if t < T_EX else 1.0


def heat_color(h):
    stops = [(0.0, "#C9CDD3"), (0.30, "#7E2418"), (0.62, "#D9301C"), (0.85, "#FF6A1F"), (1.0, "#FFC24A")]
    for (h0, c0), (h1, c1) in zip(stops, stops[1:]):
        if h <= h1:
            return interpolate_color(ManimColor(c0), ManimColor(c1), (h - h0) / (h1 - h0))
    return ManimColor(stops[-1][1])


# ---------------- static artwork ----------------
def make_breadboard():
    g = VGroup()
    body = RoundedRectangle(width=8.4, height=4.7, corner_radius=0.18,
                            fill_color="#EFEDE6", fill_opacity=1, stroke_color="#C9C5B8", stroke_width=4)
    side = RoundedRectangle(width=8.4, height=4.7, corner_radius=0.18,
                            fill_color="#BDB8AA", fill_opacity=1, stroke_width=0).shift(DOWN * 0.16)
    channel = Rectangle(width=8.0, height=0.22, fill_color="#D6D2C6", fill_opacity=1, stroke_width=0)
    g.add(side, body, channel)
    xs = np.arange(-14.5, 15.5) * 0.255
    holes = VGroup()
    for i in range(5):
        y = 0.32 + i * 0.255
        for x in xs:
            for s in (1, -1):
                holes.add(Square(0.085, fill_color="#3B3B3B", fill_opacity=1, stroke_width=0).move_to([x, s * y, 0]))
    for s in (1, -1):
        for j, y in enumerate((1.78, 2.03)):
            for k, x in enumerate(xs):
                if k % 6 == 5:
                    continue
                holes.add(Square(0.085, fill_color="#3B3B3B", fill_opacity=1, stroke_width=0).move_to([x, s * y, 0]))
        g.add(Line([-3.9, s * 1.6, 0], [3.9, s * 1.6, 0], stroke_width=4, color="#D7263D" if s > 0 else "#2F6BD9"))
        g.add(Line([-3.9, s * 2.21, 0], [3.9, s * 2.21, 0], stroke_width=4, color="#2F6BD9" if s > 0 else "#D7263D"))
    g.add(holes)
    return g


def jumper(p0, p1, color, bend):
    p0, p1 = np.array(p0), np.array(p1)
    mid = (p0 + p1) / 2 + UP * bend
    wire = VMobject(stroke_color=color, stroke_width=14)
    wire.set_points_smoothly([p0, (p0 + mid) / 2 + UP * bend * 0.3, mid, (p1 + mid) / 2 + UP * bend * 0.3, p1])
    tips = VGroup(*[Square(0.12, fill_color="#9EA3A8", fill_opacity=1, stroke_width=0).move_to(p) for p in (p0, p1)])
    shadow = wire.copy().set_stroke("#00000055", 16).shift(DOWN * 0.05 + RIGHT * 0.03)
    return VGroup(wire, tips)


def make_esp32():
    """Returns (group, shield) — shield is the part that heats up."""
    g = VGroup()
    pcb = RoundedRectangle(width=5.6, height=2.55, corner_radius=0.12,
                           fill_color="#1C2030", fill_opacity=1, stroke_color="#0B0D14", stroke_width=4)
    g.add(pcb)
    # header pins
    for s in (1, -1):
        for k in range(19):
            x = -2.3 + k * 0.255
            g.add(Square(0.16, fill_color="#0B0D14", fill_opacity=1, stroke_width=0).move_to([x, s * 1.05, 0]))
            g.add(Square(0.08, fill_color="#E3B341", fill_opacity=1, stroke_width=0).move_to([x, s * 1.05, 0]))
    # usb
    g.add(RoundedRectangle(width=0.55, height=0.8, corner_radius=0.05, fill_color="#B9BEC5", fill_opacity=1,
                           stroke_color="#7D838B", stroke_width=3).move_to([-2.75, 0, 0]))
    # buttons
    for y in (0.55, -0.55):
        g.add(Square(0.36, fill_color="#C9CDD3", fill_opacity=1, stroke_width=0).move_to([-2.15, y, 0]))
        g.add(Circle(0.11, fill_color="#15171C", fill_opacity=1, stroke_width=0).move_to([-2.15, y, 0]))
    # regulator + uart chip + leds
    g.add(Rectangle(width=0.55, height=0.38, fill_color="#121318", fill_opacity=1, stroke_width=0).move_to([-1.45, 0.35, 0]))
    for dx in (-0.18, 0, 0.18):
        g.add(Rectangle(width=0.07, height=0.12, fill_color="#B9BEC5", fill_opacity=1, stroke_width=0).move_to([-1.45 + dx, 0.1, 0]))
    g.add(Square(0.5, fill_color="#121318", fill_opacity=1, stroke_width=0).move_to([-1.0, -0.35, 0]).rotate(PI / 4))
    g.add(Rectangle(width=0.14, height=0.09, fill_color="#FF3030", fill_opacity=1, stroke_width=0).move_to([-1.7, -0.25, 0]))
    # WROOM module
    module = RoundedRectangle(width=3.3, height=1.95, corner_radius=0.05, fill_color="#20273A", fill_opacity=1,
                              stroke_width=0).move_to([0.95, 0, 0])
    g.add(module)
    ant = VMobject(stroke_color="#C9A23A", stroke_width=5)
    pts = []
    for k in range(7):
        y = 0.75 - k * 0.25
        pts += [[2.25, y, 0], [2.5, y, 0]] if k % 2 == 0 else [[2.5, y, 0], [2.25, y, 0]]
    ant.set_points_as_corners(pts)
    g.add(ant)
    shield = RoundedRectangle(width=2.3, height=1.7, corner_radius=0.06, fill_color="#C9CDD3", fill_opacity=1,
                              stroke_color="#9AA0A8", stroke_width=4).move_to(CHIP_OFF + LEFT * 0.0 + RIGHT * 0.0)
    shield.move_to([0.75, 0, 0])
    label = Text("ESP32-WROOM-32", font="JetBrains Mono", weight=BOLD, color="#4A4F57").scale(0.22).move_to([0.75, 0.35, 0])
    sub = Text("Wi-Fi + BT", font="JetBrains Mono", color="#5A6068").scale(0.17).move_to([0.75, 0.0, 0])
    logo = Circle(0.16, stroke_color="#5A6068", stroke_width=3).move_to([0.75, -0.42, 0])
    g.add(shield, label, sub, logo)
    return g, shield, VGroup(label, sub, logo)


def make_remains():
    """Charred stub left after the blast."""
    g = VGroup()
    scorch = VMobject(fill_color="#2A211C", fill_opacity=1, stroke_width=0)
    ang = np.linspace(0, TAU, 28, endpoint=False)
    r = 2.0 + rng.uniform(-0.35, 0.35, len(ang))
    scorch.set_points_smoothly([[1.55 * r[i] * np.cos(a), 0.85 * r[i] * np.sin(a), 0] for i, a in enumerate(ang)] +
                               [[1.55 * r[0], 0, 0]])
    g.add(scorch)
    stub = VMobject(fill_color="#141414", fill_opacity=1, stroke_color="#050505", stroke_width=3)
    stub.set_points_as_corners([[-2.8, 1.1, 0], [-1.2, 1.25, 0], [-0.6, 0.6, 0], [-0.1, 0.9, 0], [0.2, 0.1, 0],
                                [-0.3, -0.5, 0], [0.1, -1.2, 0], [-2.8, -1.25, 0], [-2.8, 1.1, 0]])
    g.add(stub)
    # bent pins sticking out
    for k in range(7):
        x = -2.4 + k * 0.3
        for s in (1, -1):
            p = Line([x, s * 1.05, 0], [x + rng.uniform(-0.2, 0.25), s * (1.05 + rng.uniform(0.1, 0.35)), 0],
                     stroke_color="#8C6E2A", stroke_width=6)
            g.add(p)
    # glowing embers
    for _ in range(9):
        g.add(Dot([rng.uniform(-2.2, 0.0), rng.uniform(-0.8, 0.8), 0], radius=rng.uniform(0.04, 0.08), color="#FF6A1F"))
    return g


# ---------------- particles ----------------
DEBRIS = [dict(c=rng.choice(["#1C2030", "#C9CDD3", "#E3B341", "#121318", "#7E2418"]),
               w=rng.uniform(0.12, 0.42), h=rng.uniform(0.08, 0.3),
               v=np.array([rng.uniform(-9, 9), rng.uniform(4, 15), 0]),
               w0=rng.uniform(-14, 14)) for _ in range(26)]
SPARKS = [dict(a=rng.uniform(0, TAU), s=rng.uniform(6, 16), L=rng.uniform(0.3, 0.9),
               c=rng.choice(["#FFE45C", "#FFB13B", "#FFFFFF"])) for _ in range(46)]
SMOKE_SHADES = [("#4A4A4E", "#6A6A70"), ("#5E5E63", "#808087"), ("#77777E", "#9C9CA3"), ("#8E8E95", "#B4B4BB")]
SMOKE = []
for i in range(46):
    a = rng.uniform(0, TAU)
    SMOKE.append(dict(
        t0=T_EX + rng.uniform(0.0, 0.35) + (0.0 if i < 30 else 0.3),
        p0=np.array([0.8 * np.cos(a), 0.5 * np.sin(a), 0]),
        v=np.array([rng.uniform(-1.4, 1.4) + 1.6 * np.cos(a), rng.uniform(1.2, 3.8) + 0.8 * max(np.sin(a), 0), 0]),
        R=rng.uniform(0.7, 1.55), life=rng.uniform(1.4, 2.7), shade=SMOKE_SHADES[rng.integers(0, 4)],
    ))
# low, wide puffs that swallow the board
for i in range(16):
    SMOKE.append(dict(
        t0=T_EX + rng.uniform(0.0, 0.25),
        p0=np.array([rng.uniform(-3.4, 1.6), rng.uniform(-0.9, 0.9), 0]),
        v=np.array([rng.uniform(-0.8, 0.8), rng.uniform(0.3, 1.2), 0]),
        R=rng.uniform(1.0, 1.6), life=rng.uniform(0.9, 1.6), shade=SMOKE_SHADES[rng.integers(0, 4)],
    ))
for s_ in SMOKE[:46]:
    s_["v"] = s_["v"] * 1.35
# lingering wisps rising from the remains
WISPS = [dict(t0=T_EX + 2.2 + k * 0.28, x=rng.uniform(-1.8, -0.4), R=rng.uniform(0.18, 0.35),
              shade=SMOKE_SHADES[rng.integers(1, 4)]) for k in range(14)]


def starburst(n, r_in, r_out, color, jitter=0.25):
    pts = []
    for k in range(2 * n):
        a = k * PI / n + rng.uniform(-0.08, 0.08)
        r = (r_out if k % 2 == 0 else r_in) * (1 + rng.uniform(-jitter, jitter))
        pts.append([r * np.cos(a), r * np.sin(a), 0])
    pts.append(pts[0])
    return VMobject(fill_color=color, fill_opacity=1, stroke_width=0).set_points_as_corners(pts)


BURSTS = [starburst(11, 1.6, 3.6, "#E8361E"), starburst(10, 1.2, 2.7, "#FF8A1F"),
          starburst(9, 0.8, 1.8, "#FFE14D"), starburst(7, 0.3, 0.9, "#FFFFFF", 0.15)]


class ESP32Explode(Scene):
    def construct(self):
        T = ValueTracker(0)
        jit = np.random.default_rng(3)

        bb = make_breadboard()
        wires = VGroup(
            jumper([-3.06, 1.3, 0], [-3.06, 2.03, 0], "#E0302B", 0.35),
            jumper([-2.55, -1.3, 0], [-2.55, -2.03, 0], "#2D6FE0", -0.35),
            jumper([2.55, 1.3, 0], [3.3, 2.03, 0], "#F2C230", 0.6),
            jumper([1.53, -1.3, 0], [3.06, -1.78, 0], "#E0302B", -0.5),
        )
        board = VGroup(bb, wires).move_to(BB_CENTER)
        esp, shield, shield_text = make_esp32()
        esp.move_to(BB_CENTER + DOWN * 0.0)
        esp_home = esp.get_center().copy()
        board_home = board.get_center().copy()
        remains = make_remains().move_to(BB_CENTER + LEFT * 0.4)

        self.state = dict(angle=0.0)

        def shake_amp(t):
            h = heat(t)
            return 0.0 if h < 0.12 else 0.16 * ((h - 0.12) / 0.88) ** 1.6

        def esp_update(m):
            t = T.get_value()
            if t >= T_EX:
                m.set_opacity(0)
                return
            a = shake_amp(t)
            m.rotate(-self.state["angle"], about_point=m.get_center())
            off = np.array([jit.uniform(-1, 1), jit.uniform(-1, 1), 0]) * a
            ang = jit.uniform(-1, 1) * a * 0.22
            m.move_to(esp_home + off)
            m.rotate(ang)
            self.state["angle"] = ang
            h = heat(t)
            shield.set_fill(heat_color(h))
            shield.set_stroke(interpolate_color(ManimColor("#9AA0A8"), ManimColor("#5A0E08"), min(1, h * 1.5)))
            shield_text.set_opacity(max(0, 1 - h * 1.6))

        def board_update(m):
            t = T.get_value()
            a = shake_amp(t) * 0.25
            if T_EX <= t < T_EX + 0.35:  # recoil from the blast
                a = 0.35 * (1 - (t - T_EX) / 0.35)
            m.move_to(board_home + np.array([jit.uniform(-1, 1), jit.uniform(-1, 1), 0]) * a)

        esp.add_updater(esp_update)
        board.add_updater(board_update)

        def glow():
            t = T.get_value()
            h = heat(t)
            g = VGroup()
            if t >= T_EX or h < 0.25:
                return g
            k = (h - 0.25) / 0.75
            c = shield.get_center()
            for i, (col, op) in enumerate([("#FF3B1F", 0.22), ("#FF5A1F", 0.28), ("#FF8A2A", 0.34), ("#FFB347", 0.40)]):
                s = 1 + (0.9 - 0.2 * i) * k * (1 + 0.05 * np.sin(t * 40 + i))
                g.add(RoundedRectangle(width=2.3 * s, height=1.7 * s, corner_radius=0.3 * s,
                                       fill_color=col, fill_opacity=op * k, stroke_width=0).move_to(c))
            return g

        def shimmer():
            t = T.get_value()
            h = heat(t)
            g = VGroup()
            if t >= T_EX or h < 0.4:
                return g
            k = (h - 0.4) / 0.6
            c = shield.get_center() + UP * 1.3
            for j, dx in enumerate((-0.7, 0.0, 0.7)):
                pts = [c + RIGHT * (dx + 0.12 * np.sin(6 * y - t * 14 + j)) + UP * y for y in np.linspace(0, 1.4 * k + 0.2, 14)]
                g.add(VMobject(stroke_color="#FF7A1F", stroke_width=8, stroke_opacity=1).set_points_smoothly(pts))
            return g

        def pre_sparks():
            t = T.get_value()
            h = heat(t)
            g = VGroup()
            if t >= T_EX or h < 0.7:
                return g
            r = np.random.default_rng(int(t * 60))
            c = shield.get_center()
            for _ in range(int(1 + 4 * (h - 0.7) / 0.3)):
                a = r.uniform(0, TAU)
                p = c + np.array([1.1 * np.cos(a), 0.8 * np.sin(a), 0])
                d = np.array([np.cos(a), np.sin(a), 0]) * r.uniform(0.2, 0.45)
                g.add(Line(p, p + d, stroke_color=r.choice(["#FFE45C", "#FFFFFF"]), stroke_width=6))
            return g

        chip_c = esp_home + CHIP_OFF

        def blast():
            t = T.get_value() - (T_EX - 0.1)
            g = VGroup()
            if t < 0 or t > 0.65:
                return g
            grow = smooth01(t / 0.13)
            shrink = 1 - smooth01((t - 0.25) / 0.4)
            for i, b in enumerate(BURSTS):
                s = max(0.01, grow * shrink * (1 + 0.1 * i))
                g.add(b.copy().scale(s).rotate(0.4 * t * (1 if i % 2 else -1)).move_to(chip_c))
            return g

        def sparks():
            t = T.get_value() - T_EX
            g = VGroup()
            if t < 0 or t > 0.9:
                return g
            for s in SPARKS:
                d = np.array([np.cos(s["a"]), np.sin(s["a"]), 0])
                r = s["s"] * t * (1 - 0.45 * t)
                L = s["L"] * (1 - t / 0.9)
                p = chip_c + d * (0.4 + r) + DOWN * 2.5 * t * t
                g.add(Line(p - d * L, p, stroke_color=s["c"], stroke_width=7))
            return g

        def debris():
            t = T.get_value() - T_EX
            g = VGroup()
            if t < 0 or t > 2.5:
                return g
            for d in DEBRIS:
                p = chip_c + d["v"] * t + DOWN * 14 * t * t
                g.add(Rectangle(width=d["w"], height=d["h"], fill_color=d["c"], fill_opacity=1, stroke_width=0)
                      .rotate(d["w0"] * t).move_to(p))
            return g

        def smoke():
            t = T.get_value()
            g = VGroup()
            for s in SMOKE:
                age = t - s["t0"]
                if age < 0 or age > s["life"] + 0.7:
                    continue
                drag = (1 - np.exp(-1.6 * age)) / 1.6
                p = chip_c + s["p0"] + s["v"] * drag + UP * 0.5 * age
                r = s["R"] * (1 - (1 - smooth01(age / 0.45)) ** 2)
                if age > s["life"]:
                    r *= 1 - smooth01((age - s["life"]) / 0.7)
                if r < 0.02:
                    continue
                dark, light = s["shade"]
                g.add(Circle(r, fill_color=dark, fill_opacity=1, stroke_width=0).move_to(p))
                g.add(Circle(r * 0.72, fill_color=light, fill_opacity=1, stroke_width=0).move_to(p + UL * r * 0.18))
            for w in WISPS:
                age = t - w["t0"]
                if age < 0 or age > 1.8:
                    continue
                p = esp_home + RIGHT * w["x"] + UP * (0.3 + 1.6 * age) + RIGHT * 0.25 * np.sin(age * 4)
                r = w["R"] * np.sin(np.pi * age / 1.8) * (1 + 0.6 * age)
                dark, light = w["shade"]
                g.add(Circle(r, fill_color=dark, fill_opacity=1, stroke_width=0).move_to(p))
                g.add(Circle(r * 0.7, fill_color=light, fill_opacity=1, stroke_width=0).move_to(p + UL * r * 0.18))
            return g

        def remains_fn():
            t = T.get_value()
            if t < T_EX:
                return VGroup()
            r = remains.copy()
            # embers flicker
            fl = np.random.default_rng(int(t * 20))
            for d in r[-9:]:
                d.set_fill(opacity=fl.uniform(0.4, 1))
            return r.move_to(board.get_center() + LEFT * 0.4)

        self.add(board)
        self.add(always_redraw(glow))
        self.add(esp)
        self.add(always_redraw(remains_fn))
        self.add(always_redraw(shimmer), always_redraw(pre_sparks))
        self.add(always_redraw(debris), always_redraw(sparks), always_redraw(blast), always_redraw(smoke))
        self.play(T.animate.set_value(T_END), run_time=T_END, rate_func=linear)
