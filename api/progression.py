"""Ordering by time + trend from severity series. Owner: Group 1 (Prateeksha)."""
TOLERANCE_PCT = 3.0   # change smaller than this = 'unchanged'


def order(items):
    """Sort by EXIF time if ALL images have it, else keep upload order (oldest first)."""
    if len(items) > 1 and all(i.taken_at for i in items):
        return sorted(items, key=lambda i: i.taken_at), "exif"
    return items, "upload_order"


def trend(series: list[float]) -> str:
    if len(series) < 2:
        return "single image"
    d = series[-1] - series[0]
    if d > TOLERANCE_PCT:
        return "spreading"
    if d < -TOLERANCE_PCT:
        return "improving"
    return "unchanged"
