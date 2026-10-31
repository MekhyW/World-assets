from common import *


def outlined(m, w=10):
    m.set_stroke(INK, w, background=True)
    return m


class FourierEquations(Scene):
    def construct(self):
        # ---------- 1. Continuous Fourier transform writes on ----------
        ft = MathTex(
            r"F(\omega)", r"=", r"\int_{-\infty}^{\infty}", r"f(t)", r"\,e^{-i\omega t}", r"\,dt",
            color=WHITE,
        )
        ft.width = 8.0
        ft.move_to(UP * 0.4)
        outlined(ft)

        self.wait(0.3)
        self.play(Write(ft, run_time=1.8, lag_ratio=0.25))
        self.wait(1.4)

        # ---------- 2. A boot punts it off screen (from below) ----------
        ft.set_stroke(WHITE, 1.2)  # slightly heavier glyphs
        boot = emoji("1f97e", 3.0)
        boot.flip(UP)              # toe points right
        contact = ft.get_bottom() + LEFT * 0.6 + DOWN * 0.05
        toe = RIGHT * 1.15 + UP * 0.35  # toe offset from boot centre (unrotated)

        boot_base = boot.copy()

        def boot_at(angle):
            b = boot_base.copy().rotate(angle)
            off = rotate_vector(toe, angle)
            return b, off

        a0, a1 = -25 * DEGREES, 40 * DEGREES
        p_start = contact + DOWN * 7.5 + LEFT * 1.8
        swing_path = ArcBetweenPoints(p_start, contact, angle=-PI / 4)

        def swing(m, a):
            ang = interpolate(a0, a1, a)
            b, off = boot_at(ang)
            m.become(b.shift(swing_path.point_from_proportion(a) - off - b.get_center()))

        swing(boot, 0)
        self.add(boot)
        self.play(UpdateFromAlphaFunc(boot, swing), run_time=0.3, rate_func=rate_functions.ease_in_quad)

        boom = emoji("1f4a5", 2.4).move_to(contact)
        boom.scale(0.15)
        self.add(boom)
        self.play(
            boom.animate.scale(1 / 0.15),
            ft.animate.stretch(1.06, 0).stretch(0.82, 1).shift(UP * 0.12),
            run_time=0.07, rate_func=linear,
        )

        ft0 = ft.copy()
        c0 = ft0.get_center()

        def fly(m, a):
            m.become(ft0.copy().scale(1 - 0.6 * a).rotate(-2.2 * TAU * a)
                     .move_to(c0 + RIGHT * 7.5 * a + UP * 10.5 * a))

        boot1 = boot.copy()
        c1 = boot1.get_center()

        def follow(m, a):
            m.become(boot1.copy().rotate(18 * DEGREES * a).move_to(c1 + UP * 0.9 * a + RIGHT * 0.5 * a))

        self.play(
            UpdateFromAlphaFunc(ft, fly),
            UpdateFromAlphaFunc(boot, follow),
            boom.animate.scale(0.01),
            run_time=0.65, rate_func=rate_functions.rush_from,
        )
        self.remove(ft, boom)
        self.play(boot.animate.shift(DOWN * 9 + LEFT * 1.5).rotate(-30 * DEGREES),
                  run_time=0.38, rate_func=rate_functions.ease_in_quad)
        self.remove(boot)

        # ---------- 3. Discrete Fourier transform slams in ----------
        dft = MathTex(
            r"X_k", r"=", r"\sum_{n=0}^{N-1}", r"x_n", r"\,e^{-i2\pi kn/N}",
            color=WHITE,
        )
        dft.width = 7.6
        dft.move_to(UP * 0.4)
        outlined(dft)
        dft.set_stroke(WHITE, 1.2)

        dft_target = dft.copy()
        dft.scale(2.6).set_opacity(0)
        self.play(Transform(dft, dft_target), run_time=0.35,
                  rate_func=rate_functions.ease_in_cubic)
        # little landing shake
        for dx in (0.18, -0.14, 0.09, -0.05, 0.0):
            self.play(dft.animate.move_to(UP * 0.4 + RIGHT * dx), run_time=0.035, rate_func=linear)
        self.wait(0.7)

        # ---------- 4. Thumbs up ----------
        thumb = emoji("1f44d", 2.2)
        thumb.move_to(DOWN * 2.4)
        self.play(GrowFromCenter(thumb), run_time=0.45, rate_func=rate_functions.ease_out_back)
        self.play(Rotate(thumb, 12 * DEGREES), run_time=0.12)
        self.play(Rotate(thumb, -20 * DEGREES), run_time=0.14)
        self.play(Rotate(thumb, 8 * DEGREES), run_time=0.12)
        self.wait(1.0)

        # ---------- 5. "FAST FOURIER TRANSFORM" big ----------
        self.play(
            dft.animate.scale(0.82).move_to(UP * 5.3),
            thumb.animate.scale(0.7).move_to(UP * 3.0),
            run_time=0.55, rate_func=rate_functions.ease_in_out_cubic,
        )

        fast = Text("FAST", font="Orbitron", weight="HEAVY", color="#FF8A1F")
        fast.width = 8.0
        fourier = Text("FOURIER", font="Orbitron", weight="HEAVY", color=WHITE)
        fourier.width = 7.6
        transform = Text("TRANSFORM", font="Orbitron", weight="HEAVY", color=WHITE)
        transform.width = 8.2
        title = VGroup(fast, fourier, transform).arrange(DOWN, buff=0.45)
        title.move_to(DOWN * 2.6)
        for t in title:
            outlined(t, 14)

        # speed lines behind FAST
        lines = VGroup(*[
            Line(LEFT * L, ORIGIN, stroke_width=10, color="#FFD24A").move_to(
                fast.get_left() + LEFT * (0.4 + L / 2) + UP * y)
            for L, y in [(2.2, 0.55), (3.4, 0.15), (1.8, -0.25), (2.8, -0.6)]
        ])

        fast_end = fast.copy()
        fast.shift(LEFT * 10)
        self.add(fast)
        self.play(fast.animate.move_to(fast_end), run_time=0.22, rate_func=rate_functions.ease_out_cubic)
        self.add(lines)
        self.play(lines.animate.shift(LEFT * 6).set_opacity(0), run_time=0.35, rate_func=rate_functions.ease_in_quad)
        self.remove(lines)

        for word in (fourier, transform):
            end = word.copy()
            word.scale(1.8).set_opacity(0)
            self.play(Transform(word, end), run_time=0.22, rate_func=rate_functions.ease_in_cubic)
            self.play(word.animate.shift(DOWN * 0.08), run_time=0.04)
            self.play(word.animate.shift(UP * 0.08), run_time=0.04)

        # FAST pulses once
        self.play(fast.animate.scale(1.08), run_time=0.15)
        self.play(fast.animate.scale(1 / 1.08), run_time=0.2)
        self.wait(2.2)
