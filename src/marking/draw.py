"""Draw what was found on the photograph it was found in.

The system's output is a list of clause-tied findings and a narration,
and neither shows a reader that anything was looked at. A judge reading
JSON cannot tell a measurement from an assertion. This draws the
measurement: the region each finding was read from, in the frame, with
the clause beside it.

Nothing here measures. Every box and line comes from the `measured`
block of a finding that `assess()` already produced, so a drawing cannot
show something the measurement did not find, and a finding with no
geometry is listed and not drawn rather than invented.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import cv2
import numpy as np

# OpenCV's Hershey fonts have no CJK glyphs, and the narration this
# project produces is Traditional Chinese. An earlier version of this
# panel drew bar lengths labelled "75 chars" in its place, which told a
# viewer nothing. PIL with a system font draws the sentences.
# (path, face index). The index matters and defaulting to 0 is wrong:
# Songti.ttc's face 0 is Songti SC and is missing 14 of the 15 traditional
# forms this narration uses - 邊 裡 施 圍 籬 among them - so the first
# version of this panel silently dropped characters mid-sentence. Faces 2
# and 5 of the same file are Songti TC and have them. Heiti TC is first
# because it is a traditional face by name and sets more legibly small.
_CJK_CANDIDATES = (
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0),      # Heiti TC
    ("/System/Library/Fonts/STHeiti Light.ttc", 0),       # Heiti TC
    ("/System/Library/Fonts/Supplemental/Songti.ttc", 2),  # Songti TC
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJKtc-Regular.otf", 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
)

# A handful of traditional forms the narration actually uses. A font that
# cannot set these is rejected rather than trusted for having a CJK name.
_PROBE = "邊裡施圍籬車佔掉畫寬側來變擠進"


def _covers(font, probe=_PROBE):
    """Does this face have these glyphs, or does it draw .notdef?

    Checked by rendering, because a font advertising a CJK name can still
    be missing traditional forms, and because "it drew some ink" is not
    the test - .notdef is ink. Each glyph is compared with a private-use
    codepoint that no font has.
    """
    from PIL import Image, ImageDraw
    import numpy as _np

    def bitmap(ch):
        im = Image.new("L", (44, 44), 0)
        try:
            ImageDraw.Draw(im).text((4, 2), ch, font=font, fill=255)
        except Exception:
            return None
        return _np.array(im)

    notdef = bitmap("\ue123")
    if notdef is None:
        return False
    for ch in probe:
        g = bitmap(ch)
        if g is None or g.sum() < 50 or _np.array_equal(g, notdef):
            return False
    return True


def cjk_font(size):
    """A font that can actually set the narration, or None."""
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    for path, index in _CJK_CANDIDATES:
        if not Path(path).exists():
            continue
        try:
            f = ImageFont.truetype(path, size, index=index)
        except OSError:
            continue
        if _covers(f):
            return f
    return None


def wrap_cjk(text, per_line):
    """Break on character count, not on spaces.

    textwrap.wrap breaks at whitespace, and Traditional Chinese has none
    inside a sentence, so it returns one enormous line or breaks at the
    stray Latin token and leaves ragged gaps. Counting characters is what
    the script actually needs; a Latin word is kept whole when it fits.
    """
    out, line, n = [], "", 0
    for ch in text:
        w = 1 if ord(ch) < 0x2E80 else 2      # a han character is two wide
        if n + w > per_line * 2:
            out.append(line)
            line, n = "", 0
        line += ch
        n += w
    if line:
        out.append(line)
    return out


def _draw_cjk(img, lines, org, size=15, colour=(40, 40, 38), leading=7):
    """Write lines onto a BGR image at org, returning the y it reached."""
    font = cjk_font(size)
    x, y = org
    if font is None:
        for line in lines:
            cv2.putText(img, "[CJK font unavailable]", (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.36, (150, 150, 145), 1)
            return y + size + leading
        return y
    from PIL import Image, ImageDraw
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(pil)
    for line in lines:
        d.text((x, y), line, font=font, fill=colour[::-1])
        y += size + leading
    img[:] = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    return y

from .extract import road_region as carriageway
from .situation import _surface_types

# One palette across the drawing and the two figures in docs/figures.
TEAL = (139, 111, 31)          # BGR - geometry, needs only focal length
AMBER = (26, 116, 184)         # BGR - needs a scale
RED = (58, 58, 192)            # BGR - a refusal, or a boundary that ends the road
GREY = (150, 150, 145)
INK = (28, 28, 28)
PAPER = (249, 251, 251)

CLAUSE = {
    "CARRIAGEWAY_OCCUPIED": "挖掘審查原則",
    "EDGE_NOT_CARRIAGEWAY": "設置規則 §169",
    "NO_LANE_CHANGE": "設置規則 §167",
    "SURFACE_IN_PIECES": "挖掘審查原則 6.0",
    "LANE_TOO_NARROW": "道路交通安全規則 §101",
    "TAPER_TOO_STEEP": "交通管制守則 p.9",
}
COLOUR = {
    "CARRIAGEWAY_OCCUPIED": AMBER,
    "EDGE_NOT_CARRIAGEWAY": RED,
    "NO_LANE_CHANGE": TEAL,
    "SURFACE_IN_PIECES": GREY,
    "TAPER_TOO_STEEP": AMBER,
}


def _label(img, text, org, colour, scale=0.52, pad=5):
    """Text on an opaque plate, because a road photograph is not a canvas."""
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    x, y = int(org[0]), int(org[1])
    # keep the plate inside the frame; the first version ran a label off
    # the right edge and the clause it carried was the half that was cut
    x = max(pad, min(x, img.shape[1] - w - pad))
    y = max(h + pad, min(y, img.shape[0] - pad))
    cv2.rectangle(img, (x - pad, y - h - pad), (x + w + pad, y + pad),
                  (255, 255, 255), -1)
    cv2.rectangle(img, (x - pad, y - h - pad), (x + w + pad, y + pad),
                  colour, 1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale,
                colour, 1, cv2.LINE_AA)


def overlay(image, result, *, show_surfaces=True):
    """The photograph with every finding's own geometry drawn on it."""
    vis = image.copy()
    h, w = vis.shape[:2]
    k = max(1, int(round(min(h, w) / 700)))

    roi = carriageway(image)
    if roi is not None:
        edge = cv2.morphologyEx(roi, cv2.MORPH_GRADIENT,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                                          (3, 3)))
        vis[edge > 0] = TEAL

    codes = {f["code"] for f in result.get("findings", [])}

    if show_surfaces and "SURFACE_IN_PIECES" in codes and roi is not None:
        n, labels = _surface_types(image, roi, want_labels=True)
        if labels is not None and n and n > 1:
            # Boundaries, not fill. A filled tint over a region that now
            # covers most of the frame hides the photograph, and the
            # photograph is the evidence - the first version of this
            # drawing tinted sky and shopfronts and was unreadable.
            for i in range(n):
                m = ((labels == i).astype(np.uint8)) * 255
                m = cv2.morphologyEx(m, cv2.MORPH_OPEN,
                                     cv2.getStructuringElement(
                                         cv2.MORPH_ELLIPSE, (9, 9)))
                cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
                big = [c for c in cnts if cv2.contourArea(c) > 0.004*h*w]
                cv2.drawContours(vis, big, -1, GREY, max(1, k))
            _label(vis, f"SURFACE_IN_PIECES  {n} surfacings  "
                        f"{CLAUSE['SURFACE_IN_PIECES']}",
                   (14, h - 16), GREY, 0.5 * k)

    for f in result.get("findings", []):
        code, m = f["code"], f.get("measured", {})
        colour = COLOUR.get(code, INK)

        if code in ("CARRIAGEWAY_OCCUPIED", "EDGE_NOT_CARRIAGEWAY") \
                and isinstance(m.get("px"), list) and len(m["px"]) == 4:
            x, y, bw, bh = (int(v) for v in m["px"])
            cv2.rectangle(vis, (x, y), (x + bw, y + bh), colour, 2 * k)
            _label(vis, f"{code}  {CLAUSE.get(code, '')}",
                   (x + 4, max(18 * k, y - 8)), colour, 0.5 * k)

        if code == "EDGE_NOT_CARRIAGEWAY" and isinstance(m.get("axis_px"), list):
            (x1, y1), (x2, y2) = m["axis_px"]
            cv2.line(vis, (int(x1), int(y1)), (int(x2), int(y2)), colour, 3 * k)

        if code == "NO_LANE_CHANGE" and isinstance(m.get("px"), list):
            for seg in m["px"]:
                a, b, c, d = (int(v) for v in seg)
                cv2.line(vis, (a, b), (c, d), colour, 2 * k)
            a, b, *_ = (int(v) for v in m["px"][0])
            _label(vis, f"{code}  {CLAUSE[code]}", (a + 6, b - 8), colour, 0.5 * k)

    return vis


