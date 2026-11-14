"""
VANYA - Farmer Prediction History Page
Displays past predictions as cards with filters (severity, status, search) instead of a raw dataframe.
"""
import base64
import sys
from pathlib import Path
import requests
import streamlit as st

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    from ..utils import API_URL, LEVEL_ICON
except (ImportError, ValueError):
    from utils import API_URL, LEVEL_ICON


def render():
    st.markdown('<div class="vanya-card-title">📜 My Prediction History</div>', unsafe_allow_html=True)
    st.caption("Review all previous leaf diagnoses, severity trends, and expert verification records.")

    token = st.session_state.get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        with st.spinner("Loading history records..."):
            r = requests.get(f"{API_URL}/history", headers=headers, timeout=15)

        if not r.ok:
            st.error(f"Unable to load history ({r.status_code}): {r.text}")
            return

        records = r.json()

        if not records:
            st.info("No prediction history recorded yet. Upload a leaf photo from the Detect page to get started!")
            return

        # Filtering controls
        st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
        fc1, fc2, fc3 = st.columns([1, 1, 1])
        with fc1:
            severity_filter = st.selectbox("Filter by Severity", ["All", "Low", "Medium", "High", "None"])
        with fc2:
            status_filter = st.selectbox("Filter by Verification", ["All", "pending", "confirmed", "corrected", "rejected"])
        with fc3:
            search_query = st.text_input("Search Disease or Plant ID", placeholder="e.g. Tomato or Bed-1")
        st.markdown('</div>', unsafe_allow_html=True)

        # Apply filters
        filtered = []
        for rec in records:
            if severity_filter != "All" and rec.get("severity_level") != severity_filter:
                continue
            if status_filter != "All" and rec.get("status") != status_filter:
                continue
            if search_query.strip():
                q = search_query.strip().lower()
                label_match = q in (rec.get("label") or "").lower()
                plant_match = q in (rec.get("plant_id") or "").lower()
                if not (label_match or plant_match):
                    continue
            filtered.append(rec)

        st.write(f"Showing **{len(filtered)}** of **{len(records)}** prediction report(s)")

        if not filtered:
            st.warning("No records match your selected filters.")
            return

        # Render cards
        for item in filtered:
            st.markdown('<div class="vanya-card">', unsafe_allow_html=True)

            c_thumb, c_info = st.columns([1, 3])

            with c_thumb:
                thumb_b64 = item.get("image_thumb")
                if thumb_b64:
                    try:
                        st.image(base64.b64decode(thumb_b64), use_container_width=True)
                    except Exception:
                        st.write("📷 [Image]")
                else:
                    st.write("📷 [No Preview]")

            with c_info:
                d_label = (item.get("label") or "Unknown").replace("___", " - ").replace("_", " ")
                conf = item.get("confidence", 0.0)
                sev_pct = item.get("severity_pct", 0.0)
                sev_lvl = item.get("severity_level", "None")
                status = item.get("status", "pending")
                plant_tag = item.get("plant_id")
                created = item.get("created_at", "")[:16].replace("T", " ")

                # Status pill
                badge_type = "badge-high" if sev_lvl == "High" else "badge-medium" if sev_lvl == "Medium" else "badge-low"
                v_badge = "badge-low" if status == "confirmed" else "badge-warning" if status == "corrected" else "badge-high" if status == "rejected" else "badge-medium"

                st.markdown(f"#### {d_label}")
                st.caption(f"📅 **Date:** {created} | 🏷️ **Plant Tag:** `{plant_tag or 'Untagged'}`")

                mcol1, mcol2, mcol3 = st.columns(3)
                mcol1.metric("Confidence", f"{conf*100:.1f}%")
                mcol2.metric("Severity", f"{sev_pct}% ({sev_lvl})")
                mcol3.metric("Trend", item.get("trend", "N/A").capitalize())

                st.markdown(f"""
                    <div style="margin-top: 8px;">
                        <span class="badge {badge_type}">{sev_lvl} Severity</span>
                        <span class="badge {v_badge}">Status: {status.upper()}</span>
                    </div>
                """, unsafe_allow_html=True)

                if item.get("expert_label"):
                    st.info(f"👨‍🌾 **Expert Correction:** {item['expert_label'].replace('___', ' - ').replace('_', ' ')}")

            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Failed to load records from backend: {e}")
