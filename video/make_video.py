#!/usr/bin/env python3
"""Build the submission video: one slide per script row, voiceover, subtitles burned in.

Inputs: video/script_en.md (subtitle text, verbatim), video/audio/NN.wav (make_voice.py).
Each slide lasts as long as its voiceover plus a short pause; its subtitle is split into
chunks of at most two lines, and each chunk is shown for a share of the slide's time
proportional to its length. This ffmpeg build has no subtitles/drawtext filter, so the
subtitles are drawn into the frames with PIL. A matching .srt is written as well.

    /opt/anaconda3/bin/python3 -B video/make_video.py

Writes video/out/road116.mp4 and video/out/road116.srt.
"""
import json, re, subprocess, textwrap, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "out"; FR = OUT / "frames"
W, H = 1920, 1080
PAD = 0.6                      # silence after each slide's voiceover, seconds
FONT = "/System/Library/Fonts/Helvetica.ttc"
BG = (251, 251, 250); INK = (27, 27, 27); MUTED = (94, 94, 90); TEAL = (15, 123, 123); AMBER = (192, 122, 30)


def font(size, bold=False):
    return ImageFont.truetype(FONT, size, index=1 if bold else 0)


def rows():
    out = []
    for line in (HERE / "script_en.md").read_text().splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|[^|]*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", line)
        if m:
            out.append((int(m.group(1)), re.sub(r"\s*\(`[^`]*`\)", "", m.group(2)), m.group(3)))
    return out


def fit(img, box):
    x0, y0, x1, y1 = box; bw, bh = x1 - x0, y1 - y0
    s = min(bw / img.width, bh / img.height)
    im = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)
    return im, (x0 + (bw - im.width) // 2, y0 + (bh - im.height) // 2)


def text_card(lines, title=None):
    c = Image.new("RGB", (W, H - 260), BG); d = ImageDraw.Draw(c); y = 70
    if title:
        d.text((120, y), title, font=font(64, True), fill=INK); y += 120
    for txt, style in lines:
        f, col = {"big": (font(52, True), INK), "teal": (font(44, True), TEAL), "amber": (font(44, True), AMBER),
                  "body": (font(38), INK), "muted": (font(32), MUTED)}[style]
        for ln in textwrap.wrap(txt, 84 if style in ("body", "muted") else 66):
            d.text((120, y), ln, font=f, fill=col); y += int(f.size * 1.35)
        y += 18
    return c


# English glosses of the response's Chinese action texts (shown instead of the Chinese,
# which the monospace font cannot draw). The action types are the response's own.
GLOSS = {"向交通局申請該路段的交通維持計畫": "Traffic Dept, traffic plan",
         "查該路段的道路挖掘許可": "dig permit (public record)",
         "向交通局申請該路段標線改繪核定函及劃設圖說": "Traffic Dept, marking plans",
         "向區公所申請側溝工程竣工圖說與蓋板檢驗報告": "District Office, drain records",
         "漸變段長度:這張照片答不了": "taper length",
         "紅線外移以外的公分數:這張照片答不了": "other distances",
         "水溝蓋:本程式辨識不到": "grates (online)"}


def api_card():
    b = json.loads((HERE / "assets/api_F31_local_v12.json").read_text())
    rg = b["red_line_gap"]; t = b["taper_table_4_2_7"]
    excerpt = {
        "findings": [f["code"] for f in b["findings"]],
        "red_line_gap": {"state": rg["state"], "gap_m": rg["gap_m"], "min_m": rg["min_m"], "max_m": rg["max_m"]},
        "taper_table_4_2_7": {"state": t["state"], "why": t["why"][:70] + "..."},
        "next_actions": [f'{a["action"]}: {GLOSS.get(a["what"], "")}' for a in b["next_actions"]],
    }
    c = Image.new("RGB", (W, H - 260), (30, 30, 30)); d = ImageDraw.Draw(c)
    d.text((80, 40), "POST /  (photo F31, 30 km/h)  ->  200", font=font(34, True), fill=(230, 230, 230))
    d.text((1000, 46), "Local container test, image v12", font=font(26), fill=(190, 190, 190))
    y = 100
    for ln in json.dumps(excerpt, ensure_ascii=False, indent=1).splitlines():
        d.text((80, y), ln, font=ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 24), fill=(170, 220, 170)); y += 29
    return c


