"""Animated architecture diagram: one tracking NODE -> its parts -> MJPEG stream
to the HOST PC -> the node duplicates and every node streams to the same PC.

Render (from this folder):
    MG_LANG=en manim -qh --fps 60 node_diagram.py NodeDiagram
    MG_LANG=pt manim -qh --fps 60 node_diagram.py NodeDiagram
MG_STOP_AT=<seconds> stops early (for stills with -s).
"""
import os

from common import *

LANG = os.environ.get("MG_LANG", "en")
STOP_AT = float(os.environ.get("MG_STOP_AT", "0"))

TXT = {
    "en": dict(node="NODE", node_n="NODE {}", cam_s="live video", mc_t="ESP32", mc_s="motor controller",
               sen_t="IMU + GPS", sen_s="+ magnetometer", stp_t="STEPPERS", stp_s="pan / tilt",
               pc="HOST PC", vid=("MJPEG", "VIDEO STREAM"), cmd=("PAN/TILT CMD", "UDP")),
    "pt": dict(node="NÓ", node_n="NÓ {}", cam_s="vídeo ao vivo", mc_t="ESP32", mc_s="controle dos motores",
               sen_t="IMU + GPS", sen_s="+ magnetômetro", stp_t="MOTORES DE PASSO", stp_s="pan / tilt",
               pc="PC HOST", vid=("FLUXO DE", "VÍDEO MJPEG"), cmd=("COMANDOS", "PAN/TILT · UDP")),
}[LANG]

NODE_C = KF          # node / video stream (cyan)
CMD_C = PRED         # commands back to the node (amber)
PC_C = "#B48CFF"     # host PC (violet)
CELL_BG = "#111827"
CELL_EDGE = "#26324A"

# ---------------- layout ----------------
CARD_C = np.array([0, 3.55, 0])
CARD_W, CARD_H = 8.3, 5.5
CELL_W, CELL_H = 3.95, 2.15
CELLS = [np.array([-2.03, 4.30, 0]), np.array([2.03, 4.30, 0]),
         np.array([-2.03, 2.05, 0]), np.array([2.03, 2.05, 0])]
CARD_BOTTOM = CARD_C[1] - CARD_H / 2
MON_C = np.array([0, -4.35, 0])
MON_W, MON_H = 4.4, 2.75
SCREEN_W, SCREEN_H = MON_W - 0.3, MON_H - 0.3
MINI_Y = 4.95
MINI_X = [-2.95, 0.0, 2.95]
MINI_W, MINI_H = 2.55, 2.3


def rr(w, h, r, fill, stroke=INK, sw=3, op=1):
    return RoundedRectangle(width=w, height=h, corner_radius=r, fill_color=fill, fill_opacity=op,
                            stroke_color=stroke, stroke_width=sw)


def pill(lines, color, h=0.2, fill=PANEL_BG):
    if isinstance(lines, str):
        lines = (lines,)
    t = VGroup(*[mono(s, h, color) for s in lines]).arrange(DOWN, buff=0.13)
    box = rr(t.width + 0.42, t.height + 0.3, min(0.22, (t.height + 0.3) / 2), fill, color, 3.5)
    outer = box.copy().set_fill(opacity=0).set_stroke(INK, 9)
    return VGroup(outer, box, t.move_to(box))


# ======================================================================
#  icons (all built around the origin)
# ======================================================================
def turret_icon():
    g = VGroup()
    g.add(rr(1.05, 0.26, 0.08, "#2A3448", INK, 3).move_to([0, -0.55, 0]))
    g.add(Rectangle(width=0.18, height=0.28, fill_color="#4A5568", fill_opacity=1, stroke_color=INK,
                    stroke_width=2).move_to([0, -0.3, 0]))
    yoke = VMobject(stroke_color="#8C9AB3", stroke_width=9).set_points_as_corners(
        [[-0.42, 0.25, 0], [-0.42, -0.16, 0], [0.42, -0.16, 0], [0.42, 0.25, 0]])
    g.add(yoke)
    g.add(rr(0.72, 0.5, 0.1, "#DCE2EA", INK, 3).move_to([0, 0.2, 0]))
    g.add(Circle(radius=0.17, fill_color="#20252F", fill_opacity=1, stroke_color=NODE_C, stroke_width=4).move_to([0.06, 0.2, 0]))
    g.add(Dot([0.1, 0.25, 0], radius=0.04, color=WHITE))
    g.add(Dot([-0.26, 0.36, 0], radius=0.035, color=RAW))
    return g


