"""What is wrong with this road, from one photograph.

The earlier gate answered one narrow question - is the taper steeper than a
reference - and answering it well took most of this project. But a taper
that is 3 times too steep is not what hurts anybody on its own. What hurts
is that it arrives at the same place as a lane too narrow to share, a right
edge that is not carriageway, a double white line on the left, and a
surface in pieces. Each is arguable alone. Together they leave a rider on a
motorcycle with no lawful place to be.

So this reports the set, not the number. Every finding is detected in the
image rather than assumed, carries what was measured, and names the clause
it is measured against. A finding that cannot be detected is absent from
the list rather than guessed at.

    TAPER_TOO_STEEP       the chevron's boundary against the road
    NO_LANE_CHANGE        a double white line, §167, which forbids moving over
    EDGE_NOT_CARRIAGEWAY  a red line along the road edge, §169; which surface
                          it is painted on is not decided here
    SURFACE_IN_PIECES     more than two surfacings inside the running lane
    LANE_TOO_NARROW       car plus motorcycle plus §101's half metre

The last is the only one that needs a number from outside the photograph -
a lane width - and it says so.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

import cv2
import numpy as np

from .extract import markings, road_region
from .sequential import taper_with_hatching
from .actions import next_actions
from .gate2 import _segments
from . import phone
from .site_116 import SITE_116

# A frame has to be a photograph of a road before anything is said about
# the road in it. This gate is at frame level, in front of every detector,
# because the old one was inside `taper_ensemble` and the other four
# detectors never saw it: fed `np.random.default_rng(0)` noise, the system
# returned CARRIAGEWAY_OCCUPIED with width_frac 1.00 and
# EDGE_NOT_CARRIAGEWAY, and narrated 「先看你左手邊。那裡立著施工圍籬，
# 在你行車的高度佔掉畫面寬度的 100%」 for random pixels. Measured
# 2026-09-22, 12 of 12 noise frames.
#
# The separator is the size of `road_region`'s output, and the two
# populations do not overlap at all:
#
#   12 noise frames   0.000 of the frame, every one - the grey rule keeps
#                     nothing, so no component reaches the bottom edge
#   42 real frames    0.556 to 0.600
#
# Only the LOWER bound does any work, and that is worth saying plainly.
# `road_region` is a declared band below 40% of frame height (E20), so its
# ceiling is 0.600 by construction: an upper bound under 0.60 would refuse
# real photographs and one above 0.60 can never fire. The old
# ROI_FRAC_MAX = 0.87 was calibrated against a region that no longer
# exists and had never once triggered - E13, and standing rule 5's third
# instance.
MIN_ROAD_FRAC = 0.30     # half the reachable maximum; noise gives 0.000

CLEARANCE_M = 0.5        # 道路交通安全規則 §101
CAR_M, HEAVY_M, MOTO_M = 1.78, 2.50, 0.75


@dataclass
class Finding:
    code: str
    what: str
    measured: dict
    basis: str

    def as_dict(self):
        return asdict(self)


def _merge_collinear(segments, tol_deg=3.0, gap_frac=0.02, off_frac=0.004):
    """Join fragments of one line back into the line.

    §167's test is that the members run long and unbroken, and the
    detector applied that to raw Hough output, which is neither. Over
    the field set the median segment is about 4.5 % of the frame height
    while the threshold is 15 %, so nought to two segments per frame
    cleared it and a PAIR of them almost never did: `_double_white`
    returned nothing on all 42 photographs and had no test.

    Lowering the threshold would have found the pair by giving up the
    property §167 actually states. Joining the fragments keeps it: two
    pieces merge when they point the same way, lie on the same line,
    and their ends are close.
    """
    if not segments:
        return []
    h = max(max(s[1], s[3]) for s in segments)
    max_gap, max_off = gap_frac * h, off_frac * h
    items = [tuple(float(v) for v in s) for s in segments]
    items.sort(key=lambda s: -math.hypot(s[2]-s[0], s[3]-s[1]))
    # To a fixed point, not one pass. One pass is order-dependent and
    # under-merges: with three pieces of one line, the far one can be
    # filed as separate before the middle one arrives and closes the
    # distance, and nothing goes back for it. Three collinear
    # fragments came out as two.
    for _ in range(len(items)):
        merged = _merge_pass(items, tol_deg, max_gap, max_off)
        if len(merged) == len(items):
            return merged
        items = merged
    return items


def _merge_pass(items, tol_deg, max_gap, max_off):
    out = []
    for s in items:
        for i, t in enumerate(out):
            a = math.degrees(math.atan2(s[3]-s[1], s[2]-s[0])) % 180
            b = math.degrees(math.atan2(t[3]-t[1], t[2]-t[0])) % 180
            if min(abs(a-b), 180-abs(a-b)) > tol_deg:
                continue
            lt = math.hypot(t[2]-t[0], t[3]-t[1]) or 1.0
            d = ((t[2]-t[0])/lt, (t[3]-t[1])/lt)
            n = (-d[1], d[0])
            # perpendicular distance of s's ends from t's line
            off = max(abs((s[0]-t[0])*n[0] + (s[1]-t[1])*n[1]),
                      abs((s[2]-t[0])*n[0] + (s[3]-t[1])*n[1]))
            if off > max_off:
                continue
            # along-line extent: they must overlap or nearly touch
            ps = sorted((s[0]-t[0])*d[0] + (s[1]-t[1])*d[1] for s in
                        ((s[0], s[1]), (s[2], s[3])))
            pt = sorted((0.0, lt))
            if ps[0] > pt[1] + max_gap or ps[1] < pt[0] - max_gap:
                continue
            lo, hi = min(ps[0], pt[0]), max(ps[1], pt[1])
            out[i] = (t[0]+d[0]*lo, t[1]+d[1]*lo, t[0]+d[0]*hi, t[1]+d[1]*hi)
            break
        else:
            out.append(s)
    return out


GROUND_FRAC = 0.40       # everything below this is where a road can be


def _on_road(seg, shape):
    """Both ends of this segment are low enough in the frame to be road.

    Position, not appearance. The version before this asked
    `carriageway()`, which decides by surface uniformity - and a wall is
    uniform while asphalt that has been dug and patched is not, so it
    kept the sky, the factory roofs and the shop frontages and punched
    holes in the actual road. Two of the four §167 detections it let
    through were drawn and looked at: a factory roofline and a
    restaurant's eaves. This rule excludes both.

    A road is the ground. The ground is below. That is the whole test,
    it needs no horizon fit and no appearance term, and it is the same
    rule the architecture specifies for a search region: a handheld
    photograph taken while standing puts the horizon above 40 % of the
    frame, and a frame where it does not was pointed at the sky.

    Crude, and the crudeness is the point. It does not claim to find the
    carriageway; it refuses the sky.
    """
    h = shape[0]
    return min(seg[1], seg[3]) >= h * GROUND_FRAC


def _double_white(segments, image, roi=None):   # roi kept, deliberately unused
    """Two long, close, parallel solid lines on the carriageway: §167.

    Distinguished from one wide line by the dark gap between them, and
    from a dashed line by both members running unbroken.

    Two corrections, both from 2026-09-21 and both found by looking at
    what it returned rather than at whether it returned something.

    The fragments are joined first - see `_merge_collinear`. Raw Hough
    output on these photographs has a median segment of about 4.5 % of
    the frame height against a threshold of 15 %, so a PAIR almost
    never cleared it and this returned nothing on all 42.

    And the pair must be ON THE ROAD. With only the length rule fixed
    it fired on 5 of 42, and all five were drawn and looked at: F01 is
    the corrugation ribs of the construction hoarding - two bright
    ridges with a shadow between them, which is a double white line in
    every respect except being one - and F42 is the roof edge of a
    restaurant. Nought of five were markings. A detector for a road
    marking that never asks whether it is looking at the road will find
    one in a wall, and a search region is the only thing that stops it.

    `roi` is still in the signature and is deliberately not used. The
    carriageway mask cannot be trusted here and removing the parameter
    would make the caller look like it never passed one.

    §167 has no test of its own; this is the third finding in one day
    of a detector that was believed because nothing contradicted it.
    """
    segments = [s for s in _merge_collinear(segments)
                if _on_road(s, image.shape)]
    if len(segments) < 2:
        return None
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    L = lab[:, :, 0].astype(np.float32)
    B = lab[:, :, 2].astype(np.float32)      # b*: yellow positive, blue negative
    h, w = L.shape
    best = None
    for i in range(len(segments)):
        x1, y1, x2, y2 = segments[i]
        li = math.hypot(x2-x1, y2-y1)
        if li < h*0.15:
            continue
        ai = math.degrees(math.atan2(y2-y1, x2-x1)) % 180
        di = np.array([x2-x1, y2-y1])/li
        ni = np.array([-di[1], di[0]])
        mi = np.array([(x1+x2)/2, (y1+y2)/2])
        for j in range(i+1, len(segments)):
            X1, Y1, X2, Y2 = segments[j]
            lj = math.hypot(X2-X1, Y2-Y1)
            if lj < h*0.15:
                continue
            aj = math.degrees(math.atan2(Y2-Y1, X2-X1)) % 180
            if min(abs(ai-aj), 180-abs(ai-aj)) > 4:
                continue
            mj = np.array([(X1+X2)/2, (Y1+Y2)/2])
            gap = abs(float((mj-mi) @ ni))
            # §167 sizes the pair like a 分向限制線: two 10 cm lines 10 cm
            # apart, so the gap is about one line width, not a lane
            if not (0.004*w < gap < 0.05*w):
                continue
            # Sample the gap across the two segments' OVERLAP, at
            # several points, not at one point on the normal.
            #
            # This line used to be
            #     mid = mi + ni*float((mj-mi) @ ni)/2
            # which keeps only the perpendicular component and throws
            # the along-line offset away. On F07 the two segments were
            # offset 174 px along their length, so the sample landed
            # 87 px from the real midpoint - on asphalt at L* 161
            # instead of inside the paint at L* 227 - and a SINGLE
            # painted stroke passed as a pair of lines with its own
            # width, 19.1 px, reported as their gap. That is how the
            # roof edges, the kerb and the milled joint all got through
            # the "the gap must be darker" test: it was not looking at
            # the gap.
            #
            # Two segments that do not overlap along their length are
            # not a double line at all, so that is now a rejection
            # rather than a sample somewhere else.
            pi0, pi1 = sorted(((np.array([x1, y1])-mi) @ di,
                               (np.array([x2, y2])-mi) @ di))
            pj0, pj1 = sorted(((np.array([X1, Y1])-mi) @ di,
                               (np.array([X2, Y2])-mi) @ di))
            lo, hi = max(pi0, pj0), min(pi1, pj1)
            if hi - lo < max(20.0, 0.25*min(li, lj)):
                continue
            here_vals, on_vals = [], []
            for t in np.linspace(lo, hi, 9)[1:-1]:
                base = mi + di*t
                off = float((mj-mi) @ ni)
                for pt, bag in ((base + ni*off/2, here_vals),
                                (base, on_vals), (base + ni*off, on_vals)):
                    xx, yy = int(pt[0]), int(pt[1])
                    if 0 <= xx < w and 0 <= yy < h:
                        bag.append(float(L[yy, xx]))
            if len(here_vals) < 5 or not on_vals:
                continue
            here = float(np.median(here_vals))
            on = float(np.median(on_vals))
            if on - here < 18:
                continue

            # Colour, each member on its own. Restored after the gap
            # sampling was rewritten - the edit that fixed the sample
            # point deleted this block with it, and the synthetic
            # positive test caught it immediately with a NameError.
            bi = float(B[int(mi[1]) % h, int(mi[0]) % w])
            bj = float(B[int(mj[1]) % h, int(mj[0]) % w])
            if (bi > 140) != (bj > 140):
                continue
            colour = "yellow" if bi > 140 else "white"
            section = "165" if colour == "yellow" else "167"

            # The surface outside both members must match, or this is
            # the edge of one surface against another rather than paint.
            step = max(3.0, gap)
            sgn = 1 if (mj-mi) @ ni > 0 else -1
            oa, ob = mi - ni*step*sgn, mj + ni*step*sgn
            pa = (int(oa[1]) % h, int(oa[0]) % w)
            pb = (int(ob[1]) % h, int(ob[0]) % w)
            outside = abs(float(L[pa]) - float(L[pb]))
            if outside > 30:
                continue

            score = min(li, lj)
            if best is None or score > best["length_px"]:
                best = {"gap_px": round(gap, 1), "length_px": round(score, 1),
                        "colour": colour, "section": section,
                        "b_star": [round(bi, 1), round(bj, 1)],
                        "outside_diff": round(outside, 1),
                        "contrast": round(on-here, 1),
                        "bearing_deg": round((ai+aj)/2, 1),
                        "px": [[round(v, 1) for v in segments[i]],
                               [round(v, 1) for v in segments[j]]]}
    return best


def _kerbside_red(image, roi):
    """A red line running with the road: §169.

    Whether it sits on a kerb or on the road surface is not something
    this detector can tell, and §169 provides for both - on the kerb as
    the principle, on the road surface within 30 cm of the edge where
    there is none. This docstring said "drawn on the kerb" until
    2026-09-22, and the finding below said the carriageway ended there.
    F30, F31 and F32 show the intact line on a concrete strip level
    with the road, with the kerb a separate raised element further out,
    and a second, worn line 0.63-0.68 m nearer the lane on the asphalt.
    isolation/REDLINE.md. What is detected is a red elongated component;
    nothing here has ever touched a kerb.
    """
    b, g, r = cv2.split(image.astype(np.int16))
    red = ((r - (g+b)//2 > 14) & (r > 55)).astype(np.uint8)*255
    if roi is not None:
        red = cv2.bitwise_and(red, cv2.bitwise_not(cv2.erode(
            roi, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))))
    h, w = red.shape
    red[:int(h*0.40)] = 0
    red = cv2.morphologyEx(red, cv2.MORPH_CLOSE,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(red, 8)
    best = None
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < 150:
            continue
        ys, xs = np.nonzero(lbl == i)
        p = np.stack([xs, ys], 1).astype(np.float32)
        c = p.mean(0)
        _, _, v = np.linalg.svd(p - c, full_matrices=False)
        d = v[0]/np.linalg.norm(v[0])
        pr = (p - c) @ d
        run = float(pr.max()-pr.min())
        if run < h*0.12:
            continue
        if best is None or run > best["run_px"]:
            best = {"run_px": round(run, 1), "area_px": int(st[i, cv2.CC_STAT_AREA]),
                    "bearing_deg": round(math.degrees(math.atan2(d[1], d[0])) % 180, 1),
                    "px": [int(st[i, cv2.CC_STAT_LEFT]), int(st[i, cv2.CC_STAT_TOP]),
                           int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])],
                    "axis_px": [[round(float(c[0]+d[0]*pr.min()), 1),
                                 round(float(c[1]+d[1]*pr.min()), 1)],
                                [round(float(c[0]+d[0]*pr.max()), 1),
                                 round(float(c[1]+d[1]*pr.max()), 1)]]}
    return best


def surface_types_stable(image, roi, kmax=5, runs=5):
    """The surfacing count, only when it is the same count every time.

    `_surface_types` uses `cv2.kmeans` with `KMEANS_PP_CENTERS` and no
    fixed seed, so it is not repeatable. On F30 five consecutive calls
    in one process gave 3, 3, 3, 3, 2, and over two full runs of the 42
    it differed on nine frames. SURFACE_IN_PIECES fires more often than
    any other finding - 33 of 42 - and it carries the point this project
    is about, the patched surface. A count that changes when nothing
    changed is a draw, not a measurement.

    Seeding the generator would make it repeat without making it right:
    the disagreement is real, it is the clustering being unable to
    decide, and hiding it would report one arm of a coin toss as a
    number.

    So the project's own standard applies, the one `taper_ensemble` uses
    for encodings: run it several times and answer only if every run
    agrees. Returns (count, stable). A frame where the runs disagree
    gets no finding and says so.
    """
    # Across SEEDS, not across repeats. The first version ran it five
    # times and asked whether they agreed - but the flip rate is about
    # one in five, so the answer to "is it stable" was itself a coin
    # toss: F30 gave (3, False) then (3, True) then (3, True). A
    # non-deterministic check for determinism.
    #
    # Seeding fixes the reported number so the same bytes give the same
    # answer, which is what this project claims. The spread across seeds
    # is then its uncertainty, reported rather than hidden - the same
    # shape as the taper, which refuses a point value and gives bounds.
    # One seeded call, not `runs` of them. Running it five times made
    # assess() take 194 s against a documented 30 s budget - the
    # clustering is 8.9 s a call - and it suppressed the finding on F30,
    # which is the patched surface this project is about. A correctness
    # fix that costs the product its answer and its timeout is not a fix.
    #
    # Seeding gives what the project actually claims: the same bytes give
    # the same number. `cv2.kmeans` already retries internally
    # (attempts=5) so the seeded answer is not a single draw. The spread
    # across seeds is real and is a property of the method, not of the
    # frame; it is measured once offline and recorded rather than paid
    # for on every request. `runs` is kept for that offline use.
    cv2.setRNGSeed(0)
    one = _surface_types(image, roi, kmax=kmax)
    if one is None:
        return None, False
    if runs <= 1:
        # None, not True. Returning True here claimed a stability that
        # nothing had checked, and because `assess()` calls this with
        # runs=1 the branch that reports instability could never fire -
        # a guard written and disabled in consecutive edits. ER01.
        return one, None
    seen = {one}
    for seed in range(1, runs):
        cv2.setRNGSeed(seed)
        v = _surface_types(image, roi, kmax=kmax)
        if v is not None:
            seen.add(v)
    cv2.setRNGSeed(0)
    return one, len(seen) == 1


def _surface_types(image, roi, kmax=5, want_labels=False):
    if roi is None:
        return (None, None) if want_labels else None
    h, w = image.shape[:2]
    flat = cv2.medianBlur(image, 2*int(0.03*max(h, w))//2*2 + 1)
    L = cv2.cvtColor(flat, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    rough = cv2.GaussianBlur(np.abs(L - cv2.GaussianBlur(L, (0, 0), 4)), (0, 0), 12)
    sel = roi > 0
    X = np.column_stack([L[sel], rough[sel]*6]).astype(np.float32)
    if len(X) < 500:
        return (None, None) if want_labels else None
    idx = np.random.default_rng(0).choice(len(X), min(20000, len(X)), replace=False)
    Xs = X[idx]
    found = 1
    for k in range(2, kmax+1):
        crit = (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
        _, lab, cen = cv2.kmeans(Xs, k, None, crit, 5, cv2.KMEANS_PP_CENTERS)
        lab = lab.ravel()
        within = float(np.mean([np.linalg.norm(Xs[lab == i]-cen[i], axis=1).mean()
                                for i in range(k) if (lab == i).sum() > 0]))
        sep = float(min(np.linalg.norm(cen[i]-cen[j])
                        for i in range(k) for j in range(i+1, k)))
        share = min((lab == i).sum()/len(lab) for i in range(k))
        if sep > 1.6*within and share > 0.12:
            found = k
    if not want_labels:
        return found
    # the winning clustering again, over every pixel, so a drawing can
    # show which surface is which rather than only how many there were
    crit = (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5)
    _, lab, _ = cv2.kmeans(X, max(found, 1), None, crit, 5,
                           cv2.KMEANS_PP_CENTERS)
    canvas = np.full((h, w), -1, np.int16)
    canvas[sel] = lab.ravel().astype(np.int16)
    return found, canvas


def _scenario(findings, posted_kmh, image_w=None):
    """What happens to a person riding through here, in the order it happens.

    A list of codes tells an engineer which clauses are in play. It does
    not tell anyone what the road is like to use, and that is the thing
    being complained about. None of these findings is the complaint on its
    own: the complaint is that the left is taken by the works, the right
    is not carriageway, and the lane in between is too narrow, all at the
    same moment, to the same person.

    Returns two lists, and the split is the point.

    `steps` may contain only a clause that quotes a value measured in
    this frame, or one that names inline the regulation it is read
    under. `unmeasured` holds everything true of the site that this
    program did not measure - the drain covers, the bridge - so that an
    unearned sentence has nowhere else to sit.

    This docstring used to say "Nothing is narrated that was not
    detected". It was false: the bridge, the approach, the ordering and
    a bare 1-second constant were all asserted, and fed random pixels
    the whole narration ran anyway. E21, E22.
    """
    by = {f.code: f for f in findings}
    steps, unmeasured = [], []
    if image_w is None:          # side unknown; say so rather than guess
        image_w = float("inf")

    occ = by.get("CARRIAGEWAY_OCCUPIED")
    if occ:
        m = occ.measured
        steps.append(
            f"先看你{'左' if m['side']=='left' else '右'}手邊。"
            f"那裡立著施工圍籬，在你行車的高度佔掉畫面寬度的 "
            f"{m['width_frac']*100:.0f}%。"
            f"那一側本來是路。車流沒有變少，路變窄了，"
            f"所以所有人被擠進剩下的寬度裡——包含你。")

    t = by.get("TAPER_TOO_STEEP")
    if t:
        m = t.measured
        # The ensemble reports a bound, not a point, so the narration has
        # to as well. It read `equivalent_kmh` and `rate`, which the point
        # version emitted and the bound version does not, and every frame
        # that actually asserted a taper raised KeyError here. No test
        # covered the asserting path, so 41 of 42 photographs passed and
        # the one that worked crashed.
        kmh = m.get("equivalent_kmh_at_most")
        times = m.get("times_required_at_least")
        line = "路面在你前方收窄，而你是看到才知道的。"
        if kmh is not None:
            line += (f"這個漸變段的幾何最寬容的讀法也只適合時速 "
                     f"{kmh:.0f} 公里，你正以 {posted_kmh:.0f} 公里接近它")
        else:
            line += f"你正以 {posted_kmh:.0f} 公里接近它"
        rate = m.get("rate_median") or m.get("rate")
        if rate:
            secs = (3.0/rate) / (posted_kmh/3.6)
            line += (f"；從進入到通過只有 {secs:.1f} 秒，"
                     f"而一個人從察覺到手腳做出反應要 2.5 秒。"
                     f"等你反應過來，你已經在裡面了")
        if times is not None:
            line += f"。這是所有編碼版本中最寬容的那個給的下界（至少 {times:.1f} 倍）"
        steps.append(line + "。")

    kr = by.get("EDGE_NOT_CARRIAGEWAY")
    if kr:
        m = kr.measured
        run = m.get("run_px")
        # Which side, from the detector's own bounding box. This said
        # 「右」 unconditionally, and the red line is left of frame centre
        # on 10 of the 25 frames that fire - F14 says 「往右邊看」 about a
        # thing whose box starts at x=0.
        # `px` is [x, y, w, h], a list, and the first version of this
        # read it as a dict. Every frame where the red line fires -
        # 25 of 42 - raised AttributeError, and the test written beside
        # the fix passed because it invented a dict. A test whose input
        # the real detector never produces tests nothing.
        box = m.get("px")
        cx = None
        if isinstance(box, (list, tuple)) and len(box) >= 3:
            cx = float(box[0]) + float(box[2]) / 2.0
        elif isinstance(box, dict) and box.get("x") is not None:
            cx = float(box["x"]) + float(box.get("w", 0)) / 2.0
        side = "右" if cx is None or cx >= image_w / 2 else "左"
        steps.append(
            (f"你直覺往{side}閃。那一側" if t else f"往{side}邊看。那裡") +
            (f"有一段連續 {run:.0f} 像素的紅色" if run else "有紅色") +
            "沿著路緣延伸。§169 說紅線以劃設於道路緣石正面或頂面為原則，"
            "無緣石之道路得標繪於路面上，距路面邊緣以三十公分為度。"
            "它畫在緣石上還是路面上、車道是不是到這裡為止，照片判不出來；"
            "這一段的照片裡它畫在與路面齊平的混凝土帶上，緣石另在外側。")
        # The drain covers are the owner's point and they are in the
        # photographs, and nothing in this program detects them:
        # `_grated_cover` was removed on 2026-09-21 and not replaced.
        # This sentence used to sit in the narration above, unlabelled.
        unmeasured.append(
            "紅線下方是水溝蓋，貼著紅線騎就是騎在溝蓋上。"
            "現場紀錄與照片可見，本程式未能辨識——偵測器 _grated_cover 於 "
            "2026-09-21 移除,因為它在三個畫面裡找到三個週期結構,沒有一個是溝蓋。")

    t4 = by.get("TAPER_BELOW_TABLE_4_2_7")
    if t4:
        m = t4.measured
        steps.append(
            f"槽化線的兩條邊界之間,量到的夾角換算成漸變率約 {m['ratio']:.1f}:1。"
            f"表 4.2.7 在時速 {posted_kmh:.0f} 公里要 {m['need_ratio']:.0f}:1。"
            "哪個設計速率適用要看核定文件,這張照片給不了。")

    two = by.get("TWO_RED_LINES")
    if two:
        m = two.measured
        steps.append(
            f"這裡有兩條紅線。溝帶上的新線,和柏油上磨掉的舊線,相距約 {m['gap_m']:.2f} 公尺"
            f"(用新紅線 10 公分的線寬當尺)。紅線往外移,溝帶被畫進了車道那一側。")

    dw = by.get("NO_LANE_CHANGE")
    if dw:
        m = dw.measured
        ln, gp = m.get("length_px"), m.get("gap_px")
        steps.append(
            ("那就往另一側。但那裡" if kr else "看另一側。那裡") +
            "是雙白實線，§167 禁止在此變換車道。"
            + (f"畫面內量到的兩條線相距 {gp:.0f} 像素、可見長度 {ln:.0f} 像素"
               "（這是在這一張照片裡看得到的部分，不是這條線的全長）。"
               if ln and gp else ""))
        # §167 itself says where these lines go - 設於橋樑、隧道、彎道、坡道
        # 等路段 - so the bridge is an inference from the clause, which is
        # evidence, and not an observation of this photograph. It is said
        # here with the clause named, and the part that would need
        # measuring is said separately below.
        steps.append(
            "§167 規定這種線設於橋樑、隧道、彎道、坡道等路段。"
            "依該條，一旦進入就不能變換車道，所以要走哪一道必須在它起點之前決定。")
        unmeasured.append(
            "前方的橋是樹林陸橋 2B-2(A)，引道近端距此 430 公尺，全長 355.6 公尺"
            "(新北市轄內橋梁基本資料，results/control_group.json)。"
            "時速 50 公里跑 430 公尺是 31 秒。"
            "這是公文事實，不是從這張照片量出來的——"
            "10 公分的線在 20 公尺外只有 14.2 像素(results/pixel_budget.json)，"
            "430 公尺外的結構這批照片量不到任何東西。"
            "本程式也沒有量測這條線在畫面外的延伸，"
            "沒有量測任何兩個發現之間的前後順序:敘事的排列是作者手排的。"
            "「決定的時機被推到收窄之前」因此是現場描述，不是量測結果。")

    n = by.get("LANE_TOO_NARROW")
    if n:
        m = n.measured
        steps.append(
            f"於是你留在原地，一台車跟上來跟你並行。"
            f"法規要求的半公尺側向間隔不是禮貌，是規定。"
            f"小客車加上你加上那半公尺要 {m['need_car_m']:.2f} 公尺，"
            f"大型車要 {m['need_heavy_m']:.2f} 公尺，"
            f"這條車道 {m['lane_width_m']:.2f} 公尺。兩個都湊不出來。")

    su = by.get("SURFACE_IN_PIECES")
    if su:
        steps.append(
            f"而你腳下這塊，路面分得出 {su.measured['surface_types']} 種鋪面。"
            "挖掘審查原則 6.0:新舊銜接處的高低差，3 米直規量測不得超過正負 0.6 公分。"
            "本程式數的是鋪面的種類，沒有量高低差——那需要比例尺。")

    # Count findings, not steps. §167 is narrated in two steps - the
    # measurement, then the clause it is read under - and counting steps
    # made the product say 「這兩項是同一張照片裡同時量到的」 when one
    # thing had been measured. Introduced by the G00 fix itself, found by
    # the red team the same hour.
    if len(findings) >= 3:
        steps.append(
            f"這 {len(findings)} 項是同一張照片裡同時量到的，"
            "每一項的量測與依據條文列在 findings。")
        unmeasured.append(
            "所以剩下的選項是跟旁邊的車搶那不存在的半公尺，或者往右壓到紅線上去。"
            "這不是駕駛行為的問題,是施工佔用、標線設計和上橋動線被分開處理，"
            "沒有人負責它們疊在一起時一個人要怎麼過——"
            "這是對上列量測的解讀，不是量測本身。")
    elif len(findings) == 2:
        steps.append("這兩項是同一張照片裡同時量到的，量測與依據列在 findings。")

    return steps, unmeasured


# _grated_cover was removed on 2026-09-21. It looked for coherent periodic
# low-saturation bars, which is what a grating is, and it found three of
# them in three frames: the chevron hatching (F17), a patched asphalt scar
# (F17 after a sign test was added), and the ghost of the erased chevron
# (F22). None was a drain cover. Adding the paint/slot sign test moved the
# false positive rather than removing it. The grated cover at this site is
# on the site record and in the photographs; this code does not identify
# it, and the response says so rather than leaving the reader to assume
# every listed finding is the whole of what is there.


QUALITIES = (80, 90, 100)
WORK_PX = (1000, 1400, 1800)
# Above this the "carriageway" is the whole frame. Recalibrated on
# 2026-09-21 after the carriageway() fix: the old 0.75 was measured
# against a region that cut the chevron out, so once the chevron was
# correctly included the region legitimately grew and 7 of 12 field
# photographs were refused as "not a road photograph". Over 24 real
# photographs and 16 noise frames with the fixed region, real runs
# 0.128-0.819 and noise 0.923-0.977; this sits in the gap and refuses
# every noise frame while refusing no real one.
ROI_FRAC_MAX = 0.87
CORRIDOR_WIDTH_DEG = 19.0  # the regulated search range, 1° to 20°


def taper_ensemble(image, fov_deg: float, posted_kmh: float):
    """Measure the taper on several encodings of the same photograph.

    Re-encoding a frame changes nothing about the road, so anything the
    answer does across encodings is the method's own noise. Measuring it
    once and reporting an endpoint-jitter uncertainty answered how
    precisely a chosen line could be fitted - not whether the same line
    would be chosen, which is where this method actually moves. On
    2026-09-21 that turned out to be 11.5 to 17.3 degrees, larger than the
    quantity itself.

    So the ensemble is the uncertainty measurement. The verdict is put to
    every encoding that yields a reading, and only a unanimous answer is
    reported. A split is INDETERMINATE - not a weak yes, but the honest
    statement that this photograph does not settle it.
    """
    required = 155.0 / posted_kmh**2

    # Unanimity is not enough on its own. A frame of pure random noise
    # produced five readings out of five encodings, all agreeing that the
    # taper was too steep, because the reference rate at 50 km/h is 0.062
    # - about 3.5 degrees - and almost any spurious line beats it. The
    # ensemble measures whether a reading is stable, not whether there was
    # anything there to read. So the frame must first contain a road.
    #
    # An earlier version of this tested only whether carriageway() found
    # anything, on the strength of one noise image that it refused. Over
    # 24 noise images it refuses 5 and accepts 19, so that test was a
    # coincidence generalised. What does separate them is how much of the
    # frame the region covers: noise gives 0.846 to 0.966, because there
    # is no contrast for the surface test to cut on, while 21 photographs
    # of real roads give 0.179 to 0.614. A road photograph has sky,
    # buildings and verge in it. A carriageway covering nine tenths of the
    # frame is not a carriageway.
    roi = road_region(image)
    roi_frac = 0.0 if roi is None else float((roi > 0).mean())
    # The gate that was here tested `roi_frac > ROI_FRAC_MAX = 0.87`. It
    # had never once fired: it was calibrated against `carriageway()`,
    # which is withdrawn, and `road_region` is a declared band whose
    # ceiling is 0.600 by construction, so no frame could reach 0.87.
    # Worse, its other half tested `roi is None` while `road_region`
    # returns an EMPTY but non-None mask on noise - 12 of 12 - so a
    # zero-pixel region passed as a carriageway. E13.
    #
    # The live separator is the lower bound, and it is clean:
    #   42 real frames  0.5550 - 0.6001
    #   12 noise frames 0.0000
    # An upper bound is not available and saying so is better than
    # keeping a number that cannot fire.
    if roi is None or roi_frac < MIN_ROAD_FRAC:
        return {"encodings": len(QUALITIES)*len(WORK_PX), "readings": 0,
                "required_rate": round(required, 4),
                "roi_frac": round(roi_frac, 3),
                "state": "CANNOT_MEASURE",
                "why": (f"the road region covers {roi_frac*100:.1f}% of this "
                        f"frame; 42 photographs of this road give 55.5-60.0% "
                        f"and 12 noise frames give 0.0%, so this is not a "
                        f"road photograph")}

    # Resolution moves the answer at least as much as compression does.
    # Fixing a working size does not remove that - it hides it behind a
    # choice, and the choice picks the answer: on F05 a long side of 1600
    # or 1900 px returns STEEPER_THAN_REFERENCE while 1050 or 1200 returns
    # CANNOT_MEASURE. A constant that decides the verdict is not a
    # constant, it is a thumb on the scale. So resolution joins
    # compression as an axis of the ensemble and the reading has to
    # survive both.
    # Two early exits. Neither changes an answer: each stops only work
    # whose outcome is already fixed. They matter because the grid costs
    # nine detections and the gateway allows thirty seconds, and because
    # the cases that exit early - disagreement, and too few readings - are
    # the common ones on this site.
    total = len(QUALITIES)*len(WORK_PX)
    need = math.ceil(2*total/3)
    rates, degs = [], []
    done = 0
    early = None
    # What the router needs that the readings alone do not carry: whether
    # anything chevron-shaped was ever found, as opposed to found and
    # disagreed about. A frame with no hatching anywhere and a frame whose
    # hatching moves between encodings call for different actions, and the
    # count of readings is the same in both.
    # The grid's shape is the signal, not its total. Failing only at low
    # resolution says the photograph is poor and a retake would fix it;
    # failing in all nine says there is nothing there to find. Counting
    # them together destroys exactly that distinction, which is why a
    # router given the counts answered at chance.
    ev = {"segments_min": None, "segments_max": None,
          "encodings_with_candidates": 0, "encodings_with_bordering": 0,
          "candidates_total": 0, "bordering_total": 0,
          "cells": []}
    for px in WORK_PX:
        f = px / max(image.shape[:2])
        src = cv2.resize(image, None, fx=f, fy=f,
                         interpolation=cv2.INTER_AREA if f < 1
                         else cv2.INTER_LINEAR)
        for q in QUALITIES:
            ok, buf = cv2.imencode(".jpg", src, [cv2.IMWRITE_JPEG_QUALITY, q])
            if not ok:
                continue
            im = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            segs, _ = _segments(im)
            ev["segments_min"] = (len(segs) if ev["segments_min"] is None
                                  else min(ev["segments_min"], len(segs)))
            ev["segments_max"] = (len(segs) if ev["segments_max"] is None
                                  else max(ev["segments_max"], len(segs)))
            cell = {"px": px, "q": q, "segments": len(segs),
                    "candidates": 0, "bordering": 0, "deg": None}
            if len(segs) < 6:
                ev["cells"].append(cell)
                done += 1
                continue
            t = taper_with_hatching(segs, fov_deg, im.shape[1], im.shape[0])
            cands = t.get("candidates") or []
            cell["candidates"] = len(cands)
            cell["bordering"] = sum(1 for c in cands if c.get("borders"))
            cell["cand_deg"] = [c["taper_deg"] for c in cands]
            if t.get("ok"):
                cell["deg"] = round(t["taper_deg"], 2)
                cell["members"] = t.get("members")
                cell["evidence"] = t.get("evidence")
            ev["cells"].append(cell)
            if cands:
                ev["encodings_with_candidates"] += 1
                ev["candidates_total"] += len(cands)
                nb = sum(1 for c in cands if c.get("borders"))
                ev["bordering_total"] += nb
                if nb:
                    ev["encodings_with_bordering"] += 1
            if t.get("ok"):
                rates.append(t["taper_rate"])
                degs.append(t["taper_deg"])
            done += 1
            # once readings straddle the reference, no later cell can make
            # them unanimous again
            if rates and 0 < sum(r > required for r in rates) < len(rates):
                early = "straddled"
                break
            # once the cells left cannot carry coverage to the threshold
            if len(rates) + (total - done) < need:
                early = "coverage"
                break
        if early:
            break

    n = len(rates)
    out = {"encodings": total, "attempted": done, "readings": n,
           "evidence": ev,
           "qualities": list(QUALITIES), "work_px": list(WORK_PX),
           "required_rate": round(required, 4)}
    if early == "coverage":
        out["state"] = "CANNOT_MEASURE"
        out["why"] = (f"after {done} of {total} encodings only {n} had "
                      f"yielded a reading, so the remaining {total-done} "
                      f"could not bring this photograph to the {need} "
                      f"needed; the rest found no boundary in the "
                      f"regulated corridor")
        return out
    if early == "straddled":
        st = sum(r > required for r in rates)
        out.update({"taper_deg_min": round(min(degs), 2),
                    "taper_deg_max": round(max(degs), 2),
                    "agree_steeper": st})
        out["state"] = "INDETERMINATE"
        out["why"] = (f"{st} of the first {n} readings put the taper past "
                      f"the reference and {n-st} did not, on encodings of "
                      f"one photograph. The angle ranges {min(degs):.1f}-"
                      f"{max(degs):.1f}°, so this frame does not settle it")
        return out

    # Most of the grid has to produce a reading, not just three cells of
    # it. v10 asserted STEEPER_THAN_REFERENCE on F22 from 4 readings with
    # 5 cells silent, and called that unanimity. Five encodings of the
    # same photograph failing to find the marking is evidence about the
    # marking, not an absence of evidence.
    if n < math.ceil(2*total/3):
        out["state"] = "CANNOT_MEASURE"
        out["why"] = (f"only {n} of {total} encodings of this photograph "
                      f"yielded a reading; the rest found no boundary in "
                      f"the regulated corridor")
        return out

    steeper = sum(r > required for r in rates)
    spread = max(degs) - min(degs)
    med_deg = float(np.median(degs))
    out.update({"taper_deg_median": round(med_deg, 2),
                "taper_deg_min": round(min(degs), 2),
                "taper_deg_max": round(max(degs), 2),
                "taper_deg_spread": round(spread, 2),
                "rate_median": round(float(np.median(rates)), 4),
                "agree_steeper": steeper})

    if steeper not in (0, n):
        out["state"] = "INDETERMINATE"
        out["why"] = (f"{steeper} of {n} encodings of this same photograph "
                      f"put the taper past the reference and {n-steeper} "
                      f"did not. The angle ranges {min(degs):.1f}-"
                      f"{max(degs):.1f}°, so this frame does not settle it")
        return out

    # The magnitude is not reportable and the direction is. F03's readings
    # run 6.35 to 19.17 degrees, a three-fold range, so "the geometry suits
    # 22.5 km/h" - taken from the median - is a number the measurement
    # cannot support. But every one of those readings, the mildest
    # included, exceeds what the regulation requires. That the conclusion
    # does not depend on which reading you take is the thing worth saying.
    #
    # So the verdict is stated as a bound from the most favourable
    # reading, not as a point from the middle. A bound that holds across
    # the whole ensemble is a stronger claim than a median that holds
    # nowhere, and it stops the scatter being laundered into precision.
    required_deg = math.degrees(math.atan(required))
    out["required_deg"] = round(required_deg, 2)

    # A bound is only a bound on one quantity. The regulated corridor is
    # 1 to 20 degrees wide, so readings that scatter by more than that
    # width are not repeated measurements of one taper - they are
    # measurements of different things, and the mildest of them bounds
    # nothing. F01 asserted at 1.06 times required with its readings
    # spread over 44 degrees, which is the failure this catches.
    if spread >= CORRIDOR_WIDTH_DEG:
        out["state"] = "INDETERMINATE"
        out["why"] = (f"the {n} readings scatter over {spread:.1f}°, wider "
                      f"than the {CORRIDOR_WIDTH_DEG:.0f}° range a taper can "
                      f"occupy at all. They are not repeated readings of one "
                      f"boundary, so the mildest of them bounds nothing")
        return out

    if steeper == n:
        mildest = min(rates)
        out["state"] = "STEEPER_THAN_REFERENCE"
        out["bound_from"] = "mildest reading"
        out["taper_deg_bound"] = round(min(degs), 2)
        out["times_required_at_least"] = round(mildest/required, 2)
        out["equivalent_kmh_at_most"] = round(math.sqrt(155/mildest), 1)
        out["why"] = (f"all {n} readings exceed the reference, the mildest "
                      f"({min(degs):.1f}°) by {mildest/required:.1f} times. "
                      f"The readings scatter over {spread:.1f}° so no single "
                      f"value is reportable, but the direction does not "
                      f"depend on which one is taken")
    else:
        harshest = max(rates)
        out["state"] = "WITHIN_REFERENCE"
        out["bound_from"] = "harshest reading"
        out["taper_deg_bound"] = round(max(degs), 2)
        out["equivalent_kmh_at_least"] = round(math.sqrt(155/harshest), 1)
    return out


def _works_hoarding(image, roi):
    """A construction hoarding standing where the road used to be.

    Taiwan site hoarding is painted sheet steel in a saturated blue or
    green, which no part of a road surface, a kerb or a sky ever is. It is
    found as the largest saturated blob that reaches one side of the frame
    and stands beside the carriageway, and what is reported is how much of
    the frame's width it has taken at the height a vehicle travels at -
    the occupation, not the colour.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[:, :, 0].astype(np.int16), hsv[:, :, 1], hsv[:, :, 2]
    h, w = H.shape
    m = (((H >= 35) & (H <= 135)) & (S > 70) & (V > 45)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE,
                         cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
    n, lbl, st, _ = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, n):
        a = st[i, cv2.CC_STAT_AREA]
        if a < h * w * 0.01:
            continue
        x0, y0 = st[i, cv2.CC_STAT_LEFT], st[i, cv2.CC_STAT_TOP]
        bw, bh = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT]
        touches_left, touches_right = x0 <= 2, x0 + bw >= w - 2
        if not (touches_left or touches_right):
            continue          # vegetation and signage float in the frame
        if y0 + bh < h * 0.45:
            continue          # sky and distant hills sit high and stop there
        if bh < h * 0.10 or bw < w * 0.06:
            continue
        band = lbl[int(h*0.55):int(h*0.80)] == i
        reach = (band.sum(1).max() / w) if band.any() else bw / w
        if best is None or a > best["_a"]:
            best = {"_a": int(a), "side": "left" if touches_left else "right",
                    "px": [int(x0), int(y0), int(bw), int(bh)],
                    "width_frac": round(float(reach), 3),
                    "height_frac": round(float(bh) / h, 3),
                    "area_frac": round(float(a) / (h*w), 3),
                    "hue": int(np.median(H[lbl == i]))}
    if best:
        best.pop("_a")
    return best