def visual(n):
    img = lambda p: Image.open(ROOT / p).convert("RGB")
    if n == 1:
        c = Image.new("RGB", (W, H - 260), (20, 20, 20))
        ph = img("evidence/field-2026-09-23/IMG_20260923_063437.jpg")          # cover-fill, centred
        sc = max(W / ph.width, (H - 260) / ph.height); ph = ph.resize((int(ph.width * sc), int(ph.height * sc)), Image.LANCZOS)
        top = int(ph.height * 0.42 - (H - 260) / 2); ph = ph.crop((0, top, W, top + H - 260))
        ph = Image.eval(ph, lambda v: int(v * 0.45)); c.paste(ph, (0, 0)); d = ImageDraw.Draw(c)
        d.text((120, 300), "Seven drain grates in 85 metres", font=font(88, True), fill=(255, 255, 255))
        d.text((120, 420), "County Road 116, Shulin, New Taipei", font=font(48), fill=(230, 230, 230))
        d.text((120, 490), "OpenCV 5 on AWS Lambda", font=font(40), fill=(200, 200, 200))
        return c
    if n == 3:
        return text_card([("Solo: one rider, one smartphone.", "big"),
                          ("Not here to say who broke the rules.", "body"),
                          ("Here to turn what a rider feels into numbers anyone can check.", "teal")], "Team")
    if n == 6:
        return text_card([("§169  A red line belongs on the kerb.", "body"),
                          ("§183  A red line marks the outer edge of the road.", "body"),
                          ("Urban Road Standard §2  A lane is whatever the markings enclose.", "body"),
                          ("So the new line puts the drain strip inside the road.", "teal"),
                          ("Quoted word for word from Taiwan's national law database. The last line is my reading, not the law's text.", "muted")],
                         "What the rules say")
    if n == 8:
        c = Image.new("RGB", (W, H - 260), BG)
        both = img("isolation/taper-recheck/consensus_f17_f40.jpg")          # right half is F40; left is F17 (refused)
        im, pos = fit(both.crop((both.width // 2, 0, both.width, both.height)), (40, 30, 1180, H - 290)); c.paste(im, pos)
        d = ImageDraw.Draw(c); x = 1240
        d.text((x, 90), "Lane shift at 30 km/h", font=font(40, True), fill=INK)
        d.text((x, 150), "Rule: at least 5 to 1", font=font(38), fill=MUTED)
        d.text((x, 260), "Before repainting", font=font(38, True), fill=AMBER)
        d.text((x, 310), "about 4 to 5 to 1", font=font(52, True), fill=AMBER)
        d.text((x, 420), "After", font=font(38, True), fill=TEAL)
        d.text((x, 470), "about 12 to 1", font=font(52, True), fill=TEAL)
        d.text((x, 600), "Left: F40 today, both edges", font=font(26), fill=MUTED)
        d.text((x, 636), "confirmed by two tools", font=font(26), fill=MUTED)
        return c
    if n == 11:
        return api_card()
    if n == 12:
        return text_card([("Left: a solid line you can't cross, then about 3.4 s to merge at 30 km/h.", "body"),
                          ("Right: the red line painted over seven drain grates and open drain holes.", "body"),
                          ("Ahead: the lane narrowing as the island widens.", "body"),
                          ("Winter mornings, 7-8 am: the low sun in your eyes.", "body"),
                          ("Each one sits at the limit. All of them land on the same 85 metres.", "teal")], "The stack")
    if n == 13:
        return text_card([("New Taipei Traffic Department: the approved marking plans for this stretch.", "body"),
                          ("Metro construction office: the traffic plan for works permit 1140874494.", "body"),
                          ("Shulin District Office: the drain drawings and the cover test reports.", "body"),
                          ("github.com/jiarong0423/jiarong0423-road-marking-conformity", "muted")], "Next: request the documents")
    path = {2: "video/assets/p22_en.jpg", 4: "docs/figures/schematic-85m.png", 5: "video/assets/grates_en.jpg",
            7: "video/assets/card_crop.jpg", 9: "isolation/taper-recheck/f40_picks.jpg", 10: "docs/figures/architecture.png"}[n]
    src = img(path)
    # the narration covers only part of these two figures; show that part large enough to read
    crop = {4: (0.07, 0.10, 0.93, 0.73),      # schematic: callouts, road, grates, chainage
            10: (0.0, 0.0, 1.0, 0.57)}.get(n)  # architecture: the ONLINE block
    if crop:
        x0, y0, x1, y1 = crop; src = src.crop((int(x0 * src.width), int(y0 * src.height), int(x1 * src.width), int(y1 * src.height)))
    c = Image.new("RGB", (W, H - 260), BG); im, pos = fit(src, (30, 20, W - 30, H - 280)); c.paste(im, pos)
    return c


def chunks(text, width=62):
    """Whole sentences, packed into chunks of at most two subtitle lines."""
    sents = re.split(r"(?<=[.?!])\s+", text.strip())
    out, cur = [], ""
    for sn in sents:
        cand = (cur + " " + sn).strip()
        if len(textwrap.wrap(cand, width)) <= 2:
            cur = cand; continue
        if cur: out.append(cur)
        if len(textwrap.wrap(sn, width)) <= 2:
            cur = sn
        else:                                  # one long sentence: split at clause boundaries (, : ;)
            parts = re.split(r"(?<=[,:;])\s+", sn); cur = ""
            for pt in parts:
                cand2 = (cur + " " + pt).strip()
                if len(textwrap.wrap(cand2, width)) <= 2:
                    cur = cand2
                else:
                    if cur: out.append(cur)
                    cur = pt
    if cur: out.append(cur)
    return out


def frame(vis, heading, sub):
    f = Image.new("RGB", (W, H), BG); f.paste(vis, (0, 60))
    d = ImageDraw.Draw(f)
    d.rectangle((0, 0, W, 60), fill=(240, 240, 236)); d.text((30, 14), heading, font=font(28, True), fill=MUTED)
    d.rectangle((0, H - 200, W, H), fill=(18, 18, 18))
    y = H - 175
    for ln in textwrap.wrap(sub, 62):
        tw = d.textlength(ln, font=font(46))
        d.text(((W - tw) / 2, y), ln, font=font(46), fill=(255, 255, 255)); y += 62
    return f


def ts(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def main():
    FR.mkdir(parents=True, exist_ok=True)
    concat, srt, audio, t = [], [], [], 0.0
    for n, heading, text in rows():
        wav = HERE / "audio" / f"{n:02d}.wav"
        with wave.open(str(wav)) as w:
            dur = w.getnframes() / w.getframerate()
        vis = visual(n); cs = chunks(text); total = dur + PAD; L = sum(len(c) for c in cs)
        for i, c in enumerate(cs):
            share = total * len(c) / L
            p = FR / f"{n:02d}_{i:02d}.png"; frame(vis, f"{n}/13  {heading}", c).save(p)
            concat.append(f"file '{p}'\nduration {share:.3f}")
            srt.append(f"{len(srt) + 1}\n{ts(t)} --> {ts(t + share)}\n{c}\n"); t += share
        audio.append((wav, PAD))
        print(f"slide {n:2d}: {dur:5.1f} s voice, {len(cs)} subtitle chunks")
    concat.append(f"file '{FR / sorted(p.name for p in FR.glob('13_*.png'))[-1]}'")
    (OUT / "frames.txt").write_text("\n".join(concat) + "\n")
    (OUT / "road116.srt").write_text("\n".join(srt))
    # voice track: each wav followed by PAD seconds of silence
    parts = []
    for i, (wav, pad) in enumerate(audio):
        parts += ["-i", str(wav)]
    fc = "".join(f"[{i}:a]apad=pad_dur={PAD}[a{i}];" for i in range(len(audio)))
    fc += "".join(f"[a{i}]" for i in range(len(audio))) + f"concat=n={len(audio)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *parts, "-filter_complex", fc, "-map", "[out]",
                    "-ar", "48000", str(OUT / "voice.wav")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "frames.txt"),
                    "-i", str(OUT / "voice.wav"), "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", str(OUT / "road116.mp4")], check=True)
    print(f"total {t:.1f} s -> {OUT / 'road116.mp4'}")


if __name__ == "__main__":
    main()
