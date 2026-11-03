from manim import *

# 9:16 vertical, 1080x1920 @ 60fps, pure chroma green background
config.pixel_width = 1080
config.pixel_height = 1920
config.frame_height = 16.0
config.frame_width = 9.0
config.frame_rate = 60
config.background_color = "#00FF00"

INK = "#0E1116"  # dark outline that keeps strokes readable over any footage

# (frequency in Hz, colour) — colours chosen to stay far from the key green
WAVES = [
    (1, "#FF8A1F"),  # orange
    (2, "#2F7BFF"),  # blue
    (3, "#FF2FB0"),  # magenta
]
ROW_Y = [4.3, 0.0, -4.3]
X_MAX = 2.0          # seconds of signal shown on each axis
SPEED = 0.5          # how fast the waves travel (axis units / s)


def outlined(m, w=12):
    m.set_stroke(INK, w, background=True)
    return m


class SineWaves(Scene):
    def construct(self):
        t = ValueTracker(0.0)  # scene clock: drives the travelling motion
        t.add_updater(lambda m, dt: m.increment_value(dt))
        self.add(t)
        rows = []

        for (f, col), y in zip(WAVES, ROW_Y):
            axes = Axes(
                x_range=[0, X_MAX, 0.5],
                y_range=[-1.25, 1.25, 1],
                x_length=7.6,
                y_length=2.8,
                tips=False,
                axis_config={"stroke_color": WHITE, "stroke_width": 4, "include_ticks": False},
            ).move_to(UP * y)
            # visible axis lines (white over a dark underlay); `axes` itself is
            # only used for coordinates and is never added to the scene
            x0, x1 = axes.c2p(0, 0), axes.c2p(X_MAX, 0)
            y0, y1 = axes.c2p(0, -1.25), axes.c2p(0, 1.25)
            axes_grp = VGroup(
                *[Line(a, b, color=INK, stroke_width=12).set_z_index(0) for a, b in ((x0, x1), (y0, y1))],
                *[Line(a, b, color=WHITE, stroke_width=4).set_z_index(1) for a, b in ((x0, x1), (y0, y1))],
            )

            reveal = ValueTracker(0.001)

            def make_curve(axes=axes, f=f, col=col, reveal=reveal):
                c = axes.plot(
                    lambda x: np.sin(TAU * f * (x - SPEED * t.get_value())),
                    x_range=[0, max(reveal.get_value(), 0.001), 0.004],
                    color=col,
                    stroke_width=10,
                )
                return outlined(c, 20).set_z_index(2)

            curve = always_redraw(make_curve)

            def make_dot(axes=axes, f=f, col=col, reveal=reveal):
                x = reveal.get_value()
                p = axes.c2p(x, np.sin(TAU * f * (x - SPEED * t.get_value())))
                return Dot(p, radius=0.13, color=col).set_stroke(INK, 5).set_z_index(3)

            dot = always_redraw(make_dot)

            label = MathTex(rf"f = {f}\,\mathrm{{Hz}}", color=col).scale(1.25)
            label.next_to(axes, UP, buff=0.15).align_to(axes, LEFT)
            outlined(label, 7)

            rows.append(dict(axes=axes_grp, curve=curve, dot=dot, label=label, reveal=reveal))

        # ---------- 1. axes + labels pop in ----------
        self.wait(0.2)
        self.play(
            LaggedStart(*[AnimationGroup(*[Create(l) for l in r["axes"]]) for r in rows], lag_ratio=0.2),
            LaggedStart(*[FadeIn(r["label"], shift=RIGHT * 0.4) for r in rows], lag_ratio=0.2),
            run_time=0.9,
        )

        # ---------- 2. waves draw on, staggered, with a leading dot ----------
        for r in rows:
            self.add(r["curve"], r["dot"])
        self.play(
            LaggedStart(
                *[r["reveal"].animate.set_value(X_MAX) for r in rows],
                lag_ratio=0.25,
            ),
            run_time=1.8,
            rate_func=rate_functions.ease_in_out_sine,
        )
        self.play(*[FadeOut(r["dot"], scale=2) for r in rows], run_time=0.25)
        for r in rows:
            self.remove(r["dot"])

        # ---------- 3. all three travel at the same speed ----------
        self.wait(4.5)

        # ---------- 4. out ----------
        self.play(
            LaggedStart(
                *[FadeOut(VGroup(r["axes"], r["curve"], r["label"]), shift=LEFT * 0.6) for r in rows],
                lag_ratio=0.15,
            ),
            run_time=0.7,
        )
        self.wait(0.1)
