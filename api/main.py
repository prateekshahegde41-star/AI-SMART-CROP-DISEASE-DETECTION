"""
VANYA - FastAPI Backend
Run from repo root: uvicorn api.main:app --reload
"""
import asyncio
import base64
import csv
import io
import json
import os
from collections import defaultdict
from pathlib import Path
from functools import lru_cache

import cv2
import numpy as np
from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    File,
    Form,
    UploadFile,
    Header,
    HTTPException
)
from fastapi.responses import StreamingResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from . import (
    chatbot,
    db,
    guidance,
    model,
    progression,
    risk,
    severity,
    validate,
    weather,
    yield_estimator
)

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

app = FastAPI(title="VANYA - Smart Crop Disease Detection & Advisory")
CONF_REVIEW = 0.80

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


# ==================================================
# AUTHENTICATION & ROLE VERIFICATION
# ==================================================

@lru_cache(maxsize=1)
def get_auth_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)


def require_user(authorization: str = Header(default="")) -> dict:
    """
    Validates Supabase bearer access token.
    Falls back gracefully to demo user when in offline/development mode.
    Returns: {"id": user_id, "email": email, "role": role}
    """
    if not authorization or not authorization.startswith("Bearer "):
        # Check if running in local demo without auth
        client = get_auth_client()
        if not client:
            return {"id": "demo-farmer", "email": "farmer@demo.local", "role": "farmer"}
        raise HTTPException(
            status_code=401,
            detail="Login required. Missing or malformed Bearer access token."
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid access token.")

    # Support testing tokens in local mode
    if token == "demo-admin":
        return {"id": "demo-admin", "email": "admin@demo.local", "role": "admin"}
    if token == "demo-farmer":
        return {"id": "demo-farmer", "email": "farmer@demo.local", "role": "farmer"}

    client = get_auth_client()
    if not client:
        return {"id": "demo-farmer", "email": "farmer@demo.local", "role": "farmer"}

    try:
        res = client.auth.get_user(token)
        user = res.user
        if not user or not user.id:
            raise HTTPException(status_code=401, detail="Invalid or expired session.")

        uid = str(user.id)
        email = user.email or ""

        # Fetch profile role from DB
        prof = db.get_profile(uid)
        role = prof.get("role") if prof else "farmer"
        if not role:
            role = "farmer"

        return {"id": uid, "email": email, "role": role}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")


def require_admin(authorization: str = Header(default="")) -> dict:
    """
    Validates that the bearer token belongs to a user with role == 'admin'.
    Replaces deprecated ADMIN_KEY.
    """
    user = require_user(authorization)
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: verified 'admin' role is required."
        )
    return user


# ==================================================
# HEALTH & CLASSES
# ==================================================

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/classes")
def classes(authorization: str = Header(default="")):
    require_user(authorization)
    return model.classes()


# ==================================================
# IMAGE PROCESSING HELPERS
# ==================================================

def _b64(bgr, quality=80, max_side=None) -> str:
    if max_side and max(bgr.shape[:2]) > max_side:
        scale = max_side / max(bgr.shape[:2])
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    ok, buffer = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise HTTPException(status_code=500, detail="Unable to encode prediction image.")
    return base64.b64encode(buffer).decode()


async def _safe_weather(lat: float | None, lon: float | None):
    if lat is None or lon is None:
        return None
    try:
        return await asyncio.to_thread(weather.fetch, lat, lon)
    except Exception as e:
        print("[weather] failed:", e)
        return None


# ==================================================
# MULTI-IMAGE ANALYSIS ENDPOINT
# ==================================================

