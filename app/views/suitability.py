"""
VANYA - Crop Suitability Advisory Page
(Formerly 3_Yield_Prediction.py)
Uses location and 7-day weather outlook to assess crop suitability.
"""
import sys
from pathlib import Path
import requests
import streamlit as st
import plotly.express as px
try:
    from streamlit_js_eval import get_geolocation
except Exception:
    get_geolocation = None

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from ..utils import API_URL, geocode
except (ImportError, ValueError):
    from utils import API_URL, geocode


def render():
    st.markdown('<div class="vanya-card-title">🌾 Regional Crop Suitability</div>', unsafe_allow_html=True)
    st.caption("Evaluate local agro-climatic conditions and weather suitability scores for major crops in your region.")

    token = st.session_state.get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
    st.write("##### 📍 Select Farm Location")
    use_gps = st.checkbox("Detect farm GPS location", value=False, key="suit_gps")
    lat = lon = None

    if use_gps:
        if get_geolocation is None:
            st.warning("⚠️ GPS not available on this deployment. Please type your location below.")
        else:
            loc = get_geolocation()
            if loc and "coords" in loc:
                lat = loc["coords"]["latitude"]
                lon = loc["coords"]["longitude"]
                st.success(f"GPS active: {lat:.4f}, {lon:.4f}")
            else:
                st.info("Waiting for GPS coordinates... or type a place name below.")
    else:
        place = st.text_input("Village / Town / District", placeholder="e.g. Mysuru, Karnataka, India", key="suit_place")
        if place:
            with st.spinner("Finding location..."):
                g = geocode(place)
            if g:
                lat, lon = g
                st.success(f"Found location: {lat:.4f}, {lon:.4f}")
            else:
                st.warning("Location not found.")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Evaluate Crop Suitability", type="primary", use_container_width=True):
        if lat is None or lon is None:
            st.error("Please supply a valid GPS or location address.")
            return

        try:
            with st.spinner("Analyzing regional weather, rainfall, and soil moisture patterns..."):
                r = requests.post(
                    f"{API_URL}/predict/yield",
                    json={"lat": lat, "lon": lon},
                    headers=headers,
                    timeout=25
                )

            if not r.ok:
                st.error(f"Suitability analysis failed ({r.status_code}): {r.text}")
                return

            res = r.json()
            st.session_state["suitability_result"] = res

        except Exception as e:
            st.error(f"Cannot connect to the backend: {e}")

    result = st.session_state.get("suitability_result")
    if result:
        st.divider()
        scores = result.get("suitability_scores", {})
        rec = result.get("recommended_crop", "")
        summary = result.get("weather_summary", {})
        reasons = result.get("reasons", {})

        st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="vanya-card-title">🏆 Top Recommendation: {rec}</div>', unsafe_allow_html=True)
        st.caption("Based on 7-day forecast temperatures, rainfall accumulation, and surface moisture levels.")

        # Weather overview metrics
        w1, w2, w3 = st.columns(3)
        w1.metric("Avg Temperature", f"{summary.get('average_temperature_c', 'N/A')} °C")
        w2.metric("Total 7-Day Rain", f"{summary.get('total_rainfall_mm_7_days', 'N/A')} mm")
        w3.metric("Soil Moisture", f"{summary.get('average_soil_moisture', 'N/A')}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Plotly chart of suitability scores
        st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
        st.write("##### 📊 Suitability Score Comparison")
        df_chart = [{"Crop": k, "Score": v} for k, v in scores.items()]
        fig = px.bar(
            df_chart,
            x="Crop",
            y="Score",
            text="Score",
            color="Score",
            color_continuous_scale="Greens",
            range_y=[0, 100],
            title="Crop Suitability Index (0 - 100)"
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=340)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Breakdown reasons
        st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
        st.write("##### 📝 Weather Suitability Notes")
        for crop, notes in reasons.items():
            st.write(f"**{crop} ({scores.get(crop)}/100):**")
            for note in notes:
                st.write(f"- {note}")
        st.caption(f"⚠️ *{result.get('warning')}*")
        st.markdown('</div>', unsafe_allow_html=True)
