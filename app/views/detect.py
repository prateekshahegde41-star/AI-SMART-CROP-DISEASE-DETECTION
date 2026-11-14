"""
VANYA - Crop Disease Detection Page
Multi-image upload (up to 10), camera, plant tracking, per-image cards with overlays,
aggregate diagnosis, yield estimation, weather risk, and guidance.
"""
import base64
import sys
from pathlib import Path
import pandas as pd
import requests
import streamlit as st
try:
    from streamlit_js_eval import get_geolocation
except Exception:
    get_geolocation = None

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from .chatbot_widget import render_chatbot
except (ImportError, ValueError):
    from views.chatbot_widget import render_chatbot

try:
    from ..utils import API_URL, LEVEL_ICON, geocode
except (ImportError, ValueError):
    from utils import API_URL, LEVEL_ICON, geocode


def render():
    st.markdown('<div class="vanya-card-title">🌿 Smart Crop Disease Detection</div>', unsafe_allow_html=True)
    st.caption("Upload up to 10 leaf photographs or take a live picture to detect diseases, monitor progression, and estimate harvest impact.")

    user = st.session_state.get("user")
    token = st.session_state.get("access_token", "")

    # Upload section
    st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
    st.write("##### 📸 Upload or Capture Leaf Images")
    files = st.file_uploader(
        "Select up to 10 leaf images (clear or close-up)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Upload multiple angles or leaves for confidence-weighted aggregation"
    )
    cam = st.camera_input("...or take a live photo using camera")

    # Plant Tracking Field
    st.write("##### 🏷️ Plant Tracking (Optional)")
    plant_id = st.text_input(
        "Plant Identifier / Tag (e.g. Tomato-Bed-1, Plot-A-Plant-4)",
        value=st.session_state.get("selected_plant_id", ""),
        help="Tag this specific plant to track if infection is spreading, improving, or unchanged across future visits."
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Location Section
    st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
    st.write("##### 📍 Location for Weather & Micro-climate Risk")
    use_gps = st.checkbox("Detect my current farm GPS location", value=False)
    lat = lon = None

    if use_gps:
        if get_geolocation is None:
            st.warning("⚠️ GPS not available on this deployment. Please type your location below.")
        else:
            loc = get_geolocation()
            if loc and "coords" in loc:
                lat = loc["coords"]["latitude"]
                lon = loc["coords"]["longitude"]
                st.success(f"📍 GPS coordinates active: {lat:.4f}, {lon:.4f}")
            else:
                st.info("Waiting for GPS permission... or enter your village/town below.")
    else:
        place = st.text_input("Village / Town / District (e.g. Belagavi, Dharwad, Pune)")
        if place:
            with st.spinner("Finding location..."):
                g = geocode(place)
            if g:
                lat, lon = g
                st.success(f"📍 Found location: {lat:.4f}, {lon:.4f}")
            else:
                st.warning("Location not found. Analysis will continue without weather risk.")

    # Land Area for Yield Estimation
    st.write("##### 🌾 Land Area for Yield Impact Estimation")
    col_a, col_b = st.columns(2)
    with col_a:
        crop_acres = st.number_input("Cultivated Area (Acres)", min_value=0.1, max_value=500.0, value=1.0, step=0.5)
    with col_b:
        st.caption("Standard normal yield benchmarks per acre will be applied automatically based on the detected crop.")

    st.markdown('</div>', unsafe_allow_html=True)

    # Analyze Button
    if st.button("🔍 Analyze Crop Health", type="primary", use_container_width=True):
        uploads = []
        if files:
            for f in files:
                uploads.append((f.name, f.getvalue(), f.type))
        if cam:
            uploads.append(("camera_shot.jpg", cam.getvalue(), "image/jpeg"))

        if not uploads:
            st.error("Please upload or capture at least one leaf photo to proceed.")
            st.stop()

        if len(uploads) > 10:
            st.warning("A maximum of 10 images is permitted. The first 10 will be analyzed.")
            uploads = uploads[:10]

        form_data = {
            "crop_acres": str(crop_acres)
        }
        if plant_id.strip():
            form_data["plant_id"] = plant_id.strip()
        if lat is not None and lon is not None:
            form_data["lat"] = str(lat)
            form_data["lon"] = str(lon)

        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Reset any previous report
        st.session_state.pop("report", None)
        st.session_state.pop("chat_history", None)

        try:
            with st.spinner("Processing leaves, segmenting lesions, and querying micro-climate forecast..."):
                file_tuples = [("files", (name, data, mime)) for name, data, mime in uploads]
                r = requests.post(
                    f"{API_URL}/analyze",
                    data=form_data,
                    files=file_tuples,
                    headers=headers,
                    timeout=120
                )

            if not r.ok:
                st.error(f"Analysis failed ({r.status_code}): {r.text}")
                st.stop()

            st.session_state["report"] = r.json()
            st.session_state["selected_plant_id"] = plant_id.strip()
            st.rerun()

        except Exception as e:
            st.error(f"Cannot connect to the Agri-AI service: {e}")

    # ==================================================
    # RENDER ANALYSIS REPORT
    # ==================================================
    rep = st.session_state.get("report")
    if rep:
        st.divider()
        p = rep.get("prediction", {})
        s = rep.get("severity", {})
        pr = rep.get("progression", {})
        rk = rep.get("risk", {})
        pt = rep.get("plant_tracking")
        y_est = rep.get("yield_estimate", {})
        g = rep.get("guidance", {})
        per_image = rep.get("per_image", [])

        disease_label = p.get("label", "Unknown")
        disease_readable = disease_label.replace("___", " - ").replace("_", " ")
        is_healthy = "healthy" in disease_label.lower()

        # Clarity notice if low clarity was detected
        if rep.get("any_low_clarity"):
            st.info("ℹ️ Note: One or more photos had slight blur or low clarity, but analysis was completed using enhanced edge detection.")

        if p.get("stub"):
            st.warning("⚠️ Inference weights not loaded on backend — running in demonstration STUB mode.")

        # --- 1. AGGREGATE SUMMARY CARD ---
        st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="vanya-card-title">📋 Consolidated Diagnosis ({len(per_image)} image{"s" if len(per_image)>1 else ""})</div>', unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Disease", disease_readable)
        m2.metric("Confidence", f"{p.get('confidence', 0.0) * 100:.1f}%")

        sev_pct = s.get("percent", 0.0)
        sev_lvl = s.get("level", "None")
        m3.metric("Severity", f"{sev_pct}% ({sev_lvl})")

        # Trend badge
        trend_label = pr.get("trend", "single image").capitalize()
        m4.metric("Image Trend", trend_label)

        # Confidence progress bar
        st.progress(float(p.get("confidence", 0.0)), text=f"Aggregate Model Confidence: {p.get('confidence', 0.0)*100:.1f}%")

        # Plant Tracking Alert
        if pt:
            st.markdown("---")
            pt_trend = pt.get("trend")
            trend_badge = "🔴 SPREADING" if pt_trend == "spreading" else "🟢 IMPROVING" if pt_trend == "improving" else "🟡 UNCHANGED" if pt_trend == "unchanged" else "🔵 INITIAL BASELINE"
            st.write(f"**Plant Tracking ({pt.get('plant_id')}):** {trend_badge}")
            st.caption(pt.get("message"))

        # Weekly Action alert
        if rep.get("weekly_action"):
            st.info(f"📅 **Recommended Action:** {rep['weekly_action']}")

        st.markdown('</div>', unsafe_allow_html=True)

        # --- 2. PER-IMAGE CARDS WITH OVERLAYS ---
        st.write("#### 🌿 Individual Image Results & Lesion Segmentation")
        st.caption("Inspect segmented infection regions (red overlay) and leaf contour (green outline) for every uploaded photograph.")

        cols_per_row = 2 if len(per_image) > 1 else 1
        for idx in range(0, len(per_image), cols_per_row):
            row_cols = st.columns(cols_per_row)
            for c_idx in range(cols_per_row):
                if idx + c_idx < len(per_image):
                    item = per_image[idx + c_idx]
                    with row_cols[c_idx]:
                        st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
                        st.write(f"**Image #{idx + c_idx + 1}:** `{item.get('filename')}`")

                        # Low clarity warning badge
                        if item.get("low_clarity"):
                            st.markdown('<span class="badge badge-warning">⚠️ Low Clarity</span>', unsafe_allow_html=True)

                        # Overlay image
                        if item.get("overlay_b64"):
                            st.image(
                                base64.b64decode(item["overlay_b64"]),
                                caption="Lesions (Red) / Leaf Outline (Green)",
                                use_container_width=True
                            )
                        else:
                            st.info("No infected lesion mask (leaf classified healthy).")

                        st.write(f"**Prediction:** {item.get('label', '').replace('___', ' - ').replace('_', ' ')}")
                        st.write(f"**Confidence:** {item.get('confidence', 0.0)*100:.1f}% | **Severity:** {item.get('severity_pct')}%")

                        lvl = item.get("severity_level", "None")
                        badge_cls = "badge-high" if lvl == "High" else "badge-medium" if lvl == "Medium" else "badge-low"
                        st.markdown(f'<span class="badge {badge_cls}">{lvl} Severity</span>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

        # --- 3. YIELD ESTIMATION CARD ---
        if y_est:
            st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
            st.markdown('<div class="vanya-card-title">🌾 Estimated Harvest Impact & Yield Forecast</div>', unsafe_allow_html=True)

            y1, y2, y3 = st.columns(3)
            y1.metric(f"Normal Harvest ({y_est.get('land_area_acres')} ac)", f"{y_est.get('total_normal_yield')} {y_est.get('unit')}")
            loss_pct = y_est.get("estimated_loss_pct", 0.0)
            y2.metric("Estimated Yield Loss", f"{loss_pct}%", delta=f"-{y_est.get('estimated_loss_yield')} {y_est.get('unit')}", delta_color="inverse")
            y3.metric("Expected Remaining Yield", f"{y_est.get('expected_remaining_yield')} {y_est.get('unit')}")

            with st.expander("📐 View Yield Estimation Formula & Assumptions", expanded=False):
                st.write(f"**Formula:** `{y_est.get('formula')}`")
                st.write("**Key Agronomic Assumptions:**")
                for asm in y_est.get("assumptions", []):
                    st.write(f"- {asm}")
                st.caption(f"⚠️ *{y_est.get('disclaimer')}*")

            # Allow farmer to recalculate with custom parameters
            with st.expander("⚙️ Recalculate with Custom Farm Benchmark"):
                c_crop = st.text_input("Crop", value=y_est.get("crop", "Crop"), key="custom_y_crop")
                c_area = st.number_input("Area (Acres)", value=float(y_est.get("land_area_acres", 1.0)), min_value=0.1, key="custom_y_area")
                c_norm = st.number_input("Normal Expected Yield per Acre (quintals)", value=float(y_est.get("normal_yield_per_acre", 100.0)), min_value=1.0, key="custom_y_norm")
                if st.button("Update Yield Estimate"):
                    try:
                        custom_res = requests.post(
                            f"{API_URL}/estimate/yield",
                            json={
                                "crop": c_crop,
                                "land_area_acres": c_area,
                                "normal_yield_per_acre": c_norm,
                                "disease_label": disease_label,
                                "severity_level": sev_lvl,
                                "severity_pct": sev_pct,
                                "weather_risk": rk.get("now", "Low")
                            },
                            timeout=10
                        )
                        if custom_res.ok:
                            st.session_state["report"]["yield_estimate"] = custom_res.json()
                            st.success("Yield forecast updated!")
                            st.rerun()
                    except Exception as ex:
                        st.error(f"Recalculation error: {ex}")

            st.markdown('</div>', unsafe_allow_html=True)

        # --- 4. ENVIRONMENTAL WEATHER RISK CARD ---
        st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
        st.markdown('<div class="vanya-card-title">🌦️ Environmental Risk & 7-Day Forecast</div>', unsafe_allow_html=True)

        w = rep.get("weather")
        if w and rk.get("next_7_days"):
            wc1, wc2, wc3, wc4, wc5 = st.columns(5)
            wc1.metric("Temp", f"{w.get('temp_c')}°C")
            wc2.metric("Humidity", f"{w.get('humidity')}%")
            wc3.metric("Rain", f"{w.get('rain_mm')} mm")
            wc4.metric("Wind", f"{w.get('wind_kmh')} km/h")
            wc5.metric("Soil Moisture", f"{w.get('soil_moisture')}")

            now_risk = rk.get("now", "Low")
            st.write(f"**Pathogen Spread Risk Today:** {LEVEL_ICON.get(now_risk, '⚪')} **{now_risk}**")

            dates = rk.get("dates", [f"Day {i+1}" for i in range(len(rk["next_7_days"]))])
            risk_df = pd.DataFrame({
                "Date": dates,
                "Risk Level": [f"{LEVEL_ICON.get(x, '⚪')} {x}" for x in rk["next_7_days"]]
            })
            st.dataframe(risk_df, hide_index=True, use_container_width=True)
            st.caption(rk.get("note", ""))
        else:
            st.info(rk.get("note", "Weather information unavailable for this location."))

        st.markdown('</div>', unsafe_allow_html=True)

        # --- 5. GUIDANCE CARD ---
        st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
        st.markdown('<div class="vanya-card-title">📖 Agronomic Guidance & Management</div>', unsafe_allow_html=True)

        st.write(f"**Overview:** {g.get('about', '')}")
        st.write(f"**Causes / Pathogen:** {g.get('causes', '')}")
        st.write(f"**Symptoms:** {g.get('symptoms', '')}")
        st.write(f"**Prevention:** {g.get('prevention', '')}")
        st.write(f"**Treatment & Control:** {g.get('treatment', '')}")
        st.write(f"**How It Spreads:** {g.get('spread', '')}")

        source_url = g.get("source")
        if source_url and source_url.startswith("http"):
            st.markdown(f"**Authoritative Source:** [{source_url}]({source_url})")

        st.info(f"ℹ️ {g.get('disclaimer', '')}")

        # Optional Grad-CAM
        if rep.get("gradcam_b64"):
            st.markdown("---")
            st.write("**Model Attention Heatmap (Grad-CAM):**")
            st.image(base64.b64decode(rep["gradcam_b64"]), caption="Network Focus Areas", use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Render floating round chatbot
        render_chatbot()
