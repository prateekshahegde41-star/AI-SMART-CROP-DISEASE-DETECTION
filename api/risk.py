"""Rule-based environmental risk (today + next 7 days). Owner: Group 2 (Shravani)."""
import json
from pathlib import Path

RULES = json.loads((Path(__file__).resolve().parent.parent / "data" / "risk_rules.json").read_text())
ORDER = ["Low", "Medium", "High"]


def _rule_for(label: str) -> dict:
    key = label.lower().replace("___", "_").replace(" ", "_")
    for name, rule in RULES.items():
        if name not in ("default", "_note") and name in key:
            return rule
    return RULES["default"]


def _day_level(rule: dict, day: dict) -> str:
    checks = []
    lo, hi = rule["temp_c"]
    checks.append(lo <= day["t_mean"] <= hi)
    checks.append(day["humidity"] >= rule["humidity_min"])
    if "humidity_max" in rule:
        checks.append(day["humidity"] <= rule["humidity_max"])
    if "rain_mm_min" in rule:
        checks.append(day["rain_mm"] >= rule["rain_mm_min"])
    ratio = sum(checks) / len(checks)
    return "High" if ratio == 1 else "Medium" if ratio >= 0.66 else "Low"


def assess(label: str, daily: list[dict], severity_level: str) -> dict:
    if "healthy" in label.lower():
        return {"now": "Low", "next_7_days": ["Low"] * len(daily),
            "dates": [d["date"] for d in daily], "note": "Plant looks healthy."}
    rule = _rule_for(label)
    levels = [_day_level(rule, d) for d in daily]
    now = levels[0]
    if severity_level == "High" and now != "High":      # existing heavy infection raises concern
        now = ORDER[ORDER.index(now) + 1]
    return {"now": now, "next_7_days": levels, "dates": [d["date"] for d in daily],
            "note": "Indicative rule-of-thumb thresholds, not a forecast model."}
