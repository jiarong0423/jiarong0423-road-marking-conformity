#!/usr/bin/env python3
"""OpenCV 5's new matching tools, tried on the owner's own photographs (2026-10-14).

The question: can OpenCV 5's ALIKED keypoints + LightGlue matcher, or its multi-scale ECC
alignment, register two of my photographs on the road surface well enough to measure the
same thing twice? Two kinds of pair:

  - same direction, a second apart: F30 / F31 / F32, the red-line photographs of 20 September
  - across views and days: P64 (23 September, along the road) against F34 / F35 (20 September,
    from the kerb beside the cone). Only P64 sees the island's old end from a usable angle, so a
    second measurement of it would have to come through a registration like this.

Each pair is tried three ways:
  - SIFT + ratio test + MAGSAC homography (the OpenCV 4-era baseline)
  - cv2.ALIKED + cv2.LightGlueMatcher + MAGSAC homography (new in OpenCV 5; ONNX weights from
    scripts/fetch_aliked.sh, the files OpenCV's own tests use)
  - cv2.findTransformECCMultiScale with cv2.ECCParameters (new in OpenCV 5), homography,
    on quarter-size grey images, starting from the identity

Reported: matches, RANSAC inliers, inliers on the road surface (below the horizon), the ECC
correlation, and how far apart the SIFT and LightGlue homographies put the same road points.
Nothing here is ground truth; it says whether a registration exists, not how accurate it is.

    sh scripts/fetch_aliked.sh
    python3 -B scripts/opencv5_matchers_trial.py      (writes results/opencv5_matchers_trial.json)
"""
import json
import os
import time
import cv2
import numpy as np

D20, D23 = "evidence/field-2026-09-20/", "evidence/field-2026-09-23/"
PHOTOS = {"F30": D20 + "IMG_20260920_160015.jpg", "F31": D20 + "IMG_20260920_160016.jpg", "F32": D20 + "IMG_20260920_160017.jpg",
          "F34": D20 + "IMG_20260920_160046.jpg", "F35": D20 + "IMG_20260920_160047.jpg", "P64": D23 + "IMG_20260923_063437.jpg"}
# rows below which the frame is road surface, read off each photograph (horizon plus a margin)
ROAD_FROM_Y = {"F30": 2200, "F31": 2200, "F32": 2200, "F34": 1900, "F35": 1900, "P64": 1500}
PAIRS = [("F30", "F31", "same direction, 1 s apart"), ("F31", "F32", "same direction, 1 s apart"),
         ("F30", "F32", "same direction, 2 s apart"), ("P64", "F34", "across views, 3 days apart"),
         ("P64", "F35", "across views, 3 days apart")]

ALIKED = cv2.ALIKED.create("models/aliked/aliked-n16rot-top1k-640.onnx")
LIGHTGLUE = cv2.LightGlueMatcher.create("models/aliked/aliked_lightglue.onnx")
SIFT = cv2.SIFT_create(4000)
img = {k: cv2.imread(v) for k, v in PHOTOS.items()}
grey = {k: cv2.cvtColor(v, cv2.COLOR_BGR2GRAY) for k, v in img.items()}


def homography(pa, pb):
    if len(pa) < 8:
        return None, np.zeros(len(pa), bool)
    H, mask = cv2.findHomography(pa, pb, cv2.USAC_MAGSAC, 8.0)
    return H, (mask.ravel() > 0) if mask is not None else np.zeros(len(pa), bool)


def summary(a, pa, H, inl, n, t):
    return {"matches": int(n), "inliers": int(inl.sum()), "inliers_on_road": int((pa[inl][:, 1] > ROAD_FROM_Y[a]).sum()),
            "seconds": round(t, 1)}, H


