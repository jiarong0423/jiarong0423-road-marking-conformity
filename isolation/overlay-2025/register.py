"""Register the 2025-06 Street View (before erasure) onto F17 by a ground-plane homography.

Owner's direction 2026-09-23: overlay the two, and fill the erased part from 2025.
SIFT + ratio test + RANSAC homography, matches kept on the road surface only
(below the horizon in both images), because a homography holds for one plane.
"""
import sys, json, cv2, numpy as np

SV = "data/streetview/2025-06_before_erasure_CLY3P.jpg"   # owner screenshot of Street View; data/ is not in git
F17 = "evidence/field-2026-09-20/IMG_20260920_155843.jpg"
SCALE = 0.5            # F17 worked at half resolution for matching; H is rescaled to full


def main(out_dir):
    sv = cv2.imread(SV); ph_full = cv2.imread(F17)
    ph = cv2.resize(ph_full, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_AREA)
    g1 = cv2.cvtColor(sv, cv2.COLOR_BGR2GRAY); g2 = cv2.cvtColor(ph, cv2.COLOR_BGR2GRAY)
    m1 = np.zeros_like(g1); m1[int(g1.shape[0] * 0.28):] = 255          # below SV horizon
    m2 = np.zeros_like(g2); m2[int(g2.shape[0] * 0.40):] = 255          # below F17 horizon
    sift = cv2.SIFT_create(8000)
    k1, d1 = sift.detectAndCompute(g1, m1); k2, d2 = sift.detectAndCompute(g2, m2)
    mt = cv2.BFMatcher(cv2.NORM_L2).knnMatch(d1, d2, k=2)
    good = [a for a, b in mt if a.distance < 0.75 * b.distance]
    p1 = np.float32([k1[m.queryIdx].pt for m in good]); p2 = np.float32([k2[m.trainIdx].pt for m in good])
    Hh, inl = cv2.findHomography(p1, p2, cv2.USAC_MAGSAC, 3.0, maxIters=20000, confidence=0.9999)
    inl = inl.ravel().astype(bool)
    err = np.linalg.norm(cv2.perspectiveTransform(p1[inl][None], Hh)[0] - p2[inl], axis=1)
    S = np.diag([1 / SCALE, 1 / SCALE, 1.0]); Hfull = S @ Hh
    warped = cv2.warpPerspective(sv, Hfull, (ph_full.shape[1], ph_full.shape[0]))
    valid = cv2.warpPerspective(np.full(sv.shape[:2], 255, np.uint8), Hfull, (ph_full.shape[1], ph_full.shape[0])) > 0
    blend = ph_full.copy(); blend[valid] = (0.5 * ph_full[valid] + 0.5 * warped[valid]).astype(np.uint8)
    cv2.imwrite(f"{out_dir}/F17_overlay_2025.jpg", blend, [cv2.IMWRITE_JPEG_QUALITY, 88])
    cv2.imwrite(f"{out_dir}/F17_warped_2025.jpg", warped, [cv2.IMWRITE_JPEG_QUALITY, 88])
    np.save(f"{out_dir}/H_sv_to_F17.npy", Hfull)
    # matched inliers drawn, for checking where the registration comes from
    vis = cv2.drawMatches(sv, k1, ph, k2, [good[i] for i in np.nonzero(inl)[0][:200]], None,
                          matchColor=(0, 255, 0), flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    cv2.imwrite(f"{out_dir}/F17_matches.jpg", vis, [cv2.IMWRITE_JPEG_QUALITY, 80])
    rep = {"matches_ratio_test": len(good), "inliers": int(inl.sum()),
           "reproj_err_px_half_res": {"median": round(float(np.median(err)), 2), "p90": round(float(np.percentile(err, 90)), 2)}}
    json.dump(rep, open(f"{out_dir}/register_report.json", "w"), indent=1); print(rep)


if __name__ == "__main__":
    main(sys.argv[1])