def esp32cam_icon():
    g = VGroup()
    g.add(rr(0.95, 1.35, 0.06, "#1C2030", "#3D4B6B", 3))
    for s in (-1, 1):
        for k in range(8):
            g.add(Square(0.07, fill_color="#D4A73A", fill_opacity=1, stroke_width=0).move_to([s * 0.38, 0.52 - k * 0.15, 0]))
    g.add(Rectangle(width=0.26, height=0.12, fill_color="#C97B2A", fill_opacity=1, stroke_width=0).move_to([0, -0.08, 0]))
    g.add(rr(0.56, 0.56, 0.05, "#2B2F3A", INK, 2).move_to([0, 0.24, 0]))
    g.add(Circle(radius=0.21, fill_color="#111318", fill_opacity=1, stroke_color="#5A6272", stroke_width=3).move_to([0, 0.24, 0]))
    g.add(Circle(radius=0.11, fill_color="#1E3A5F", fill_opacity=1, stroke_width=0).move_to([0, 0.24, 0]))
    g.add(Dot([0.04, 0.29, 0], radius=0.03, color=WHITE))
    g.add(rr(0.16, 0.1, 0.02, "#DCE2EA", INK, 1.5).move_to([0, -0.45, 0]))
    return g


def motor_ctrl_icon():
    g = VGroup()
    g.add(rr(1.6, 1.1, 0.07, "#1D4E9E", "#3C74D0", 3))
    for y in (-0.32, -0.18, 0.3):
        g.add(Line([-0.55, y, 0], [0.55, y, 0], stroke_color="#4F82DA", stroke_width=2))
    g.add(rr(0.62, 0.36, 0.03, "#B9C0CA", INK, 2).move_to([0.1, 0.27, 0]))          # ESP32 module can
    chip = Square(0.36, fill_color="#111318", fill_opacity=1, stroke_color="#3A3F4A", stroke_width=2).move_to([0.1, -0.2, 0])
    g.add(chip)
    for k in range(4):
        for s in (-1, 1):
            g.add(Line([0.1 + s * 0.18, -0.32 + k * 0.08, 0], [0.1 + s * 0.24, -0.32 + k * 0.08, 0],
                       stroke_color="#C9D1DC", stroke_width=2))
    for s in (-1, 1):
        tb = rr(0.24, 0.5, 0.03, "#E8742A", INK, 2).move_to([s * 0.66, -0.05, 0])
        g.add(tb)
        for y in (0.1, -0.12):
            g.add(Circle(radius=0.055, fill_color="#C9D1DC", fill_opacity=1, stroke_color=INK, stroke_width=1.5).move_to([s * 0.66, y - 0.05, 0]))
    for x in (-0.38, -0.25):
        g.add(Circle(radius=0.06, fill_color="#C9D1DC", fill_opacity=1, stroke_color=INK, stroke_width=1.5).move_to([x, 0.32, 0]))
    return g


