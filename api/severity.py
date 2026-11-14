"""Leaf mask + lesion mask + severity %. Owner: Group 1 (Prateeksha).

Baseline = classic OpenCV (works with no training). Pipeline:
  1. leaf mask (GrabCut, fallback: saturation threshold)
  2. inside the leaf, anything that is NOT healthy-green = lesion
  3. severity % = lesion pixels / leaf pixels
Tune HEALTHY_* and LEVELS on real samples. A U-Net can replace estimate() later
with the same return shape.
"""
import cv2
import numpy as np

HEALTHY_H = (35, 85)     # OpenCV hue range for green (0-179)
HEALTHY_S_MIN = 40
HEALTHY_V_MIN = 40
LEVELS = [(10.0, "Low"), (30.0, "Medium")]   # <10 Low, <30 Medium, else High
MAX_SIDE = 512


def level_for(pct: float) -> str:
    for limit, name in LEVELS:
        if pct < limit:
            return name
    return "High"


def leaf_mask(bgr: np.ndarray) -> np.ndarray:
    h, w = bgr.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    rect = (int(w * .04), int(h * .04), int(w * .92), int(h * .92))
    try:
        cv2.grabCut(bgr, mask, rect, np.zeros((1, 65)), np.zeros((1, 65)), 3, cv2.GC_INIT_WITH_RECT)
        leaf = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    except cv2.error:
        leaf = np.zeros((h, w), np.uint8)
    if leaf.sum() / 255 < 0.10 * h * w:                      # GrabCut failed -> colour fallback
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        leaf = (hsv[..., 1] > 40).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    leaf = cv2.morphologyEx(leaf, cv2.MORPH_CLOSE, k)
    return cv2.morphologyEx(leaf, cv2.MORPH_OPEN, k)


def estimate(bgr: np.ndarray) -> dict:
    """bgr uint8 image -> {percent, level, overlay_bgr, leaf_ok}"""
    scale = MAX_SIDE / max(bgr.shape[:2])
    if scale < 1:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    leaf = leaf_mask(bgr)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    H, S, V = cv2.split(hsv)
    healthy = (H >= HEALTHY_H[0]) & (H <= HEALTHY_H[1]) & (S >= HEALTHY_S_MIN) & (V >= HEALTHY_V_MIN)
    lesion = ((leaf > 0) & ~healthy).astype(np.uint8) * 255
    lesion = cv2.morphologyEx(lesion, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    leaf_px = max(int((leaf > 0).sum()), 1)
    pct = round(100.0 * int((lesion > 0).sum()) / leaf_px, 1)

    overlay = bgr.copy()
    red = np.zeros_like(bgr); red[:] = (0, 0, 255)
    sel = lesion > 0
    overlay[sel] = cv2.addWeighted(bgr, 0.45, red, 0.55, 0)[sel]
    cnts, _ = cv2.findContours(leaf, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, cnts, -1, (0, 255, 0), 2)
    return {"percent": pct, "level": level_for(pct), "overlay_bgr": overlay,
            "leaf_ok": leaf_px > 0.10 * bgr.shape[0] * bgr.shape[1]}