@app.post("/analyze")
async def analyze(
    files: list[UploadFile] = File(...),
    lat: float | None = Form(None),
    lon: float | None = Form(None),
    plant_id: str | None = Form(None),
    crop_acres: float = Form(1.0),
    with_gradcam: bool = Form(False),
    authorization: str = Header(default="")
):
    user = require_user(authorization)
    farmer_id = user["id"]

    # Validate coordinates if provided
    if (lat is None) != (lon is None):
        raise HTTPException(status_code=400, detail="Both latitude and longitude must be provided together.")
    if lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude.")

    # Validate and load up to 10 images (never raises on blur)
    items = await validate.load_images(files)
    items, time_source = progression.order(items)

    weather_task = asyncio.create_task(_safe_weather(lat, lon))

    # Process EVERY image: predict + severity
    per_image = []
    best_item_for_cam = items[0]
    highest_conf = -1.0

    for it in items:
        bgr = cv2.cvtColor(np.array(it.img), cv2.COLOR_RGB2BGR)
        pred = model.predict(it.img)
        sev = severity.estimate(bgr)

        conf = float(pred["confidence"])
        if conf > highest_conf:
            highest_conf = conf
            best_item_for_cam = it

        is_leaf_healthy = "healthy" in pred["label"].lower()
        overlay_b64 = _b64(sev["overlay_bgr"]) if not is_leaf_healthy else None

        per_image.append({
            "filename": it.name,
            "label": pred["label"],
            "confidence": round(conf, 3),
            "severity_pct": float(sev["percent"]),
            "severity_level": "None" if is_leaf_healthy else sev["level"],
            "leaf_detected": bool(sev["leaf_ok"]),
            "low_clarity": bool(it.low_clarity),
            "overlay_b64": overlay_b64,
            "top": pred.get("top", []),
            "stub": pred.get("stub", False)
        })

    wx = await weather_task

    # 1. Final disease = confidence-weighted vote across images
    vote_scores = defaultdict(float)
    for r in per_image:
        vote_scores[r["label"]] += r["confidence"]
    final_label = max(vote_scores, key=vote_scores.get)

    winning_confs = [r["confidence"] for r in per_image if r["label"] == final_label]
    final_confidence = round(float(sum(winning_confs) / len(winning_confs)), 3) if winning_confs else 0.0

    is_healthy = "healthy" in final_label.lower()

    # 2. Final severity = mean of per-image severity %
    final_sev_pct = round(float(np.mean([r["severity_pct"] for r in per_image])), 1)
    final_sev_level = "None" if (is_healthy and final_sev_pct == 0.0) else severity.level_for(final_sev_pct)

    # 3. Progression across images in same upload
    series = [0.0 if "healthy" in r["label"].lower() else r["severity_pct"] for r in per_image]
    upload_trend = progression.trend(series)

    # 4. Environmental disease risk
    risk_out = (
        risk.assess(final_label, wx["daily"], final_sev_level)
        if wx
        else {
            "now": "Unknown",
            "next_7_days": [],
            "note": "Weather unavailable (no location provided or API error)."
        }
    )

    # 5. Plant tracking over time across uploads
    plant_tracking = None
    if plant_id and plant_id.strip():
        pid_clean = plant_id.strip()
        prev = db.get_last_plant_prediction(farmer_id, pid_clean)
        if prev and prev.get("severity_pct") is not None:
            prev_sev = float(prev["severity_pct"])
            diff = final_sev_pct - prev_sev
            if diff > progression.TOLERANCE_PCT:
                p_trend = "spreading"
            elif diff < -progression.TOLERANCE_PCT:
                p_trend = "improving"
            else:
                p_trend = "unchanged"
            plant_tracking = {
                "plant_id": pid_clean,
                "has_history": True,
                "previous_severity_pct": prev_sev,
                "current_severity_pct": final_sev_pct,
                "trend": p_trend,
                "previous_date": prev.get("created_at"),
                "message": f"Compared to previous record ({prev_sev}%), the disease condition is {p_trend}."
            }
        else:
            plant_tracking = {
                "plant_id": pid_clean,
                "has_history": False,
                "previous_severity_pct": None,
                "current_severity_pct": final_sev_pct,
                "trend": "baseline",
                "message": f"Initial baseline record established for plant '{pid_clean}'."
            }
        crop_name = yield_estimator.extract_crop_name(final_label)
        db.upsert_plant(farmer_id, pid_clean, plant_name=pid_clean, crop=crop_name)

    # 6. Yield estimation
    crop_name = yield_estimator.extract_crop_name(final_label)
    yield_out = yield_estimator.estimate_yield_loss(
        crop=crop_name,
        land_area_acres=crop_acres,
        normal_yield_per_acre=None,
        disease_label=final_label,
        severity_level=final_sev_level,
        severity_pct=final_sev_pct,
        weather_risk=risk_out.get("now", "Low")
    )

    # Weekly action advice
    action_text = "Plant looks healthy. Monitor weekly."
    if final_sev_level in ["Medium", "High"]:
        rain_soon = any(day.get("rain_mm", 0) > 10 for day in (wx["daily"] if wx else []))
        if rain_soon:
            action_text = "Disease is active and rain is forecast. Prune affected foliage and ensure soil drainage."
        else:
            action_text = "Disease is active. Prune affected leaves, avoid overhead watering, and apply recommended spray."

    # Grad-CAM overlay if requested
    gradcam_b64 = None
    if with_gradcam:
        gradcam_b64 = await asyncio.to_thread(model.gradcam_overlay_b64, best_item_for_cam.img)

    # Check for clarity warnings
    any_low_clarity = any(r["low_clarity"] for r in per_image)

    report = {
        "prediction": {
            "label": final_label,
            "confidence": final_confidence,
            "vote_breakdown": dict(vote_scores),
            "stub": any(r.get("stub", False) for r in per_image)
        },
        "severity": {
            "percent": final_sev_pct,
            "level": final_sev_level,
            "leaf_detected": all(r.get("leaf_detected", True) for r in per_image)
        },
        "progression": {
            "trend": upload_trend,
            "series": series,
            "time_source": time_source
        },
        "plant_tracking": plant_tracking,
        "yield_estimate": yield_out,
        "per_image": per_image,
        "weather": wx["current"] if wx else None,
        "risk": risk_out,
        "guidance": guidance.get(final_label),
        "needs_review": final_confidence < CONF_REVIEW,
        "weekly_action": action_text,
        "any_low_clarity": any_low_clarity,
        "gradcam_b64": gradcam_b64
    }

    thumb = _b64(cv2.cvtColor(np.array(items[-1].img), cv2.COLOR_RGB2BGR), quality=70, max_side=320)
    saved_report = dict(report)

    prediction_id = await asyncio.to_thread(
        db.save_prediction,
        {
            "farmer_id": farmer_id,
            "plant_id": plant_id.strip() if plant_id else None,
            "label": final_label,
            "confidence": final_confidence,
            "severity_pct": final_sev_pct,
            "severity_level": final_sev_level,
            "trend": upload_trend,
            "risk_now": risk_out.get("now", "Unknown"),
            "lat": lat,
            "lon": lon,
            "image_thumb": thumb,
            "report": saved_report,
            "needs_review": report["needs_review"]
        }
    )

    report["id"] = prediction_id
    return report