def sensors_icon():
    g = VGroup()
    # GPS puck on a short mast
    g.add(Rectangle(width=0.07, height=0.55, fill_color="#5B6678", fill_opacity=1, stroke_width=0).move_to([-0.55, -0.12, 0]))
    dome = Sector(radius=0.3, angle=PI, start_angle=0, fill_color="#C9D1DC", fill_opacity=1, stroke_color=INK, stroke_width=2.5)
    g.add(dome.move_to([-0.55, 0.28, 0]))
    g.add(rr(0.66, 0.08, 0.03, "#8C9AB3", INK, 2).move_to([-0.55, 0.2, 0]))
    # IMU breakout with axes
    g.add(rr(0.72, 0.72, 0.06, "#1D4E9E", "#3C74D0", 3).move_to([0.32, 0.1, 0]))
    g.add(Square(0.24, fill_color="#111318", fill_opacity=1, stroke_width=0).move_to([0.32, 0.1, 0]))
    o = np.array([0.32, 0.1, 0])
    for d, c in ((RIGHT * 0.5, RAW), (UP * 0.5, NODE_C), (np.array([-0.32, -0.32, 0]), CMD_C)):
        g.add(Arrow(o, o + d, buff=0, stroke_width=5, max_tip_length_to_length_ratio=0.3, color=c))
    # compass
    cp = np.array([0.0, -0.45, 0])
    g.add(Circle(radius=0.2, fill_color="#F1F3F6", fill_opacity=1, stroke_color=INK, stroke_width=2.5).move_to(cp))
    g.add(Polygon(cp + [0, 0.15, 0], cp + [0.05, 0, 0], cp + [-0.05, 0, 0], fill_color=RAW, fill_opacity=1, stroke_width=0))
    g.add(Polygon(cp + [0, -0.15, 0], cp + [0.05, 0, 0], cp + [-0.05, 0, 0], fill_color="#2A3448", fill_opacity=1, stroke_width=0))
    return g


