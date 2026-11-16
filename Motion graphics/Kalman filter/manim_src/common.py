from pathlib import Path

import numpy as np
from PIL import Image
from manim import *

# 9:16 vertical, 1080x1920 @ 60fps, pure chroma green background
config.pixel_width = 1080
config.pixel_height = 1920
config.frame_height = 16.0
config.frame_width = 9.0
config.frame_rate = 60
config.background_color = "#00FF00"

INK = "#0E1116"      # dark outline that keeps text readable over any footage
FONT = "JetBrains Mono"

# palette - all far away from the key green
RAW = "#FF3B4E"      # noisy detections
KF = "#22D3FF"       # Kalman estimate
PRED = "#FFB020"     # prediction while target is hidden
PANEL_BG = "#0A0E16"
PANEL_EDGE = "#2C3850"
GRID = "#151D2B"
SLATE = "#8C9AB3"

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"


def outlined(m, w=8):
    m.set_stroke(INK, w, background=True)
    for sm in m.get_family():
        sm.joint_type = LineJointType.ROUND   # no miter spikes on sharp glyph corners
    return m


_CAP = {}


def mono(s, height, color=WHITE, weight=BOLD):
    """Monospace label whose CAP height is `height` (accents/descenders don't shrink it)."""
    if weight not in _CAP:
        _CAP[weight] = Text("HXE", font=FONT, weight=weight).height
    t = Text(s, font=FONT, weight=weight, color=color)
    return t.scale(height / _CAP[weight])


def keyed_rgba(path, key=(255, 0, 255)):
    """Load a Higgsfield PNG rendered on flat magenta and key the magenta out.

    Returns an RGBA uint8 array cropped to the subject.
    """
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    # "magenta-ness": how much both R and B exceed G
    m = np.minimum(r, b) - g
    alpha = 1.0 - np.clip((m - 60.0) / (150.0 - 60.0), 0, 1)
    # despill: pull any leftover magenta fringe toward neutral
    spill = np.clip(np.minimum(r, b) - g - 30.0, 0, None) * 0.7
    im[..., 0] -= spill
    im[..., 2] -= spill
    im = np.clip(im, 0, 255)
    rgba = np.dstack([im, alpha * 255]).astype(np.uint8)
    ys, xs = np.where(alpha > 0.05)
    if len(xs) == 0:
        return rgba
    pad = 4
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, rgba.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, rgba.shape[1])
    return rgba[y0:y1, x0:x1]