# 表 4.2.7 直行車道偏移漸變: the ratios the story quotes (docs/evidence.md L19).
TABLE_4_2_7 = {20: 3.0, 30: 5.0, 40: 10.0, 50: 16.0, 60: 23.0, 70: 44.0, 80: 50.0, 90: 56.0}


def _taper_427(image, K, posted_kmh):
    """Chevron taper against 表 4.2.7, reported only if encodings agree."""
    core, probe = phone.encoding_probe(phone.taper_427, image, K,
                                       lambda o: o["taper_ratio"], rel_tol=0.10)
    need = TABLE_4_2_7.get(int(round(posted_kmh)))
    base = {"source": phone.SRC, "probe": probe, "need_ratio": need,
            "posted_kmh": posted_kmh}
    if not probe["stable"]:
        return {**base, "state": "CANNOT_MEASURE",
                "why": f"encodings disagree or refuse: {probe['why']}"
                       + ("" if core.get("ok") else f"; as received: {core.get('why')}")}
    ratio, spread = probe["median"], probe["spread"]
    base.update({"ratio": ratio, "spread": spread,
                 "taper_deg": core.get("taper_deg")})
    if need is None:
        return {**base, "state": "INDETERMINATE",
                "why": f"表 4.2.7 has no row for {posted_kmh:.0f} km/h"}
    if abs(ratio - need) <= spread:
        return {**base, "state": "INDETERMINATE",
                "why": f"{ratio}:1 is within the encoding spread {spread} of {need:.0f}:1"}
    return {**base, "state": "STEEPER_THAN_REFERENCE" if ratio < need else "WITHIN_REFERENCE",
            "why": None}


