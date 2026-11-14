"""
VANYA - Regional Disease Outbreak Map (Farmer Visible)
Visualizes disease clusters and infection hotspots across agricultural zones.
Clearly labels synthetic demo reports vs real farmer reports.
"""
import sys
from pathlib import Path
import folium
import requests
import streamlit as st
from folium.plugins import HeatMap
from streamlit_folium import st_folium

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from ..utils import API_URL
except (ImportError, ValueError):
    from utils import API_URL


def render():
    st.markdown('<div class="vanya-card-title">🗺️ Regional Disease Outbreak Map</div>', unsafe_allow_html=True)
    st.caption("Track disease clusters reported across farming communities to anticipate transmission risks in your district.")

    token = st.session_state.get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        with st.spinner("Loading hotspot telemetry..."):
            r = requests.get(f"{API_URL}/hotspots", headers=headers, timeout=20)

        if not r.ok:
            st.error(f"Unable to load hotspot telemetry ({r.status_code}): {r.text}")
            return

        hs = r.json()

        st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
        # Stats summary
        total_clusters = len(hs)
        total_reports = sum(h.get("count", 0) for h in hs)
        synth_reports = sum(h.get("synthetic", 0) for h in hs)
        real_reports = total_reports - synth_reports

        c1, c2, c3 = st.columns(3)
        c1.metric("Active Hotspot Clusters", str(total_clusters))
        c2.metric("Total Incident Reports", str(total_reports))
        c3.metric("Verified / Real Reports", f"{real_reports} (Synthetic: {synth_reports})")
        st.markdown('</div>', unsafe_allow_html=True)

        # Center map on Karnataka / South India default or first hotspot
        center_lat, center_lon = 15.35, 75.50
        if hs:
            center_lat, center_lon = hs[0]["lat"], hs[0]["lon"]

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles="OpenStreetMap"
        )

        if hs:
            # Add HeatMap layer
            heat_data = [[h["lat"], h["lon"], h["count"]] for h in hs]
            HeatMap(heat_data, radius=24, blur=15, max_zoom=10).add_to(m)

            for h in hs:
                is_mostly_synthetic = h.get("synthetic", 0) > 0 and h.get("synthetic") == h.get("count")
                marker_color = "orange" if is_mostly_synthetic else "red"

                data_label = (
                    "⚠️ SYNTHETIC DEMO DATA"
                    if is_mostly_synthetic
                    else f"REAL FARMER REPORTS ({h['synthetic']} synthetic)"
                    if h.get("synthetic", 0) > 0
                    else "REAL FIELD REPORT"
                )

                d_name = h['label'].replace('___', ' - ').replace('_', ' ')
                popup_html = f"""
                    <div style='font-family: sans-serif; font-size: 12px; width: 220px;'>
                        <b>Disease:</b> {d_name}<br>
                        <b>Total Reports:</b> {h['count']}<br>
                        <b>Status:</b> {data_label}<br>
                        <b>Location:</b> {h['lat']:.3f}, {h['lon']:.3f}
                    </div>
                """

                folium.CircleMarker(
                    [h["lat"], h["lon"]],
                    radius=6 + min(h["count"], 12),
                    color=marker_color,
                    fill=True,
                    fill_opacity=0.75,
                    popup=folium.Popup(popup_html, max_width=250)
                ).add_to(m)

            st_folium(m, height=480, use_container_width=True)
        else:
            st.info("No active disease outbreak clusters detected in the database.")

        st.caption("ℹ️ *Map indicates reported agricultural disease incidents. Simulated demo clusters are tagged as SYNTHETIC DEMO DATA in marker tooltips.*")

    except Exception as e:
        st.error(f"Failed to render outbreak telemetry: {e}")