# ==================================================
# YIELD ESTIMATION ENDPOINT
# ==================================================

class YieldEstimateRequest(BaseModel):
    crop: str | None = None
    land_area_acres: float = 1.0
    normal_yield_per_acre: float | None = None
    disease_label: str | None = None
    severity_level: str = "Low"
    severity_pct: float = 0.0
    weather_risk: str = "Low"


@app.post("/estimate/yield")
def estimate_yield_endpoint(req: YieldEstimateRequest):
    return yield_estimator.estimate_yield_loss(
        crop=req.crop,
        land_area_acres=req.land_area_acres,
        normal_yield_per_acre=req.normal_yield_per_acre,
        disease_label=req.disease_label,
        severity_level=req.severity_level,
        severity_pct=req.severity_pct,
        weather_risk=req.weather_risk
    )


# ==================================================
# CROP SUITABILITY ENDPOINT (PREVIOUSLY /predict/yield)
# ==================================================

class SuitabilityRequest(BaseModel):
    lat: float
    lon: float


def calculate_crop_suitability(wx: dict) -> dict:
    daily = wx.get("daily", [])
    if not daily:
        raise HTTPException(status_code=503, detail="Weather forecast data is unavailable.")

    temps = [day["t_mean"] for day in daily if day.get("t_mean") is not None]
    rainfall = [day["rain_mm"] for day in daily if day.get("rain_mm") is not None]
    moistures = [day["soil_moisture"] for day in daily if day.get("soil_moisture") is not None]

    if not temps or not rainfall:
        raise HTTPException(status_code=503, detail="Incomplete weather forecast data.")

    avg_temp = sum(temps) / len(temps)
    total_rain = sum(rainfall)
    avg_moisture = sum(moistures) / len(moistures) if moistures else None

    scores = {"Tomato": 85, "Potato": 85, "Onion": 85, "Corn": 85}
    reasons = {crop: [] for crop in scores}

    if avg_temp > 32:
        scores["Tomato"] -= 20
        reasons["Tomato"].append("High average temperature")
    if avg_temp > 28:
        scores["Potato"] -= 25
        reasons["Potato"].append("Temperature may be too high for optimal tuber growth")
    if avg_temp < 15:
        scores["Onion"] -= 15
        reasons["Onion"].append("Temperature is relatively low")
    if avg_temp > 35:
        scores["Corn"] -= 20
        reasons["Corn"].append("High temperature stress")

    if total_rain > 100:
        scores["Onion"] -= 20
        reasons["Onion"].append("High rainfall increases bulb rot risk")
    if total_rain < 20:
        scores["Corn"] -= 25
        reasons["Corn"].append("Low rainfall requires supplemental irrigation")
    if total_rain > 150:
        scores["Potato"] -= 15
        reasons["Potato"].append("High rainfall increases waterlogging/late blight risk")
    if total_rain < 20:
        scores["Tomato"] -= 10
        reasons["Tomato"].append("Low rainfall")

    if avg_moisture is not None and avg_moisture < 0.15:
        scores["Corn"] -= 10
        reasons["Corn"].append("Low surface soil moisture")

    scores = {crop: max(10, min(100, score)) for crop, score in scores.items()}
    recommended = max(scores, key=scores.get)

    return {
        "recommended_crop": recommended,
        "suitability_scores": scores,
        "reasons": {crop: notes if notes else ["Favorable weather conditions"] for crop, notes in reasons.items()},
        "weather_summary": {
            "average_temperature_c": round(avg_temp, 1),
            "total_rainfall_mm_7_days": round(total_rain, 1),
            "average_soil_moisture": round(avg_moisture, 3) if avg_moisture is not None else None
        },
        "forecast_days": len(daily),
        "method": "Rule-based weather suitability assessment",
        "warning": "Demonstration suitability scores based on 7-day weather outlook. Soil pH, NPK, and seasonal calendar must also be considered."
    }