def _red_line_gap(image, K):
    """Intact red line to worn red line, ruler = the line's own 10 cm width."""
    core, probe = phone.encoding_probe(phone.redline_gap, image, K,
                                       lambda o: o["summary"]["median_m"], abs_tol=0.05)
    if not probe["stable"]:
        return {"state": "CANNOT_MEASURE", "probe": probe,
                "why": f"encodings disagree or refuse: {probe['why']}"
                       + ("" if core.get("ok") else f"; as received: {core.get('why')}")}
    vals = [r["value"] for r in probe["readings"] if r["value"] is not None]
    return {"state": "MEASURED", "gap_m": probe["median"],
            "min_m": round(min(vals), 3), "max_m": round(max(vals), 3),
            "probe": probe, "ruler": {"m": phone.RULER_M, "source": phone.RULER_SRC},
            "what_was_measured": core.get("what_was_measured")}


def assess(image, fov_deg: float, posted_kmh: float,
           lane_width_m: float | None = None) -> dict:
    """The set of things wrong with this road, each detected and cited."""
    h, w = image.shape[:2]
    roi = road_region(image)
    roi_frac = 0.0 if roi is None else float((roi > 0).mean())

    # Nothing is said about a frame that is not a photograph of a road.
    # Not "no findings" with a narrative attached - nothing.
    if roi is None or roi_frac < MIN_ROAD_FRAC:
        return {"scenario": [],
                "site_description_not_measured": [],
                "findings": [], "checked": [],
                "taper": {"state": "CANNOT_MEASURE",
                          "why": "not a road photograph", "readings": 0},
                "carriageway_found": False,
                "roi_frac": round(roi_frac, 4),
                "not_checked": [
                    f"every check: the road region covers {roi_frac*100:.1f}% "
                    f"of this frame and a road photograph gives at least "
                    f"{MIN_ROAD_FRAC*100:.0f}% (42 real frames: 55.6-60.0%, "
                    f"12 noise frames: 0.0%). Nothing here was measured."],
                "state": "NOT_A_ROAD_PHOTOGRAPH",
                "site_116_not_measured_from_this_photograph": SITE_116,
                "next_actions": next_actions(
                    {"state": "NOT_A_ROAD_PHOTOGRAPH",
                     "roi_frac": round(roi_frac, 4)})}

    segs, _ = _segments(image)
    findings, checked = [], []

    checked.append("taper")
    te = taper_ensemble(image, fov_deg, posted_kmh)
    if te["state"] == "STEEPER_THAN_REFERENCE":
        findings.append(Finding(
            "TAPER_TOO_STEEP",
            f"車道縮減的漸變段比 {posted_kmh:.0f} km/h 所需**至少**陡 "
            f"{te['times_required_at_least']:.1f} 倍，其幾何**至多**適合 "
            f"{te['equivalent_kmh_at_most']:.0f} km/h。"
            f"這是 {te['readings']} 個編碼版本中最寬容的那個給的下界；"
            f"讀數散布 {te['taper_deg_spread']:.1f}°，故不報單一數值",
            te,
            "L = W·V²/155, 施工之交通管制守則 p.9。本程式註記:該守則寫給國道，"
            "新北市的拘束鏈未規定漸變段長度"))

    # 表 4.2.7, the reference the story uses, alongside the ensemble
    # above (owner's decision 2026-09-23: run both). Pose-free: the angle
    # between the chevron's two edge pencils. Reported only if four
    # encodings of the same bytes agree - F40 read 11.9:1 as received and
    # 23.2:1 after one re-encode at quality 97.
    checked.append("taper_table_4_2_7")
    K = phone.K_from_fov(w, h, fov_deg)
    t427 = _taper_427(image, K, posted_kmh)
    if t427["state"] == "STEEPER_THAN_REFERENCE":
        findings.append(Finding(
            "TAPER_BELOW_TABLE_4_2_7",
            f"槽化線兩條邊界的夾角換算漸變率約 {t427['ratio']:.1f}:1"
            f"(四種編碼讀數相差 {t427['spread']:.1f});"
            f"表 4.2.7 在 {posted_kmh:.0f} km/h 要 {t427['need_ratio']:.0f}:1",
            t427,
            "市區道路及附屬工程設計規範:表 4.2.7 直行車道偏移漸變長度及縮減車道寬度漸變比例;"
            "偏移漸變長度不足 20 公尺,以 20 公尺計。"
            "本程式註記:哪個設計速率適用(施工前 50、施工期 30)要看核定文件,本程式不判"))

    checked.append("double_white")
    dw = _double_white(segs, image, roi)
    # `section` was computed and never read, so a double YELLOW line -
    # §165, 分向限制線, which separates opposing traffic - was reported as
    # §167 禁止變換車道, telling a rider they may not change lanes on the
    # strength of a line that means something else. The colour test exists
    # precisely to tell them apart; this is where it has to be used.
    if dw and dw.get("section") == "165":
        findings.append(Finding(
            "CENTRE_LINE_SOLID",
            "畫面內有雙黃實線，該處為分向限制線，不得跨越至對向",
            dw,
            # UNVERIFIED. This project holds no text of §165 - the words
            # 分向限制線 appear nowhere in docs/ - and the sentence that
            # used to stand here was written by this agent an hour after
            # recording E25, which is about fabricating a clause number.
            # The clause number is right; the words are not sourced, so
            # they are not asserted.
            "設置規則 §165。本專案未持有該條原文，未查證其內容;"
            "本程式僅指出:偵測到的是雙黃線而非雙白線，§167 不適用"))
    elif dw:
        findings.append(Finding(
            "NO_LANE_CHANGE",
            "畫面內有雙白實線，該處禁止變換車道，被擠壓的車輛無法向左閃避",
            dw,
            "設置規則 §167：禁止變換車道線，用以禁止行車變換車道；"
            "雙邊禁止變換車道線為雙白實線；設於交通特別繁雜而同向具有"
            "多車道之橋樑、隧道、彎道、坡道、接近交岔路口或其他認為有"
            "必要之路段。"
            "本程式解讀:橋樑引道的雙白線一旦開始就不能變換，"
            "選車道的決策點因此被推到它起點之前"))

    checked.append("kerbside_red")
    kr = _kerbside_red(image, roi)
    if kr:
        findings.append(Finding(
            "EDGE_NOT_CARRIAGEWAY",
            "右側有沿路的紅線。§169 允許它畫在緣石上，也允許無緣石時畫在路面上；"
            "它畫在哪一種面上、可行駛路面是否到此為止，本程式判不出來",
            kr,
            "設置規則 §169：以劃設於道路緣石正面或頂面為原則，"
            "無緣石之道路得標繪於路面上，距路面邊緣以三十公分為度"))

    checked.append("red_line_gap")
    rg = _red_line_gap(image, K)
    if rg["state"] == "MEASURED":
        findings.append(Finding(
            "TWO_RED_LINES",
            f"畫面裡有兩條紅線:溝帶上完整的新線,和它左側柏油上磨掉的舊線。"
            f"新線內緣到舊線中心約 {rg['gap_m']:.2f} m"
            f"(四種編碼讀數 {rg['min_m']:.2f}–{rg['max_m']:.2f} m)。"
            f"尺是新紅線自己的線寬",
            rg,
            "設置規則 §169:本標線為紅色實線,線寬一○公分。"
            "本程式註記:線寬拿來當尺,不需相機姿態;"
            "2026-09-23 以標準卡片實測新漆線寬 95–97 mm"))

    checked.append("works_hoarding")
    wh = _works_hoarding(image, roi)
    if wh and wh["width_frac"] >= 0.08:
        findings.append(Finding(
            "CARRIAGEWAY_OCCUPIED",
            f"{'左' if wh['side']=='left' else '右'}側有施工圍籬，"
            f"在行車高度佔去畫面寬度的 {wh['width_frac']*100:.0f}%。"
            f"被圍走的那一側原本是可行駛路面，車流被擠到剩下的寬度裡",
            wh,
            # The string here used to read 「佔用車道施工應維持必要車道數
            # 與寬度，並設置漸變段導引車流」, attributed to this document.
            # None of it is in the document. Checked 2026-09-22 against
            # docs/source-ntpc-excavation-6.0.txt: 必要車道數 0 hits,
            # 漸變段 0, 導引車流 0, 佔用車道 0. Fabricated clause text,
            # under a government document's name, in the delivery
            # function. E36. What the document actually says is below,
            # verbatim from line 96, and it is a better basis than the
            # invention because it names things a photograph can show.
            "新北市道路挖掘作業審查原則：施工場所須設置施工告示牌"
            "（附貼路證影本）、交通錐、警示燈，並於施工位置前適當距離"
            "之路段，設置車道縮減警示並派員指揮交通，引導車輛依指示通行。"
            "（本程式偵測到圍籬的存在，未查證告示牌、警示燈或車道縮減"
            "警示是否設置。）"))

    checked.append("surface")
    # runs=1: one seeded draw. Deterministic for the same bytes, which
    # is what this project claims, but the spread across seeds is a
    # property of the clustering and is NOT measured here - see the
    # not_checked entry below and G25.
    st, st_stable = surface_types_stable(image, roi, runs=1)
    if st and st > 2:
        findings.append(Finding(
            "SURFACE_IN_PIECES",
            f"行車道內可分辨出 {st} 種不同鋪面，代表存在新舊路面銜接處",
            {"surface_types": st,
             "note": "此為鋪面種類，非高低差。高低差需 3 米直規量測"},
            "新北市道路挖掘作業審查原則 6.0:「新舊路面銜接處與原有路面之"
            "高低差，以 3 米直規量取單點高低差不得超過正負 0.6 公分」。"
            "本程式數的是鋪面種類,未量高低差"))

    checked.append("lane_width")
    if lane_width_m is not None:
        need_car = CAR_M + CLEARANCE_M + MOTO_M
        need_heavy = HEAVY_M + CLEARANCE_M + MOTO_M
        if lane_width_m < need_heavy:
            findings.append(Finding(
                "LANE_TOO_NARROW",
                f"車道寬 {lane_width_m:.2f} m。汽機車並行需 {need_car:.2f} m"
                f"（小客車）或 {need_heavy:.2f} m（大型車），"
                f"{'兩者皆不足' if lane_width_m < need_car else '大型車旁不足'}",
                {"lane_width_m": lane_width_m, "need_car_m": round(need_car, 2),
                 "need_heavy_m": round(need_heavy, 2)},
                "道路交通安全規則 §101:超車時應「於前車左側保持半公尺以上之間隔超過」"))

    scenario, unmeasured = _scenario(findings, posted_kmh, image_w=w)
    out = {"scenario": scenario,
            "site_description_not_measured": unmeasured,
            "findings": [f.as_dict() for f in findings],
            "checked": checked,
            "taper": te,
            "taper_table_4_2_7": t427,
            "red_line_gap": rg,
            "site_116_not_measured_from_this_photograph": SITE_116,
            "not_checked": ([] if te["state"] == "STEEPER_THAN_REFERENCE"
                            else [f"taper: {te['state']} — "
                                  f"{te.get('why', '未超過參考值')}"]) +
                           ([] if lane_width_m is not None
                            else ["lane_width: 需提供車道寬，照片無比例尺"]) +
                           ([] if st_stable is not None else
                            ["surface: 種類數是固定亂數種子下的單次分群。"
                             "同樣的位元組會得到同樣的數,但「換一個種子會不會"
                             "得到別的數」本程式沒有量 —— 未定種子時 F18 曾在"
                             "同一個 process 內給出 4,4,5,5,4,5,4,4。"
                             "跨種子散布見 G25,尚未量測"]) +
                           ([] if t427["state"] not in ("CANNOT_MEASURE",) else
                            [f"taper_table_4_2_7: {t427['why']}"]) +
                           ([] if rg["state"] == "MEASURED" else
                            [f"red_line_gap: {rg['why']}"]) +
                           ["grated_cover: 現場有水溝蓋，但週期性條紋偵測器"
                            "在三張圖各誤判為槽化線、補綻、塗銷痕跡，已移除，"
                            "不列為已偵測項目"],
            "segments": len(segs),
            # bool(), because `.any()` returns numpy.bool_ and that is not
            # JSON-serialisable. Introduced by the G01 commit and it made
            # every real photograph a 500 with no body: `json.dumps` in
            # aws/handler.py sits OUTSIDE the try that wraps assess(). E40.
            "carriageway_found": bool(roi is not None and (roi > 0).any()),
            "summary": (f"這條路在這張照片裡有 {len(findings)} 項問題"
                        if findings else
                        "這張照片裡沒有偵測到可判定的問題")}
    # The image result drives what to do next, which is the Agentic
    # Vision criterion and the owner's 「系統要做的是提示」 - the same
    # requirement in two languages. Attached here rather than left for
    # a caller to remember, because `route.py` was built for this
    # criterion, imported by nothing, and sat unused for two days.
    out["next_actions"] = next_actions(out)
    return out