def sift(a, b):
    t = time.time()
    ka, da = SIFT.detectAndCompute(grey[a], None); kb, db = SIFT.detectAndCompute(grey[b], None)
    good = [m for m, n in cv2.BFMatcher().knnMatch(da, db, k=2) if m.distance < 0.75 * n.distance]
    pa = np.float32([ka[m.queryIdx].pt for m in good]); pb = np.float32([kb[m.trainIdx].pt for m in good])
    H, inl = homography(pa, pb)
    return summary(a, pa, H, inl, len(good), time.time() - t)


def lightglue(a, b):
    t = time.time()
    ka, da = ALIKED.detectAndCompute(img[a], None); kb, db = ALIKED.detectAndCompute(img[b], None)
    xa = np.float32([k.pt for k in ka]); xb = np.float32([k.pt for k in kb])
    LIGHTGLUE.setPairInfo(xa, xb, (img[a].shape[1], img[a].shape[0]), (img[b].shape[1], img[b].shape[0]))
    m = LIGHTGLUE.match(da, db)
    pa = xa[[x.queryIdx for x in m]]; pb = xb[[x.trainIdx for x in m]]
    H, inl = homography(pa, pb)
    return summary(a, pa, H, inl, len(m), time.time() - t)


def ecc(a, b):
    t = time.time()
    s = 0.25; ga = cv2.resize(grey[a], None, fx=s, fy=s); gb = cv2.resize(grey[b], None, fx=s, fy=s)
    p = cv2.ECCParameters(); p.motionType = cv2.MOTION_HOMOGRAPHY
    try:
        cc, W = cv2.findTransformECCMultiScale(ga, gb, np.eye(3, dtype=np.float32), p)
        S = np.diag([s, s, 1.0]); W = np.linalg.inv(S) @ W.astype(np.float64) @ S      # back to full-size pixels
        moved = round(float(np.abs(W - np.eye(3)).max()), 4)
        return {"converged": True, "correlation": round(float(cc), 3), "max_change_from_identity": moved,
                "seconds": round(time.time() - t, 1)}, W
    except cv2.error as e:
        return {"converged": False, "why": str(e).strip().splitlines()[-1][:160], "seconds": round(time.time() - t, 1)}, None


def disagreement_px(a, H1, H2):
    """median distance, in the second photograph, between where the two homographies put a grid of road points"""
    if H1 is None or H2 is None:
        return None
    h, w = grey[a].shape
    g = np.float32([[x, y] for y in np.linspace(ROAD_FROM_Y[a], h - 50, 8) for x in np.linspace(50, w - 50, 8)])[None]
    return round(float(np.median(np.linalg.norm(cv2.perspectiveTransform(g, H1)[0] - cv2.perspectiveTransform(g, H2)[0], axis=1))), 1)


rows = []
for a, b, kind in PAIRS:
    s, Hs = sift(a, b); l, Hl = lightglue(a, b); e, He = ecc(a, b)
    rows.append({"pair": [a, b], "kind": kind, "sift": s, "aliked_lightglue": l, "ecc_multiscale": e,
                 "sift_vs_lightglue_on_road_px": disagreement_px(a, Hs, Hl),
                 "sift_vs_ecc_on_road_px": disagreement_px(a, Hs, He)})
    print(rows[-1])

out = {"date": "2026-10-14", "opencv": cv2.__version__,
       "weights": {"aliked-n16rot-top1k-640.onnx": "41faa7bf5d7eb68a2851471ba03aa20c9db30e4c",
                   "aliked_lightglue.onnx": "02723aa521990e57fe33d90b67977590c460e351",
                   "note": "sha1 as listed in opencv_extra testdata/dnn/download_models.py; ALIKED BSD-3-Clause, LightGlue Apache-2.0"},
       "photographs": PHOTOS, "road_from_y_px": ROAD_FROM_Y, "pairs": rows,
       "not_ground_truth": "these counts say whether a registration exists, not how accurate it is"}
with open("results/opencv5_matchers_trial.json.tmp", "w") as fh:
    fh.write(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
os.replace("results/opencv5_matchers_trial.json.tmp", "results/opencv5_matchers_trial.json")
