#!/usr/bin/env python3
"""
make_ascii.py — turn a prepped photo into the ASCII portrait on the left of the card.

    python prep_photo.py selfie.png --crop X1 Y1 X2 Y2 -o prepped.png
    python make_ascii.py prepped.png

It builds the portrait from four layers instead of raw brightness, which is what
makes a face actually readable at 46x34 characters:

    silhouette  the outline of you against the knocked-out background
    edges       CLAHE + Canny, so the eye, nose, lips and jaw get drawn
    skin        shaded across a light band, so the face stays open
    dark mass   hair and clothing, rendered dense

Writes ascii_art.txt, which today.py reads.
"""

import argparse
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    raise SystemExit("this needs opencv: pip install opencv-python-headless")

RAMP = " .`',:;i!|+*%&8@#"     # sparsest -> densest
CHAR_ASPECT = 0.5              # mono glyphs are ~2x taller than wide


def build(path, cols, rows, a):
    bgr = cv2.cvtColor(np.array(Image.open(path).convert("RGB")), cv2.COLOR_RGB2BGR)

    h, w = bgr.shape[:2]
    target = (cols * CHAR_ASPECT) / rows
    if w / h > target:
        nw = int(h * target)
        bgr = bgr[:, (w - nw) // 2:(w - nw) // 2 + nw]
    else:
        bgr = bgr[:int(w / target)]

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    bg = gray >= 245
    sub = ~bg

    # ── skin vs. dark mass ───────────────────────────────────────────────
    ycc = cv2.cvtColor(cv2.bilateralFilter(bgr, 9, 60, 60), cv2.COLOR_BGR2YCrCb)
    Y, Cr, Cb = ycc[..., 0], ycc[..., 1], ycc[..., 2]
    skin = (Cr >= 133) & (Cr <= 182) & (Cb >= 76) & (Cb <= 128) & (Y > 60) & sub
    skin = cv2.morphologyEx(skin.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    skin = cv2.morphologyEx(skin, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8)).astype(bool)

    dens = np.zeros(gray.shape, np.float32)
    if skin.any():
        yv = Y.astype(np.float32)
        lo, hi = np.percentile(yv[skin], 4), np.percentile(yv[skin], 96)
        norm = np.clip((yv - lo) / max(hi - lo, 1), 0, 1)
        dens[skin] = a.skin_hi - (a.skin_hi - a.skin_lo) * norm[skin]
    dens[sub & ~skin] = a.dark

    # ── feature edges ────────────────────────────────────────────────────
    smooth = cv2.cvtColor(cv2.bilateralFilter(bgr, 11, 70, 70), cv2.COLOR_BGR2GRAY)
    boosted = cv2.createCLAHE(clipLimit=a.clahe, tileGridSize=(10, 10)).apply(smooth)
    edges = cv2.Canny(cv2.GaussianBlur(boosted, (0, 0), 1.6), a.canny_lo, a.canny_hi)
    edges[bg] = 0
    edges = cv2.GaussianBlur(
        cv2.dilate(edges, np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 3)

    # ── silhouette ───────────────────────────────────────────────────────
    sil = cv2.morphologyEx(sub.astype(np.uint8) * 255, cv2.MORPH_GRADIENT,
                           np.ones((9, 9), np.uint8))
    sil = cv2.GaussianBlur(sil.astype(np.float32), (0, 0), 3)

    def down(x, weight=1.0):
        d = cv2.resize(x, (cols, rows), interpolation=cv2.INTER_AREA)
        return np.clip(d / max(d.max(), 1e-6), 0, 1) * weight

    v = np.clip(np.maximum.reduce([
        cv2.resize(dens, (cols, rows), interpolation=cv2.INTER_AREA),
        down(edges, a.edge),
        down(sil, a.silhouette),
    ]), 0, 1)

    # dithered dissolve at the bottom so the shoulders don't end in a hard slab
    if a.fade:
        rng = np.random.default_rng(11)
        for k in range(a.fade):
            r = rows - 1 - k
            keep = (k + 0.5) / (a.fade + 0.5)
            v[r] *= keep
            v[r] *= (rng.random(cols) < keep + 0.25)

    lines = []
    for r in range(rows):
        s = ""
        for c in range(cols):
            n = float(v[r, c])
            s += " " if n < a.cutoff else RAMP[
                min(int((n - a.cutoff) / (1 - a.cutoff) * len(RAMP)), len(RAMP) - 1)]
        lines.append(s.rstrip())
    return lines


def main():
    p = argparse.ArgumentParser()
    p.add_argument("image")
    p.add_argument("-o", "--out", default="ascii_art.txt")
    p.add_argument("--cols", type=int, default=46)
    p.add_argument("--rows", type=int, default=34)
    p.add_argument("--skin-lo", type=float, default=0.11, help="density of lit skin")
    p.add_argument("--skin-hi", type=float, default=0.44, help="density of shadowed skin")
    p.add_argument("--dark", type=float, default=0.80, help="density of hair/clothing")
    p.add_argument("--edge", type=float, default=1.00)
    p.add_argument("--silhouette", type=float, default=0.95)
    p.add_argument("--clahe", type=float, default=3.0)
    p.add_argument("--canny-lo", type=int, default=16)
    p.add_argument("--canny-hi", type=int, default=54)
    p.add_argument("--cutoff", type=float, default=0.055)
    p.add_argument("--fade", type=int, default=5, help="rows to dissolve at the bottom")
    a = p.parse_args()

    lines = build(a.image, a.cols, a.rows, a)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\n-> wrote {a.out} ({a.cols}x{a.rows})")


if __name__ == "__main__":
    main()