def stepper_icon():
    g = VGroup()
    c = 0.09
    s = 0.48
    face = Polygon([-s + c, -s, 0], [s - c, -s, 0], [s, -s + c, 0], [s, s - c, 0], [s - c, s, 0], [-s + c, s, 0],
                   [-s, s - c, 0], [-s, -s + c, 0], fill_color="#3A4150", fill_opacity=1, stroke_color=INK, stroke_width=3)
    face.shift(DOWN * 0.12)
    top = Polygon([-s, s - 0.12, 0], [s, s - 0.12, 0], [s + 0.18, s + 0.08, 0], [-s + 0.18, s + 0.08, 0],
                  fill_color="#5A6476", fill_opacity=1, stroke_color=INK, stroke_width=3)
    side = Polygon([s, s - 0.12, 0], [s + 0.18, s + 0.08, 0], [s + 0.18, -s - 0.04, 0], [s, -s - 0.24, 0],
                   fill_color="#2A3040", fill_opacity=1, stroke_color=INK, stroke_width=3)
    g.add(side, face, top)
    for y in (0.12, -0.05, -0.22):
        g.add(Line([-s + 0.05, y, 0], [s - 0.05, y, 0], stroke_color="#4A5366", stroke_width=2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.add(Dot([sx * 0.34, -0.12 + sy * 0.34, 0], radius=0.04, color="#9AA4B3"))
    g.add(Ellipse(width=0.42, height=0.13, fill_color="#9AA4B3", fill_opacity=1, stroke_color=INK, stroke_width=2).move_to([0.09, 0.46, 0]))
    g.add(Rectangle(width=0.09, height=0.36, fill_color="#DCE2EA", fill_opacity=1, stroke_color=INK, stroke_width=2).move_to([0.09, 0.66, 0]))
    return g


def rot_arrow(center, color):
    a = Arc(radius=0.3, start_angle=-PI / 2 + 0.3, angle=1.6 * PI, stroke_color=color, stroke_width=4).move_arc_center_to(center)
    a.add_tip(tip_length=0.12, tip_width=0.12)
    return a


def frame_packet():
    g = VGroup()
    g.add(rr(0.44, 0.32, 0.05, "#0E1830", NODE_C, 2.5))
    g.add(Polygon([-0.16, -0.1, 0], [-0.04, 0.05, 0], [0.04, -0.03, 0], [0.09, 0.02, 0], [0.16, -0.1, 0],
                  fill_color=NODE_C, fill_opacity=0.8, stroke_width=0))
    g.add(Dot([0.1, 0.08, 0], radius=0.03, color=NODE_C))
    return g


def arrow_path(points, color, width=6, tip=0.26):
    path = VMobject(stroke_color=color, stroke_width=width)
    if len(points) == 4:
        path.set_points(np.array([points[0], points[1], points[2], points[3]]))
    else:
        path.set_points_as_corners(points)
    end = path.get_end()
    d = end - path.point_from_proportion(0.985)
    d /= np.linalg.norm(d)
    n = np.array([-d[1], d[0], 0])
    head = Polygon(end + d * 0.02, end - d * tip + n * tip * 0.55, end - d * tip - n * tip * 0.55,
                   fill_color=color, fill_opacity=1, stroke_color=INK, stroke_width=2)
    under = path.copy().set_stroke(INK, width + 6)
    return VGroup(under, path, head), path


def cell_box(c):
    return rr(CELL_W, CELL_H, 0.12, CELL_BG, CELL_EDGE, 2.5).move_to(c)


def cell_content(c, icon, title, sub):
    icon.scale_to_fit_height(1.12).move_to(c + UP * 0.28)
    t = mono(title, 0.19, WHITE).move_to(c + DOWN * 0.6)
    s = mono(sub, 0.14, SLATE, weight=MEDIUM).move_to(c + DOWN * 0.86)
    return icon, VGroup(t, s)


def mini_node(x, label):
    c = np.array([x, MINI_Y, 0])
    box = rr(MINI_W, MINI_H, 0.16, PANEL_BG, NODE_C, 3.5).move_to(c)
    ic = turret_icon().scale_to_fit_height(1.15).move_to(c + UP * 0.22)
    lb = mono(label, 0.2, NODE_C).move_to(c + DOWN * 0.78)
    return VGroup(box, ic, lb)


def tile_feed(rect_c, w, h, t, seed, e):
    """A tiny camera feed with a drone and a YOLO box (drawn on the PC screen)."""
    g = VGroup()
    g.add(Rectangle(width=w, height=h, fill_color="#0E1830", fill_opacity=e, stroke_color="#2C3850",
                    stroke_width=2, stroke_opacity=e).move_to(rect_c))
    ph = seed * 1.7
    p = rect_c + np.array([0.28 * w * np.sin(0.9 * t + ph), 0.18 * h * np.sin(1.3 * t + 2 * ph), 0])
    dr = VGroup(Line(LEFT * 0.21, RIGHT * 0.21, stroke_color="#DCE2EA", stroke_width=4),
                Rectangle(width=0.15, height=0.08, fill_color="#DCE2EA", fill_opacity=1, stroke_width=0),
                *[Line([sx * 0.21 - 0.08, 0.05, 0], [sx * 0.21 + 0.08, 0.05, 0], stroke_color="#8C9AB3", stroke_width=3)
                  for sx in (-1, 1)])
    g.add(dr.move_to(p).set_opacity(e))
    rng = np.random.default_rng(int(t * 30) + seed * 1000)
    j = rng.normal(0, 0.012, 2)
    box = Rectangle(width=0.6, height=0.32, stroke_color=RAW, stroke_width=3, stroke_opacity=e).move_to(p + [j[0], j[1], 0])
    g.add(box)
    rec = Dot(rect_c + np.array([-w / 2 + 0.1, h / 2 - 0.1, 0]), radius=0.035,
              fill_color=RAW, fill_opacity=e * (1.0 if (t * 2) % 1 < 0.6 else 0.2))
    g.add(rec)
    return g


# ======================================================================
class NodeDiagram(ClockScene):
    def construct(self):
        self.start_clock()
        T = self.T
        ph = {}           # phase start times, filled in as the timeline runs

        # ---------------- static pieces ----------------
        small_card = rr(2.7, 2.7, 0.22, PANEL_BG, NODE_C, 4).move_to(CARD_C + DOWN * 0.3)
        small_icon = turret_icon().scale_to_fit_height(1.45).move_to(small_card)
        small_lbl = pill(TXT["node"], NODE_C, 0.26).next_to(small_card, DOWN, buff=0.25)

        card = rr(CARD_W, CARD_H, 0.22, PANEL_BG, NODE_C, 4).move_to(CARD_C)
        head_bar = Line(CARD_C + [-CARD_W / 2 + 0.2, CARD_H / 2 - 0.62, 0], CARD_C + [CARD_W / 2 - 0.2, CARD_H / 2 - 0.62, 0],
                        stroke_color=CELL_EDGE, stroke_width=2)
        head_icon = turret_icon().scale_to_fit_height(0.46)
        head_txt = mono(TXT["node"], 0.27, NODE_C)
        head = VGroup(head_icon, head_txt).arrange(RIGHT, buff=0.18).move_to(CARD_C + [0, CARD_H / 2 - 0.31, 0])

        cells = [cell_box(c) for c in CELLS]
        contents = [
            cell_content(CELLS[0], esp32cam_icon(), "ESP32-CAM", TXT["cam_s"]),
            cell_content(CELLS[1], motor_ctrl_icon(), TXT["mc_t"], TXT["mc_s"]),
            cell_content(CELLS[2], sensors_icon(), TXT["sen_t"], TXT["sen_s"]),
            cell_content(CELLS[3], stepper_icon(), TXT["stp_t"], TXT["stp_s"]),
        ]
        step_ic = contents[3][0]
        spin = rot_arrow(step_ic.get_top() + DOWN * 0.18 + RIGHT * 0.06, CMD_C).scale(0.9)

        # host PC
        bezel = rr(MON_W, MON_H, 0.16, "#1A2030", "#3D4B6B", 4).move_to(MON_C)
        screen = Rectangle(width=SCREEN_W, height=SCREEN_H, fill_color="#070A10", fill_opacity=1, stroke_width=0).move_to(MON_C)
        neck = Polygon(MON_C + [-0.25, -MON_H / 2, 0], MON_C + [0.25, -MON_H / 2, 0], MON_C + [0.38, -MON_H / 2 - 0.4, 0],
                       MON_C + [-0.38, -MON_H / 2 - 0.4, 0], fill_color="#2A3448", fill_opacity=1, stroke_color=INK, stroke_width=3)
        base = rr(1.9, 0.18, 0.08, "#2A3448", INK, 3).move_to(MON_C + [0, -MON_H / 2 - 0.48, 0])
        chips = VGroup(pill("YOLOv8", PC_C, 0.15), pill("KALMAN", PC_C, 0.15)).arrange(RIGHT, buff=0.15)
        chips.move_to(MON_C + [0, -SCREEN_H / 2 + 0.27, 0])
        pc_lbl = pill(TXT["pc"], PC_C, 0.26).next_to(base, DOWN, buff=0.22)
        pc = Group(bezel, screen, neck, base)

        mon_top = MON_C[1] + MON_H / 2
        vid_arrow, vid_path = arrow_path([np.array([-1.1, CARD_BOTTOM, 0]), np.array([-1.1, mon_top + 0.02, 0])], NODE_C)
        cmd_arrow, cmd_path = arrow_path([np.array([1.1, mon_top, 0]), np.array([1.1, CARD_BOTTOM + 0.02, 0])], CMD_C)
        vid_pill = pill(TXT["vid"], NODE_C).move_to([-2.75, (CARD_BOTTOM + mon_top) / 2, 0])
        cmd_pill = pill(TXT["cmd"], CMD_C).move_to([2.75, (CARD_BOTTOM + mon_top) / 2, 0])

        # ---------------- per-frame layers ----------------
        pkt = frame_packet()
        multi_paths = []

        def packets():
            t = T()
            g = VGroup()
            env = 1.0
            if "out" in ph:
                env = 1 - smooth01((t - ph["out"]) / 0.4)
            if "collapse" in ph:                  # packets fade out as the node folds up
                env *= 1 - smooth01((t - ph["collapse"]) / 0.3)
            if "vid" in ph and env > 0.01 and "multi" not in ph:
                g.add(*_stream(vid_path, t - ph["vid"], 4, 1.0, env))
            if "cmd" in ph and env > 0.01 and "multi" not in ph:
                for k in range(3):
                    s = (t - ph["cmd"]) * 0.75 - k / 3
                    if s < 0:
                        continue
                    s %= 1.0
                    a = env * smooth01(s / 0.12) * smooth01((1 - s) / 0.12)
                    g.add(Dot(cmd_path.point_from_proportion(s), radius=0.09, fill_color=CMD_C, fill_opacity=a,
                              stroke_color=INK, stroke_width=3, stroke_opacity=a))
            if "multi" in ph:
                env = 1.0 if "out" not in ph else 1 - smooth01((t - ph["out"]) / 0.4)
                for i, p in enumerate(multi_paths):
                    g.add(*_stream(p, t - ph["multi"] - 0.15 * i, 3, 1.45, env))
            return g

        def _stream(path, age, n, speed, env, offset=0.0):
            """n frame-packets travelling along `path`, spawned one after another."""
            out = []
            v = speed * 0.55                      # path fraction per second
            for k in range(n):
                s = age * v - k / n + offset * 0
                if s < 0:
                    continue
                s %= 1.0
                a = env * smooth01(s / 0.1) * smooth01((1 - s) / 0.1)
                if a <= 0.01:
                    continue
                m = pkt.copy().move_to(path.point_from_proportion(s))
                out.append(m.set_opacity(a))
            return out

        def screen_feeds():
            t = T()
            g = VGroup()
            env = 1.0
            if "out" in ph:
                env = 1 - smooth01((t - ph["out"]) / 0.4)
            top = MON_C[1] + SCREEN_H / 2 - 0.12
            bottom = MON_C[1] - SCREEN_H / 2 + 0.52
            hh = top - bottom
            cy = (top + bottom) / 2
            if "multi" in ph:
                n_on = sum(t - ph["multi"] > 0.5 + 0.15 * i for i in range(3))
                w = (SCREEN_W - 0.4) / 3
                for i in range(n_on):
                    x = -SCREEN_W / 2 + 0.15 + w / 2 + i * (w + 0.05)
                    g.add(tile_feed(np.array([x, cy, 0]), w, hh, t, i + 1, env))
            elif "vid" in ph and t - ph["vid"] > 0.9:
                e = env * smooth01((t - ph["vid"] - 0.9) / 0.2)
                if "collapse" in ph:
                    e *= 1 - smooth01((t - ph["collapse"]) / 0.3)
                g.add(tile_feed(np.array([0, cy, 0]), SCREEN_W - 0.3, hh, t, 1, e))
            return g

        layer_pk = redraw(packets, 7)
        layer_scr = redraw(screen_feeds, 3)
        self.add(layer_pk, layer_scr)

        # z order
        for m in (card, small_card):
            m.set_z_index(1)
        for m in cells:
            m.set_z_index(2)
        for ic, lb in contents:
            ic.set_z_index(3)
            lb.set_z_index(3)
        for m in (head, small_icon, small_lbl, spin):
            m.set_z_index(4)
        bezel.set_z_index(1)
        screen.set_z_index(2)
        neck.set_z_index(0)
        base.set_z_index(1)
        chips.set_z_index(5)
        pc_lbl.set_z_index(5)
        vid_arrow.set_z_index(6)
        cmd_arrow.set_z_index(6)
        vid_pill.set_z_index(8)
        cmd_pill.set_z_index(8)

        def hold(until):
            if STOP_AT and until >= STOP_AT:
                self.wait(max(STOP_AT - T(), 0.001))
                return True
            self.wait(max(until - T(), 0.001))
            return False

        # ============ 1. NODE icon ============
        self.wait(0.15)
        self.play(GrowFromCenter(small_card), FadeIn(small_icon, scale=0.5), run_time=0.45, rate_func=rate_functions.ease_out_back)
        self.play(FadeIn(small_lbl, shift=UP * 0.2), run_time=0.3)
        if hold(1.25):
            return

        # ============ 2. expand into its parts ============
        self.play(
            ReplacementTransform(small_card, card),
            ReplacementTransform(small_icon, head_icon),
            ReplacementTransform(small_lbl, head_txt),
            run_time=0.6, rate_func=rate_functions.ease_in_out_cubic,
        )
        head.set_z_index(4)
        self.play(Create(head_bar), LaggedStart(*[FadeIn(c, scale=0.92) for c in cells], lag_ratio=0.12), run_time=0.45)
        for k, (ic, lb) in enumerate(contents):
            extra = [FadeIn(spin, scale=0.5)] if k == 3 else []
            self.play(FadeIn(ic, scale=0.6), FadeIn(lb, shift=UP * 0.12),
                      cells[k].animate.set_stroke(NODE_C, 4), *extra,
                      run_time=0.42, rate_func=rate_functions.ease_out_back)
            self.play(cells[k].animate.set_stroke(CELL_EDGE, 2.5), run_time=0.22)
        self.add(spin)
        spin.add_updater(lambda m, dt: m.rotate(-2.2 * dt, about_point=step_ic.get_top() + DOWN * 0.18 + RIGHT * 0.06))
        if hold(4.95):
            return

        # ============ 3. MJPEG stream -> HOST PC ============
        self.play(cells[0].animate.set_stroke(NODE_C, 5), Create(vid_arrow), FadeIn(vid_pill, shift=RIGHT * 0.2),
                  run_time=0.6)
        self.play(FadeIn(pc, shift=UP * 0.4), FadeIn(pc_lbl, shift=UP * 0.2), run_time=0.5,
                  rate_func=rate_functions.ease_out_cubic)
        ph["vid"] = T()
        self.play(FadeIn(chips, shift=UP * 0.1), run_time=0.3)
        if hold(7.6):
            return
        self.play(cells[1].animate.set_stroke(CMD_C, 5), Create(cmd_arrow), FadeIn(cmd_pill, shift=LEFT * 0.2),
                  run_time=0.6)
        ph["cmd"] = T()
        if hold(9.9):
            return

        # ============ 4. node collapses and duplicates ============
        ph["collapse"] = T()
        node1 = mini_node(0, TXT["node_n"].format(1))
        node1.set_z_index(4)
        parts = VGroup(*cells, *[VGroup(ic, lb) for ic, lb in contents], spin, head_bar)
        spin.clear_updaters()
        self.play(
            FadeOut(parts, scale=0.6),
            FadeOut(VGroup(vid_arrow, cmd_arrow, vid_pill, cmd_pill)),
            ReplacementTransform(card, node1[0]),
            ReplacementTransform(head_icon, node1[1]),
            ReplacementTransform(head_txt, node1[2]),
            run_time=0.7, rate_func=rate_functions.ease_in_out_cubic,
        )
        # duplicate: NODE 1 slides left, copies 2 and 3 are revealed / slide right
        n2 = mini_node(0, TXT["node_n"].format(2)).set_z_index(3.5)
        n3 = mini_node(0, TXT["node_n"].format(3)).set_z_index(3.4)
        self.add(n2, n3)
        self.play(
            node1.animate.move_to([MINI_X[0], MINI_Y, 0]),
            n3.animate.move_to([MINI_X[2], MINI_Y, 0]),
            run_time=0.65, rate_func=rate_functions.ease_out_back,
        )

        mon_pts = [-1.2, 0.0, 1.2]
        arrows = []
        for x, xe in zip(MINI_X, mon_pts):
            p0 = np.array([x, MINI_Y - MINI_H / 2, 0])
            p3 = np.array([xe, mon_top + 0.02, 0])
            ar, path = arrow_path([p0, p0 + DOWN * 2.6, p3 + UP * 2.6, p3], NODE_C)
            ar.set_z_index(6)
            arrows.append(ar)
            multi_paths.append(path)
        multi_pill = pill(TXT["vid"], NODE_C).move_to([0, (MINI_Y - MINI_H / 2 + mon_top) / 2 - 0.15, 0]).set_z_index(8)
        self.play(LaggedStart(*[Create(a) for a in arrows], lag_ratio=0.15), FadeIn(multi_pill, scale=0.9), run_time=0.75)
        ph["multi"] = T()
        if hold(14.8):
            return

        # ============ out ============
        ph["out"] = T()
        everything = [m for m in self.mobjects if m not in (self.clock, layer_pk, layer_scr)]
        self.play(*[FadeOut(m) for m in everything], run_time=0.4)
        self.wait(0.15)


def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)