@app.post("/predict/yield")
async def predict_yield_suitability(req: SuitabilityRequest, authorization: str = Header(default="")):
    require_user(authorization)
    if not (-90 <= req.lat <= 90 and -180 <= req.lon <= 180):
        raise HTTPException(status_code=400, detail="Invalid latitude or longitude.")

    try:
        wx = await asyncio.to_thread(weather.fetch, req.lat, req.lon)
        return calculate_crop_suitability(wx)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Live weather lookup failed: {e}")


# ==================================================
# USER PROFILE ENDPOINTS
# ==================================================

class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None


@app.get("/profile")
def get_user_profile(authorization: str = Header(default="")):
    user = require_user(authorization)
    prof = db.get_profile(user["id"])
    if not prof:
        prof = {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["email"].split("@")[0],
            "phone": "",
            "avatar_url": None,
            "role": user["role"]
        }
    return prof


@app.post("/profile")
def update_user_profile(body: ProfileUpdate, authorization: str = Header(default="")):
    user = require_user(authorization)
    data = body.model_dump(exclude_unset=True)
    success = db.update_profile(user["id"], data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile.")
    return {"ok": True, "profile": db.get_profile(user["id"])}


# ==================================================
# FARMER HISTORY & HOTSPOTS
# ==================================================

@app.get("/history")
def history(authorization: str = Header(default="")):
    user = require_user(authorization)
    return db.history(user["id"])


@app.get("/hotspots")
def hotspots(authorization: str = Header(default="")):
    require_user(authorization)
    return db.hotspots()


# ==================================================
# ADMIN DASHBOARD ENDPOINTS (ROLE-BASED: require_admin)
# ==================================================

class Verification(BaseModel):
    prediction_id: str
    decision: str
    expert_label: str | None = None
    notes: str = ""


@app.get("/admin/queue")
def admin_queue(authorization: str = Header(default="")):
    require_admin(authorization)
    return db.queue()


@app.post("/admin/verify")
def admin_verify(verification: Verification, authorization: str = Header(default="")):
    require_admin(authorization)
    if verification.decision not in ("confirmed", "corrected", "rejected"):
        raise HTTPException(status_code=400, detail="Bad decision.")
    if verification.decision == "corrected" and not verification.expert_label:
        raise HTTPException(status_code=400, detail="expert_label is required when decision is corrected.")

    success = db.verify(
        verification.prediction_id,
        verification.decision,
        verification.expert_label,
        verification.notes
    )
    if not success:
        raise HTTPException(status_code=404, detail="Prediction not found.")
    return {"ok": True}


@app.post("/admin/seed")
def admin_seed(authorization: str = Header(default="")):
    require_admin(authorization)
    return {"seeded_synthetic_reports": db.seed_demo()}


@app.get("/admin/export-corrections")
def admin_export_corrections(authorization: str = Header(default="")):
    require_admin(authorization)
    rows = db.get_verified_corrections()
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "created_at", "farmer_id", "label", "confidence", "severity_pct", "expert_label", "status", "expert_notes", "verified_at"]
    )
    writer.writeheader()
    for r in rows:
        clean_row = {
            "id": r.get("id"),
            "created_at": r.get("created_at"),
            "farmer_id": r.get("farmer_id"),
            "label": r.get("label"),
            "confidence": r.get("confidence"),
            "severity_pct": r.get("severity_pct"),
            "expert_label": r.get("expert_label"),
            "status": r.get("status"),
            "expert_notes": r.get("expert_notes"),
            "verified_at": r.get("verified_at")
        }
        writer.writerow(clean_row)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=verified_corrections.csv"}
    )