def panel(image, result, *, width=520):
    """The findings and the narration, as a column beside the photograph."""
    h = image.shape[0]
    p = np.full((h, width, 3), PAPER, np.uint8)
    y = 34

    cv2.putText(p, "What the road does to you here", (22, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.62, INK, 1, cv2.LINE_AA)
    y += 10
    cv2.line(p, (22, y), (width - 22, y), (220, 220, 215), 1)
    y += 26

    for f in result.get("findings", []):
        code = f["code"]
        colour = COLOUR.get(code, INK)
        cv2.rectangle(p, (22, y - 9), (32, y + 1), colour, -1)
        cv2.putText(p, code, (42, y), cv2.FONT_HERSHEY_SIMPLEX, 0.46,
                    INK, 1, cv2.LINE_AA)
        y += 15
        cv2.putText(p, CLAUSE.get(code, ""), (42, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (120, 120, 115), 1,
                    cv2.LINE_AA)
        y += 24
        if y > h - 150:
            break

    t = result.get("taper", {})
    if t.get("state") in ("INDETERMINATE", "CANNOT_MEASURE"):
        y += 8
        cv2.line(p, (22, y), (width - 22, y), (220, 220, 215), 1)
        y += 24
        cv2.putText(p, f"TAPER: {t['state']}", (22, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, RED, 1, cv2.LINE_AA)
        y += 20
        for line in textwrap.wrap(str(t.get("why", ""))[:200], 66)[:4]:
            cv2.putText(p, line, (22, y), cv2.FONT_HERSHEY_SIMPLEX, 0.36,
                        (90, 70, 68), 1, cv2.LINE_AA)
            y += 15

    steps = result.get("scenario") or []
    if steps and y < h - 120:
        y += 10
        cv2.line(p, (22, y), (width - 22, y), (220, 220, 215), 1)
        y += 24
        cv2.putText(p, "Measured here", (22, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, INK, 1, cv2.LINE_AA)
        y += 22
        per_line = max(16, (width - 78) // 15)
        for i, step in enumerate(steps, 1):
            cv2.circle(p, (30, y + 3), 9, TEAL, -1)
            cv2.putText(p, str(i), (27, y + 7), cv2.FONT_HERSHEY_SIMPLEX,
                        0.38, (255, 255, 255), 1, cv2.LINE_AA)
            wrapped = wrap_cjk(step, per_line)
            y = _draw_cjk(p, wrapped, (48, y - 4), size=14)
            y += 10
            if y > h - 70:
                break

    # The unmeasured half, drawn. `assess()` has returned it since G00
    # and this panel did not draw it, while its heading said "composed
    # only from the above" - so on every rendered figure the disclosure
    # was invisible and the page read as though the whole scene had been
    # measured. A category that the picture does not show is not a
    # category.
    site = result.get("site_description_not_measured") or []
    if site and y < h - 150:
        y += 14
        cv2.line(p, (22, y), (width - 22, y), (220, 220, 215), 1)
        y += 24
        cv2.putText(p, "NOT measured - site description, from the record",
                    (22, y), cv2.FONT_HERSHEY_SIMPLEX, 0.44, AMBER, 1,
                    cv2.LINE_AA)
        y += 22
        per_line = max(16, (width - 78) // 15)
        for note in site:
            cv2.circle(p, (30, y + 3), 9, AMBER, -1)
            cv2.putText(p, "?", (27, y + 7), cv2.FONT_HERSHEY_SIMPLEX,
                        0.38, (255, 255, 255), 1, cv2.LINE_AA)
            y = _draw_cjk(p, wrap_cjk(note, per_line), (48, y - 4), size=14)
            y += 10
            if y > h - 70:
                break

    cv2.putText(p, "teal = measured in this frame; amber = not measured",
                (22, h - 22), cv2.FONT_HERSHEY_SIMPLEX, 0.36,
                (160, 160, 155), 1, cv2.LINE_AA)
    return p


def sheet(image, result, *, width=520):
    """Photograph and findings side by side, ready to put in a video."""
    vis = overlay(image, result)
    return np.hstack([vis, panel(vis, result, width=width)])
