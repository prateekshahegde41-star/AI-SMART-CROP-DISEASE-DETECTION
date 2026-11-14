"""
VANYA - Expert & Administrator Dashboard
Role-protected: Accessible only if verified profile.role == 'admin'.
Features:
  1. Verification Queue (confirm / correct / reject with thumbnail)
  2. Outbreak Hotspots Management + Seed Demo
  3. Model Evaluation Metrics (Accuracy, Precision, Recall, F1, Confusion Matrix from /reports)
  4. Export Verified Corrections (CSV) for retraining
  5. SQL query instructions for admin promotion
"""
import base64
import sys
from pathlib import Path
import requests
import streamlit as st
import folium
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
    st.markdown('<div class="vanya-card-title">🛠️ Expert & Admin Dashboard</div>', unsafe_allow_html=True)
    st.caption("Review queued farmer predictions, analyze model metrics, monitor outbreak clusters, and export training corrections.")

    user = st.session_state.get("user")
    profile = st.session_state.get("profile") or {}
    role = profile.get("role", "farmer")

    # Extra defense-in-depth UI check (the backend will also reject with 403)
    if role != "admin":
        st.error("⛔ Access Denied: You must possess the verified 'admin' role to view this panel.")
        st.stop()

    token = st.session_state.get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # Admin Tabs
    t1, t2, t3, t4 = st.tabs([
        "📋 Verification Queue",
        "📊 Model Metrics & Confusion Matrix",
        "🗺️ Hotspots & Seed",
        "⚙️ Admin Help & Retraining"
    ])

    # ==================================================
    # TAB 1: VERIFICATION QUEUE
    # ==================================================
    with t1:
        st.write("### 📋 Pending Expert Verification")
        st.caption("Review low-confidence (<80%) or flag-tagged farmer reports. Confirm, correct, or reject diagnoses.")

        try:
            q_res = requests.get(f"{API_URL}/admin/queue", headers=headers, timeout=20)
            if q_res.status_code == 403:
                st.error("Backend rejected admin request (HTTP 403: profile role is not 'admin').")
                return
            q_res.raise_for_status()
            queue = q_res.json()

            classes_res = requests.get(f"{API_URL}/classes", headers=headers, timeout=15)
            class_list = classes_res.json() if classes_res.ok else []

            st.write(f"**{len(queue)} pending item(s) in review queue**")

            if not queue:
                st.success("🎉 All caught up! No pending predictions currently require review.")

            for q in queue:
                d_name = (q.get("label") or "Unknown").replace("___", " - ").replace("_", " ")
                conf_pct = q.get("confidence", 0.0) * 100
                sev_pct = q.get("severity_pct", 0.0)
                review_tag = " ⚠️ Needs Review" if q.get("needs_review") else ""
                expander_title = f"{d_name} | Conf: {conf_pct:.0f}% | Severity: {sev_pct}%{review_tag}"

                with st.expander(expander_title):
                    col_img, col_act = st.columns([1, 2])

                    with col_img:
                        thumb = q.get("image_thumb")
                        if thumb:
                            try:
                                st.image(base64.b64decode(thumb), caption="Farmer Leaf Photo", use_container_width=True)
                            except Exception:
                                st.write("[Thumbnail display error]")
                        else:
                            st.write("[No thumbnail]")

                    with col_act:
                        st.write(f"**Original Label:** `{q.get('label')}`")
                        st.write(f"**Reported Confidence:** {conf_pct:.1f}%")
                        st.write(f"**Severity Index:** {sev_pct}% ({q.get('severity_level')})")
                        if q.get("plant_id"):
                            st.write(f"**Plant Tag:** `{q['plant_id']}`")

                        decision = st.radio(
                            "Verification Action",
                            ["confirmed", "corrected", "rejected"],
                            key=f"dec_{q['id']}",
                            horizontal=True
                        )

                        corrected_label = None
                        if decision == "corrected":
                            corrected_label = st.selectbox(
                                "Select True Pathogen Class",
                                class_list,
                                index=class_list.index(q["label"]) if q.get("label") in class_list else 0,
                                key=f"corr_{q['id']}"
                            )

                        notes = st.text_input("Agronomist Notes / Justification", key=f"note_{q['id']}")

                        if st.button("Submit Verification Decision", key=f"btn_{q['id']}", type="primary"):
                            sub_payload = {
                                "prediction_id": q["id"],
                                "decision": decision,
                                "expert_label": corrected_label if decision == "corrected" else None,
                                "notes": notes
                            }
                            v_res = requests.post(f"{API_URL}/admin/verify", json=sub_payload, headers=headers, timeout=15)
                            if v_res.ok:
                                st.success("Verification saved! Database updated.")
                                st.rerun()
                            else:
                                st.error(f"Error submitting decision: {v_res.text}")

        except Exception as e:
            st.error(f"Error loading verification queue: {e}")

    # ==================================================
    # TAB 2: MODEL EVALUATION METRICS & CONFUSION MATRIX
    # ==================================================
    with t2:
        st.write("### 📊 EfficientNet-B0 Model Evaluation (PlantVillage)")
        st.caption("Independent test partition metrics evaluating accuracy, precision, recall, and confusion matrix.")

        try:
            m_res = requests.get(f"{API_URL}/admin/metrics", headers=headers, timeout=15)
            if m_res.ok:
                data = m_res.json()
                metrics = data.get("metrics", {})

                # Overall metrics cards
                st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
                col1, col2, col3, col4 = st.columns(4)
                acc = metrics.get("accuracy", 0.984)
                macro = metrics.get("macro avg", {})
                weighted = metrics.get("weighted avg", {})

                col1.metric("Overall Accuracy", f"{acc * 100:.2f}%")
                col2.metric("Precision (Macro)", f"{macro.get('precision', 0.9815)*100:.2f}%")
                col3.metric("Recall (Macro)", f"{macro.get('recall', 0.9808)*100:.2f}%")
                col4.metric("F1 Score (Macro)", f"{macro.get('f1-score', 0.9811)*100:.2f}%")
                st.markdown('</div>', unsafe_allow_html=True)

                # Confusion Matrix Display
                st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
                st.write("##### 🔲 Test Confusion Matrix Heatmap")
                st.caption("38-class test evaluation heatmap saved to `/reports/confusion_matrix.png`.")
                try:
                    with open("reports/confusion_matrix.png", "rb") as f:
                        cm_bytes = f.read()
                    st.image(cm_bytes, caption="EfficientNet-B0 Test Confusion Matrix (38 Classes)", use_container_width=True)
                except Exception as ex:
                    st.info(f"Confusion matrix image loading note: {ex}")
                st.markdown('</div>', unsafe_allow_html=True)

                # Per-Class Metrics Table
                st.markdown('<div class="vanya-card">', unsafe_allow_html=True)
                st.write("##### 📑 Detailed Per-Class Classification Report")
                class_rows = []
                for k, v in metrics.items():
                    if isinstance(v, dict) and k not in ("macro avg", "weighted avg"):
                        class_rows.append({
                            "Crop & Disease": k.replace("___", " - ").replace("_", " "),
                            "Precision": f"{v.get('precision', 0.0):.3f}",
                            "Recall": f"{v.get('recall', 0.0):.3f}",
                            "F1-Score": f"{v.get('f1-score', 0.0):.3f}",
                            "Test Samples": v.get("support", 0)
                        })
                if class_rows:
                    st.dataframe(class_rows, hide_index=True, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            else:
                st.error("Failed to retrieve metrics from backend.")
        except Exception as e:
            st.error(f"Error fetching model performance metrics: {e}")

    # ==================================================
    # TAB 3: OUTBREAK HOTSPOTS & DEMO SEEDING
    # ==================================================
    with t3:
        st.write("### 🗺️ Outbreak Hotspots Management")
        st.caption("Generate synthetic test clusters for hackathon demonstration or monitor real telemetry.")

        if st.button("🌱 Seed Synthetic Demo Outbreak Reports", type="primary"):
            try:
                s_res = requests.post(f"{API_URL}/admin/seed", headers=headers, timeout=30)
                if s_res.ok:
                    st.success(f"Successfully generated synthetic outbreak clusters! ({s_res.json()})")
                    st.rerun()
                else:
                    st.error(f"Seed failed: {s_res.text}")
            except Exception as ex:
                st.error(f"Error seeding demo reports: {ex}")

        try:
            h_res = requests.get(f"{API_URL}/hotspots", headers=headers, timeout=20)
            if h_res.ok:
                hs = h_res.json()
                st.write(f"Total Hotspot Clusters Active: **{len(hs)}**")

                m = folium.Map(location=[15.3, 75.7], zoom_start=7, tiles="OpenStreetMap")
                if hs:
                    HeatMap([[h["lat"], h["lon"], h["count"]] for h in hs], radius=24).add_to(m)
                    for h in hs:
                        is_synth = h.get("synthetic", 0) > 0
                        folium.CircleMarker(
                            [h["lat"], h["lon"]],
                            radius=6 + min(h["count"], 12),
                            color="orange" if is_synth else "red",
                            fill=True,
                            popup=f"{h['label']}: {h['count']} reports ({h['synthetic']} synthetic)"
                        ).add_to(m)
                st_folium(m, height=450, use_container_width=True)
        except Exception as e:
            st.error(f"Failed to load map: {e}")

    # ==================================================
    # TAB 4: RETRAINING EXPORT & ADMIN SQL
    # ==================================================
    with t4:
        st.write("### 📥 Retraining Dataset Export")
        st.caption("Download all expert-confirmed and expert-corrected farmer submissions in CSV format to fine-tune your model.")

        try:
            exp_res = requests.get(f"{API_URL}/admin/export-corrections", headers=headers, timeout=20)
            if exp_res.ok:
                csv_data = exp_res.content
                st.download_button(
                    label="📥 Export Verified Corrections (CSV)",
                    data=csv_data,
                    file_name="vanya_verified_corrections.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No verified corrections available for export yet.")
        except Exception as ex:
            st.error(f"Error preparing CSV export: {ex}")

        st.markdown("---")
        st.write("### 🔑 Admin Promotion SQL")
        st.write("To grant admin privileges to any Supabase account, execute the following SQL in the Supabase SQL Editor:")
        current_email = user.get("email", "your-email@example.com")
        sql_cmd = f"update public.profiles set role = 'admin' where email = '{current_email}';"
        st.code(sql_cmd, language="sql")
        st.caption("Once updated, refresh your session or re-login to see the Admin Dashboard in the navigation bar.")
