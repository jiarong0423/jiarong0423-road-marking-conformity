"""Refine the 2025 -> F17 homography from a rough hand placement by ECC on paint masks.

Input: the four corners the owner placed in the overlay tool (F17 half-res px).
Both images reduced to paint masks by local contrast (paint is brighter than
its surroundings and colourless); F17's threshold is lower so the erased
chevron's residue counts. ECC (cv2.findTransformECC, MOTION_HOMOGRAPHY) on
blurred masks, coarse to fine.
"""
import sys, json, cv2, numpy as np

SV = "data/streetview/2025-06_before_erasure_CLY3P.jpg"   # owner screenshot of Street View; data/ is not in git
F17 = "evidence/field-2026-09-20/IMG_20260920_155843.jpg"


def paint(img, thr, blur):
    L = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[..., 0].astype(np.float32)
    res = L - cv2.GaussianBlur(L, (0, 0), blur)
    sat = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[..., 1]
    m = ((res > thr) & (sat < 60)).astype(np.uint8)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(np.float32)


def main(corners_json, out_dir):
    c = np.float32(json.loads(corners_json))
    sv = cv2.imread(SV); ph = cv2.resize(cv2.imread(F17), (1536, 2048), interpolation=cv2.INTER_AREA)
    H0 = cv2.getPerspectiveTransform(np.float32([[0, 0], [1024, 0], [1024, 1024], [0, 1024]]), c)
    ms = paint(sv, 18, 15); ms[:int(1024 * 0.27)] = 0; ms[970:, :110] = 0
    mp = paint(ph, 10, 20); mp[:int(2048 * 0.40)] = 0
    W = np.linalg.inv(H0).astype(np.float32)          # ECC warp: template (F17) -> input (SV)
    hist = []
    for sigma in (12, 6, 3):
        t = cv2.GaussianBlur(mp, (0, 0), sigma); i = cv2.GaussianBlur(ms, (0, 0), sigma * 1024 / 1536)
        try:
            cc, W = cv2.findTransformECC(t, i, W, cv2.MOTION_HOMOGRAPHY,
                                         (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6), None, 5)
            hist.append({"sigma": sigma, "ecc": round(float(cc), 4)})
        except cv2.error as e:
            hist.append({"sigma": sigma, "error": str(e)[:80]}); break
    H = np.linalg.inv(W); H /= H[2, 2]
    corners = cv2.perspectiveTransform(np.float32([[[0, 0], [1024, 0], [1024, 1024], [0, 1024]]]), H)[0]
    warped = cv2.warpPerspective(ms, H, (1536, 2048))
    over = ph.copy(); over[warped > 0.5] = (0.35 * over[warped > 0.5] + 0.65 * np.array([200, 40, 255])).astype(np.uint8)
    cv2.imwrite(f"{out_dir}/refined_overlay.jpg", over, [cv2.IMWRITE_JPEG_QUALITY, 88])
    ov0 = ph.copy(); w0 = cv2.warpPerspective(ms, H0, (1536, 2048)); ov0[w0 > 0.5] = (0.35 * ov0[w0 > 0.5] + 0.65 * np.array([200, 40, 255])).astype(np.uint8)
    cv2.imwrite(f"{out_dir}/start_overlay.jpg", ov0, [cv2.IMWRITE_JPEG_QUALITY, 88])
    np.save(f"{out_dir}/H_refined_half.npy", H)
    print(json.dumps({"ecc": hist, "corners_refined": np.round(corners, 1).tolist()}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
