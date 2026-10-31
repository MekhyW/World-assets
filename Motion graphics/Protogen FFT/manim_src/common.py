from manim import *

# 9:16 vertical, 1080x1920 @ 60fps, pure chroma green background
config.pixel_width = 1080
config.pixel_height = 1920
config.frame_height = 16.0
config.frame_width = 9.0
config.frame_rate = 60
config.background_color = "#00FF00"

EMOJI_DIR = "/home/claude/fft/package"
INK = "#0E1116"  # dark outline that keeps white text readable over any footage


def emoji(code, height):
    m = SVGMobject(f"{EMOJI_DIR}/{code}.svg")
    m.height = height
    return m
