#!/usr/bin/env python3
"""
prep_photo.py — clean a selfie for ASCII conversion:
removes flat background, patches out earbuds / phone, crops to head+shoulders.
Writes prepped.png (white background, subject retained).
"""
import argparse
import cv2
import numpy as np
from PIL import Image


def patch(img, boxes, radius=12):
    """Inpaint rectangular regions (x1,y1,x2,y2) using surrounding pixels."""
    if not boxes:
        return img
    mask = np.zeros(img.shape[:2], np.uint8)
    for x1, y1, x2, y2 in boxes:
        mask[y1:y2, x1:x2] = 255
    return cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)


def fill(img, boxes, color):
    for x1, y1, x2, y2 in boxes:
        img[y1:y2, x1:x2] = color
    return img


def knock_out_background(img, tol=26):
    """Flood fill from the border to turn a flat wall into pure white."""
    h, w = img.shape[:2]
    ff = img.copy()
    mask = np.zeros((h + 2, w + 2), np.uint8)
    seeds = [(2, 2), (w - 3, 2), (w // 2, 2), (2, h // 4), (w - 3, h // 4),
             (w // 4, 2), (3 * w // 4, 2)]
    for s in seeds:
        cv2.floodFill(ff, mask, s, (255, 255, 255),
                      (tol,) * 3, (tol,) * 3, cv2.FLOODFILL_FIXED_RANGE | 8)
    bg = mask[1:-1, 1:-1].astype(bool)
    bg = cv2.morphologyEx(bg.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    bg = cv2.GaussianBlur(bg.astype(np.float32), (0, 0), 3)
    out = img.astype(np.float32)
    white = np.full_like(out, 255.0)
    a = np.clip(bg, 0, 1)[..., None]
    return (out * (1 - a) + white * a).astype(np.uint8)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("image")
    p.add_argument("-o", "--out", default="prepped.png")
    p.add_argument("--crop", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"))
    p.add_argument("--inpaint", nargs=4, type=int, action="append", default=[],
                   metavar=("X1", "Y1", "X2", "Y2"), help="region to blend away (earbud, mole...)")
    p.add_argument("--erase", nargs=4, type=int, action="append", default=[],
                   metavar=("X1", "Y1", "X2", "Y2"), help="region to blank to background (phone, hand...)")
    p.add_argument("--tol", type=int, default=26)
    a = p.parse_args()

    img = cv2.cvtColor(np.array(Image.open(a.image).convert("RGB")), cv2.COLOR_RGB2BGR)
    img = patch(img, a.inpaint)
    img = fill(img, a.erase, (255, 255, 255))
    img = knock_out_background(img, a.tol)
    img = fill(img, a.erase, (255, 255, 255))
    if a.crop:
        x1, y1, x2, y2 = a.crop
        img = img[y1:y2, x1:x2]

    Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).save(a.out)
    print(f"-> {a.out} {img.shape[1]}x{img.shape[0]}")


if __name__ == "__main__":
    main()
