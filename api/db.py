"""Supabase access (service-role key stays here). Falls back to in-memory if not configured.
Owner: Group 2 (Shravani)."""
import os, random, uuid
from collections import defaultdict
from datetime import datetime, timezone

_MEM: list[dict] = []
_MEM_PLANTS: list[dict] = []
_MEM_PROFILES: list[dict] = []
_client_cache = {}


def _client():
    if "c" in _client_cache:
        return _client_cache["c"]
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
    c = None
    if url and key:
        from supabase import create_client
        c = create_client(url, key)
    _client_cache["c"] = c
    return c


def save_prediction(row: dict) -> str:
    c = _client()
    if c:
        return c.table("predictions").insert(row).execute().data[0]["id"]
    row = {
        **row,
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending"
    }
    _MEM.append(row)
    return row["id"]


def get_last_plant_prediction(farmer_id: str, plant_id: str) -> dict | None:
    c = _client()
    if c:
        try:
            res = (c.table("predictions")
                   .select("id,created_at,label,severity_pct,severity_level,trend")
                   .eq("farmer_id", farmer_id).eq("plant_id", plant_id)
                   .order("created_at", desc=True).limit(1).execute().data)
            return res[0] if res else None
        except Exception:
            return None
    matches = [r for r in _MEM if r.get("farmer_id") == farmer_id and r.get("plant_id") == plant_id]
    return matches[-1] if matches else None


def upsert_plant(farmer_id: str, plant_id: str, plant_name: str = "", crop: str = ""):
    c = _client()
    now = datetime.now(timezone.utc).isoformat()
    if c:
        try:
            c.table("plants").upsert({
                "id": plant_id,
                "farmer_id": farmer_id,
                "plant_name": plant_name or plant_id,
                "crop": crop,
                "updated_at": now
            }).execute()
        except Exception as e:
            print("[db] upsert plant error:", e)
    for p in _MEM_PLANTS:
        if p["id"] == plant_id and p.get("farmer_id") == farmer_id:
            p.update(plant_name=plant_name or plant_id, crop=crop, updated_at=now)
            return
    _MEM_PLANTS.append({
        "id": plant_id,
        "farmer_id": farmer_id,
        "plant_name": plant_name or plant_id,
        "crop": crop,
        "created_at": now,
        "updated_at": now
    })


def get_farmer_plants(farmer_id: str) -> list[dict]:
    c = _client()
    if c:
        try:
            return c.table("plants").select("*").eq("farmer_id", farmer_id).order("updated_at", desc=True).execute().data
        except Exception:
            pass
    return [p for p in _MEM_PLANTS if p.get("farmer_id") == farmer_id]


def history(farmer_id: str, limit: int = 100) -> list[dict]:
    cols = "id,created_at,label,confidence,severity_pct,severity_level,trend,risk_now,status,expert_label,plant_id,image_thumb"
    c = _client()
    if c:
        try:
            return (c.table("predictions").select(cols).eq("farmer_id", farmer_id)
                    .order("created_at", desc=True).limit(limit).execute().data)
        except Exception:
            pass
    keys = cols.split(",")
    rows = [r for r in _MEM if r.get("farmer_id") == farmer_id]
    return [{k: r.get(k) for k in keys} for r in reversed(rows)][:limit]


def queue(limit: int = 50) -> list[dict]:
    c = _client()
    if c:
        rows = (c.table("predictions").select("*").eq("status", "pending")
                .eq("is_synthetic", False).order("confidence").limit(limit).execute().data)
    else:
        rows = [r for r in _MEM if r.get("status") == "pending" and not r.get("is_synthetic")]
    rows = sorted(rows, key=lambda r: (not r.get("needs_review"), r.get("confidence") or 0))
    for r in rows:
        r.pop("report", None)
    return rows[:limit]


