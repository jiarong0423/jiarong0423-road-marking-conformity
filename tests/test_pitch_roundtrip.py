"""Round-trip a known ground segment through the projection at several pitches.

If rectify.py is right, a segment of fixed ground length comes back the same
length whatever pitch it was photographed at. Nothing here touches an image.

This file printed its results and exited 0 whatever they were, which is not
a test: a regression in rectify.py would have changed every number and the
exit code would still have said fine. It now asserts.
"""
import sys, math
import numpy as np
sys.path.insert(0, "src")
from marking.rectify import ground_from_image, focal_px

W = H = 640

def project(Xg, Zg, fov, pitch_deg):
    """Ground point (X, Z) in camera-height units -> pixel, the forward map."""
    f = focal_px(fov, W)
    t = math.radians(pitch_deg)
    # world point sits on y = 1 (one camera height below the camera)
    P = np.array([Xg, 1.0, Zg])
    # undo the rotation ground_from_image applies
    R = np.array([[1, 0, 0],
                  [0, math.cos(t), -math.sin(t)],
                  [0, math.sin(t), math.cos(t)]])
    cam = R.T @ P            # inverse of rays @ R.T
    if cam[2] <= 1e-9:
        return None
    return np.array([cam[0]/cam[2]*f + W/2, cam[1]/cam[2]*f + H/2])

def main():
    print("a 0.20-wide segment lying across the road at Z = 3 camera heights\n")

    print(f"{'pitch':>7}{'fov':>6}{'px a':>18}{'px b':>18}{'read back':>12}{'error':>9}")
    bad = 0
    for pitch in (-12, -20, -25, -35, -40, -42):
        for fov in (40, 60, 75, 90):
            a = project(-0.10, 3.0, fov, pitch)
            b = project(+0.10, 3.0, fov, pitch)
            if a is None or b is None:
                print(f"{pitch:>7}{fov:>6}   behind the camera"); continue
            if not (0 <= a[0] < W and 0 <= a[1] < H and 0 <= b[0] < W and 0 <= b[1] < H):
                print(f"{pitch:>7}{fov:>6}   off frame ({a[0]:.0f},{a[1]:.0f}) "
                      f"({b[0]:.0f},{b[1]:.0f})"); continue
            g = ground_from_image([a, b], fov, pitch, (W, H))
            if not np.isfinite(g).all():
                print(f"{pitch:>7}{fov:>6}   came back above the horizon"); bad += 1; continue
            L = float(np.linalg.norm(g[1]-g[0]))
            err = L - 0.20
            flag = "" if abs(err) < 1e-6 else "   <-- WRONG"
            if abs(err) >= 1e-6: bad += 1
            print(f"{pitch:>7}{fov:>6}  ({a[0]:6.1f},{a[1]:6.1f})  "
                  f"({b[0]:6.1f},{b[1]:6.1f}){L:>12.6f}{err:>+9.6f}{flag}")
    print(f"\n{bad} of the cases failed" if bad else
          "\nevery case round-trips exactly: rectify.py handles pitch correctly, "
          "so the inconsistency is in what is being measured, not in the projection")
    if bad:
        raise SystemExit(1)

def test_ground_length_survives_every_pitch():
    """The projection returns a known ground length at any pitch and fov."""
    checked = 0
    for pitch in (-12, -20, -25, -35, -40, -42):
        for fov in (40, 60, 75, 90):
            a = project(-0.10, 3.0, fov, pitch)
            b = project(+0.10, 3.0, fov, pitch)
            if a is None or b is None:
                continue
            if not (0 <= a[0] < W and 0 <= a[1] < H
                    and 0 <= b[0] < W and 0 <= b[1] < H):
                continue                      # off frame, not a failure
            g = ground_from_image([a, b], fov, pitch, (W, H))
            assert np.isfinite(g).all(), (
                f"fov {fov} pitch {pitch}: came back above the horizon")
            length = float(np.linalg.norm(g[1] - g[0]))
            assert abs(length - 0.20) < 1e-6, (
                f"fov {fov} pitch {pitch}: 0.20 went in, {length:.6f} came back")
            checked += 1
    # the guard that matters: if the loop silently stopped finding cases,
    # an assertion that never runs is not a passing test
    assert checked >= 20, f"only {checked} cases were in frame; expected 22"


if __name__ == "__main__":
    main()
