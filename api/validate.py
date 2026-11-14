"""Image validation + loading. Owner: Group 1 (Prateeksha)."""
import io
import cv2
import numpy as np
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps

MAX_BYTES = 8 * 1024 * 1024
MAX_IMAGES = 10
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MIN_SIDE = 64

def check_image_quality(im: Image.Image) -> tuple[bool, str]:
    """
    Checks whether a leaf image has low sharpness/clarity using Laplacian variance.
    NEVER raises an exception.
    Returns (True, "Image quality is clear.") if clear.
    Returns (False, "Image appears blurry or low clarity.") if blurry.
    """
    try:
        image = np.array(im.convert("RGB"))
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if variance < 100:
            return False, "Low clarity (blurry image detected)."
        return True, "Image quality is clear."
    except Exception:
        return True, "Quality check bypassed."


@dataclass
class Item:
    name: str
    img: Image.Image            # RGB, EXIF-rotated
    taken_at: datetime | None   # from EXIF if present
    low_clarity: bool = False   # Warning flag for blurry/low clarity photo


def _exif_time(im: Image.Image):
    try:
        exif = im.getexif()
        raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)  # DateTimeOriginal / DateTime
        return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S") if raw else None
    except Exception:
        return None


async def load_images(files: list[UploadFile]) -> list[Item]:
    if not files:
        raise HTTPException(400, "Upload at least one leaf image.")
    if len(files) > MAX_IMAGES:
        raise HTTPException(400, f"At most {MAX_IMAGES} images allowed.")
    items = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(400, f"{f.filename}: larger than 8 MB.")
        if f.content_type not in ALLOWED:
            raise HTTPException(400, f"{f.filename}: only JPEG/PNG/WEBP allowed.")
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
        except Exception:
            raise HTTPException(400, f"{f.filename}: not a readable image.")
        taken = _exif_time(im)
        im = ImageOps.exif_transpose(im).convert("RGB")
        if min(im.size) < MIN_SIDE:
            raise HTTPException(400, f"{f.filename}: image too small.")

        # Check image quality - NEVER raises, sets low_clarity flag
        is_clear, _ = check_image_quality(im)
        low_clarity = not is_clear

        items.append(Item(f.filename or "image", im, taken, low_clarity=low_clarity))
    return items