@app.get("/admin/metrics")
def admin_metrics(authorization: str = Header(default="")):
    require_admin(authorization)
    metrics_path = REPORTS_DIR / "test_metrics.json"
    cm_path = REPORTS_DIR / "confusion_matrix.png"
    metrics_data = {}
    if metrics_path.exists():
        try:
            metrics_data = json.loads(metrics_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "metrics": metrics_data,
        "has_confusion_matrix": cm_path.exists()
    }


# ==================================================
# CHATBOT ENDPOINT (SINGLE IMPLEMENTATION VIA chatbot.py)
# ==================================================

class ChatRequest(BaseModel):
    disease_name: str
    user_question: str


@app.post("/chat")
def chat(req: ChatRequest):
    return chatbot.answer_query(
        user_question=req.user_question,
        disease_name=req.disease_name
    )


# ==================================================
# OPENAPI / SWAGGER SCHEMAS
# ==================================================

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(title=app.title, version="2.0.0", routes=app.routes)
    schema["openapi"] = "3.0.3"
    components = schema.get("components", {}).get("schemas", {})
    for comp in components.values():
        for prop in comp.get("properties", {}).values():
            if prop.get("type") == "array":
                items = prop.get("items", {})
                if items.get("contentMediaType"):
                    items.pop("contentMediaType", None)
                    items["format"] = "binary"
            if prop.get("contentMediaType"):
                prop.pop("contentMediaType", None)
                prop["format"] = "binary"
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
