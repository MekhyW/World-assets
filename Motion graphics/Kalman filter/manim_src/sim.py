"""Target trajectory, noisy detections and a real constant-velocity Kalman filter.

Everything here is in *panel-local* coordinates (panel is 4.15 x 9.0 units,
origin at its centre).  The Manim scene just looks these arrays up by time.
"""
import numpy as np
from scipy.interpolate import CubicSpline

FPS = 60
T_END = 10.4            # total clip length (s)
DET_HZ = 30.0           # detector rate (YOLO on the host PC)
T_FIRST_DET = 1.15

# ---------------- scene geometry (panel-local) ----------------
PANEL_W, PANEL_H = 4.15, 9.0
GROUND_Y = -3.55
# tree canopy = union of circles (cx, cy, r) - also used for occlusion tests
CANOPY = [
    (0.10, -0.66, 0.80),
    (-0.50, -1.05, 0.58),
    (0.72, -0.92, 0.58),
    (-0.32, -0.25, 0.58),
    (0.55, -0.22, 0.58),
    (0.10, 0.11, 0.52),
    (0.10, -1.28, 0.58),
]
TRUNK = dict(x=0.10, y_top=-1.6, y_bot=GROUND_Y, w_top=0.30, w_bot=0.55)
DRONE_W, DRONE_H = 0.95, 0.42   # visual footprint used for occlusion

# ---------------- target trajectory ----------------
WAYPOINTS = [  # (t, x, y)
    (0.60, 1.14, 3.85),
    (1.55, 0.04, 3.55),
    (2.40, -1.01, 3.00),
    (2.95, -1.32, 2.35),
    (3.40, -1.23, 1.65),
    (3.85, -0.88, 1.00),
    (4.30, -0.51, 0.36),
    (4.75, -0.14, -0.28),
    (5.20, 0.23, -0.92),
    (5.65, 0.60, -1.56),
    (6.10, 0.97, -2.20),
    (6.60, 1.28, -2.65),
    (7.20, 1.43, -1.90),
    (7.85, 1.43, -0.60),
    (8.55, 1.14, 0.75),
    (9.35, 0.40, 1.55),
    (10.40, -0.22, 1.85),
]
_wt = np.array([w[0] for w in WAYPOINTS])
_sx = CubicSpline(_wt, [w[1] for w in WAYPOINTS], bc_type="natural")
_sy = CubicSpline(_wt, [w[2] for w in WAYPOINTS], bc_type="natural")


def truth(t):
    t = np.clip(t, _wt[0], _wt[-1])
    return np.array([float(_sx(t)), float(_sy(t))])


def truth_vel(t):
    t = np.clip(t, _wt[0], _wt[-1])
    return np.array([float(_sx(t, 1)), float(_sy(t, 1))])


def in_canopy(x, y):
    for cx, cy, r in CANOPY:
        if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
            return True
    return False


_gx, _gy = np.meshgrid(np.linspace(-0.5, 0.5, 9), np.linspace(-0.5, 0.5, 5))
_GRID = np.stack([_gx.ravel() * DRONE_W, _gy.ravel() * DRONE_H], 1)


def visible_frac(t, occluder=in_canopy):
    p = truth(t)
    hidden = sum(occluder(p[0] + dx, p[1] + dy) for dx, dy in _GRID)
    return 1.0 - hidden / len(_GRID)


# ---------------- detections ----------------
def make_detections(occluder=in_canopy, seed=11):
    rng = np.random.default_rng(seed)
    dets = []  # (t, x, y)
    t = T_FIRST_DET
    while t < T_END:
        vis = visible_frac(t, occluder)
        if vis > 0.55 and rng.random() > 0.06:           # occasional dropped frame
            p = truth(t)
            n = rng.normal(0, 0.13, 2)
            if rng.random() < 0.08:                        # YOLO glitch / outlier
                n += rng.normal(0, 0.42, 2)
            dets.append((t, p[0] + n[0], p[1] + n[1]))
        t += 1.0 / DET_HZ
    return dets