def verify(pid: str, decision: str, expert_label: str | None, notes: str) -> bool:
    c = _client()
    now = datetime.now(timezone.utc).isoformat()
    if c:
        cur = c.table("predictions").select("label").eq("id", pid).execute().data
        if not cur:
            return False
        final = expert_label if decision == "corrected" else cur[0]["label"]
        c.table("predictions").update({"status": decision, "expert_label": final,
                                       "expert_notes": notes, "verified_at": now}).eq("id", pid).execute()
        c.table("verifications").insert({"prediction_id": pid, "decision": decision,
                                         "original_label": cur[0]["label"], "expert_label": final,
                                         "notes": notes}).execute()
        return True
    for r in _MEM:
        if r["id"] == pid:
            r.update(status=decision, expert_notes=notes, verified_at=now,
                     expert_label=expert_label if decision == "corrected" else r["label"])
            return True
    return False


def get_verified_corrections() -> list[dict]:
    c = _client()
    if c:
        try:
            return c.table("predictions").select(
                "id,created_at,farmer_id,label,confidence,severity_pct,expert_label,status,expert_notes,verified_at"
            ).in_("status", ["confirmed", "corrected"]).order("verified_at", desc=True).execute().data
        except Exception:
            pass
    return [r for r in _MEM if r.get("status") in ("confirmed", "corrected")]


def hotspots(grid: float = 0.1) -> list[dict]:
    c = _client()
    if c:
        rows = c.table("predictions").select("lat,lon,label,is_synthetic").not_.is_("lat", "null").limit(5000).execute().data
    else:
        rows = [r for r in _MEM if r.get("lat") is not None]
    agg = defaultdict(lambda: {"count": 0, "synthetic": 0})
    for r in rows:
        if "healthy" in (r.get("label") or "").lower():
            continue
        k = (round(r["lat"] / grid) * grid, round(r["lon"] / grid) * grid, r["label"])
        agg[k]["count"] += 1
        agg[k]["synthetic"] += 1 if r.get("is_synthetic") else 0
    return [{"lat": round(k[0], 3), "lon": round(k[1], 3), "label": k[2], **v} for k, v in agg.items()]


def get_profile(user_id: str) -> dict | None:
    c = _client()
    if c:
        try:
            res = c.table("profiles").select("*").eq("id", user_id).execute().data
            if res:
                return res[0]
        except Exception as e:
            print("[db] get_profile error:", e)
    for p in _MEM_PROFILES:
        if p["id"] == user_id:
            return p
    return None


def update_profile(user_id: str, data: dict) -> bool:
    c = _client()
    clean_data = {k: v for k, v in data.items() if k in ("full_name", "phone", "avatar_url", "role", "email")}
    if c:
        try:
            c.table("profiles").upsert({"id": user_id, **clean_data}).execute()
            return True
        except Exception as e:
            print("[db] update_profile error:", e)
            return False
    for p in _MEM_PROFILES:
        if p["id"] == user_id:
            p.update(clean_data)
            return True
    _MEM_PROFILES.append({"id": user_id, "role": "farmer", **clean_data})
    return True


def seed_demo() -> int:
    """Synthetic outbreak reports for the demo map. Always flagged is_synthetic=True."""
    places = [("Tomato___Late_blight", 15.85, 74.50), ("Tomato___Late_blight", 15.46, 75.01),
              ("Tomato___Late_blight", 15.36, 75.12), ("Potato___Early_blight", 12.30, 76.64),
              ("Potato___Early_blight", 12.52, 76.90), ("Corn_(maize)___Common_rust_", 16.21, 77.35),
              ("Corn_(maize)___Common_rust_", 16.83, 75.71)]
    n = 0
    for label, lat, lon in places:
        for _ in range(random.randint(6, 14)):
            save_prediction({"farmer_id": "synthetic", "label": label, "confidence": 0.9,
                             "severity_pct": round(random.uniform(5, 40), 1), "severity_level": "Medium",
                             "trend": "spreading", "risk_now": "High",
                             "lat": lat + random.uniform(-.15, .15), "lon": lon + random.uniform(-.15, .15),
                             "needs_review": False, "is_synthetic": True})
            n += 1
    return n
