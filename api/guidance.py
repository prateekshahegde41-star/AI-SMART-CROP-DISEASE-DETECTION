"""Curated, cited disease guidance. Owner: Group 2 (Shravani)."""
import json
from pathlib import Path

GUIDANCE_FILE = Path(__file__).resolve().parent.parent / "data" / "guidance.json"

def _load_data():
    try:
        return json.loads(GUIDANCE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

DATA = _load_data()
DISCLAIMER = ("General information only - not a substitute for advice from an "
              "agricultural expert.")


def get(label: str) -> dict:
    # Reload in case file updated
    global DATA
    if not DATA:
        DATA = _load_data()
    entry = DATA.get(label) or DATA.get("_default", {})
    res = {**entry, "disclaimer": DISCLAIMER}
    if "management" not in res:
        res["management"] = f"{res.get('prevention', '')} {res.get('treatment', '')}".strip()
    return res