# ---------------- Kalman filter (constant velocity, per axis) ----------------
Q_ACC = 0.6     # white-acceleration spectral density (low = smooth)
R_STD = 0.25    # assumed measurement std
GATE = 11.0     # chi^2(2) ~99.6 %: outlier detections are ignored


def _FQ(dt):
    F1 = np.array([[1, dt], [0, 1]])
    Q1 = Q_ACC * np.array([[dt ** 3 / 3, dt ** 2 / 2], [dt ** 2 / 2, dt]])
    return np.kron(np.eye(2), F1), np.kron(np.eye(2), Q1)   # state: x, vx, y, vy


def run_kf(dets, fps=FPS, t_end=T_END):
    """Returns per-frame arrays: t, est(x,y), cov(2x2), mode (0 none, 1 track, 2 predict)."""
    n = int(round(t_end * fps)) + 1
    ts = np.arange(n) / fps
    est = np.full((n, 2), np.nan)
    cov = np.zeros((n, 2, 2))
    mode = np.zeros(n, int)
    accepted = []
    H = np.zeros((2, 4))
    H[0, 0] = H[1, 2] = 1
    R = np.eye(2) * R_STD ** 2
    x = P = t_state = t_last = t_first = None

    def predict(x, P, dt):
        F, Q = _FQ(dt)
        return F @ x, F @ P @ F.T + Q

    di = 0
    for i, t in enumerate(ts):
        while di < len(dets) and dets[di][0] <= t + 1e-9:
            tm, mx, my = dets[di]
            z = np.array([mx, my])
            if x is None:
                x = np.array([mx, 0, my, 0], float)
                P = np.diag([R_STD ** 2, 4.0] * 2)
                t_first = tm
                t_state = t_last = tm
                accepted.append(True)
            else:
                x, P = predict(x, P, tm - t_state)
                t_state = tm
                S = H @ P @ H.T + R
                yv = z - H @ x
                if yv @ np.linalg.solve(S, yv) < (GATE if tm - t_first > 0.6 else 1e9):
                    K = P @ H.T @ np.linalg.inv(S)
                    x = x + K @ yv
                    P = (np.eye(4) - K @ H) @ P
                    t_last = tm
                    accepted.append(True)
                else:
                    accepted.append(False)
            di += 1
        if x is None:
            continue
        xp, Pp = predict(x, P, t - t_state)
        est[i] = xp[[0, 2]]
        cov[i] = Pp[np.ix_([0, 2], [0, 2])]
        mode[i] = 2 if (t - t_last) > 0.22 else 1
    return ts, est, cov, mode, accepted


if __name__ == "__main__":
    dets = make_detections()
    ts, est, cov, mode, acc = run_kf(dets)
    tr = np.array([truth(t) for t in ts])
    ok = ~np.isnan(est[:, 0])
    err = np.linalg.norm(est - tr, axis=1)
    print("dets", len(dets), "rejected", acc.count(False))
    print("rms err tracking", np.sqrt(np.nanmean(err[mode == 1] ** 2)))
    print("max err predicting", np.nanmax(err[mode == 2]) if (mode == 2).any() else None)
    pred_t = ts[mode == 2]
    print("predict window", pred_t.min(), pred_t.max())
    raw = np.array([[d[1], d[2]] for d in dets])
    rt = np.array([truth(d[0]) for d in dets])
    print("raw rms", np.sqrt(np.mean(np.sum((raw - rt) ** 2, 1))))
    # jitter (accel of displayed line)
    acc2 = np.linalg.norm(np.diff(est[ok], 2, axis=0), axis=1) * FPS ** 2
    print("est accel p95", np.percentile(acc2, 95))
    vis = [visible_frac(t) for t in ts]
    hid = ts[np.array(vis) < 0.55]
    print("hidden window", hid.min(), hid.max())
    # error right after reacquire
    i = np.where(mode == 2)[0][-1]
    print("err at end of prediction", err[i], "after", err[i + 1:i + 20:4])
    print("speed range", min(np.linalg.norm(truth_vel(t)) for t in ts[60:]), max(np.linalg.norm(truth_vel(t)) for t in ts[60:]))
